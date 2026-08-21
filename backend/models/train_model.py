"""
VAYU - XGBoost Atmospheric AQI Predictive Model Training Pipeline
Constructs temporal lag features, U/V wind vectors, boundary layer inversion factors,
fits XGBRegressor(n_estimators=300, lr=0.03, max_depth=6), benchmarks validation RMSE,
and exports the pre-trained weights artifact to backend/models/aqi_model.json (~2 MB).
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


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs feature matrix:
    - Temporal lags: AQI(t-1), AQI(t-3), AQI(t-24)
    - Meteorological vectors: U & V wind components
    - Boundary layer inversion factor: 1000 / BLH
    - Calendar signals: hour, day of week, month, day of year sin/cos
    """
    logger.info("Constructing feature matrix with temporal lags and meteorological physics...")

    # Ensure chronological sort by station and time
    df = df.sort_values(by=["station_id", "time"]).reset_index(drop=True)

    # 1. Temporal Lags (computed per station)
    df["aqi_lag_1h"] = df.groupby("station_id")["aqi"].shift(1)
    df["aqi_lag_3h"] = df.groupby("station_id")["aqi"].shift(3)
    df["aqi_lag_24h"] = df.groupby("station_id")["aqi"].shift(24)

    # 2. Wind Components U & V
    rad = np.radians(df["wind_direction_10m"].values)
    df["wind_u"] = -df["wind_speed_10m"] * np.sin(rad)
    df["wind_v"] = -df["wind_speed_10m"] * np.cos(rad)

    # 3. Inversion Factor (lower BLH = higher entrapment)
    df["inversion_factor"] = 1000.0 / np.clip(df["boundary_layer_height"], 100.0, 3000.0)

    # 4. Calendar Signals
    if not pd.api.types.is_datetime64_any_dtype(df["time"]):
        df["time"] = pd.to_datetime(df["time"])

    df["hour"] = df["time"].dt.hour
    df["dayofweek"] = df["time"].dt.dayofweek
    df["month"] = df["time"].dt.month
    df["dayofyear"] = df["time"].dt.dayofyear

    # Cyclical encodings
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["doy_sin"] = np.sin(2 * np.pi * df["dayofyear"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["dayofyear"] / 365.25)

    # Clean initial NaN lag rows
    clean_df = df.dropna().reset_index(drop=True)
    logger.info(f"Cleaned feature matrix: {len(clean_df)} complete samples.")
    return clean_df


FEATURE_COLUMNS = [
    "aqi_lag_1h",
    "aqi_lag_3h",
    "aqi_lag_24h",
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


def train_aqi_model():
    """
    Trains XGBoost regressor, evaluates on held-out temporal validation split,
    benchmarks against persistence baseline, and exports aqi_model.json.
    """
    if not os.path.exists(TRAINING_CSV_PATH):
        logger.info(f"{TRAINING_CSV_PATH} not found. Generating training data matrix...")
        raw_df = generate_training_matrix(TRAINING_CSV_PATH)
    else:
        logger.info(f"Loading existing training dataset from {TRAINING_CSV_PATH}...")
        raw_df = pd.read_csv(TRAINING_CSV_PATH)

    feat_df = build_features(raw_df)

    # Chronological train-validation split (last 20% time horizon)
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

    # Fit XGBRegressor
    logger.info("Fitting XGBRegressor(n_estimators=300, learning_rate=0.03, max_depth=6)...")
    model = xgb.XGBRegressor(
        n_estimators=300,
        learning_rate=0.03,
        max_depth=6,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        tree_method="hist",
        n_jobs=-1
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=50
    )

    # Benchmark Evaluations
    y_pred = model.predict(X_test)
    y_persistence = X_test["aqi_lag_1h"].values

    rmse_model = np.sqrt(mean_squared_error(y_test, y_pred))
    mae_model = mean_absolute_error(y_test, y_pred)
    r2_model = r2_score(y_test, y_pred)

    rmse_persist = np.sqrt(mean_squared_error(y_test, y_persistence))
    mae_persist = mean_absolute_error(y_test, y_persistence)

    logger.info("=" * 65)
    logger.info("MODEL EVALUATION & VALIDATION BENCHMARK RESULTS")
    logger.info("=" * 65)
    logger.info(f"VAYU XGBoost Model   -> RMSE: {rmse_model:.2f} | MAE: {mae_model:.2f} | R²: {r2_model:.4f}")
    logger.info(f"Persistence Baseline -> RMSE: {rmse_persist:.2f} | MAE: {mae_persist:.2f}")
    logger.info(f"RMSE Improvement Over Persistence: {((rmse_persist - rmse_model) / rmse_persist) * 100:.2f}%")
    logger.info("=" * 65)

    # Feature importances
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    logger.info("Top Predictive Atmospheric Features:")
    for idx in sorted_idx[:7]:
        logger.info(f"  - {FEATURE_COLUMNS[idx]}: {importances[idx]:.4f}")

    # Export Model Artifact
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    model.save_model(MODEL_OUTPUT_PATH)
    file_size_mb = os.path.getsize(MODEL_OUTPUT_PATH) / (1024 * 1024)
    logger.info(f"Successfully exported pre-trained model artifact to {MODEL_OUTPUT_PATH} ({file_size_mb:.2f} MB)")

    return model


if __name__ == "__main__":
    train_aqi_model()
