import json 
import requests
import numpy as np
from scipy.interpolate import interp1d
from scipy.stats import pearsonr
import matplotlib.pyplot as plt

url = 'https://imag-data.bgs.ac.uk/GIN_V1/GINServices?Request=GetData&format=COVJSON&testObsys=0&observatoryIagaCode=IZN&samplesPerDay=minute&publicationState=Best%20available&dataStartDate=2024-07-26&dataDuration=1&orientation=HDZF'
response = requests.get(url)

root = json.loads(response.text)

timestamps = []
values = []

timestamps_raw = root["domain"]["axes"]["t"]["values"]
values_raw = root["ranges"]["H"]["values"]

for timestamp in timestamps_raw:
    timestamps.append(timestamp)

for Yvalue in values_raw:
    if Yvalue is not None:
        values.append(float(Yvalue))

data = np.array(values)

# Interpolate to every 1/2 minute
interp_func_data = interp1d(np.arange(len(data)), data, kind='linear')
x2 = interp_func_data(np.arange(0, len(data) - 1, 0.5))

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

plt.plot(results)
plt.show()

print('Done')

