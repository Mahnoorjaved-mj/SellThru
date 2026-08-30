"""Sales router. Mounted at /api/sales (legacy) and /api/v1/sales (canonical)."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Request, Query

from app.services import sales_service as ctrl
from app.core.deps import get_current_user, require_admin

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/upload")
async def upload_sales_csv(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    return await ctrl.upload_sales_csv(user["org_id"], str(user["_id"]), file, request)


@router.get("/imports")
async def list_imports(user: dict = Depends(get_current_user)):
    return await ctrl.get_import_history(user["org_id"])


@router.post("/imports/{import_id}/undo")
async def undo_import(import_id: str, request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.undo_import(user["org_id"], import_id, request)


@router.get("/summary")
async def get_dashboard_summary(
    days: int = Query(30, ge=7, le=365),
    user: dict = Depends(get_current_user)
):
    return await ctrl.get_dashboard_summary(user["org_id"], days)


@router.get("/history")
async def get_sales_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    return await ctrl.get_sales_history(
        user["org_id"], page, limit, store_id, product_id, category, start_date, end_date
    )


@router.post("/seed")
async def seed_sales_data(request: Request, user: dict = Depends(require_admin)):
    """Seed synthetic sales data for development/demo. Admin only."""
    from app.ml.predictor import ai_predictor
    count = await ai_predictor.seed_synthetic_data(user["org_id"])
    return {
        "status": "success",
        "message": f"Seeded {count} sales transactions" if count > 0 else "Sales database already contains data"
    }
