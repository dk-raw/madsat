import numpy as np
from scipy.stats import pearsonr
import csv
import requests
from datetime import datetime, timezone
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import json 
import twitter
import pandas as pd
import logging
import os
import pymongo
from bson.objectid import ObjectId

logger = logging.getLogger("liggma")

try:
     client = pymongo.MongoClient("localhost",27017)
     db = client["madsat"]
     global eventsCollection
     eventsCollection = db["events"]
except Exception as e:
     logger.critical(e)
     exit(1)

def updateEvent(eventId, iaga, event_year, event_month, event_day, event_datetime_utc, tweetId, obs_name, eventTimestamp):
    logger.info(f"Observatory {iaga} has updated data for event {eventId}.\nGrabbing data...")
    #get data, process data, reply to tweet, change status to True
    url = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetData&format=COVJSON&testObsys=0&observatoryIagaCode={iaga}&samplesPerDay=minute&publicationState=Best%20available&dataStartDate={event_year}-{event_month}-{event_day}&dataDuration=1&orientation=XYZS"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            root = json.loads(res.text)
            raw_y_values = root["ranges"]["Y"]["values"]
            raw_datetimes = root["domain"]["axes"]["t"]["values"]
            y_values = []
            datetimes = []
            for raw_y_value in raw_y_values:
                if raw_y_value is not None:
                    y_values.append(float(raw_y_value))
                else:
                    y_values.append(0)
            for raw_datetime in raw_datetimes:
                datetimes.append(raw_datetime)

            df_data = {"time": datetimes, "value": y_values}
            df = pd.DataFrame(df_data)
            df["time"] = pd.to_datetime(df["time"], utc=True)
            center_time = pd.to_datetime(eventTimestamp, unit='s', utc=True)
            time_window = pd.Timedelta(hours=2)
            start_time = center_time - time_window / 2
            end_time = center_time + time_window / 2
            filtered_df = df[(df["time"] >= start_time) & (df["time"] <= end_time)]
            filtered_df.set_index("time", inplace=True)
            processed = anomalies(filtered_df, eventId)
            graph(processed, eventId, iaga, obs_name, event_year, event_month, event_day, center_time)
            image_id = twitter.upload(f"temp/image-{eventId}.png")
            twitter.reply(f"{iaga} observatory data for this event at {event_datetime_utc} UTC",tweetId, [str(image_id)])
            resolveEvent(eventId)
            logger.info(f"Event {eventId} resolved.")
        else:
            logger.error(f"Error fetching {iaga} observatory data with status code {res.status_code}.")
    except Exception as e:
        logger.error(e)

def checkEvents():
    logger.info("Updating events...")
    try:
        events = eventsCollection.find({"resolved": False})
        logger.info(f"{eventsCollection.count_documents({"resolved": False})} unresolved event(s) loaded successfully.")
        for event in events:
            current_time_utc = datetime.now(timezone.utc).timestamp()
            # if current_time_utc - event["timestamp"] > 172800: # 2 days
            #     twitter.reply(f"Event {event["_id"]} expired as there will be no data available.", event["tweetID"])
            #     resolveEvent(event["_id"])
            event_datetime_utc = datetime.fromtimestamp(event["timestamp"], tz=timezone.utc)
            event_day = event_datetime_utc.day
            event_month = event_datetime_utc.month
            event_year = event_datetime_utc.year
            #Get data directory in JSON to see when was the last update
            url = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetDataDirectory&observatoryIagaCodeList={event["obsIAGA"]}&samplesPerDay=minute&dataStartDate={event_year}-{event_month}-{event_day}&dataDuration=1&publicationState=adj-or-rep&options=showgaps&format=json"
            res = requests.get(url)
            # print(url)
            if res.status_code==200:
                root = json.loads(res.text)
                if root["data"][0]["embargo_applied"] == "true":
                    logger.info(f"Data embargo applied for observatory {event["obsIAGA"]}.")
                    resolveEvent(event["_id"])
                elif root["data"][0]["publication_state"] == "none":
                    logger.info(f"No data for {event["obsIAGA"]} at {event_year}-{event_month}-{event_day}.")
                else:
                    #Case where there as some data
                    if root["data"][0]["days"][0]["gap_start_times"]: #if there is a gap in the data
                        date_string=root["data"][0]["days"][0]["gap_start_times"][-1]
                        last_obs_update_utc=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
                        if last_obs_update_utc - event["timestamp"] > 600: #10 minute margin
                            updateEvent(event["_id"], event["obsIAGA"], event_year, event_month, event_day, event_datetime_utc, event["tweetID"], event["obsName"], event["timestamp"])
                        else:
                            logger.info(f"Observatory {event["obsIAGA"]} has no updated data for event {event["_id"]}.")
                    elif root["data"][0]["days"][0]["samples_missing"] == 0:
                     updateEvent(event["_id"], event["obsIAGA"], event_year, event_month, event_day, event_datetime_utc, event["tweetID"], event["obsName"], event["timestamp"])
            else:
                logger.error(f"Error fetching {event["obsIAGA"]} observatory data directory with status code {res.status_code}.")
    except Exception as e:
        logger.critical(e)
        exit(1)

def anomalies(df,id):
    try:
        df_resampled = df.resample("30S").interpolate("linear")
        df_resampled.reset_index(inplace=True)
        x2 = df_resampled["value"].values
        # Normalize to minimum
        xn = x2 - np.min(x2)
        # Pattern column vector
        y = np.array([0, 0.5, 1, 0.5, 0, 0.33, 0.67, 1, 0.67, 0.33, 0])
        th = 0.4
        logger.info("Starting to process anomalies...")
        # Output array
        results = np.zeros(len(x2), dtype=int)
        # Main loop
        for m in range(len(x2)):
            r = 0
            for k in range(11):  # filling the first slot
                segment = xn[m+k : m+k+11]
                if len(segment) == len(y):  # Ensure the segment length matches y
                    c, _ = pearsonr(segment, y)
                    if abs(c) >= th:
                        r += 1
            results[m] = r  # save probability
        df_resampled["value"] = results
        df_resampled.to_csv(f"temp/data-{id}.csv", header=False, index=False)
        return df_resampled
    except Exception as e:
        logger.critical(e)
        exit(1)

def graph(df, eventId, iaga, obs_name, year, month, day, center_time):
    try:
        logger.info("Starting to plot data...")
        # Plotting
        plt.figure(figsize=(12, 6))
        plt.plot(df["time"], df["value"], color="red" )
        plt.xlabel("Time")
        plt.ylabel("Data")
        plt.title("Data Plot")
        plt.grid(True)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.axvline(x=center_time, color="g", linestyle="--")
        plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        plt.ylim(bottom=0)
        plt.xlabel(f"{year}-{month}-{day}")
        plt.ylabel("Relative Propability")
        plt.title(f"{iaga} - {obs_name}")
        plt.savefig(f"temp/image-{eventId}.png")
    except Exception as e:
        logger.critical(e)
        exit(1)

def resolveEvent(id):
    try:
        eventsCollection.update_one({
            "_id": ObjectId(id)
        },
        {
            "$set": {
                "resolved": True
            }
        })
        os.remove(f"temp/image-{id}.png")
    except Exception as e:
        logger.critical(e)
        exit(1)
