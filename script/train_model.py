from pathlib import Path
import json
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import ParameterGrid
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from preprocessing import load_source_data, make_hourly_series, build_features, get_model_columns

ROOT = Path(__file__).resolve().parents[1]
OUT, MODELS = ROOT / "outputs", ROOT / "models"
OUT.mkdir(exist_ok=True)
MODELS.mkdir(exist_ok=True)

def make_model(nums, cats, params):
    prep = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), nums),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), cats)
    ])
    return Pipeline([("prep", prep),
                     ("rf", RandomForestRegressor(random_state=42, n_jobs=-1, **params))])

def score(y, pred):
    return {"MAE": mean_absolute_error(y, pred),
            "RMSE": np.sqrt(mean_squared_error(y, pred)),
            "R2": r2_score(y, pred)}

def main():
    data = build_features(make_hourly_series(load_source_data()))
    print(f"Dataset prepared: {len(data)} observations", flush=True)
    nums, cats = get_model_columns()
    cols = nums + cats
    X, y = data[cols], data["traffic_volume"]
    n, v = len(data), int(len(data) * .70)
    t = int(len(data) * .85)
    Xtr, ytr = X.iloc[:v], y.iloc[:v]
    Xval, yval = X.iloc[v:t], y.iloc[v:t]
    Xtest, ytest = X.iloc[t:], y.iloc[t:]

    baseline = make_model(nums, cats, {"n_estimators": 100, "max_depth": 12, "min_samples_leaf": 2})
    baseline.fit(Xtr, ytr)
    print("Training baseline Random Forest model...", flush=True)
    results = [{"experiment": "Baseline Random Forest", **score(yval, baseline.predict(Xval))}]

    best_params, best_rmse = None, float("inf")
    for p in ParameterGrid({"n_estimators": [150, 250], "max_depth": [16, None], "min_samples_leaf": [1, 2]}):
        print(f"Testing parameters: {p}", flush=True)
        model = make_model(nums, cats, p)
        model.fit(Xtr, ytr)
        rmse = np.sqrt(mean_squared_error(yval, model.predict(Xval)))
        if rmse < best_rmse:
            best_params, best_rmse = p, rmse
    results.append({"experiment": "Tuned Random Forest", **score(yval, make_model(nums, cats, best_params).fit(Xtr, ytr).predict(Xval))})
    pd.DataFrame(results).to_csv(OUT / "experiment_results.csv", index=False)

    final_model = make_model(nums, cats, best_params)
    print("Training final model...", flush=True)
    final_model.fit(pd.concat([Xtr, Xval]), pd.concat([ytr, yval]))
    pred = final_model.predict(Xtest)
    test_scores = score(ytest, pred)
    comparison = pd.DataFrame({"date_time": data.iloc[t:]["date_time"], "actual": ytest, "predicted": pred})
    comparison.to_csv(OUT / "test_predictions.csv", index=False)
    plt.figure(figsize=(12, 5))
    plt.plot(comparison.date_time, comparison.actual, label="Actual")
    plt.plot(comparison.date_time, comparison.predicted, label="Predicted")
    plt.title("Hourly Traffic Volume: Actual vs Predicted")
    plt.xlabel("Date"); plt.ylabel("Traffic volume"); plt.legend(); plt.tight_layout()
    plt.savefig(OUT / "actual_vs_predicted.png", dpi=150); plt.close()
    joblib.dump({"model": final_model, "feature_columns": cols, "best_params": best_params},
                MODELS / "traffic_volume_model.joblib")
    (OUT / "training_summary.json").write_text(json.dumps({
        "rows": n, "train_rows": len(Xtr), "validation_rows": len(Xval),
        "test_rows": len(Xtest), "best_params": best_params, "test_metrics": test_scores
    }, indent=2))
    print(pd.DataFrame(results).to_string(index=False))
    print("Final test metrics:", test_scores)

if __name__ == "__main__":
    main()
