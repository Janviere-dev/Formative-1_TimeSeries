"""Shared loading/cleaning of the Metro Interstate Traffic Volume CSV.

Both database loaders (MySQL and MongoDB) call `load_readings()` so the two
stores always hold exactly the same records.

Cleaning applied before storage (kept deliberately light, the databases hold
the raw hourly observations and Task 1/Task 4 do the modelling preprocessing):
  1. Exact duplicate rows are dropped (17 rows in the source file).
  2. The string "None" in `holiday` becomes a real NULL/None.
  3. The source only labels the *midnight* row of a holiday. The label is
     propagated to every hour of that same date, matching the date-based
     filling used in the Task 1 notebook.
  4. `weather_description` is lower-cased, merging "Sky is Clear" into
     "sky is clear" (the only case-only duplicate, 1,726 rows).
  5. `date_time` is parsed to a real datetime so both databases can index it
     and run range queries.

Rows that share a timestamp are kept: the source records one row per weather
condition observed in that hour (e.g. "Rain" and "Mist" at 10:00), and each
row maps to one weather_conditions entry in SQL.
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "Metro_Interstate_Traffic_Volume.csv"

READING_COLUMNS = [
    "date_time",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "traffic_volume",
    "weather_main",
    "weather_description",
    "holiday",
]


def load_readings(csv_path: Path = CSV_PATH) -> pd.DataFrame:
    """Return the cleaned readings, sorted by time, with READING_COLUMNS."""
    # keep_default_na=False stops pandas turning the literal "None" into NaN
    # silently; we convert it ourselves so the rule is explicit.
    df = pd.read_csv(csv_path, keep_default_na=False)
    df = df.drop_duplicates().copy()

    df["date_time"] = pd.to_datetime(df["date_time"], format="%Y-%m-%d %H:%M:%S")
    df["holiday"] = df["holiday"].str.strip().replace({"None": None, "": None})

    # Spread each holiday label from its midnight row to the whole day.
    date = df["date_time"].dt.date
    label_by_date = df.dropna(subset=["holiday"]).groupby(date)["holiday"].first()
    df["holiday"] = df["holiday"].fillna(date.map(label_by_date))
    df["holiday"] = df["holiday"].astype(object).where(df["holiday"].notna(), None)

    df["weather_main"] = df["weather_main"].str.strip()
    # The source spells one condition two ways ("sky is clear" / "Sky is Clear");
    # MySQL's default collation treats them as equal and the unique key rejects it.
    df["weather_description"] = df["weather_description"].str.strip().str.lower()

    return df.sort_values("date_time", kind="stable").reset_index(drop=True)[READING_COLUMNS]
