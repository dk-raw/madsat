import numpy as np
from scipy.interpolate import interp1d
from scipy.stats import pearsonr
import csv
import requests
from datetime import datetime, timezone
import json 
import twitter

def updateEvents():
    print("Updating events...")
    with open("events.txt",mode='r', newline='') as csvfile:
        events_arr = []
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            if row[8]=="False":
                events_arr.append(tuple(row))
        events = tuple(events_arr)
        print(f"{len(events)} unresolved event(s) loaded successfully.")
    # current_datetime_utc = datetime.now(timezone.utc)
    # utc_day = current_datetime_utc.day
    # utc_month = current_datetime_utc.month
    # utc_year = current_datetime_utc.year
    for id,time,iaga,name,lat,lon,norad,sat,resolved,tweetId in events:
        event_datetime_utc = datetime.fromtimestamp(float(time))
        event_day = event_datetime_utc.day
        event_month = event_datetime_utc.month
        event_year = event_datetime_utc.year
        url = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetDataDirectory&observatoryIagaCodeList={iaga}&samplesPerDay=minute&dataStartDate={event_year}-{event_month}-{event_day}&dataDuration=1&publicationState=adj-or-rep&options=showgaps&format=json"
        res = requests.get(url)
        # print(url)
        if res.status_code==200:
            root = json.loads(res.text)
            if root["data"][0]["embargo_applied"] == "true":
                print(f"Data embargo applied for observatory {iaga}.")
            elif root["data"][0]["publication_state"] == "none":
                print(f"No data for {iaga} at {event_year}-{event_month}-{event_day}.")
            else:
                if root["data"][0]["days"][0]["gap_start_times"]:
                    date_string=root["data"][0]["days"][0]["gap_start_times"][0]
                    last_obs_update_utc=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
                    if last_obs_update_utc - float(time) > 0:
                        print(f"Observatory {iaga} has updated data since last check for event {id}.\nGrabbing data...")
                        #get data, process data, reply to tweet, change status to True
                        url_image = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetData&format=PNG&observatoryIagaCode={iaga}&samplesPerDay=minute&publicationState=Best%20available&dataStartDate={event_year}-{event_month}-{event_day}&dataDuration=1&traceList=Y&colourTraces=true&pictureSize=Automatic&dataScale=Automatic"
                        res_image = requests.get(url_image)
                        if res_image.status_code == 200:
                            with open(f"temp/temp-image-{id}", 'wb') as f:
                                f.write(res_image.content)
                            image_id = twitter.upload(f"temp/temp-image-{id}")
                            twitter.reply(f"{iaga} observatory data for this event at {event_datetime_utc} UTC",tweetId, [str(image_id)])
                        else:
                            print(f"Error fetching {iaga} observatory image data with status code {res.status_code}.")
                    else:
                        print(f"Observatory {iaga} has no updated data for event {id}.")
                elif root["data"][0]["days"][0]["samples_missing"] == 0:
                    print(f"Observatory {iaga} has updated data since last check for event {id}.\nGrabbing data...")
                    url_image = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetData&format=PNG&observatoryIagaCode={iaga}&samplesPerDay=minute&publicationState=Best%20available&dataStartDate={event_year}-{event_month}-{event_day}&dataDuration=1&traceList=Y&colourTraces=true&pictureSize=Automatic&dataScale=Automatic"
                    res_image = requests.get(url_image)
                    if res_image.status_code == 200:
                        with open(f"temp/temp-image-{id}", 'wb') as f:
                            f.write(res_image.content)
                        image_id = twitter.upload(f"temp/temp-image-{id}")
                        twitter.reply(f"{iaga} observatory data for this event at {event_datetime_utc} UTC",tweetId, [str(image_id)])
                    else:
                        print(f"Error fetching {iaga} observatory image data with status code {res.status_code}.")
        else:
            print(f"Error fetching {iaga} observatory data directory with status code {res.status_code}.")

def anomalies(raw_values):
    data = np.array(raw_values)
    # Interpolate to every 1/2 minute
    interp_func_data = interp1d(np.arange(len(data)), data, kind='linear')
    x2 = interp_func_data(np.arange(0, len(data) - 1, 0.5))
    # Normalize to minimum
    xn = x2 - np.min(x2)
    # Pattern column vector
    y = np.array([0, 0.5, 1, 0.5, 0, 0.33, 0.67, 1, 0.67, 0.33, 0])
    th = 0.4
    print('Processing anomalies...')
    # Output array
    results = np.zeros(2859, dtype=int)
    # Main loop
    for m in range(2859):
        r = 0
        for k in range(11):  # filling the first slot
            segment = xn[m+k : m+k+11]
            if len(segment) == len(y):  # Ensure the segment length matches y
                c, _ = pearsonr(segment, y)
                if abs(c) >= th:
                    r += 1
        results[m] = r  # save probability
    print('Anomalies processed successfully.')
    return results
