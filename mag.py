import numpy as np
from scipy.interpolate import interp1d
from scipy.stats import pearsonr
import csv
import requests
from datetime import datetime, timezone
import json 
import twitter

def checkData():
    print("Updating events...")
    with open("events.txt",mode='r', newline='') as csvfile:
        events_arr = []
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            if row[8]=="False":
                events_arr.append(tuple(row))
        events = tuple(events_arr)
        print(f"{len(events)} unresolved event(s) loaded successfully.")
    current_datetime_utc = datetime.now(timezone.utc)
    utc_day = current_datetime_utc.day
    utc_month = current_datetime_utc.month
    utc_year = current_datetime_utc.year
    for id,time,iaga,name,lat,lon,norad,sat,resolved,tweetId in events:
        url = f"https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetDataDirectory&observatoryIagaCodeList={iaga}&samplesPerDay=minute&dataStartDate={utc_year}-{utc_month}-{utc_day}&dataDuration=1&publicationState=adj-or-rep&options=showgaps&format=json"
        res = requests.get(url)
        # print(url)
        if res.status_code==200:
            root = json.loads(res.text)
            if root["data"][0]["embargo_applied"] == "true":
                print(f"Data embargo applied for observatory {iaga}.")
            else:
                date_string=root["data"][0]["days"][0]["gap_start_times"][0]
                last_obs_update_utc=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
                if last_obs_update_utc - float(time) > 0:
                    print(f"Observatory {iaga} has updated data since last check for event {id}.")
                    #get data, process data, reply to tweet, change status to True
                    twitter.reply("Update status for this event.",tweetId)
                else:
                    print(f"Observatory {iaga} has no updated data for event {id}.")
        else:
            print(f"Error fetching observatory data with status code {res.status_code}.")

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
