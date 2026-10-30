"""Load the traffic CSV into MongoDB (two collections) and export samples.

Usage (from the repo root):
    python -m mongodb.load_mongo            # load (fails if data exists)
    python -m mongodb.load_mongo --reset    # drop both collections first

Collections (see mongodb/README.md for the design rationale):
  traffic_readings  one flat document per hourly observation. Same shape the
                    FastAPI /mongo/readings endpoints read and write.
  daily_traffic     one document per calendar day with its 24 hourly values
                    embedded (bucket pattern) plus pre-computed daily stats.

Connection settings come from api/config.py: MONGO_URI, MONGO_DB.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from api.config import settings
from common.dataset import load_readings

HERE = Path(__file__).resolve().parent
SAMPLES_PATH = HERE / "sample_documents.json"
READINGS = "traffic_readings"
DAILY = "daily_traffic"
CHUNK_SIZE = 5000


def reading_documents(df: pd.DataFrame) -> list[dict]:
    """One flat document per row, matching api.schemas.ReadingCreate."""
    return [
        {
            "date_time": r.date_time.to_pydatetime(),
            "temp": float(r.temp),
            "rain_1h": float(r.rain_1h),
            "snow_1h": float(r.snow_1h),
            "clouds_all": int(r.clouds_all),
            "traffic_volume": int(r.traffic_volume),
            "weather_main": r.weather_main,
            "weather_description": r.weather_description,
            "holiday": r.holiday,
        }
        for r in df.itertuples(index=False)
    ]


def daily_documents(df: pd.DataFrame) -> list[dict]:
    """One document per day with the hourly series embedded."""
    # Collapse repeated timestamps (one row per weather condition) to one hour.
    hourly = (
        df.groupby("date_time")
        .agg(
            traffic_volume=("traffic_volume", "first"),
            temp=("temp", "mean"),
            rain_1h=("rain_1h", "mean"),
            snow_1h=("snow_1h", "mean"),
            clouds_all=("clouds_all", "mean"),
            weather=("weather_main", lambda s: list(dict.fromkeys(s))),
            holiday=("holiday", "first"),
        )
        .reset_index()
    )
    hourly["day"] = hourly["date_time"].dt.normalize()

    docs = []
    for day, g in hourly.groupby("day"):
        peak = g.loc[g["traffic_volume"].idxmax()]
        weather_counts: dict[str, int] = {}
        for conditions in g["weather"]:
            for condition in conditions:
                weather_counts[condition] = weather_counts.get(condition, 0) + 1
        holiday = g["holiday"].dropna()
        docs.append({
            "_id": day.strftime("%Y-%m-%d"),
            "date": day.to_pydatetime(),
            "day_of_week": day.day_name(),
            "is_weekend": day.dayofweek >= 5,
            "holiday": holiday.iloc[0] if len(holiday) else None,
            "hours_recorded": len(g),
            "total_volume": int(g["traffic_volume"].sum()),
            "avg_hourly_volume": round(float(g["traffic_volume"].mean()), 1),
            "peak": {"hour": int(peak["date_time"].hour), "traffic_volume": int(peak["traffic_volume"])},
            "avg_temp_k": round(float(g["temp"].mean()), 2),
            "total_rain_mm": round(float(g["rain_1h"].sum()), 2),
            "total_snow_mm": round(float(g["snow_1h"].sum()), 2),
            "weather_hours": weather_counts,
            "hourly": [
                {
                    "hour": int(h.date_time.hour),
                    "traffic_volume": int(h.traffic_volume),
                    "temp": round(float(h.temp), 2),
                    "clouds_all": int(round(h.clouds_all)),
                    "weather": h.weather,
                }
                for h in g.itertuples(index=False)
            ],
        })
    return docs


def create_indexes(db: Database) -> None:
    # Range scans and "latest" lookups both walk this index.
    db[READINGS].create_index([("date_time", ASCENDING)])
    db[READINGS].create_index([("weather_main", ASCENDING), ("date_time", ASCENDING)])
    db[DAILY].create_index([("date", DESCENDING)])
    db[DAILY].create_index([("holiday", ASCENDING)], sparse=True)


def export_samples(db: Database) -> None:
    """Write a few real documents to sample_documents.json for the report."""
    def clean(doc: dict) -> dict:
        return json.loads(json.dumps(doc, default=lambda v: v.isoformat() if isinstance(v, datetime) else str(v)))

    samples = {
        READINGS: [clean(d) for d in db[READINGS].find({"date_time": datetime(2018, 9, 27, 7)})]
                  + [clean(db[READINGS].find_one({"holiday": "Labor Day"}, sort=[("date_time", -1)]))],
        DAILY: [clean(db[DAILY].find_one({"_id": "2018-09-27"}))],
    }
    SAMPLES_PATH.write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")


def load(db: Database, df: pd.DataFrame) -> dict[str, int]:
    readings = reading_documents(df)
    for start in range(0, len(readings), CHUNK_SIZE):
        db[READINGS].insert_many(readings[start:start + CHUNK_SIZE])
    db[DAILY].insert_many(daily_documents(df))
    create_indexes(db)
    return {name: db[name].count_documents({}) for name in (READINGS, DAILY)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="drop both collections before loading")
    args = parser.parse_args()

    db = MongoClient(settings.mongo_uri)[settings.mongo_db]
    existing = db[READINGS].estimated_document_count()
    if existing and not args.reset:
        raise SystemExit(f"{READINGS} already has {existing} documents; rerun with --reset to reload.")
    if args.reset:
        db.drop_collection(READINGS)
        db.drop_collection(DAILY)

    df = load_readings()
    print(f"Loading {len(df)} cleaned readings into {settings.mongo_uri} / {settings.mongo_db} ...")
    for name, count in load(db, df).items():
        print(f"  {name:<17} {count:>6} documents")
    export_samples(db)
    print(f"Saved {SAMPLES_PATH}")


if __name__ == "__main__":
    main()
