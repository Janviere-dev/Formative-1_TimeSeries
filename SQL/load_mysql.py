"""Load the cleaned Task 1 CSV into DB
Run from project root:
  python -m SQL.load_mysql --csv data/traffic_cleaned.csv
  python -m SQL.load_mysql --csv data/traffic_cleaned.csv --reset

Expected CSV columns: date_time, traffic_volume, temp, rain_1h, snow_1h,
clouds_all, weather_main, weather_description.
"""
import argparse
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required = {"date_time","traffic_volume","temp","rain_1h","snow_1h",
                "clouds_all","weather_main","weather_description"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing CSV columns: {sorted(missing)}")
    df["date_time"] = pd.to_datetime(df["date_time"], errors="raise")
    df = df.sort_values("date_time").drop_duplicates("date_time")
    if df["date_time"].duplicated().any():
        raise SystemExit("Duplicate timestamps remain; clean them in Task 1 first.")

    url = os.getenv("DATABASE_URL") or URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER","root"),
        password=os.getenv("MYSQL_PASSWORD",""),
        host=os.getenv("MYSQL_HOST","localhost"),
        port=int(os.getenv("MYSQL_PORT","3306")),
        database=os.getenv("MYSQL_DATABASE","traffic_timeseries")
    )
    engine = create_engine(url, pool_pre_ping=True)

    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(text(statement))

    with engine.begin() as conn:
        if args.reset:
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            conn.execute(text("TRUNCATE TABLE traffic_readings"))
            conn.execute(text("TRUNCATE TABLE weather_conditions"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        count = conn.execute(text("SELECT COUNT(*) FROM traffic_readings")).scalar_one()
        if count and not args.reset:
            raise SystemExit(f"traffic_readings already has {count} rows; use --reset to replace them.")

        location_id = conn.execute(text(
            "SELECT id FROM locations WHERE location_name='I-94 Minneapolis-St Paul'"
        )).scalar_one()

        weather_pairs = df[["weather_main","weather_description"]].drop_duplicates()
        weather_ids = {}
        for row in weather_pairs.itertuples(index=False):
            main = None if pd.isna(row.weather_main) else str(row.weather_main)
            desc = None if pd.isna(row.weather_description) else str(row.weather_description)
            conn.execute(text("""
              INSERT INTO weather_conditions(weather_main,weather_description)
              VALUES(:m,:d)
              ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
            """), {"m":main,"d":desc})
        for row in conn.execute(text(
            "SELECT id,weather_main,weather_description FROM weather_conditions"
        )).mappings():
            weather_ids[(row["weather_main"],row["weather_description"])] = row["id"]

        rows = []
        for r in df.itertuples(index=False):
            m = None if pd.isna(r.weather_main) else str(r.weather_main)
            d = None if pd.isna(r.weather_description) else str(r.weather_description)
            rows.append({
              "date_time":r.date_time.to_pydatetime(),
              "traffic_volume":int(r.traffic_volume),
              "temp":None if pd.isna(r.temp) else float(r.temp),
              "rain_1h":None if pd.isna(r.rain_1h) else float(r.rain_1h),
              "snow_1h":None if pd.isna(r.snow_1h) else float(r.snow_1h),
              "clouds_all":None if pd.isna(r.clouds_all) else float(r.clouds_all),
              "location_id":location_id,
              "weather_id":weather_ids.get((m,d))
            })
        for start in range(0,len(rows),5000):
            conn.execute(text("""
              INSERT INTO traffic_readings
              (date_time,traffic_volume,temp,rain_1h,snow_1h,clouds_all,location_id,weather_id)
              VALUES (:date_time,:traffic_volume,:temp,:rain_1h,:snow_1h,:clouds_all,:location_id,:weather_id)
            """), rows[start:start+5000])

        print("Loaded rows:", len(rows))
        for table in ("locations","weather_conditions","traffic_readings"):
            n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            print(f"{table}: {n}")
    engine.dispose()

if __name__ == "__main__":
    main()
