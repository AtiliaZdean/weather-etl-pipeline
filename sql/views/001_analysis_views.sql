-- analytical views over the readings table. each view answers one spesific question, kept single purpose rather than one
-- giant query - easier to explain, test, n reuse individually (e.g. the chart script in the next phase will just
-- SELECT * FROM each view)

-- ===
-- v_moving_avg: 7-day moving avg of mean temp, per city. smooths daily noise so we can see real trend direction rather
-- than day to day fluctuation
-- ===
CREATE OR REPLACE VIEW v_moving_avg_temp AS
SELECT 
    c.city_name,
    r.reading_date,
    r.temp_mean_c, 
    -- AVG() OVER (...) is a window function: unlike a normal AVG() w/ GROUP BY (which collapses rows into one),
    -- this computes an average FOR EACH ROW using a "window" of nearby rows, while keeping every row visible in the output
    ROUND(
        AVG(r.temp_mean_c) OVER (
            PARTITION BY r.city_id  -- restart the average separately for each city
            ORDER BY r.reading_date -- window slides in date order
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW    -- current day + 6 before =7-day window
        ), 1
    ) AS temp_7day_avg_c
FROM readings r
JOIN cities c ON r.city_id = c.city_id
ORDER BY c.city_name, r.reading_date;

-- ===
-- v_day_over_day_change: how mich did mean temp change from the previous day, per city. highlights volatility -- a
-- city tht swings +/-5C day2day tells a diff story than one tht's steady
-- ===
CREATE OR REPLACE VIEW v_day_over_day_change AS
SELECT 
    c.city_name,
    r.reading_date,
    r.temp_mean_c,
    -- LAG() looks at a PREVIOUS row within the same window - here, "the previous day's temp_mean_c for this same
    -- city". LAG(x, 1) means "1 row back". this is wht makes day over day comparison possible in a single query
    -- w/out a self-join
    LAG(r.temp_mean_c, 1) OVER (
        PARTITION BY r.city_id
        ORDER BY r.reading_date
    ) AS prev_day_temp_c,
    ROUND(
        r.temp_mean_c - LAG(r.temp_mean_c, 1) OVER (
            PARTITION BY r.city_id
            ORDER BY r.reading_date
        ), 1
    ) AS temp_change_c
FROM readings r
JOIN cities c ON r.city_id = c.city_id
ORDER BY c.city_name, r.reading_date;

-- ===
-- v_city_rainfall_ranking: ranks cities by total rainfall over all data collected so far. simple aggregation + RANK(),
-- answers "which city is wettest" at a glance
-- ===
CREATE OR REPLACE VIEW v_city_rainfall_ranking AS
SELECT
    c.city_name,
    ROUND(SUM(r.rainfall_mm), 1) AS total_rainfall_mm,
    ROUND(AVG(r.rainfall_mm), 1) AS avg_daily_rainfall_mm,
    -- RANK() assigns 1 to the highest total_rainfall_mm, 2 to the next, etc. ties get the same rank (unlike 
    -- ROW_NUMBER(), which would arbitrarily break ties) - appropriate here since 2 cities genuinely tying on 
    -- rainfall SHOULD show the same rank
    RANK() OVER (ORDER BY SUM(r.rainfall_mm) DESC) AS rainfall_rank
FROM readings r
JOIN cities c ON r.city_id = c.city_id
GROUP BY c.city_name
ORDER BY rainfall_rank;

-- ===
-- v_extremes_per_city: the single hottest n wettest day on record for each city. simple MAX() aggregation, useful for
-- spotting outlier/extreme events at a glance
-- ===
CREATE OR REPLACE VIEW v_extremes_per_city AS
SELECT
    c.city_name,
    MAX(r.temp_max_c) AS hottest_temp_c,
    (SELECT reading_date FROM readings r2
     WHERE r2.city_id = r.city_id AND r2.temp_max_c = MAX(r.temp_max_c)
     LIMIT 1) AS hottest_date,
    MAX(r.rainfall_mm) AS wettest_day_mm,
    (SELECT reading_date FROM readings r3
     WHERE r3.city_id = r.city_id AND r3.rainfall_mm = MAX(r.rainfall_mm)
     LIMIT 1) AS wettest_date
FROM readings r
JOIN cities c ON r.city_id = c.city_id
GROUP BY c.city_name, r.city_id
ORDER BY c.city_name;