"""Insights service — anomaly detection (z-score + robust MAD) and trend/BI cards."""
from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import timedelta

from app.repositories import anomaly_acks_repo, sales_repo

# Sensitivity controls how many standard deviations / MAD-multiples count as
# an outlier. Lower threshold = more sensitive = more anomalies surfaced.
SENSITIVITY_THRESHOLDS = {"low": 3.0, "medium": 2.2, "high": 1.5}
MAD_CONSTANT = 1.4826  # scales MAD to be comparable to a standard deviation under normality


async def get_anomalies(org_id: str, sensitivity: str = "medium") -> dict:
    """Detect unusual sales drops or spikes.

    Two methods run side by side and results are merged (de-duplicated by
    store/product/date, keeping the higher-confidence hit): a rolling
    z-score (mean/std) and a rolling median + MAD score, which is more
    robust when a single earlier spike would otherwise skew a plain std-dev
    threshold. Rows a user has acknowledged as "expected" are excluded.
    """
    threshold = SENSITIVITY_THRESHOLDS.get(sensitivity, SENSITIVITY_THRESHOLDS["medium"])

    latest_sale = await sales_repo.find_latest(org_id)
    if not latest_sale:
        return {"status": "success", "anomalies": [], "sensitivity": sensitivity}

    anchor_date = latest_sale["date"]
    start_date = anchor_date - timedelta(days=60)  # evaluate last 60 days

    data = await sales_repo.find_in_range(org_id, start_date, anchor_date, limit=5000)

    if not data:
        return {"status": "success", "anomalies": [], "sensitivity": sensitivity}

    acknowledged = await anomaly_acks_repo.list_acknowledged_keys(org_id)

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    anomalies_by_key: dict[str, dict] = {}

    grouped = df.groupby(["store_id", "product_id"])
    for (store, prod), group in grouped:
        if len(group) < 7:
            continue

        group = group.sort_values("date")
        qtys = group["quantity"].values

        rolling_mean = group["quantity"].rolling(7, min_periods=3).mean().values
        rolling_std = group["quantity"].rolling(7, min_periods=3).std().values
        rolling_median = group["quantity"].rolling(7, min_periods=3).median().values

        for idx in range(len(group)):
            val = qtys[idx]
            row = group.iloc[idx]
            date_iso = row["date"].strftime("%Y-%m-%d")
            key = f"{store}|{prod}|{date_iso}"
            if key in acknowledged:
                continue

            m = rolling_mean[idx]
            s = rolling_std[idx]
            z_score = None
            if not (pd.isna(m) or pd.isna(s) or s == 0):
                z_score = (val - m) / s

            window_start = max(0, idx - 6)
            window_vals = qtys[window_start:idx + 1]
            med = rolling_median[idx]
            mad_score = None
            if not pd.isna(med) and len(window_vals) >= 3:
                mad = np.median(np.abs(window_vals - med))
                if mad > 1e-8:
                    mad_score = (val - med) / (MAD_CONSTANT * mad)

            hit_method = None
            hit_score = None
            expected = m if not pd.isna(m) else med
            if z_score is not None and abs(z_score) >= threshold:
                hit_method, hit_score = "zscore", z_score
            if mad_score is not None and abs(mad_score) >= threshold:
                # Prefer whichever score is more extreme when both methods fire.
                if hit_method is None or abs(mad_score) > abs(hit_score):
                    hit_method, hit_score = "mad", mad_score

            if hit_method is None:
                continue

            anomalies_by_key[key] = {
                "date": date_iso,
                "store_id": store,
                "product_id": prod,
                "category": row["category"],
                "quantity": int(val),
                "expected_mean": round(float(expected), 1) if not pd.isna(expected) else None,
                "z_score": round(float(hit_score), 2),
                "method": hit_method,
                "type": "spike" if hit_score > 0 else "drop",
            }

    anomalies = sorted(anomalies_by_key.values(), key=lambda x: x["date"], reverse=True)[:25]

    return {
        "status": "success",
        "sensitivity": sensitivity,
        "anomalies": anomalies
    }


async def acknowledge_anomaly(org_id: str, user_id: str, store_id: str, product_id: str, date: str) -> dict:
    await anomaly_acks_repo.acknowledge(org_id, store_id, product_id, date, user_id)
    return {"status": "success", "message": "Anomaly acknowledged — it won't surface again"}


async def get_trends(org_id: str) -> dict:
    """Generate business intelligence alerts and trend reports from the dataset."""
    latest_sale = await sales_repo.find_latest(org_id)
    if not latest_sale:
        return {
            "status": "success",
            "trends": [
                {
                    "title": "Welcome to AI Insights",
                    "description": "Please upload a historical sales CSV file to begin trend and promotional analyses.",
                    "type": "info"
                }
            ]
        }

    anchor_date = latest_sale["date"]
    start_date = anchor_date - timedelta(days=90)

    data = await sales_repo.find_in_range(org_id, start_date, anchor_date, limit=10000)

    if not data:
        return {"status": "success", "trends": []}

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["dayofweek"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month

    trends = []

    # 1. Weekly seasonality peak
    weekday_avgs = df.groupby("dayofweek")["quantity"].mean()
    if not weekday_avgs.empty:
        peak_day = weekday_avgs.idxmax()
        peak_val = weekday_avgs.max()
        weekday_mean = weekday_avgs[~weekday_avgs.index.isin([5, 6])].mean()

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        diff_pct = ((peak_val - weekday_mean) / (weekday_mean + 1e-8)) * 100

        if diff_pct > 10:
            trends.append({
                "title": f"Strong Weekly Seasonality on {day_names[peak_day]}s",
                "description": f"Sales on {day_names[peak_day]}s peak, averaging {diff_pct:.1f}% higher quantities than typical weekdays.",
                "type": "trend"
            })

    # 2. Promotional Uplift Analysis
    promo_sales = df[df["is_promo"] == True]["quantity"].mean()
    non_promo_sales = df[df["is_promo"] == False]["quantity"].mean()

    if not pd.isna(promo_sales) and not pd.isna(non_promo_sales) and non_promo_sales > 0:
        uplift = ((promo_sales - non_promo_sales) / non_promo_sales) * 100
        trends.append({
            "title": "Promotional Boost",
            "description": f"Running a promotion increases product sales volume by an average of {uplift:.1f}% compared to regular days.",
            "type": "promo"
        })

    # 3. Top Store Contribution
    store_revs = df.groupby("store_id")["revenue"].sum()
    if not store_revs.empty:
        top_store = store_revs.idxmax()
        top_rev = store_revs.max()
        total_rev = store_revs.sum()
        share = (top_rev / total_rev) * 100

        trends.append({
            "title": f"Top Revenue Driver: {top_store}",
            "description": f"Store {top_store} contributes {share:.1f}% of total business revenue over the last 90 days (${top_rev:,.2f}).",
            "type": "store"
        })

    # 4. Inventory Alert based on predictions (stock depleting soon)
    from app.ml.predictor import ai_predictor
    try:
        preds = await ai_predictor.predict(org_id, horizon_days=7)
        if preds:
            pred_df = pd.DataFrame(preds)
            summed_forecast = pred_df.groupby(["store_id", "product_id"])["quantity"].sum().reset_index()
            top_depletions = summed_forecast.sort_values("quantity", ascending=False).head(3)

            for _, row in top_depletions.iterrows():
                trends.append({
                    "title": f"Stock Alert: {row['product_id']} at {row['store_id']}",
                    "description": f"High demand expected! Forecast predicts {int(row['quantity'])} units of {row['product_id']} will be sold at {row['store_id']} over the next 7 days.",
                    "type": "alert"
                })
    except Exception:
        pass

    return {
        "status": "success",
        "trends": trends
    }
