USE traffic;

CREATE TABLE IF NOT EXISTS holidays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS weather_conditions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    weather_main VARCHAR(32) NOT NULL,
    weather_description VARCHAR(64) NOT NULL,
    UNIQUE KEY uq_weather (weather_main, weather_description)
);

CREATE TABLE IF NOT EXISTS traffic_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date_time DATETIME NOT NULL,
    temp DOUBLE NOT NULL,
    rain_1h DOUBLE NOT NULL,
    snow_1h DOUBLE NOT NULL,
    clouds_all INT NOT NULL,
    traffic_volume INT NOT NULL,
    weather_id INT NOT NULL,
    holiday_id INT NULL,
    INDEX idx_readings_date_time (date_time),
    CONSTRAINT fk_readings_weather
        FOREIGN KEY (weather_id) REFERENCES weather_conditions (id),
    CONSTRAINT fk_readings_holiday
        FOREIGN KEY (holiday_id) REFERENCES holidays (id)
);
