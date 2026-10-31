-- MariaDB schema for the traffic time-series assignment
CREATE DATABASE IF NOT EXISTS traffic_timeseries CHARACTER SET utf8mb4;
USE traffic_timeseries;

CREATE TABLE IF NOT EXISTS locations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  location_name VARCHAR(150) NOT NULL UNIQUE,
  road_name VARCHAR(120) NOT NULL,
  city VARCHAR(120) NOT NULL,
  country VARCHAR(80) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS weather_conditions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  weather_main VARCHAR(80),
  weather_description VARCHAR(160),
  UNIQUE KEY uq_weather_pair (weather_main, weather_description)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS traffic_readings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  date_time DATETIME NOT NULL,
  traffic_volume INT NOT NULL,
  temp DOUBLE,
  rain_1h DOUBLE,
  snow_1h DOUBLE,
  clouds_all DOUBLE,
  location_id INT NOT NULL,
  weather_id INT NULL,
  CONSTRAINT chk_traffic_volume CHECK (traffic_volume >= 0),
  CONSTRAINT chk_clouds_all CHECK (clouds_all IS NULL OR clouds_all BETWEEN 0 AND 100),
  CONSTRAINT fk_reading_location FOREIGN KEY (location_id) REFERENCES locations(id),
  CONSTRAINT fk_reading_weather FOREIGN KEY (weather_id) REFERENCES weather_conditions(id),
  INDEX ix_reading_datetime (date_time),
  INDEX ix_reading_location_datetime (location_id, date_time)
) ENGINE=InnoDB;

INSERT INTO locations (location_name, road_name, city, country)
VALUES ('I-94 Minneapolis-St Paul', 'Interstate 94', 'Minneapolis-St Paul', 'United States')
ON DUPLICATE KEY UPDATE location_name=VALUES(location_name);
