"""
-   orchestrates the full pipeline: extract -> transform -> load, w/ run tracking in the pipeline_runs table
-   this is the single entry point github actions scheduler will call
"""

from datetime import date, timedelta
from src.extract.fetch_weather import fetch_all_cities
from src.transform.clean import clean_records
from src.load.upsert import get_connection, upsert_readings

def run_pipeline():
    conn = get_connection()

    """
    record the start of this run immediately - if the pipeline crashes anywhere below, we still have  running row
    showing when it started, which is useful for spotting stuck/crashed runs
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (status) VALUES ('running') RETURNING run_id"
        )
        run_id = cur.fetchone()[0]
    conn.commit()

    try:
        yesterday = (date.today() - timedelta(days = 1)).isoformat()
        raw_records = fetch_all_cities(start_date = yesterday, end_date = yesterday)
        valid_records, rejected_records = clean_records(raw_records)

        rows_written = upsert_readings(conn, valid_records)

        # mark the run as successful, recording how many rows landed
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_runs
                SET finished_at = now(), status = 'success', rows_loaded = %s
                WHERE run_id = %s
                """,
                (rows_written, run_id),
            )
        conn.commit()

        print(f"Pipeline run { run_id }: loaded { rows_written } rows, "
              f"rejected { len(rejected_records) } rows")
        
    except Exception as e:
        """
        record the failure so it's visible in pipeline_runs, then reraise - we want github actions to actually
        see this run as failed (a red X), not swallow the error silently
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_runs
                SET finished_at = now(), status = 'failed', error_message = %s
                WHERE run_id = %s
                """,
                (str(e), run_id),
            )
        conn.commit()
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    run_pipeline()