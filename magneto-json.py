import json 
import matplotlib.pyplot as plt
import requests
import numpy as np
from scipy.interpolate import interp1d
from scipy.stats import pearsonr
import datetime

url = 'https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetData&format=COVJSON&testObsys=0&observatoryIagaCode=BDV&samplesPerDay=minute&publicationState=Best%20available&dataStartDate=2024-07-22&dataDuration=1&orientation=Native'
response = requests.get(url)

root = json.loads(response.text)

time = []
value = []

timestamps = root["domain"]["axes"]["t"]["values"]
values = root["ranges"]["Y"]["values"]

for timestamp in timestamps:
    time.append(timestamp)

for Yvalue in values:
    if Yvalue is not None:
        value.append(float(Yvalue))

data = np.array(value)

# Interpolate to every 1/2 minute
interp_func = interp1d(np.arange(len(data)), data, kind='linear')
x2 = interp_func(np.arange(0, len(data) - 1, 0.5))

# Normalize to minimum
xn = x2 - np.min(x2)

# Pattern column vector
y = np.array([0, 0.5, 1, 0.5, 0, 0.33, 0.67, 1, 0.67, 0.33, 0])

th = 0.4
print('Running')

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

print('Done')

time_intervals = np.arange(0, len(results) * 0.5, 0.5)

def format_time(x, pos):
    total_seconds = int(x * 60)
    return str(datetime.timedelta(seconds=total_seconds))

plt.figure(figsize=(10, 6))
plt.plot(time_intervals, results, linestyle='-', color='r')
plt.xticks(np.arange(0, time_intervals[-1] + 1, 60), rotation=45)
plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(format_time))
plt.ylabel('Relative Propability')
plt.ylim(0, 10)
plt.yticks(np.arange(0, 11, 1))
plt.xlabel('Time')
plt.grid(axis='y', linestyle='--', color='gray', alpha=0.7)
plt.show()

