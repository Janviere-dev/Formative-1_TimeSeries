-- =====================================================================
-- Task 2 - SQL queries on the traffic database (MySQL 8+)
--
-- Each query starts with a "-- @query:" title line. SQL/run_queries.py
-- reads this file, runs every query and writes the outputs to
-- SQL/query_results.md, so the queries and their results never drift apart.
--
-- Several timestamps appear more than once (one row per weather condition
-- in that hour, all with the same traffic_volume). Queries that measure
-- traffic over time first collapse to one row per hour in an `hourly` CTE
-- so those hours are not double counted.
-- =====================================================================

USE traffic;

-- @query: Q1 - Latest record (most recent hour, with weather and holiday joined)
SELECT r.id,
       r.date_time,
       r.traffic_volume,
       ROUND(r.temp - 273.15, 1) AS temp_c,
       w.weather_main,
       w.weather_description,
       h.name AS holiday
FROM traffic_readings r
JOIN weather_conditions w ON w.id = r.weather_id
LEFT JOIN holidays h      ON h.id = r.holiday_id
ORDER BY r.date_time DESC, r.id DESC
LIMIT 1;

-- @query: Q2 - Records by date range (morning rush hour, 2018-09-24 to 2018-09-28)
SELECT r.date_time,
       r.traffic_volume,
       w.weather_main,
       r.rain_1h,
       r.clouds_all
FROM traffic_readings r
JOIN weather_conditions w ON w.id = r.weather_id
WHERE r.date_time BETWEEN '2018-09-24 00:00:00' AND '2018-09-28 23:59:59'
  AND HOUR(r.date_time) = 7
ORDER BY r.date_time;

-- @query: Q3 - Average traffic volume by hour of day (daily seasonality)
WITH hourly AS (
    SELECT date_time, MAX(traffic_volume) AS traffic_volume
    FROM traffic_readings
    GROUP BY date_time
)
SELECT HOUR(date_time)              AS hour_of_day,
       COUNT(*)                     AS hours_observed,
       ROUND(AVG(traffic_volume))   AS avg_volume,
       MIN(traffic_volume)          AS min_volume,
       MAX(traffic_volume)          AS max_volume
FROM hourly
GROUP BY HOUR(date_time)
ORDER BY hour_of_day;

-- @query: Q4 - Traffic and readings per weather category (join + group by)
SELECT w.weather_main,
       COUNT(*)                               AS readings,
       COUNT(DISTINCT w.weather_description)  AS descriptions,
       ROUND(AVG(r.traffic_volume))           AS avg_volume,
       ROUND(AVG(r.temp) - 273.15, 1)         AS avg_temp_c
FROM traffic_readings r
JOIN weather_conditions w ON w.id = r.weather_id
GROUP BY w.weather_main
ORDER BY readings DESC;

-- @query: Q5 - Holidays vs ordinary days (average total daily traffic)
WITH hourly AS (
    SELECT date_time,
           MAX(traffic_volume) AS traffic_volume,
           MAX(holiday_id)     AS holiday_id
    FROM traffic_readings
    GROUP BY date_time
),
daily AS (
    SELECT DATE(date_time)      AS day,
           SUM(traffic_volume)  AS daily_volume,
           COUNT(*)             AS hours_observed,
           MAX(holiday_id)      AS holiday_id
    FROM hourly
    GROUP BY DATE(date_time)
    HAVING COUNT(*) >= 20       -- skip days with large data gaps
)
SELECT COALESCE(h.name, '(no holiday)') AS holiday,
       COUNT(*)                         AS days,
       ROUND(AVG(d.daily_volume))       AS avg_daily_volume
FROM daily d
LEFT JOIN holidays h ON h.id = d.holiday_id
GROUP BY COALESCE(h.name, '(no holiday)')
ORDER BY avg_daily_volume DESC;

-- @query: Q6 - Lag features and 24-hour moving average (window functions, last 30 hours)
WITH hourly AS (
    SELECT date_time, MAX(traffic_volume) AS traffic_volume
    FROM traffic_readings
    GROUP BY date_time
),
features AS (
    SELECT date_time,
           traffic_volume,
           LAG(traffic_volume, 1)  OVER (ORDER BY date_time) AS lag_1h,
           LAG(traffic_volume, 24) OVER (ORDER BY date_time) AS lag_24h,
           ROUND(AVG(traffic_volume) OVER (
               ORDER BY date_time ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
           )) AS moving_avg_24h
    FROM hourly
)
SELECT *
FROM features
WHERE date_time >= '2018-09-29 18:00:00'
ORDER BY date_time;
