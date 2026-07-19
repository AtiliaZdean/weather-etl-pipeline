"""
configuration for the extract stage: which cities we track n their coordinates. kept separate from the db on
purpose - the extract stage should only need to talk to the open-meteo api, not postgres. this list must stay
in sync w the 'cities' table since the load stage will match rows here to city_id by city_name
"""

CITIES = [
    {"city_name": "Seremban", "latitude": 2.7297, "longitude": 101.9381},
    {"city_name": "Kuala Lumpur", "latitude": 3.1390, "longitude": 101.6869},
    {"city_name": "Penang", "latitude": 5.4141, "longitude": 100.3288},
    {"city_name": "Johor Bahru", "latitude": 1.4927, "longitude": 103.7414},
]