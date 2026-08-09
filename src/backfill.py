"""
one-time backfill script: pulls a longer historical date range from open-meteo n loads it into the db, so our analysis views
(moving averages, day over day change) have enough history to show real trends instead of NULLs

this is deliberately separate from main.oy - main.py's job is "run the daily pipeline for yesterday", not "fetch an
arbitary custom range". keeping them separate avoids main.py growing extra command-line arguments just to serve this
one time task
"""

from datetime import date, timedelta
from src.extract.fetch_weather import fetch_all_cities
from src.transform.clean import clean_records
from src.load.upsert import get_connection, upsert_readings

def run_backfill(days: int = 60):
    end_date = (date.today() - timedelta(days = 1)).isoformat() # yesterday
    start_date = (date.today() - timedelta(days = days)).isoformat()

    print(f"Backfilling from {start_date} to {end_date}...")

    conn = get_connection()
    raw_records = fetch_all_cities(start_date = start_date, end_date = end_date)
    valid_records, rejected_records = clean_records(raw_records)
    rows_written = upsert_readings(conn, valid_records)
    conn.close()

    print(f"Backfill complete: loaded {rows_written} rows, "
          f"rejected {len(rejected_records)} rows")

if __name__ == "__main__":
    run_backfill(days = 60)