-- core schema for the weather ETL pipeline

-- ===
-- cities: reference table, one row per city we track
-- normalized out of readings so city metadata (like coordinates) lives in exactly one place. if a city's coordinates ever need correcting, we update one row here instead of thousands ever need
-- correcting, we update one row here instead of thousands of reading rows
-- ===

CREATE TABLE cities (
    city_id     SERIAL PRIMARY KEY,
    city_name   VARCHAR(50) NOT NULL UNIQUE,
    latitude    NUMERIC(9,6) NOT NULL,
    longitude   NUMERIC(9,6) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()   -- timestamptz stores timezone-aware values
);

-- ===
-- readings: the actual weather data, one row per city per day
-- composite primary key (city_id, date) enforces "one reading per city per day" at the database level 
-- it's impossible to insert a duplicate even if our Python code has a bug. this is also what lets us use ON CONFLICT (city_id, date) DO UPDATE later for
-- idempotent loading: rerunning the pipeline for a date we already have simply overwrites that row instead of erroring or duplicating
-- ===

CREATE TABLE readings (
    city_id         INTEGER NOT NULL REFERENCES cities(city_id),
    reading_date    DATE NOT NULL,
    temp_max_c      NUMERIC(4,1),   -- not float since we want exact decimal comparisons
    temp_min_c      NUMERIC(4,1),
    temp_mean_c     NUMERIC(4,1),
    rainfall_mm     NUMERIC(6,1),
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (city_id, reading_date)
);

-- index to speed up future analytical queries tht filter or sort by date across all cities, e.g. "show me last 30 days"
-- without this, postgres has to scan the whole table for date-range queries
CREATE INDEX idx_readings_date ON readings(reading_date);

-- pipeline_runs: audit log of every ETL execution
CREATE TABLE pipeline_runs (
    run_id          SERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,    -- to detect runs tht crashed mid-way (finished at still NULL long after started)
    status          VARCHAR(20) NOT NULL DEFAULT 'running', -- running | success | failed
    rows_loaded     INTEGER,
    error_message   TEXT
);