-- Execute after loading the cleaned Task 1 dataset.
USE traffic_timeseries;

-- @query: Q1 Latest record (required)
SELECT r.id, r.date_time, r.traffic_volume,
       ROUND(r.temp - 273.15, 1) AS temp_c,
       r.rain_1h, r.snow_1h, r.clouds_all,
       w.weather_main, w.weather_description, l.location_name
FROM traffic_readings r
LEFT JOIN weather_conditions w ON w.id=r.weather_id
JOIN locations l ON l.id=r.location_id
ORDER BY r.date_time DESC, r.id DESC LIMIT 1;

-- @query: Q2 Records within a date range (required)
SELECT r.date_time, r.traffic_volume, w.weather_main,
       w.weather_description, r.temp, r.rain_1h, r.snow_1h, r.clouds_all
FROM traffic_readings r
LEFT JOIN weather_conditions w ON w.id=r.weather_id
WHERE r.date_time BETWEEN '2018-09-24 00:00:00' AND '2018-09-28 23:59:59'
ORDER BY r.date_time;

-- @query: Q3 Average traffic volume by hour of day
SELECT HOUR(date_time) AS hour_of_day, COUNT(*) AS observations,
       ROUND(AVG(traffic_volume)) AS average_traffic,
       MIN(traffic_volume) AS minimum_traffic, MAX(traffic_volume) AS maximum_traffic
FROM traffic_readings
GROUP BY HOUR(date_time) ORDER BY hour_of_day;

-- @query: Q4 Average traffic volume by weather category
SELECT COALESCE(w.weather_main, 'Unknown') AS weather_category,
       COUNT(*) AS observations, ROUND(AVG(r.traffic_volume)) AS average_traffic,
       ROUND(AVG(r.temp)-273.15, 1) AS average_temperature_c
FROM traffic_readings r
LEFT JOIN weather_conditions w ON w.id=r.weather_id
GROUP BY COALESCE(w.weather_main, 'Unknown')
ORDER BY observations DESC;

-- @query: Q5 Average traffic volume by weekday
SELECT DAYNAME(date_time) AS weekday_name, COUNT(*) AS observations,
       ROUND(AVG(traffic_volume)) AS average_traffic
FROM traffic_readings
GROUP BY DAYOFWEEK(date_time), DAYNAME(date_time)
ORDER BY DAYOFWEEK(date_time);

-- @query: Q6 Lag and trailing 24-observation moving average
-- The full cleaned dataset has timestamp gaps, so lag means previous available
-- observation, not necessarily exactly one clock hour earlier.
-- Exclude the current row from the moving average to avoid target leakage.
WITH features AS (
  SELECT date_time, traffic_volume,
         LAG(traffic_volume, 1) OVER (ORDER BY date_time) AS previous_observation,
         LAG(traffic_volume, 24) OVER (ORDER BY date_time) AS lag_24_observations,
         ROUND(AVG(traffic_volume) OVER (
           ORDER BY date_time ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING
         )) AS previous_24_observations_avg
  FROM traffic_readings
)
SELECT * FROM features ORDER BY date_time DESC LIMIT 30;
