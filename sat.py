import requests
from skyfield.api import EarthSatellite, Topos, load
import numpy as np
import time as tm
import uuid 
import csv

last_tle_update = tm.time()
DEG_MARGIN = 2

satellites = []
tles = []

try:
     with open("SATELLITES.csv", newline='') as csvfile:
          csv_reader = csv.reader(csvfile)
          for row in csv_reader:
               satellites.append(row[0])
     print(f"{len(satellites)} satellites loaded successfully.")
except Exception as e:
    print(e)

try:
     with open("TEST-STATIONS.csv", newline='') as csvfile:
          csv_reader = csv.reader(csvfile)
          observatories = tuple(tuple(row) for row in csv_reader)
          print(f"{len(observatories)} observatories loaded successfully.")
except Exception as e:
     print(e)

try:
     for sat in satellites:
          url = f"https://celestrak.com/NORAD/elements/gp.php?CATNR={sat}"
          res = requests.get(url)
          tle = res.text.splitlines()
          tles.append(tle)
     print(f"{len(tles)} TLE data fetched successfully.")
except Exception as e:
     print(e)

parsed_observatories = [(point[0], point[1], float(point[3]), float(point[4])) for point in observatories]

def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0  # Earth radius in km
        phi1 = np.radians(lat1)
        phi2 = np.radians(lat2)
        delta_phi = np.radians(lat2 - lat1)
        delta_lambda = np.radians(lon2 - lon1)
        a = np.sin(delta_phi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return round(R * c,1)

def saveEvent(time, observatory, sat):
     eventId = uuid.uuid4()
     eventData = f'{eventId},{time},{observatory["IAGA"]},{observatory["Name"]},{observatory["Lat"]},{observatory["Lon"]},{sat["ID"]},{sat["Name"]},False\n'
     try:
          with open("events.txt", 'a') as file:
               file.write(eventData)
               print(f"Event {eventId} saved successfully.")
     except Exception as e:
         print(e)

def updateTLE():
     try:
          tles=[]
          for sat in satellites:
               url = f"https://celestrak.com/NORAD/elements/gp.php?CATNR={sat}"
               res = requests.get(url)
               tle = res.text.splitlines()
               tles.append(tle)
          print(f"{len(tles)} TLE data updated successfully.")
     except Exception as e:
          print(e)

while True:
    current_time = tm.time()
    if current_time - last_tle_update >= 30: #time is seconds
         updateTLE()
         last_tle_update = current_time
    
    ts = load.timescale()
    time = ts.now()

    for tle in tles:
     satellite = EarthSatellite(tle[1], tle[2], tle[0], ts)
     geocentric = satellite.at(time)
     subpoint = geocentric.subpoint()
    
     sat_lat, sat_lon = subpoint.latitude.degrees, subpoint.longitude.degrees

     #print(f"{satellite.name} is at {sat_lat}, {sat_lon}")
    
     for iaga, name, lat, lon in parsed_observatories:
        distance = haversine(lat, lon, sat_lat, sat_lon)
        print(f"Distance from {iaga} to {satellite.name} satellite: {distance} km")
        
        if distance <= DEG_MARGIN * 111:  # Convert degrees to approximate km (1 degree ~ 111 km)
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
            saveEvent(current_time, obs, sat)
            print(f"Satellite {satellite.name} is within 2 degrees of the {iaga} station")

        
    print("================================================")
    tm.sleep(4) 