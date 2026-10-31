# Metro Interstate Traffic Volume: Time-Series Pipeline

## 1. Project Overview

This project builds an end-to-end time-series data pipeline using the **Metro Interstate Traffic Volume** dataset. It explores historical traffic patterns, prepares time-series features, trains a machine-learning model to predict hourly traffic volume, stores traffic data in relational and non-relational databases, exposes the data through a REST API, and provides a script for generating a next-hour prediction.

The project was developed for **Formative 1: Building a Pipeline for Time Series Data**.

### Problem Statement

Traffic volume changes over time and is influenced by factors such as the hour of the day, day of the week, weather conditions, and recent traffic levels. Understanding these patterns can help describe traffic behaviour and support short-term traffic forecasting.

The main prediction task in this project is:

> Predict the traffic volume for the next hour using historical traffic observations, time-based features, and weather information.

### Dataset

- **Dataset:** Metro Interstate Traffic Volume
- **Target variable:** `traffic_volume`
- **Timestamp column:** `date_time`
- **Other variables:** `temp`, `rain_1h`, `snow_1h`, `clouds_all`, `weather_main`, `weather_description`, and `holiday`
- **Original dataset size:** 48,204 rows and 9 columns
- **Date range:** 2 October 2012 to 30 September 2018
- **Data source:** [Metro Interstate Traffic Volume on Kaggle](https://www.kaggle.com/code/ramyahr/metro-interstate-traffic-volume?select=Metro_Interstate_Traffic_Volume.csv)

The source data contains hourly traffic observations. Some timestamps occur more than once because multiple weather conditions can be reported for the same hour. The preprocessing pipeline groups observations by timestamp when constructing the hourly series.


## 2. Project Objectives

The project is organized around the four tasks:

1. **Time-series preprocessing and exploratory analysis**
   - Understand the dataset and its time coverage.
   - Investigate traffic patterns and relationships with other variables.
   - Engineer lagged and moving-average features.
   - Train and evaluate a forecasting model.

2. **Database design and implementation**
   - Design a relational database using MySQL.
   - Design MongoDB collections for traffic observations and daily summaries.
   - Run analytical queries against both databases.

3. **API development**
   - Implement POST, GET, PUT, and DELETE operations for MySQL and MongoDB.
   - Provide endpoints for retrieving the latest record and records within a date range.

4. **Prediction script**
   - Retrieve historical records from the API or a local CSV file.
   - Apply the forecasting preprocessing pipeline.
   - Load the trained model.
   - Predict traffic volume for the next hour.

---

## 3. Repository Structure

```text
Formative-1_TimeSeries-feature-traffic-data-eda/
│
├── api/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── health.py
│   │   ├── sql_readings.py
│   │   ├── mongo_readings.py
│   │   └── version.py
│   └── tests/
│
├── common/
│   └── dataset.py
│
├── data/
│   ├── Metro_Interstate_Traffic_Volume.csv
│   └── traffic_cleaned.csv
│
├── ERD/
│   ├── erd.png
│
├── SQL/
│   ├── schema.sql
│   ├── load_mysql.py
│   ├── queries.sql
│   └── query_results.txt
│
├── mongodb/
│   ├── load_mongo.py
│   ├── sample_documents.json
│   ├── run_queries.py
│   ├── query_results.md
│   └── README.md
│
├── script/
│   ├── preprocessing.py
│   ├── train_model.py
│   └── predict.py
│
├── experiments/
│   └── model_comparison.csv
│
├── outputs/
│   ├── actual_vs_predicted.png
│   ├── experiment_results.csv
│   ├── test_predictions.csv
│   └── training_summary.json
│
├── notebook.ipynb
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── .env.example
```

### Main components

| Component | Description |
|---|---|
| `notebook.ipynb` | Exploratory data analysis, preprocessing, feature engineering, and forecasting experiments. |
| `common/dataset.py` | Shared data loading and cleaning logic used by the database loaders. |
| `data/` | Original and cleaned traffic datasets. |
| `SQL/` | MySQL schema, data-loading script, queries, and query results. |
| `mongodb/` | MongoDB collection loading, sample documents, queries, and results. |
| `ERD/` | Entity Relationship Diagram and its generation script. |
| `api/` | FastAPI application, database connections, schemas, and API routes. |
| `script/` | Shared forecasting preprocessing, model training, and prediction scripts. |
| `experiments/` and `outputs/` | Model comparison, evaluation results, predictions, and visualizations. |

---

## 4. Exploratory Data Analysis and Preprocessing

The exploratory analysis is available in `notebook.ipynb`.

The notebook investigates the following questions:

1. How does traffic volume vary throughout the day?
2. Does traffic volume differ by day of the week?
3. Does traffic volume show a long-term trend?
4. Is current traffic volume related to traffic volume in the previous hour?
5. Are daily lag effects and weather conditions associated with traffic volume?
6. How do moving averages reveal traffic patterns?

The analysis uses visualizations such as line plots, scatter plots, and comparisons of traffic volume over time.

### Preprocessing

The shared database cleaning process in `common/dataset.py`:

- Removes exact duplicate rows.
- Converts the literal `"None"` in the holiday column into a null value.
- Propagates holiday labels to the other hours of the same date.
- Standardizes weather descriptions to lowercase.
- Converts `date_time` into a datetime value.
- Sorts observations chronologically.

The forecasting preprocessing in `script/preprocessing.py`:

- Groups observations by timestamp to construct an hourly series.
- Creates a complete hourly timeline.
- Extracts time-based features, including hour, day of the week, month, day of the year, and weekend indicator.
- Creates `lag_1` and `lag_24` traffic features.
- Calculates a 24-hour rolling mean using previous observations.
- Removes rows that do not have the historical values required for forecasting.

The notebook also investigates 3-hour, 6-hour, and 24-hour moving averages within continuous periods.

---

## 5. Model Training and Evaluation

The project uses a **Random Forest Regressor** to predict hourly traffic volume.

The model uses:
- Weather variables: temperature, rainfall, snowfall, and cloud cover.
- Calendar features: hour, day of the week, month, day of the year, and weekend indicator.
- Historical traffic features: previous-hour traffic, previous-24-hour traffic, and the 24-hour rolling mean.

### Training approach

The training script is `script/train_model.py`.

It:
1. Loads and preprocesses the traffic dataset.
2. Builds time-based and historical features.
3. Splits the data chronologically into training, validation, and test sets.
4. Trains a baseline Random Forest model.
5. Tests different hyperparameter combinations.
6. Selects the best configuration using validation RMSE.
7. Evaluates the final model on the test set.
8. Saves the trained model and evaluation outputs.

The chronological split is important because future observations should not be used to train a model that predicts earlier observations.

### Experiment comparison

The recorded validation experiments in `outputs/experiment_results.csv` are:

| Experiment | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline Random Forest | 166.74 | 264.89 | 0.9821 |
| Tuned Random Forest | 163.93 | 261.45 | 0.9826 |

The tuned model achieved lower validation MAE and RMSE and a slightly higher R² than the baseline experiment.

### Final test results

According to `outputs/training_summary.json`, the final model achieved:

| Metric | Test result |
|---|---:|
| MAE | 133.01 |
| RMSE | 204.66 |
| R² | 0.9893 |

The results are also saved in:
- `outputs/training_summary.json`
- `outputs/test_predictions.csv`
- `outputs/actual_vs_predicted.png`

The training script creates the `models/traffic_volume_model.joblib` model artifact. This file is generated when training is run.

---

## 6. Database Design and Implementation

The project uses both MySQL and MongoDB to store and query the traffic dataset.

### 6.1 MySQL

The relational database uses three tables:

| Table | Purpose |
|---|---|
| `traffic_readings` | Stores traffic observations, timestamps, numerical measurements, and foreign keys. |
| `weather_conditions` | Stores distinct weather categories and descriptions. |
| `holidays` | Stores distinct holiday names. |

The `traffic_readings` table is the main fact table. It references the weather and holiday lookup tables through foreign keys.

The database also includes:
- Primary and foreign keys.
- Constraints for valid rainfall, snowfall, cloud cover, and traffic volume values.
- An index on `date_time`.
- A `v_readings` view that joins the tables into a flat reading format.

**Important files:**
- `SQL/schema.sql`
- `SQL/load_mysql.py`
- `SQL/queries.sql`
- `SQL/run_queries.py`
- `SQL/query_results.md`

### 6.2 MongoDB

MongoDB uses two collections:

**`traffic_readings`**

Stores individual traffic observations as documents. Weather and holiday information are embedded directly in each document.

**`daily_traffic`**

Stores daily traffic summaries using the bucket pattern. Each document includes daily traffic statistics, peak traffic information, weather summaries, and an embedded hourly array.

Indexes are created to support time-based and other frequently used queries.

**Important files:**
- `mongodb/load_mongo.py`
- `mongodb/sample_documents.json`
- `mongodb/run_queries.py`
- `mongodb/query_results.md`

### 6.3 Loading the databases

After starting MySQL and MongoDB and configuring the environment variables, run these commands from the repository root:

```bash
python -m SQL.load_mysql --reset
python -m SQL.run_queries

python -m mongodb.load_mongo --reset
python -m mongodb.run_queries
```

The loaders use the shared cleaning process in `common/dataset.py`.

Expected loading counts:
- MySQL: 48,187 traffic readings.
- MongoDB `traffic_readings`: 48,187 documents.
- MongoDB `daily_traffic`: 1,860 documents.

The `--reset` option clears the existing project tables or collections before loading. Use it carefully because it replaces the existing stored data.

---

## 7. API Development

The API is implemented using **FastAPI** and supports both MySQL and MongoDB.

The SQL routes are defined in `api/routers/sql_readings.py`, while MongoDB routes are defined in `api/routers/mongo_readings.py`.

### Base URL

When running locally:

```text
http://127.0.0.1:8000
```

### SQL endpoints

Base path: `/sql/readings`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/sql/readings` | Create a traffic reading. |
| GET | `/sql/readings` | List readings with pagination. |
| GET | `/sql/readings/{reading_id}` | Retrieve a reading by ID. |
| GET | `/sql/readings/latest` | Retrieve the latest reading. |
| GET | `/sql/readings/range?start=...&end=...` | Retrieve readings within a date range. |
| PUT | `/sql/readings/{reading_id}` | Update a reading. |
| DELETE | `/sql/readings/{reading_id}` | Delete a reading. |

### MongoDB endpoints

Base path: `/mongo/readings`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/mongo/readings` | Create a traffic reading. |
| GET | `/mongo/readings` | List readings with pagination. |
| GET | `/mongo/readings/{reading_id}` | Retrieve a reading by MongoDB ID. |
| GET | `/mongo/readings/latest` | Retrieve the latest reading. |
| GET | `/mongo/readings/range?start=...&end=...` | Retrieve readings within a date range. |
| PUT | `/mongo/readings/{reading_id}` | Update a reading. |
| DELETE | `/mongo/readings/{reading_id}` | Delete a reading. |

Additional endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Lists the main SQL and MongoDB reading paths. |
| GET | `/health` | Checks API health. |

### Example requests

Retrieve the latest SQL reading:

```bash
curl http://127.0.0.1:8000/sql/readings/latest
```

Retrieve the latest MongoDB reading:

```bash
curl http://127.0.0.1:8000/mongo/readings/latest
```

Retrieve SQL readings within a date range:

```bash
curl "http://127.0.0.1:8000/sql/readings/range?start=2018-09-24T00:00:00&end=2018-09-28T23:59:59"
```

Retrieve MongoDB readings within a date range:

```bash
curl "http://127.0.0.1:8000/mongo/readings/range?start=2018-09-24T00:00:00&end=2018-09-28T23:59:59"
```

### Interactive API documentation

Once the API is running, open:

```text
http://127.0.0.1:8000/docs
```

FastAPI provides interactive documentation that can be used to test the available endpoints.

---

## 8. Prediction and Forecast Script

The prediction script is located at:

```text
script/predict.py
```

It supports two ways of obtaining historical traffic observations:

- From an API endpoint returning historical readings.
- From a local CSV file.

The script then:
1. Loads the historical records.
2. Converts timestamps into datetime values and sorts the records.
3. Constructs the hourly time series.
4. Creates the next-hour feature row.
5. Builds the required time-based, lagged, and rolling features.
6. Loads the trained Random Forest model.
7. Predicts the traffic volume for the next hour.

### Train the model first

From the repository root:

```bash
python script/train_model.py
```

This generates the model artifact at:

```text
models/traffic_volume_model.joblib
```

### Run prediction using a local CSV

```bash
python script/predict.py --csv data/traffic_cleaned.csv
```

### Run prediction using the API

For example, retrieve a historical range from the SQL API:

```bash
python script/predict.py --api-url "http://127.0.0.1:8000/sql/readings/range?start=2018-09-01T00:00:00&end=2018-09-30T23:00:00"
```

The selected date range must contain enough historical observations to calculate the required lag and rolling features.

The script prints:
- The latest observed hour.
- The prediction timestamp.
- The predicted next-hour traffic volume.

**Forecasting assumption:** The script assumes that the latest observed weather conditions persist into the next hour. This is an assumption, not a weather forecast.

---

## 9. Installation and Setup

### Prerequisites

Install the following before running the project:

- Python 3.10 or later (the deployment configuration specifies Python 3.12.7).
- MySQL 8 or later.
- MongoDB 7 or later.
- Git.
- Docker and Docker Compose (optional, for running the databases in containers).

### Step 1: Clone the repository

```bash
git clone <https://github.com/Janviere-dev/Formative-1_TimeSeries.git>
cd Formative-1_TimeSeries
```


### Step 2: Create and activate a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Update `.env` with the credentials and connection details for your local databases.

For the Docker Compose database configuration, use these local-host settings when running the Python loaders and API directly on your computer:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=traffic
MYSQL_PASSWORD=traffic
MYSQL_DATABASE=traffic

MONGO_URI=mongodb://localhost:27018
MONGO_DB=traffic
```

If you use independently installed MySQL and MongoDB servers, replace these values with your own database credentials and connection ports.

### Step 5: Start MySQL and MongoDB with Docker Compose

If you want to use the database containers defined in `docker-compose.yml`, run:

```bash
docker compose up -d mysql mongodb
```

Check the containers:

```bash
docker compose ps
```

### Step 6: Load the databases

After the database services are ready, run:

```bash
python -m SQL.load_mysql --reset
python -m mongodb.load_mongo --reset
```

### Step 7: Start the API

```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### Step 8: Train and evaluate the model

In another terminal, from the repository root:

```bash
python script/train_model.py
```

### Step 9: Generate a prediction

Using a local CSV:

```bash
python script/predict.py --csv data/traffic_cleaned.csv
```

Or using the running API:

```bash
python script/predict.py --api-url "http://127.0.0.1:8000/sql/readings/range?start=2018-09-01T00:00:00&end=2018-09-30T23:00:00"
```

---

## 10. Running Tests

The API test files are located in `api/tests/`.

Run the test suite from the repository root:

```bash
pytest
```

The tests cover API configuration, reading endpoints, and version-related functionality.

---

## 11. Deployment

The repository includes deployment configuration files:

- `Dockerfile` for building the API container.
- `docker-compose.yml` for running the API and database services locally.
- `render.yaml` for the Render web-service configuration.

The Render configuration expects the required database connection settings to be provided through the deployment environment. The databases must be reachable by the deployed API.

---

## 12. Project Outputs

Important generated outputs include:

| File | Description |
|---|---|
| `outputs/experiment_results.csv` | Validation comparison between baseline and tuned Random Forest experiments. |
| `outputs/training_summary.json` | Dataset split information, best parameters, and final test metrics. |
| `outputs/test_predictions.csv` | Actual and predicted traffic volumes for the test period. |
| `outputs/actual_vs_predicted.png` | Visualization comparing actual and predicted traffic volume. |
| `SQL/query_results.md` | SQL query statements and their results. |
| `mongodb/query_results.md` | MongoDB query statements and their results. |
| `mongodb/sample_documents.json` | Sample documents from the MongoDB collections. |
| `ERD/erd.png` | Entity Relationship Diagram for the MySQL database. |

---

## 13. Limitations and Future Improvements

- The next-hour prediction assumes that the latest weather conditions continue into the next hour.
- The source dataset contains gaps and repeated timestamps, which require careful preprocessing for time-series analysis.
- Forecast accuracy may be improved by incorporating reliable future weather forecasts and testing additional forecasting models.
- Further work could include more extensive API validation, monitoring, and deployment testing.

---

## 14. Conclusion

This project demonstrates an end-to-end time-series pipeline for traffic-volume analysis and forecasting. It combines exploratory data analysis, preprocessing, feature engineering, Random Forest model training, MySQL and MongoDB database implementation, FastAPI CRUD endpoints, and a prediction script.

The repository brings these components together to demonstrate how time-series data can be explored, stored, accessed, and used to generate short-term predictions.

---

## Contributors

1. Janviere Munezero
2. Kethia Ngabire Kayigire
3. Francoise Jeanne Beulla Rugero
4. Kaze Ange Santhiana
