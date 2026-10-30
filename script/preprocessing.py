
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_source_data():
    from common.dataset import load_readings
    return load_readings()


def make_hourly_series(df):
    df = df.copy()
    df["date_time"] = pd.to_datetime(df["date_time"])

    numeric = [
        "temp",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "traffic_volume",
    ]

    categorical = [
        "holiday",
        "weather_main",
        "weather_description",
    ]

    def mode_or_none(series):
        mode = series.dropna().mode()
        return mode.iloc[0] if len(mode) else None

    agg = {
        col: "mean"
        for col in numeric
        if col in df.columns
    }

    agg.update({
        col: mode_or_none
        for col in categorical
        if col in df.columns
    })

    hourly = (
        df.groupby("date_time")
        .agg(agg)
        .sort_index()
    )

    # Create a complete hourly timeline.
    hourly = hourly.reindex(
        pd.date_range(
            hourly.index.min(),
            hourly.index.max(),
            freq="h",
        )
    )

    hourly.index.name = "date_time"

    return hourly.reset_index()


def build_features(hourly):
    df = hourly.copy()

    dt = pd.to_datetime(df["date_time"])

    df["hour"] = dt.dt.hour
    df["day_of_week"] = dt.dt.dayofweek
    df["month"] = dt.dt.month
    df["day_of_year"] = dt.dt.dayofyear
    df["is_weekend"] = (
        dt.dt.dayofweek >= 5
    ).astype(int)

    y = df["traffic_volume"]

    df["lag_1"] = y.shift(1)
    df["lag_24"] = y.shift(24)

    df["rolling_mean_24"] = (
        y.shift(1)
        .rolling(24, min_periods=24)
        .mean()
    )

    # Only retain observations with a known target
    # and sufficient historical traffic information.
    df = df.dropna(
        subset=[
            "traffic_volume",
            "lag_1",
            "lag_24",
            "rolling_mean_24",
        ]
    )

    return df.reset_index(drop=True)


def get_model_columns():
    numeric = [
        "temp",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "hour",
        "day_of_week",
        "month",
        "day_of_year",
        "is_weekend",
        "lag_1",
        "lag_24",
        "rolling_mean_24",
    ]

    categorical = [
        "holiday",
        "weather_main",
        "weather_description",
    ]

    return numeric, categorical
