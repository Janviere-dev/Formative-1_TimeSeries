-- =====================================================================
-- Metro Interstate Traffic Volume - relational schema (MySQL 8+)
--
-- 3NF design with one fact table and two lookup (dimension) tables:
--   holidays            one row per distinct US holiday name
--   weather_conditions  one row per (weather_main, weather_description)
--   traffic_readings    one row per hourly observation (the time series)
--
-- The repeated text columns in the CSV (holiday, weather_main,
-- weather_description) are moved into lookup tables, so each reading only
-- stores small integer foreign keys. This matches api/models.py, which the
-- FastAPI CRUD endpoints use.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS traffic;
USE traffic;

-- ---------------------------------------------------------------------
-- holidays: 1 holiday -> many readings (every hour of that date)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS holidays (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- weather_conditions: 1 condition -> many readings
-- weather_main is the category (Clouds, Rain, Snow, ...),
-- weather_description is the detail (light rain, broken clouds, ...)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_conditions (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    weather_main        VARCHAR(32) NOT NULL,
    weather_description VARCHAR(64) NOT NULL,
    UNIQUE KEY uq_weather (weather_main, weather_description)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- traffic_readings: the hourly time series (fact table)
-- temp is in Kelvin, rain_1h / snow_1h in mm for the hour,
-- clouds_all is % cloud cover, traffic_volume is cars per hour (target).
-- A timestamp can appear more than once when several weather conditions
-- were reported in the same hour, so date_time is indexed but not unique.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS traffic_readings (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    date_time      DATETIME NOT NULL,
    temp           DOUBLE   NOT NULL,
    rain_1h        DOUBLE   NOT NULL,
    snow_1h        DOUBLE   NOT NULL,
    clouds_all     INT      NOT NULL,
    traffic_volume INT      NOT NULL,
    weather_id     INT      NOT NULL,
    holiday_id     INT      NULL,
    INDEX idx_readings_date_time (date_time),
    CONSTRAINT chk_rain_non_negative   CHECK (rain_1h >= 0),
    CONSTRAINT chk_snow_non_negative   CHECK (snow_1h >= 0),
    CONSTRAINT chk_clouds_percent      CHECK (clouds_all BETWEEN 0 AND 100),
    CONSTRAINT chk_volume_non_negative CHECK (traffic_volume >= 0),
    CONSTRAINT fk_readings_weather
        FOREIGN KEY (weather_id) REFERENCES weather_conditions (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_readings_holiday
        FOREIGN KEY (holiday_id) REFERENCES holidays (id)
        ON DELETE SET NULL
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Convenience view: rebuilds the original flat CSV shape with joins,
-- which is what analysis code and the forecast script expect.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_readings AS
SELECT r.id,
       r.date_time,
       r.temp,
       r.rain_1h,
       r.snow_1h,
       r.clouds_all,
       r.traffic_volume,
       w.weather_main,
       w.weather_description,
       h.name AS holiday
FROM traffic_readings r
JOIN weather_conditions w ON w.id = r.weather_id
LEFT JOIN holidays h      ON h.id = r.holiday_id;
