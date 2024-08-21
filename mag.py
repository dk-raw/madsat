import sys
import os
import logging
import json
from datetime import datetime, timezone
import requests
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import pymongo
from bson.objectid import ObjectId
import numpy as np
from scipy.stats import pearsonr
import twitter

logger = logging.getLogger("liggma")

try:
     client = pymongo.MongoClient("localhost",27017)
     db = client["madsat"]
     #global eventsCollection
     eventsCollection = db["events"]
except Exception as e:
     logger.critical(e)
     sys.exit()

def update_event(event_id, iaga, event_datetime, tweet_id, obs_name, event_timestamp):
    logger.info("Observatory %s has updated data for event %s.\nGrabbing data...", iaga, event_id)
    #get data, process data, reply to tweet, change status to True
    url = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetData&format=COVJSON&testObsys=0&observatoryIagaCode={iaga}&samplesPerDay=minute&publicationState=Best%20available&dataStartDate={event_datetime.year}-{event_datetime.month}-{event_datetime.day}&dataDuration=1&orientation=XYZS"
    try:
        res = requests.get(url, timeout=5)
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
            center_time = pd.to_datetime(event_timestamp, unit='s', utc=True)
            time_window = pd.Timedelta(hours=2)
            start_time = center_time - time_window / 2
            end_time = center_time + time_window / 2
            filtered_df = df[(df["time"] >= start_time) & (df["time"] <= end_time)]
            filtered_df.set_index("time", inplace=True)
            processed = anomalies(filtered_df, event_id)
            graph(processed, event_id, iaga, obs_name, event_datetime, center_time)
            image_id = twitter.upload(f"temp/image-{event_id}.png")
            twitter.reply(f"{iaga} observatory data for this event at {event_datetime.strftime('%Y-%m-%d %H:%M')} UTC",tweet_id, [str(image_id)])
            resolve_event(event_id)
            logger.info("Event %s resolved.", event_id)
        else:
            logger.error("Error fetching %s observatory data with status code %s.", iaga, res.status_code)
    except Exception as e:
        logger.error(e)

def check_events():
    logger.info("Updating events...")
    try:
        events = eventsCollection.find({"resolved": False})
        for event in events:
            current_time_utc = datetime.now(timezone.utc).timestamp()
            # if current_time_utc - event["timestamp"] > 172800: # 2 days
            #     twitter.reply(f"Event {event["_id"]} expired as there will be no data available.", event["tweetID"])
            #     resolve_event(event["_id"])
            event_datetime = datetime.fromtimestamp(event["timestamp"], tz=timezone.utc)
            #Get data directory in JSON to see when was the last update
            url = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetDataDirectory&observatoryIagaCodeList={event['obsIAGA']}&samplesPerDay=minute&dataStartDate={event_datetime.year}-{event_datetime.month}-{event_datetime.day}&dataDuration=1&publicationState=adj-or-rep&options=showgaps&format=json"
            res = requests.get(url, timeout=5)
            # print(url)
            if res.status_code==200:
                root = json.loads(res.text)
                if root["data"][0]["embargo_applied"] == "true":
                    logger.info("Data embargo applied for observatory %s.", event['obsIAGA'])
                    resolve_event(event["_id"])
                elif root["data"][0]["publication_state"] == "none":
                    logger.info("No data for %s at %s-%s-%s.", event['obsIAGA'], event_datetime.year, event_datetime.month, event_datetime.day)
                else:
                    #Case where there as some data
                    if root["data"][0]["days"][0]["gap_start_times"]: #if there is a gap in the data
                        date_string=root["data"][0]["days"][0]["gap_start_times"][-1]
                        last_obs_update_utc=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
                        if last_obs_update_utc - event["timestamp"] > 600: #10 minute margin
                            update_event(event["_id"], event["obsIAGA"], event_datetime, event["tweetID"], event["obsName"], event["timestamp"])
                        else:
                            logger.info("Observatory %s has no updated data for event %s.", event['obsIAGA'], event['_id'])
                    elif root["data"][0]["days"][0]["samples_missing"] == 0:
                     update_event(event["_id"], event["obsIAGA"], event_datetime, event["tweetID"], event["obsName"], event["timestamp"])
            else:
                logger.error("Error fetching %s observatory data directory with status code %s.", event['obsIAGA'], res.status_code)
    except Exception as e:
        logger.critical(e)
        sys.exit(1)

def check_expired_events(current_time):
    try:
        res = eventsCollection.update_many({
            "timestamp": {
                "$lt": current_time - 345600 #3 days
            }
        },
        {
            "$set": {
                "resolved": True
            }
        })
        logger.info("Resolved %s expired events.", res.modified_count)
    except Exception as e:
        logger.error("Error checking for expired events: %s", e)

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
        sys.exit(1)

def graph(df, eventId, iaga, obs_name, datetime, center_time):
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
        plt.xlabel(f"{datetime.year}-{datetime.month}-{datetime.day}")
        plt.ylabel("Relative Propability")
        plt.title(f"{iaga} - {obs_name}")
        plt.savefig(f"temp/image-{eventId}.png")
    except Exception as e:
        logger.critical(e)
        sys.exit(1)

def resolve_event(id):
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
        sys.exit(1)
