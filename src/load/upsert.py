"""
load stage: takes cleaned records from the transform stage n writes them into pg uing an idempotent upsert

this is the only module in the pipleline tht touches the db - tht boundary is intentional, matching the same
"each stage only depends on wht it strictly needs" principle from the extract stage
"""

import os
import psycopg
from dotenv import load_dotenv

# load variables from .env into the environment. called once at import time so DATABASE_URL is available wherever this module is used
load_dotenv()

def get_connection():
    """
    -   opens a new connection to pg using DATABASE_URL from .env
    -   why a function instead of a module-level connection object: opening the connection lazily (only when
        this is actually called) means importing this module elsewhere doesnt silently require a live db - useful
        if we ever want to import just get_city_id_map w/out connecting, e.g. for testing
    """
    database_url = os.environ["DATABASE_URL"]
    return psycopg.connect(database_url)

def get_city_id_map(conn) -> dict[str, int]:
    """
    builds a lookup dict mapping city_name -> city_id by querying the cities table. our records from extract/transform
    only carry city_name (a string), but the readings table needs city_id (the fk) - this function bridges tht gap
    """
    with conn.cursor() as cur:
        cur.execute("SELECT city_id, city_name FROM cities")
        rows = cur.fetchall()
    return { city_name: city_id for city_id, city_name in rows }

def upsert_readings(conn, records: list[dict]) -> int:
    """
    -   upserts a list of cleaned weather records into the readings table. returns the number of rows successfully
        written
    -   uses ON CONFLICT (city_id, reading_date) DO UPDATE so rerunning the pipeline for a date we already have
        overwrites tht row instead of erroring or duplicating - this is wht makes the pipeline safe to run more
        thn once for the same day
    """
    city_id_map = get_city_id_map(conn)

    upsert_sql = """
                 INSERT INTO readings (city_id, reading_date, temp_max_c, temp_min_c, temp_mean_c, rainfall_mm)
                 VALUES (%s, %s, %s, %s, %s, %s)
                 ON CONFLICT (city_id, reading_date)
                 DO UPDATE SET
                    temp_max_c = EXCLUDED.temp_max_c,
                    temp_min_c = EXCLUDED.temp_min_c,
                    temp_mean_c = EXCLUDED.temp_mean_c,
                    rainfall_mm = EXCLUDED.rainfall_mm,
                    loaded_at = now();
                 """
    
    rows_written = 0
    with conn.cursor() as cur:
        for record in records:
            city_id = city_id_map[record["city_name"]]
            cur.execute(upsert_sql, (
                city_id,
                record["reading_date"],
                record["temp_max_c"],
                record["temp_min_c"],
                record["temp_mean_c"],
                record["rainfall_mm"],
            ))
            rows_written += 1

    conn.commit()
    return rows_written