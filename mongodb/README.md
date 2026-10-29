# MongoDB collection design

| File | What it does |
|---|---|
| [`load_mongo.py`](load_mongo.py) | Cleans the CSV (`common/dataset.py`), fills both collections, creates the indexes and exports `sample_documents.json`. |
| [`sample_documents.json`](sample_documents.json) | Real documents from each collection. |
| [`run_queries.py`](run_queries.py) | The 7 Task 2 queries in mongosh form and pymongo form. Writes [`query_results.md`](query_results.md). |

## Run it

From the repo root, with MongoDB running and `.env` filled in:

```bash
python -m mongodb.load_mongo --reset
python -m mongodb.run_queries
```

Expected load output: `traffic_readings 48187`, `daily_traffic 1860` documents.

## Collections

### 1. `traffic_readings`: one document per hourly observation

```json
{
  "_id": ObjectId("..."),
  "date_time": ISODate("2018-09-27T07:00:00Z"),
  "temp": 285.17,
  "rain_1h": 0.0,
  "snow_1h": 0.0,
  "clouds_all": 90,
  "traffic_volume": 6589,
  "weather_main": "Rain",
  "weather_description": "light rain",
  "holiday": null
}
```

* **Flat and denormalised.** Weather and holiday are stored inline, not as references. In SQL they needed lookup tables, but in MongoDB each document is read in one go with no `$lookup`. This is the collection the FastAPI `/mongo/readings` CRUD endpoints use, so its fields match `api/schemas.py`.
* **`date_time` is a real BSON `Date`**, not a string, so range queries (`$gte`/`$lte`) and date operators (`$hour`) work.
* **Indexes:** `{date_time: 1}` serves the latest-record and date-range queries. `{weather_main: 1, date_time: 1}` serves weather-filtered time ranges.

### 2. `daily_traffic`: one document per day (bucket pattern)

```json
{
  "_id": "2018-09-27",
  "date": ISODate("2018-09-27T00:00:00Z"),
  "day_of_week": "Thursday",
  "is_weekend": false,
  "holiday": null,
  "hours_recorded": 24,
  "total_volume": 87845,
  "avg_hourly_volume": 3660.2,
  "peak": { "hour": 7, "traffic_volume": 6589 },
  "avg_temp_k": 286.31,
  "total_rain_mm": 0.5,
  "total_snow_mm": 0.0,
  "weather_hours": { "Clouds": 15, "Drizzle": 3, "Rain": 4, "Clear": 3 },
  "hourly": [
    { "hour": 0, "traffic_volume": 654,  "temp": 285.26, "clouds_all": 40, "weather": ["Clouds"] },
    { "hour": 7, "traffic_volume": 6589, "temp": 285.17, "clouds_all": 90, "weather": ["Rain", "Drizzle"] }
  ]
}
```

(`hourly` holds all 24 entries. See `sample_documents.json` for the full document.)

* **Bucket pattern.** Time-series data is usually read a whole window at a time. One document holds a full day, so a 24-hour input window for the model is a single read instead of 24.
* **Embedded `hourly` array.** It is bounded: never more than 24 elements, so it can't grow without limit. Hours with several weather reports become one entry with a `weather` array, which removes the duplicate-timestamp problem from the raw rows.
* **Pre-computed stats** (`total_volume`, `peak`, `weather_hours`, `is_weekend`) make daily dashboards and the weekday/holiday comparison cheap.
* **Natural `_id`** (the date string) makes "get day X" an `_id` lookup and stops a day being inserted twice.
* **Indexes:** `{date: -1}` for most-recent days and `{holiday: 1}` (sparse) for holiday look-ups.

`daily_traffic` is derived from `traffic_readings`. Rerun `load_mongo.py --reset` after bulk changes to rebuild it.

## Queries

| # | Question | Mongo features |
|---|---|---|
| M1 | Latest record | `find().sort().limit(1)` |
| M2 | Records by date range | `$gte` / `$lte` on a `Date`, projection |
| M3 | Average traffic by hour of day | Two-stage `$group`, `$hour` |
| M4 | Traffic per weather category | `$group`, `$project`, arithmetic |
| M5 | Weekday vs weekend vs holiday | `$match`, `$cond`, uses the bucket collection |
| M6 | Five busiest days | Sort on pre-computed field, embedded `peak` |
| M7 | Hourly series for one day | `$unwind` of the embedded array |
