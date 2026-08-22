"""
VAYU - XGBoost Atmospheric AQI Predictive Model Training Pipeline
Constructs temporal lag features, U/V wind vectors, boundary layer inversion factors,
fits XGBRegressor(n_estimators=300, lr=0.03, max_depth=6), benchmarks validation RMSE,
and exports the pre-trained weights artifact to backend/models/aqi_model.json.
"""

import os
import math
import json
import logging
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from backend.models.fetch_historical import generate_training_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_OUTPUT_PATH = "backend/models/aqi_model.json"
TRAINING_CSV_PATH = "backend/models/training_data.csv"

FEATURE_COLUMNS = [
    "aqi_lag_1h",
    "aqi_lag_2h",
    "aqi_lag_3h",
    "aqi_lag_24h",
    "station_base",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_u",
    "wind_v",
    "surface_pressure",
    "boundary_layer_height",
    "inversion_factor",
    "hour",
    "dayofweek",
    "month",
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(by=["station_id", "time"]).reset_index(drop=True)

    df["aqi_lag_1h"] = df.groupby("station_id")["aqi"].shift(1)
    df["aqi_lag_2h"] = df.groupby("station_id")["aqi"].shift(2)
    df["aqi_lag_3h"] = df.groupby("station_id")["aqi"].shift(3)
    df["aqi_lag_24h"] = df.groupby("station_id")["aqi"].shift(24)

    rad = np.radians(df["wind_direction_10m"].values)
    df["wind_u"] = -df["wind_speed_10m"] * np.sin(rad)
    df["wind_v"] = -df["wind_speed_10m"] * np.cos(rad)

    df["inversion_factor"] = 1000.0 / np.clip(df["boundary_layer_height"], 100.0, 3000.0)

    if not pd.api.types.is_datetime64_any_dtype(df["time"]):
        df["time"] = pd.to_datetime(df["time"])

    df["hour"] = df["time"].dt.hour
    df["dayofweek"] = df["time"].dt.dayofweek
    df["month"] = df["time"].dt.month
    df["dayofyear"] = df["time"].dt.dayofyear

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["doy_sin"] = np.sin(2 * np.pi * df["dayofyear"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["dayofyear"] / 365.25)

    clean_df = df.dropna().reset_index(drop=True)
    return clean_df


def train_aqi_model():
    logger.info("Generating calibrated training data matrix...")
    raw_df = generate_training_matrix(TRAINING_CSV_PATH)

    feat_df = build_features(raw_df)

    unique_times = np.sort(feat_df["time"].unique())
    split_idx = int(len(unique_times) * 0.8)
    split_time = unique_times[split_idx]

    train_mask = feat_df["time"] < split_time
    test_mask = feat_df["time"] >= split_time

    X_train = feat_df.loc[train_mask, FEATURE_COLUMNS]
    y_train = feat_df.loc[train_mask, "aqi"]
    X_test = feat_df.loc[test_mask, FEATURE_COLUMNS]
    y_test = feat_df.loc[test_mask, "aqi"]

    logger.info(f"Training samples: {len(X_train)} | Validation samples: {len(X_test)}")

    model = xgb.XGBRegressor(
        n_estimators=350,
        learning_rate=0.04,
        max_depth=7,
        subsample=0.88,
        colsample_bytree=0.88,
        random_state=42,
        tree_method="hist",
        n_jobs=-1
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=100
    )

    y_pred = model.predict(X_test)
    y_persistence = X_test["aqi_lag_1h"].values

    rmse_model = np.sqrt(mean_squared_error(y_test, y_pred))
    mae_model = mean_absolute_error(y_test, y_pred)
    r2_model = r2_score(y_test, y_pred)
    mape_model = np.mean(np.abs(y_test - y_pred) / np.maximum(20.0, y_test))
    accuracy_pct = (1.0 - mape_model) * 100.0

    rmse_persist = np.sqrt(mean_squared_error(y_test, y_persistence))
    mae_persist = mean_absolute_error(y_test, y_persistence)

    logger.info("=" * 65)
    logger.info(f"CALIBRATED XGBoost Model -> Accuracy: {accuracy_pct:.2f}% | R²: {r2_model:.4f} | RMSE: {rmse_model:.2f} | MAE: {mae_model:.2f}")
    logger.info(f"Persistence Baseline    -> RMSE: {rmse_persist:.2f} | MAE: {mae_persist:.2f}")
    logger.info(f"RMSE Improvement: {((rmse_persist - rmse_model) / rmse_persist) * 100:.2f}%")
    logger.info("=" * 65)

    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    model.save_model(MODEL_OUTPUT_PATH)
    logger.info(f"Exported model to {MODEL_OUTPUT_PATH}")

    return model


if __name__ == "__main__":
    train_aqi_model()
