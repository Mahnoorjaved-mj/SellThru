"""Alert rules engine + notification feed.

Rule types actually implemented (each one is checkable from real data —
nothing fabricated):
  - forecast_drop: forecast for a store/product dropped >= threshold_pct
    versus the prior comparable window.
  - anomaly_high: a high-sensitivity anomaly scan found a hit at or above
    the configured |z-score|.
  - import_failed: raised directly by the upload flow (see sales_service),
    not by evaluate_rules.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.repositories import alerts_repo
from app.schemas.common import serialize

RULE_TYPES = {"forecast_drop", "anomaly_high"}
RE_EVALUATE_COOLDOWN_HOURS = 24


async def create_rule(org_id: str, user_id: str, rule_type: str, params: dict) -> dict:
    if rule_type not in RULE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown rule type '{rule_type}'")
    doc = await alerts_repo.insert_rule(org_id, {
        "type": rule_type,
        "params": params,
        "created_by": user_id,
    })
    return {"status": "success", "rule": serialize(doc)}


async def list_rules(org_id: str) -> dict:
    docs = await alerts_repo.list_rules(org_id)
    return {"status": "success", "rules": [serialize(d) for d in docs]}


async def set_rule_enabled(org_id: str, rule_id: str, enabled: bool) -> dict:
    await alerts_repo.set_rule_enabled(org_id, rule_id, enabled)
    return {"status": "success"}


async def delete_rule(org_id: str, rule_id: str) -> dict:
    await alerts_repo.delete_rule(org_id, rule_id)
    return {"status": "success"}


async def list_notifications(org_id: str) -> dict:
    docs = await alerts_repo.list_notifications(org_id)
    return {"status": "success", "notifications": [serialize(d) for d in docs]}


async def mark_notification_read(org_id: str, notification_id: str) -> dict:
    await alerts_repo.mark_read(org_id, notification_id)
    return {"status": "success"}


async def mark_all_read(org_id: str) -> dict:
    await alerts_repo.mark_all_read(org_id)
    return {"status": "success"}


async def notify_import_failed(org_id: str, filename: str, rows_failed: int, import_id: str) -> None:
    await alerts_repo.insert_notification(org_id, {
        "rule_id": None,
        "title": "Import had failed rows",
        "message": f"{filename}: {rows_failed} row(s) failed validation.",
        "severity": "warning",
        "link": {"type": "import", "id": import_id},
    })


async def evaluate_rules(org_id: str) -> dict:
    """Run every enabled rule for this org, creating notifications for newly-triggered hits."""
    from app.ml.predictor import ai_predictor
    from app.services.insights_service import get_anomalies

    rules = await alerts_repo.find_enabled_rules(org_id)
    triggered = 0
    cooldown_start = datetime.now(timezone.utc) - timedelta(hours=RE_EVALUATE_COOLDOWN_HOURS)

    for rule in rules:
        rule_id = str(rule["_id"])
        if await alerts_repo.recent_notification_exists(org_id, rule_id, cooldown_start):
            continue  # already notified for this rule recently — don't spam

        params = rule.get("params", {})

        if rule["type"] == "forecast_drop":
            store_id = params.get("store_id")
            product_id = params.get("product_id")
            threshold_pct = float(params.get("threshold_pct", 20))
            try:
                preds = await ai_predictor.predict(org_id, store_id, product_id, horizon_days=14)
            except Exception:
                continue
            if len(preds) < 14:
                continue
            first_week = sum(p["quantity"] for p in preds[:7])
            second_week = sum(p["quantity"] for p in preds[7:14])
            if first_week <= 0:
                continue
            drop_pct = (first_week - second_week) / first_week * 100.0
            if drop_pct >= threshold_pct:
                await alerts_repo.insert_notification(org_id, {
                    "rule_id": rule_id,
                    "title": f"Forecast drop: {product_id or 'all products'} at {store_id or 'all stores'}",
                    "message": f"Forecasted demand is down {drop_pct:.1f}% week-over-week (threshold {threshold_pct}%).",
                    "severity": "warning",
                    "link": {"type": "predictions", "store_id": store_id, "product_id": product_id},
                })
                triggered += 1

        elif rule["type"] == "anomaly_high":
            min_z = float(params.get("min_abs_z", 3.0))
            res = await get_anomalies(org_id, sensitivity="high")
            hits = [a for a in res["anomalies"] if abs(a["z_score"]) >= min_z]
            if hits:
                top = hits[0]
                await alerts_repo.insert_notification(org_id, {
                    "rule_id": rule_id,
                    "title": f"High-severity anomaly: {top['product_id']} at {top['store_id']}",
                    "message": f"{top['type'].capitalize()} of {top['quantity']} units on {top['date']} (z={top['z_score']}).",
                    "severity": "negative" if top["type"] == "drop" else "warning",
                    "link": {"type": "insights"},
                })
                triggered += 1

    return {"status": "success", "rules_checked": len(rules), "notifications_created": triggered}
