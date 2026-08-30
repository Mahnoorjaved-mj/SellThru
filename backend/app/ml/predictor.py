"""Machine Learning Sales Predictor.

Uses Scikit-Learn RandomForestRegressor to perform daily sales forecasting.
Features engineered: day of week, day of month, month, year, weekend flag,
holiday flag, promo flag, lag features (7-day lag), and rolling average features.
Includes a robust fallback to a statistical seasonal model and a database seeder.

Note: this is the Phase-1 relocation of the original predictor with org_id
scoping bolted on (one model artifact per org). The feature engineering,
backtesting, and model registry described in Section 8 of the build brief
are Phase 5 work — not done here.
"""
from __future__ import annotations

import logging
import os
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

from app.repositories import models_repo, sales_repo
from app.ml.holidays import holiday_flags
from app.ml.metrics import all_metrics, wape

log = logging.getLogger("forecastiq.ml")
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "saved_models"
os.makedirs(MODELS_DIR, exist_ok=True)


class AIPredictor:
    """Each trained version gets its own artifact file so a "candidate" that
    doesn't get promoted never overwrites the artifact `predict()` actually
    serves — that's looked up from whichever version the registry (Mongo
    `models` collection) currently marks `status: active`.
    """

    def _model_path(self, org_id: str, version: str) -> Path:
        return MODELS_DIR / f"rf_sales_model_{org_id}_{version}.pkl"

    def _meta_path(self, org_id: str, version: str) -> Path:
        return MODELS_DIR / f"rf_meta_{org_id}_{version}.pkl"

    async def seed_synthetic_data(self, org_id: str) -> int:
        """Seed MongoDB with 6 months of historical daily sales data for 3 stores and 4 products."""
        count = await sales_repo.count(org_id)
        if count > 0:
            return 0

        log.info("Seeding synthetic sales data for org=%s...", org_id)
        stores = ["Store-101", "Store-102", "Store-103"]
        products = [
            {"id": "PROD-A", "category": "Electronics", "price": 299.99, "base_sales": 15},
            {"id": "PROD-B", "category": "Apparel", "price": 49.99, "base_sales": 35},
            {"id": "PROD-C", "category": "Home & Kitchen", "price": 89.99, "base_sales": 22},
            {"id": "PROD-D", "category": "Fitness", "price": 120.00, "base_sales": 12},
        ]

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=180)
        docs = []

        for day_idx in range(180):
            current_date = start_date + timedelta(days=day_idx)
            day_of_week = current_date.weekday()
            month = current_date.month

            is_holiday = False
            if (month == 11 and current_date.day in [25, 26, 27]) or (month == 12 and current_date.day in [24, 25, 31]):
                is_holiday = True

            for store in stores:
                for prod in products:
                    is_promo = np.random.rand() < 0.10

                    base = prod["base_sales"]
                    store_mult = 1.0 if store == "Store-101" else (1.2 if store == "Store-102" else 0.8)
                    weekly_mult = 1.5 if day_of_week in [4, 5] else 0.9
                    holiday_mult = 2.0 if is_holiday else 1.0
                    promo_mult = 1.6 if is_promo else 1.0
                    trend_mult = 1.0 + (day_idx / 360.0)

                    noise = np.random.normal(0, base * 0.15)
                    qty = int(max(1, (base * store_mult * weekly_mult * holiday_mult * promo_mult * trend_mult) + noise))
                    rev = round(qty * prod["price"], 2)

                    docs.append({
                        "date": datetime(current_date.year, current_date.month, current_date.day, tzinfo=timezone.utc),
                        "store_id": store,
                        "product_id": prod["id"],
                        "category": prod["category"],
                        "quantity": qty,
                        "revenue": rev,
                        "is_holiday": is_holiday,
                        "is_promo": is_promo
                    })

        chunk_size = 1000
        for i in range(0, len(docs), chunk_size):
            await sales_repo.insert_many(org_id, docs[i:i + chunk_size])

        log.info("Seeded %d sales records successfully for org=%s", len(docs), org_id)
        return len(docs)

    async def train_model(self, org_id: str) -> dict:
        """Fetch sales data, engineer features, train Random Forest models, and persist."""
        far_past = datetime(1970, 1, 1, tzinfo=timezone.utc)
        far_future = datetime.now(timezone.utc) + timedelta(days=1)
        data = await sales_repo.find_in_range(org_id, far_past, far_future, limit=100000)

        if len(data) < 30:
            raise ValueError(f"Insufficient sales data to train model. Need at least 30 records, found {len(data)}")

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        le_store = LabelEncoder()
        le_prod = LabelEncoder()
        le_cat = LabelEncoder()

        df["store_code"] = le_store.fit_transform(df["store_id"])
        df["prod_code"] = le_prod.fit_transform(df["product_id"])
        df["cat_code"] = le_cat.fit_transform(df["category"])

        df["dayofweek"] = df["date"].dt.dayofweek
        df["dayofmonth"] = df["date"].dt.day
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
        df["is_weekend"] = df["dayofweek"].isin([5, 6]).astype(int)
        pk_flags = df["date"].apply(lambda d: holiday_flags(d.date()))
        df["is_holiday_int"] = (df["is_holiday"].astype(bool) | pk_flags.apply(lambda f: f["is_holiday"])).astype(int)
        df["is_ramadan_int"] = pk_flags.apply(lambda f: f["is_ramadan"]).astype(int)
        df["is_promo_int"] = df["is_promo"].astype(int)

        df["qty_lag_1"] = df.groupby(["store_id", "product_id"])["quantity"].shift(1)
        df["qty_lag_7"] = df.groupby(["store_id", "product_id"])["quantity"].shift(7)
        df["qty_roll_mean_7"] = df.groupby(["store_id", "product_id"])["quantity"].shift(1).rolling(7).mean()

        global_avg = df["quantity"].mean()
        df["qty_lag_1"] = df["qty_lag_1"].fillna(global_avg)
        df["qty_lag_7"] = df["qty_lag_7"].fillna(global_avg)
        df["qty_roll_mean_7"] = df["qty_roll_mean_7"].fillna(global_avg)

        feature_cols = [
            "store_code", "prod_code", "cat_code",
            "dayofweek", "dayofmonth", "month", "year",
            "is_weekend", "is_holiday_int", "is_ramadan_int", "is_promo_int",
            "qty_lag_7", "qty_roll_mean_7"
        ]

        X = df[feature_cols]
        y_qty = df["quantity"]
        y_rev = df["revenue"]

        # ---- Rolling-origin backtest: 3 expanding-window folds, RF vs baselines ----
        backtest = self._rolling_origin_backtest(df, feature_cols)

        # ---- Final holdout (last 15%) used for the deployed model's headline metrics + intervals ----
        split_idx = int(len(df) * 0.85)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_qty_train, y_qty_val = y_qty.iloc[:split_idx], y_qty.iloc[split_idx:]
        y_rev_train, y_rev_val = y_rev.iloc[:split_idx], y_rev.iloc[split_idx:]

        holdout_rf = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
        holdout_rf.fit(X_train, y_qty_train)
        holdout_preds = holdout_rf.predict(X_val)
        residuals = y_qty_val.values - holdout_preds
        residual_lower = float(np.percentile(residuals, 5))
        residual_upper = float(np.percentile(residuals, 95))

        # ---- Train the deployed model on ALL available data ----
        rf_qty = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
        rf_qty.fit(X, y_qty)

        rf_rev = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
        rf_rev.fit(X, y_rev)

        qty_mae = float(np.mean(np.abs(y_qty_val - holdout_preds)))
        qty_rmse = float(np.sqrt(np.mean((y_qty_val - holdout_preds) ** 2)))
        y_val_mean = np.mean(y_qty_val)
        ss_tot = np.sum((y_qty_val - y_val_mean) ** 2)
        ss_res = np.sum((y_qty_val - holdout_preds) ** 2)
        r2 = float(1.0 - (ss_res / (ss_tot + 1e-8)))
        accuracy_metrics = all_metrics(y_qty_val.values, holdout_preds, y_qty_train.values)

        model_artifacts = {
            "model_qty": rf_qty,
            "model_rev": rf_rev,
            "le_store": le_store,
            "le_prod": le_prod,
            "le_cat": le_cat,
        }

        version = f"v1.{int(datetime.now(timezone.utc).timestamp())}"

        with open(self._model_path(org_id, version), "wb") as f:
            pickle.dump(model_artifacts, f)

        avg_prices = df.groupby("product_id")["revenue"].sum() / (df.groupby("product_id")["quantity"].sum() + 1e-8)
        avg_prices = avg_prices.to_dict()

        meta_artifacts = {
            "features": feature_cols,
            "avg_prices": avg_prices,
            "train_date": datetime.now(timezone.utc),
            "metrics": {"mae": qty_mae, "rmse": qty_rmse, "r2": r2, **accuracy_metrics},
            "residual_lower": residual_lower,
            "residual_upper": residual_upper,
        }

        with open(self._meta_path(org_id, version), "wb") as f:
            pickle.dump(meta_artifacts, f)

        beats_baseline = backtest["rf_wape"] < backtest["best_baseline_wape"]

        # Guardrail: only auto-promote to "active" if this beats the current
        # active model's WAPE by a margin, or there is no (usable) active model yet.
        current_active = await models_repo.find_active(org_id)
        if current_active is not None:
            active_version = current_active.get("version")
            active_artifact_exists = active_version and os.path.exists(self._model_path(org_id, active_version))
            if not active_artifact_exists:
                current_active = None  # stale registry entry with no matching artifact — treat as no active model

        promote_margin = 0.02  # 2%
        if current_active is None:
            status = "active"
        else:
            current_wape = current_active.get("metrics", {}).get("wape")
            if current_wape is not None and accuracy_metrics["wape"] < current_wape * (1 - promote_margin):
                status = "active"
                await models_repo.archive_all(org_id)
            else:
                status = "candidate"

        model_doc = {
            "trained_at": datetime.now(timezone.utc),
            "features": feature_cols,
            "metrics": meta_artifacts["metrics"],
            "backtest": backtest,
            "beats_seasonal_naive_baseline": beats_baseline,
            "training_rows": int(len(df)),
            "status": status,
            "version": version,
        }
        model_doc = await models_repo.insert(org_id, model_doc)

        log.info(
            "Model trained for org=%s! status=%s R2=%.4f WAPE=%.2f%% beats_baseline=%s",
            org_id, status, r2, accuracy_metrics["wape"], beats_baseline,
        )
        return model_doc

    def _rolling_origin_backtest(self, df: pd.DataFrame, feature_cols: list[str], n_folds: int = 3) -> dict:
        """Walk-forward validation: RF vs naive/seasonal-naive/moving-average baselines.

        Each fold trains on an expanding window and validates on the next
        chunk, so later folds see more history — the same discipline as
        production retraining. Metrics are averaged across folds.
        """
        n = len(df)
        chunk = n // (n_folds + 1)
        if chunk < 5:
            # Not enough data for a meaningful walk-forward split; report the
            # single-holdout result as a one-fold "backtest" instead of crashing.
            n_folds = 1
            chunk = max(1, n // 2)

        fold_results = {"rf": [], "naive": [], "seasonal_naive": [], "moving_avg": []}

        for fold in range(1, n_folds + 1):
            train_end = chunk * fold
            val_end = min(n, chunk * (fold + 1))
            if val_end <= train_end:
                continue

            train_df = df.iloc[:train_end]
            val_df = df.iloc[train_end:val_end]
            if len(train_df) < 10 or len(val_df) < 1:
                continue

            X_train, y_train = train_df[feature_cols], train_df["quantity"]
            X_val, y_val = val_df[feature_cols], val_df["quantity"]

            rf = RandomForestRegressor(n_estimators=60, max_depth=10, random_state=42)
            rf.fit(X_train, y_train)
            rf_preds = rf.predict(X_val)

            fold_results["rf"].append(wape(y_val.values, rf_preds))
            fold_results["naive"].append(wape(y_val.values, val_df["qty_lag_1"].values))
            fold_results["seasonal_naive"].append(wape(y_val.values, val_df["qty_lag_7"].values))
            fold_results["moving_avg"].append(wape(y_val.values, val_df["qty_roll_mean_7"].values))

        avg = {k: round(float(np.mean(v)), 2) if v else None for k, v in fold_results.items()}
        baseline_scores = {k: v for k, v in avg.items() if k != "rf" and v is not None}
        best_baseline = min(baseline_scores, key=baseline_scores.get) if baseline_scores else None

        return {
            "folds": n_folds,
            "rf_wape": avg["rf"],
            "naive_wape": avg["naive"],
            "seasonal_naive_wape": avg["seasonal_naive"],
            "moving_avg_wape": avg["moving_avg"],
            "best_baseline": best_baseline,
            "best_baseline_wape": baseline_scores.get(best_baseline) if best_baseline else float("inf"),
        }

    async def predict(self, org_id: str, store_id: str | None = None, product_id: str | None = None, horizon_days: int = 30) -> list[dict]:
        """Generate sales predictions for the next N days. Fallback to seasonal baseline if no model exists."""
        now = datetime.now(timezone.utc)
        target_dates = [datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=i) for i in range(1, horizon_days + 1)]

        active_model = await models_repo.find_active(org_id)
        if not active_model:
            log.warning("No active ML model for org=%s. Falling back to statistical baseline.", org_id)
            return await self._generate_baseline_predictions(org_id, store_id, product_id, target_dates)

        version = active_model["version"]
        model_path = self._model_path(org_id, version)
        meta_path = self._meta_path(org_id, version)

        if not os.path.exists(model_path) or not os.path.exists(meta_path):
            log.warning("Active model artifact missing on disk for org=%s version=%s. Falling back to statistical baseline.", org_id, version)
            return await self._generate_baseline_predictions(org_id, store_id, product_id, target_dates)

        try:
            with open(model_path, "rb") as f:
                artifacts = pickle.load(f)
            with open(meta_path, "rb") as f:
                meta = pickle.load(f)
        except Exception as e:
            log.error("Failed to load ML model files for org=%s: %s. Using baseline.", org_id, e)
            return await self._generate_baseline_predictions(org_id, store_id, product_id, target_dates)

        rf_qty = artifacts["model_qty"]
        rf_rev = artifacts["model_rev"]
        le_store = artifacts["le_store"]
        le_prod = artifacts["le_prod"]
        le_cat = artifacts["le_cat"]

        target_stores = [store_id] if store_id else list(le_store.classes_)
        target_prods = [product_id] if product_id else list(le_prod.classes_)

        recent_sales = await sales_repo.find_recent(org_id, limit=200)
        recent_df = pd.DataFrame(recent_sales) if recent_sales else pd.DataFrame()

        predictions = []

        for store in target_stores:
            for prod in target_prods:
                if store not in le_store.classes_ or prod not in le_prod.classes_:
                    continue

                store_code = le_store.transform([store])[0]
                prod_code = le_prod.transform([prod])[0]

                prod_cat = "General"
                if recent_sales:
                    matches = recent_df[recent_df["product_id"] == prod]
                    if not matches.empty:
                        prod_cat = matches.iloc[0]["category"]
                cat_code = le_cat.transform([prod_cat])[0] if prod_cat in le_cat.classes_ else 0

                hist_series = []
                if not recent_df.empty:
                    match_series = recent_df[(recent_df["store_id"] == store) & (recent_df["product_id"] == prod)]
                    if not match_series.empty:
                        hist_series = list(match_series.sort_values("date")["quantity"].tail(7))

                while len(hist_series) < 7:
                    hist_series.append(15.0)

                current_history = hist_series.copy()

                residual_lower = meta.get("residual_lower", -1.64 * meta["metrics"]["rmse"])
                residual_upper = meta.get("residual_upper", 1.64 * meta["metrics"]["rmse"])

                for d_idx, t_date in enumerate(target_dates):
                    day_of_week = t_date.weekday()
                    day_of_month = t_date.day
                    month = t_date.month
                    year = t_date.year
                    is_weekend = int(day_of_week in [5, 6])

                    flags = holiday_flags(t_date.date())
                    is_holiday = int(flags["is_holiday"])
                    is_ramadan = int(flags["is_ramadan"])
                    is_promo = 0

                    qty_lag_7 = current_history[-7]
                    qty_roll_mean_7 = np.mean(current_history[-7:])

                    feat_dict = {
                        "store_code": store_code,
                        "prod_code": prod_code,
                        "cat_code": cat_code,
                        "dayofweek": day_of_week,
                        "dayofmonth": day_of_month,
                        "month": month,
                        "year": year,
                        "is_weekend": is_weekend,
                        "is_holiday_int": is_holiday,
                        "is_ramadan_int": is_ramadan,
                        "is_promo_int": is_promo,
                        "qty_lag_7": qty_lag_7,
                        "qty_roll_mean_7": qty_roll_mean_7
                    }
                    X_pred = pd.DataFrame([feat_dict])

                    pred_qty = float(rf_qty.predict(X_pred)[0])
                    pred_qty = max(0.0, pred_qty)

                    pred_rev = float(rf_rev.predict(X_pred)[0])
                    pred_rev = max(0.0, pred_rev)

                    current_history.append(pred_qty)

                    # Empirical residual-quantile interval, widened with horizon distance
                    # (uncertainty compounds the further out the forecast reaches).
                    widen = np.sqrt(1 + d_idx / max(1, horizon_days))
                    confidence_lower = max(0.0, pred_qty + residual_lower * widen)
                    confidence_upper = pred_qty + residual_upper * widen

                    predictions.append({
                        "date": t_date,
                        "store_id": store,
                        "product_id": prod,
                        "category": prod_cat,
                        "quantity": round(pred_qty, 2),
                        "revenue": round(pred_rev, 2),
                        "confidence_lower": round(confidence_lower, 2),
                        "confidence_upper": round(confidence_upper, 2),
                        "is_baseline": False
                    })

        return predictions

    async def _generate_baseline_predictions(self, org_id: str, store_id: str | None, product_id: str | None, target_dates: list[datetime]) -> list[dict]:
        """Statistical baseline forecaster used as fallback or cold-start helper."""
        stores = [store_id] if store_id else ["Store-101", "Store-102", "Store-103"]
        products = [
            {"id": "PROD-A", "category": "Electronics", "price": 299.99, "base_sales": 15},
            {"id": "PROD-B", "category": "Apparel", "price": 49.99, "base_sales": 35},
            {"id": "PROD-C", "category": "Home & Kitchen", "price": 89.99, "base_sales": 22},
            {"id": "PROD-D", "category": "Fitness", "price": 120.00, "base_sales": 12},
        ]
        if product_id:
            products = [p for p in products if p["id"] == product_id]

        db_averages = {}
        count = await sales_repo.count(org_id)
        if count > 0:
            pipeline = [
                {"$group": {
                    "_id": {"store_id": "$store_id", "product_id": "$product_id"},
                    "avg_qty": {"$avg": "$quantity"},
                    "avg_rev": {"$avg": "$revenue"},
                    "category": {"$first": "$category"}
                }}
            ]
            for res in await sales_repo.aggregate(org_id, pipeline, length=10000):
                key = (res["_id"]["store_id"], res["_id"]["product_id"])
                db_averages[key] = {
                    "avg_qty": res["avg_qty"],
                    "avg_rev": res["avg_rev"],
                    "category": res.get("category", "General")
                }

        predictions = []

        for store in stores:
            for prod_item in products:
                prod = prod_item["id"]
                category = prod_item["category"]
                price = prod_item["price"]
                base = prod_item["base_sales"]

                db_match = db_averages.get((store, prod))
                if db_match:
                    base = db_match["avg_qty"]
                    category = db_match["category"]
                    price = db_match["avg_rev"] / (base + 1e-8)

                for idx, t_date in enumerate(target_dates):
                    day_of_week = t_date.weekday()
                    month = t_date.month

                    weekly_mult = 1.4 if day_of_week in [4, 5] else 0.8
                    monthly_mult = 1.2 if month in [11, 12] else 0.95
                    trend_mult = 1.0 + ((idx + 180) / 360.0)

                    pred_qty = base * weekly_mult * monthly_mult * trend_mult
                    pred_qty = max(1.0, pred_qty + np.sin(idx * 0.5) * 2.0)
                    pred_rev = pred_qty * price

                    confidence_lower = max(0.0, pred_qty * 0.75)
                    confidence_upper = pred_qty * 1.25

                    predictions.append({
                        "date": t_date,
                        "store_id": store,
                        "product_id": prod,
                        "category": category,
                        "quantity": round(pred_qty, 2),
                        "revenue": round(pred_rev, 2),
                        "confidence_lower": round(confidence_lower, 2),
                        "confidence_upper": round(confidence_upper, 2),
                        "is_baseline": True
                    })

        return predictions


ai_predictor = AIPredictor()
