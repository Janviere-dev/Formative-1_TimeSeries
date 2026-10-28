"""Create the MySQL schema and load the traffic CSV into it.

Usage (from the repo root):
    python -m SQL.load_mysql            # create schema + load (fails if data exists)
    python -m SQL.load_mysql --reset    # empty the tables first, then load

Connection settings come from api/config.py (env vars or a .env file):
MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE.
"""

import argparse
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.engine import Engine

from api.config import settings
from api.models import Holiday, TrafficReading, WeatherCondition
from common.dataset import load_readings

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
CHUNK_SIZE = 5000


def schema_statements(sql: str) -> list[str]:
    """Split schema.sql into statements, dropping comment-only chunks."""
    statements = []
    for chunk in sql.split(";"):
        body = "\n".join(line for line in chunk.splitlines() if not line.strip().startswith("--"))
        if body.strip():
            statements.append(body.strip())
    return statements


def create_schema() -> None:
    """Run schema.sql against the server (it creates the database itself)."""
    server_url = settings.sqlalchemy_url.rsplit("/", 1)[0]
    engine = create_engine(server_url)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    # schema.sql hardcodes the `traffic` database; follow MYSQL_DATABASE instead.
    sql = re.sub(r"\btraffic;", f"`{settings.mysql_database}`;", sql)
    with engine.begin() as conn:
        for statement in schema_statements(sql):
            conn.execute(text(statement))
    engine.dispose()


def reset_tables(engine: Engine) -> None:
    """Empty all three tables and restart their AUTO_INCREMENT ids at 1."""
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in (TrafficReading, WeatherCondition, Holiday):
            conn.execute(text(f"TRUNCATE TABLE {table.__tablename__}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def load(engine: Engine, df: pd.DataFrame) -> dict[str, int]:
    """Insert lookups first, then the readings with their foreign keys."""
    with engine.begin() as conn:
        holidays = sorted(df["holiday"].dropna().unique())
        conn.execute(insert(Holiday), [{"name": name} for name in holidays])
        holiday_ids = dict(conn.execute(select(Holiday.name, Holiday.id)).all())

        weather = df[["weather_main", "weather_description"]].drop_duplicates()
        conn.execute(insert(WeatherCondition), weather.to_dict("records"))
        weather_ids = {
            (main, desc): wid
            for wid, main, desc in conn.execute(
                select(WeatherCondition.id, WeatherCondition.weather_main,
                       WeatherCondition.weather_description)
            ).all()
        }

        rows = [
            {
                "date_time": r.date_time.to_pydatetime(),
                "temp": float(r.temp),
                "rain_1h": float(r.rain_1h),
                "snow_1h": float(r.snow_1h),
                "clouds_all": int(r.clouds_all),
                "traffic_volume": int(r.traffic_volume),
                "weather_id": weather_ids[(r.weather_main, r.weather_description)],
                "holiday_id": holiday_ids.get(r.holiday) if r.holiday else None,
            }
            for r in df.itertuples(index=False)
        ]
        for start in range(0, len(rows), CHUNK_SIZE):
            conn.execute(insert(TrafficReading), rows[start:start + CHUNK_SIZE])

    with engine.connect() as conn:
        return {
            table.__tablename__: conn.scalar(select(func.count()).select_from(table))
            for table in (Holiday, WeatherCondition, TrafficReading)
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete existing rows before loading")
    args = parser.parse_args()

    print(f"Creating schema on {settings.mysql_host}:{settings.mysql_port} ...")
    create_schema()
    engine = create_engine(settings.sqlalchemy_url)

    with engine.connect() as conn:
        existing = conn.scalar(select(func.count()).select_from(TrafficReading))
    if existing and not args.reset:
        raise SystemExit(f"traffic_readings already has {existing} rows; rerun with --reset to reload.")
    if args.reset:
        reset_tables(engine)

    df = load_readings()
    print(f"Loading {len(df)} cleaned readings ...")
    for table, count in load(engine, df).items():
        print(f"  {table:<20} {count:>6} rows")


if __name__ == "__main__":
    main()
