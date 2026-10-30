
"""Predict next-hour traffic volume using API JSON or a local CSV."""

import argparse
from pathlib import Path

import joblib
import pandas as pd
import requests

from preprocessing import make_hourly_series, build_features

ROOT = Path(__file__).resolve().parents[1]


def records_from(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("records", "data", "results", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]

    raise ValueError(
        "Expected a JSON list or records/data/results/items list."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Predict traffic volume for the next hour."
    )

    parser.add_argument("--api-url", help="API endpoint returning historical readings.")
    parser.add_argument("--csv", help="Local CSV file containing historical readings.")

    args = parser.parse_args()

    if args.csv:
        raw = pd.read_csv(args.csv)

    elif args.api_url:
        response = requests.get(args.api_url, timeout=30)
        response.raise_for_status()
        raw = pd.DataFrame(records_from(response.json()))

    else:
        parser.error("Supply --api-url or --csv.")

    if raw.empty:
        raise ValueError("No historical observations were received.")

    raw["date_time"] = pd.to_datetime(raw["date_time"])
    raw = raw.sort_values("date_time")

    # Create one observation per hour.
    hourly = make_hourly_series(raw)

    if hourly.empty:
        raise ValueError("No hourly observations available.")

    latest_time = hourly["date_time"].max()

    # Create a new row for the next hour.
    # Weather values are assumed to persist from the latest observation.
    future_row = hourly.iloc[-1].copy()
    future_row["date_time"] = latest_time + pd.Timedelta(hours=1)

    # Placeholder target: it is not used as a model feature.
    # It allows the existing feature builder to calculate the future
    # row's lag and rolling features from historical traffic.
    future_row["traffic_volume"] = 0.0

    hourly_with_future = pd.concat(
        [hourly, pd.DataFrame([future_row])],
        ignore_index=True,
    )

    features = build_features(hourly_with_future)

    future_features = features[
        features["date_time"] == latest_time + pd.Timedelta(hours=1)
    ]

    if future_features.empty:
        raise ValueError(
            "Not enough valid hourly history to calculate next-hour features."
        )

    # Load the trained model.
    artifact = joblib.load(
        ROOT / "models" / "traffic_volume_model.joblib"
    )

    feature_columns = artifact["feature_columns"]

    X_future = future_features[feature_columns]

    prediction = artifact["model"].predict(X_future)[0]

    print("Latest observed hour:", latest_time)
    print(
        "Prediction time:",
        latest_time + pd.Timedelta(hours=1),
    )
    print(
        f"Next-hour predicted traffic volume: {prediction:.2f}"
    )
    print(
        "Weather assumption: latest observed weather conditions persist."
    )


if __name__ == "__main__":
    main()
