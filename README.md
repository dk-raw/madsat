# MAD SAT
Tracking heavy LEO satellites and the magnetic anomalies they create.

The app runs locally on a Rasberry Pi 5.

Satellite TLE data are provided by [CelesTrak](https://celestrak.org/)

Magnetometer data are provided by [INTERMAGNET](https://intermagnet.org/)

Propabilities of magnetic anomalies are calculated using [Richard Cordaro's](https://x.com/rrichcord) method from [The Magnetic Precursor Earthquake Warning Method](https://drive.google.com/file/d/15R22vXYmGZV35gZN_0MiSoCf_ZIBH8zW/view)

## Files
- `SATELLITES.csv` list of NORAD numbers of satellites to track
- `STATIONS.csv` list of magnetometer observatories
- `main.py` program entry point and base functions
- `mag.py` functions associated with magnetometer data fetching and processing
- `twitter.py` functions associated with posts for the @madsatbot twitter bot
- `update.sh` automatic repo update script for my rasberry pi

## API
[madsat-api](https://github.com/dk-raw/madsat-api) has endpoints for the satellite passage data, logs and application status.

## Donations
Please consider donating to [PayPal](https://paypal.me/ddkatsios) to help maintain this and other similar open-source science projects.