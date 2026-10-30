"""Run the MongoDB queries and save the results as Markdown.

Usage (from the repo root, after `python -m mongodb.load_mongo`):
    python -m mongodb.run_queries

Each query is listed with its mongosh form (what you would type in the shell)
and run through pymongo. Results go to mongodb/query_results.md.
"""

import json
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient
from pymongo.database import Database

from api.config import settings

RESULTS_PATH = Path(__file__).resolve().parent / "query_results.md"

QUERIES = [
    {
        "title": "M1 - Latest record (most recent hourly reading)",
        "shell": 'db.traffic_readings.find({}, {_id: 0}).sort({date_time: -1, _id: -1}).limit(1)',
        "run": lambda db: db.traffic_readings.find({}, {"_id": 0})
        .sort([("date_time", -1), ("_id", -1)]).limit(1),
    },
    {
        "title": "M2 - Records by date range (evening of 2018-09-30, 17:00-23:00)",
        "shell": (
            "db.traffic_readings.find(\n"
            '  {date_time: {$gte: ISODate("2018-09-30T17:00:00Z"), $lte: ISODate("2018-09-30T23:00:00Z")}},\n'
            "  {_id: 0, date_time: 1, traffic_volume: 1, weather_main: 1, temp: 1}\n"
            ").sort({date_time: 1})"
        ),
        "run": lambda db: db.traffic_readings.find(
            {"date_time": {"$gte": datetime(2018, 9, 30, 17), "$lte": datetime(2018, 9, 30, 23)}},
            {"_id": 0, "date_time": 1, "traffic_volume": 1, "weather_main": 1, "temp": 1},
        ).sort("date_time", 1),
    },
    {
        "title": "M3 - Average traffic by hour of day (aggregation pipeline)",
        "shell": (
            "db.traffic_readings.aggregate([\n"
            "  // collapse repeated timestamps (one doc per weather condition) to one per hour\n"
            '  {$group: {_id: "$date_time", volume: {$first: "$traffic_volume"}}},\n'
            '  {$group: {_id: {$hour: "$_id"}, avg_volume: {$avg: "$volume"}, hours: {$sum: 1}}},\n'
            '  {$project: {_id: 0, hour_of_day: "$_id", hours: 1, avg_volume: {$round: ["$avg_volume", 0]}}},\n'
            "  {$sort: {hour_of_day: 1}}\n"
            "])"
        ),
        "run": lambda db: db.traffic_readings.aggregate([
            {"$group": {"_id": "$date_time", "volume": {"$first": "$traffic_volume"}}},
            {"$group": {"_id": {"$hour": "$_id"}, "avg_volume": {"$avg": "$volume"}, "hours": {"$sum": 1}}},
            {"$project": {"_id": 0, "hour_of_day": "$_id", "hours": 1,
                          "avg_volume": {"$round": ["$avg_volume", 0]}}},
            {"$sort": {"hour_of_day": 1}},
        ]),
    },
    {
        "title": "M4 - Readings and average traffic per weather category",
        "shell": (
            "db.traffic_readings.aggregate([\n"
            '  {$group: {_id: "$weather_main", readings: {$sum: 1},\n'
            '            avg_volume: {$avg: "$traffic_volume"}, avg_temp_k: {$avg: "$temp"}}},\n'
            '  {$project: {_id: 0, weather_main: "$_id", readings: 1,\n'
            '              avg_volume: {$round: ["$avg_volume", 0]},\n'
            '              avg_temp_c: {$round: [{$subtract: ["$avg_temp_k", 273.15]}, 1]}}},\n'
            "  {$sort: {readings: -1}}\n"
            "])"
        ),
        "run": lambda db: db.traffic_readings.aggregate([
            {"$group": {"_id": "$weather_main", "readings": {"$sum": 1},
                        "avg_volume": {"$avg": "$traffic_volume"}, "avg_temp_k": {"$avg": "$temp"}}},
            {"$project": {"_id": 0, "weather_main": "$_id", "readings": 1,
                          "avg_volume": {"$round": ["$avg_volume", 0]},
                          "avg_temp_c": {"$round": [{"$subtract": ["$avg_temp_k", 273.15]}, 1]}}},
            {"$sort": {"readings": -1}},
        ]),
    },
    {
        "title": "M5 - Weekday vs weekend vs holiday daily traffic (daily_traffic buckets)",
        "shell": (
            "db.daily_traffic.aggregate([\n"
            "  {$match: {hours_recorded: {$gte: 20}}},\n"
            "  {$group: {\n"
            '    _id: {$cond: [{$ne: ["$holiday", null]}, "holiday",\n'
            '                  {$cond: ["$is_weekend", "weekend", "weekday"]}]},\n'
            '    days: {$sum: 1}, avg_daily_volume: {$avg: "$total_volume"},\n'
            '    avg_peak_hour: {$avg: "$peak.hour"}}},\n'
            '  {$project: {_id: 0, day_type: "$_id", days: 1,\n'
            '              avg_daily_volume: {$round: ["$avg_daily_volume", 0]},\n'
            '              avg_peak_hour: {$round: ["$avg_peak_hour", 1]}}},\n'
            "  {$sort: {avg_daily_volume: -1}}\n"
            "])"
        ),
        "run": lambda db: db.daily_traffic.aggregate([
            {"$match": {"hours_recorded": {"$gte": 20}}},
            {"$group": {
                "_id": {"$cond": [{"$ne": ["$holiday", None]}, "holiday",
                                  {"$cond": ["$is_weekend", "weekend", "weekday"]}]},
                "days": {"$sum": 1}, "avg_daily_volume": {"$avg": "$total_volume"},
                "avg_peak_hour": {"$avg": "$peak.hour"}}},
            {"$project": {"_id": 0, "day_type": "$_id", "days": 1,
                          "avg_daily_volume": {"$round": ["$avg_daily_volume", 0]},
                          "avg_peak_hour": {"$round": ["$avg_peak_hour", 1]}}},
            {"$sort": {"avg_daily_volume": -1}},
        ]),
    },
    {
        "title": "M6 - Five busiest days on record (embedded peak sub-document)",
        "shell": (
            "db.daily_traffic.find({}, {_id: 1, day_of_week: 1, holiday: 1, total_volume: 1, peak: 1})\n"
            "  .sort({total_volume: -1}).limit(5)"
        ),
        "run": lambda db: db.daily_traffic.find(
            {}, {"_id": 1, "day_of_week": 1, "holiday": 1, "total_volume": 1, "peak": 1}
        ).sort("total_volume", -1).limit(5),
    },
    {
        "title": "M7 - Hourly series for one day via $unwind (input window for forecasting)",
        "shell": (
            "db.daily_traffic.aggregate([\n"
            '  {$match: {_id: "2018-09-30"}},\n'
            '  {$unwind: "$hourly"},\n'
            '  {$match: {"hourly.hour": {$gte: 12}}},\n'
            '  {$project: {_id: 0, day: "$_id", hour: "$hourly.hour",\n'
            '              traffic_volume: "$hourly.traffic_volume", weather: "$hourly.weather"}}\n'
            "])"
        ),
        "run": lambda db: db.daily_traffic.aggregate([
            {"$match": {"_id": "2018-09-30"}},
            {"$unwind": "$hourly"},
            {"$match": {"hourly.hour": {"$gte": 12}}},
            {"$project": {"_id": 0, "day": "$_id", "hour": "$hourly.hour",
                          "traffic_volume": "$hourly.traffic_volume", "weather": "$hourly.weather"}},
        ]),
    },
]


def to_jsonable(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    return str(value)


def run_all(db: Database, source: str) -> str:
    sections = [
        "# MongoDB query results",
        "",
        f"Generated by `python -m mongodb.run_queries` on {datetime.now():%Y-%m-%d %H:%M} "
        f"against `{source}`.",
    ]
    for query in QUERIES:
        docs = list(query["run"](db))
        print(f"{query['title']}: {len(docs)} documents")
        sections += [
            "", f"## {query['title']}", "", "```javascript", query["shell"], "```", "",
            f"**Result ({len(docs)} documents):**", "", "```json",
            json.dumps(docs, indent=2, default=to_jsonable), "```",
        ]
    return "\n".join(sections) + "\n"


def main() -> None:
    db = MongoClient(settings.mongo_uri)[settings.mongo_db]
    RESULTS_PATH.write_text(run_all(db, f"{settings.mongo_uri} / {settings.mongo_db}"), encoding="utf-8")
    print(f"Saved {RESULTS_PATH}")


if __name__ == "__main__":
    main()
