"""Forecast service.

Handles predictions retrieval, actual vs forecast comparisons, and manual retraining.
"""
from __future__ import annotations

from typing import Optional
from fastapi import HTTPException, Request

from app.repositories import models_repo
from app.ml.predictor import ai_predictor
from app.schemas.common import serialize
from app.services.audit_service import log_event


async def get_predictions(
    org_id: str,
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    horizon_days: int = 30
) -> dict:
    """Retrieve AI or statistical baseline predictions."""
    try:
        preds = await ai_predictor.predict(org_id, store_id, product_id, horizon_days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate predictions: {e}")

    serialized_preds = []
    for p in preds:
        serialized_preds.append({
            "date": p["date"].strftime("%Y-%m-%d"),
            "store_id": p["store_id"],
            "product_id": p["product_id"],
            "category": p["category"],
            "quantity": p["quantity"],
            "revenue": p["revenue"],
            "confidence_lower": p["confidence_lower"],
            "confidence_upper": p["confidence_upper"],
            "is_baseline": p["is_baseline"]
        })

    active_model = await models_repo.find_active(org_id)

    return {
        "status": "success",
        "predictions": serialized_preds,
        "horizon_days": horizon_days,
        "model": serialize(active_model) if active_model else None
    }


async def train_model(org_id: str, request: Request) -> dict:
    """Trigger manual AI model training.

    The new model only becomes "active" automatically if it beats the
    current active model's WAPE by a margin (or there is no active model
    yet) — otherwise it's saved as a "candidate" for manual promotion.
    """
    try:
        model_doc = await ai_predictor.train_model(org_id)
        await log_event(
            "model_trained",
            org_id=org_id,
            request=request,
            metadata={"version": model_doc["version"], "metrics": model_doc["metrics"], "status": model_doc["status"]}
        )
        if model_doc["status"] == "active":
            message = "AI model trained and promoted to active."
        else:
            message = (
                f"AI model trained as a candidate (WAPE {model_doc['metrics']['wape']}%) — "
                "it didn't beat the current active model by enough to auto-promote."
            )
        return {
            "status": "success",
            "message": message,
            "model": serialize(model_doc)
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {e}")


async def get_models_list(org_id: str) -> dict:
    """Retrieve history of model training sessions."""
    docs = await models_repo.list_recent(org_id, limit=50)
    return {
        "status": "success",
        "models": [serialize(d) for d in docs]
    }


async def promote_model(org_id: str, model_oid: str, request: Request) -> dict:
    """Manually promote a candidate/archived model version to active."""
    model_doc = await models_repo.find_by_id(org_id, model_oid)
    if not model_doc:
        raise HTTPException(status_code=404, detail="Model version not found")
    await models_repo.promote(org_id, model_oid)
    await log_event("model_promoted", org_id=org_id, request=request, metadata={"version": model_doc["version"]})
    return {"status": "success", "message": f"Promoted {model_doc['version']} to active"}
