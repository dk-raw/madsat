import sys
import os
import logging
from datetime import datetime, timezone
import time as tm
import csv
import requests
from skyfield.api import EarthSatellite, load
import pymongo
import numpy as np
from dotenv import load_dotenv
import twitter
import mag as im

load_dotenv()

last_tle_update = last_mag_update = last_expired_events_check = tm.time()
DEG_MARGIN = 2
EVENT_DURATION_THRESHOLD = 5*60
TIME_BETWEEN_EVENT_CHECKS = int(os.getenv("time_between_event_checks"))
TIME_BETWEEN_TLE_UPDATES = int(os.getenv("time_between_tle_updates"))
LOGGER_FORMAT = "%(levelname)s : %(asctime)s : %(message)s"

last_event_time = {}
global satellite
global tles
satellites = []
tles = []

logging.basicConfig(filename="liggma.log", level=logging.INFO, format=LOGGER_FORMAT)
logger = logging.getLogger("liggma")

try:
     client = pymongo.MongoClient("localhost",27017)
     db = client["madsat"]
     global eventsCollection
     eventsCollection = db["events"]
except Exception as e:
     logger.critical(e)
     sys.exit(1)

try:
     with open("SATELLITES.csv", newline='') as csvfile:
          csv_reader = csv.reader(csvfile)
          for row in csv_reader:
               satellites.append(row[0])
          logger.info("%s satellite(s) loaded successfully.", len(satellites))
except Exception as e:
     logger.critical(e)
     sys.exit(1)

try:
     with open("STATIONS.csv", newline='') as csvfile:
          csv_reader = csv.reader(csvfile)
          observatories = tuple(tuple(row) for row in csv_reader)
          logger.info("%s observatories loaded successfully.", len(observatories))
except Exception as e:
     logger.critical(e)
     sys.exit(1)

try:
     for sat in satellites:
          url = f"https://celestrak.com/NORAD/elements/gp.php?CATNR={sat}"
          res = requests.get(url, timeout=5)
          if res.status_code == 200:
               tle = res.text.splitlines()
               tles.append(tle)
          else:
               logger.critical("Error fetching initial TLE data for satelite %s with status code %s.", sat, res.status_code)
               sys.exit(1)
     logger.info("%s TLE(s) fetched successfully.", len(tles))
except Exception as e:
     logger.critical(e)
     sys.exit(1)

parsed_observatories = [(point[0], point[1], float(point[3]), float(point[4])) for point in observatories]

def haversine(lat1, lon1, lat2, lon2):
        radius = 6371.0  # Earth radius in km
        phi1 = np.radians(lat1)
        phi2 = np.radians(lat2)
        delta_phi = np.radians(lat2 - lat1)
        delta_lambda = np.radians(lon2 - lon1)
        a = np.sin(delta_phi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return round(radius * c,1)

def save_event(time, observatory, sat, tweet_id):
     try:
          event_dict = {
               "timestamp": round(time,0),
               "obsIAGA": observatory["IAGA"],
               "obsName": observatory["Name"],
               "obsLat": observatory["Lat"],
               "obsLon": observatory["Lon"],
               "satNORAD": sat["ID"],
               "satName": sat["Name"],
               "tweetID": tweet_id,
               "resolved": False
          }
          event = eventsCollection.insert_one(event_dict)
          logger.info("Event %s saved successfully.", event.inserted_id)
     except Exception as e:
          logger.critical(e)
          sys.exit(1)

def update_tles():
     try:
          global tles
          updated_tles = []
          for sat in satellites:
               url = f"https://celestrak.com/NORAD/elements/gp.php?CATNR={sat}"
               res = requests.get(url, timeout=5)
               if res.status_code == 200:
                    tle = res.text.splitlines()
                    updated_tles.append(tle)
               else:
                    logger.error("Error fetching updated TLE data for satelite %s with status code %s.", sat, res.status_code)
          if len(updated_tles) == len(tles):
               tles = updated_tles
               logger.info("%s TLEs updated successfully.", len(updated_tles))
          else:
               logger.info("Using previously fetched TLEs.")
     except Exception as e:
          logger.error(e)

while True:
    try:
     current_time = tm.time()
     current_time_utc = datetime.now(timezone.utc).timestamp()

     ts = load.timescale()
     time = ts.now()

     for tle in tles:
          satellite = EarthSatellite(tle[1], tle[2], tle[0], ts)
          geocentric = satellite.at(time)
          subpoint = geocentric.subpoint()
          sat_lat, sat_lon = subpoint.latitude.degrees, subpoint.longitude.degrees

          for iaga, name, lat, lon in parsed_observatories:
               distance = haversine(lat, lon, sat_lat, sat_lon)
               #print(f"Distance from {iaga} to {satellite.name} satellite: {distance} km")
               if distance <= DEG_MARGIN * 111:  # Convert degrees to approximate km (1 degree ~ 111 km)
                    #print(f"Satellite {satellite.name} is within 2 degrees of the {iaga} station")
                    key = (satellite.model.satnum, iaga)
                    if key not in last_event_time or current_time_utc - last_event_time[key] >= EVENT_DURATION_THRESHOLD:
                         logger.info("Satellite %s is within 2 degrees of the %s station", satellite.name, iaga)
                         obs = {
                              "IAGA": iaga,
                              "Name": name,
                              "Lat": lat,
                              "Lon": lon
                         }
                         sat = {
                              "ID": satellite.model.satnum,
                              "Name": satellite.name
                         }
                         tweetId = twitter.tweet(f"🔔🛰️ Satellite {satellite.name} ({satellite.model.satnum}) is now within 2º of {name} ({iaga}) observatory at {datetime.fromtimestamp(round(float(current_time_utc),1), tz=timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
                         save_event(current_time_utc, obs, sat, tweetId)
                         last_event_time[key] = current_time_utc
     #print("================================================")
     if current_time - last_tle_update >= TIME_BETWEEN_TLE_UPDATES:
          update_tles()
          last_tle_update = current_time
     if current_time - last_mag_update >= TIME_BETWEEN_EVENT_CHECKS:
          im.check_events()
          last_mag_update = current_time
     if current_time - last_expired_events_check >= 345600:#3 days
          im.check_expired_events(current_time_utc)
          last_expired_events_check = current_time
     tm.sleep(5) 
    except Exception as e:
     logger.critical(e)
     sys.exit(1)
         