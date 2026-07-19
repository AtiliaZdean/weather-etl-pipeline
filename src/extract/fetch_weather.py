"""
extract stage: pulls daily weather data from the open-meteo archive api for each city defined in confiq.py.
this module ONLY fetches n reshapes data from the API, it does not touch th db n doesnt clean/validate values --
thts the transform stage's job. keeping the boundary strict makes each stage independently testable
"""

import requests
from datetime import date, timedelta
from src.extract.config import CITIES

# open-meteo's historical/archive endpoint -- this is what serves past dates. note: for "today" or future dates, 
# open-meteo requires a different endpoint (the forecast api) since archive data has a short reporting delay. 
# we'll only be pulling past-completed days, which fits our daily scheduled run (we'll fetch "yesterday", not 
# "today")
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# the spesific daily fields we want back from the api, comma-separated as the api expects. keeping this as one
# constant means if we ever want to track e.g. wind speed later, we change it in exactly one place
DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum"

def fetch_city_weather(city_name: str, latitude: float, longitude: float, start_date: str, end_date: str) -> list[dict]:
    """
    - fetch daily weather for one city between start_date n end_date (includsive, both as 'YYY-MM-DD' strings)
    - returns a list of dicts one per day, e.g.:
        [{"city_name": "Seremban", "reading_date": "2026-07-08","temp_max_c": 30.7, "temp_min_c": 23.1, "temp_mean_c": 27.2,"rainfall_mm": 2.70}, ...]
    - raising an exception on failure (rather than returning none or an empty list) is deliberate: a silent empty result could get loaded
    as "zero readings" without anyone noticing something went wrong. an exception forces the caller (and later, our pipeline_runs
    logging) to actually notice and record the failure
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": DAILY_FIELDS,
        "timezone": "Asia/Singapore",
    }

    response = requests.get(BASE_URL, params = params, timeout = 30)
    response.raise_for_status()     # raises an exception on http errors
    data = response.json()

    daily = data["daily"]

    # zip the parallel arrays together by index to build one dict per day
    # this is the core transformation: API gives us "columns", we want "rows"
    records = []
    for i in range(len(daily["time"])):
        records.append({
            "city_name": city_name,
            "reading_date": daily["time"][i],
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "temp_mean_c": daily["temperature_2m_mean"][i],
            "rainfall_mm": daily["precipitation_sum"][i],
        })

    return records

def fetch_all_cities(start_date: str, end_date: str) -> list[dict]:
    """
    -   loop over every city in CITIES n fetch its weather data for the given date range
    -   returns one combined flat list of records across all cities -- easier for the load stage to iterate over
        than a nested per-city structure
    """
    all_records = []
    for city in CITIES:
        city_records = fetch_city_weather(
            city_name = city["city_name"],
            latitude = city["latitude"],
            longitude = city["longitude"],
            start_date = start_date,
            end_date = end_date,
        )
        all_records.extend(city_records)
    return all_records

if __name__ == "__main__":
    # manual test hook: running this file directly fetches yesterday's weather for all 4 cities n prints it, so
    # we can sanity-check the ectract logic works before wiring it into the full pipeline
    yesterday = (date.today() - timedelta(days = 1)).isoformat()
    results = fetch_all_cities(start_date = yesterday, end_date = yesterday)
    for record in results:
        print(record)