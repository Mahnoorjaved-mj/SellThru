"""Sales data service.

Handles CSV parsing/upload, paginated historical querying, and dashboard
summaries. Every read/write is scoped to the caller's org_id.
"""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, UploadFile, Request

from app.repositories import imports_repo, products_repo, sales_repo, stores_repo
from app.schemas.common import serialize
from app.services.audit_service import log_event

MAX_UPLOAD_ROWS = 100_000
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB


def _row_hash(org_id: str, store_id: str, product_id: str, date_iso: str, qty: int, rev: float) -> str:
    raw = f"{org_id}|{store_id}|{product_id}|{date_iso}|{qty}|{rev}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def upload_sales_csv(org_id: str, user_id: str, file: UploadFile, request: Request) -> dict:
    """Parse, validate, and idempotently bulk-load a CSV file of sales data.

    Valid rows are imported even if some rows fail — failures are collected
    into an error report rather than aborting the whole file. Rows that
    duplicate an already-imported row (same org/store/product/date/qty/revenue)
    are skipped and counted, not re-inserted.
    """
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)}MB upload limit")

    file_hash = hashlib.sha256(contents).hexdigest()

    try:
        csv_text = contents.decode("utf-8")
    except UnicodeDecodeError:
        try:
            csv_text = contents.decode("latin-1")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid file encoding: {e}")

    reader = csv.DictReader(io.StringIO(csv_text))

    # Required columns validation
    required_cols = {"date", "store_id", "product_id", "category", "quantity", "revenue"}
    headers = {h.strip().lower() for h in reader.fieldnames or []}
    missing = required_cols - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {', '.join(missing)}"
        )

    records = []
    errors = []
    row_num = 1

    for row in reader:
        row_num += 1
        if row_num - 1 > MAX_UPLOAD_ROWS:
            errors.append({"row": row_num, "error": f"Row cap of {MAX_UPLOAD_ROWS} exceeded — remaining rows skipped"})
            break

        row_clean = {k.strip().lower(): v.strip() for k, v in row.items() if k}

        try:
            dt_str = row_clean["date"]
            dt = None
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

            if not dt:
                raise ValueError(f"Unrecognized date format: '{dt_str}'")

            qty = int(row_clean["quantity"])
            rev = float(row_clean["revenue"])

            if qty < 0 or rev < 0:
                raise ValueError("Quantity and Revenue must be non-negative values")
            if not row_clean.get("store_id") or not row_clean.get("product_id"):
                raise ValueError("store_id and product_id are required")

            is_holiday = row_clean.get("is_holiday", "false").lower() in ("true", "1", "yes")
            is_promo = row_clean.get("is_promo", "false").lower() in ("true", "1", "yes")
            date_iso = dt.strftime("%Y-%m-%d")

            records.append({
                "date": dt,
                "store_id": row_clean["store_id"],
                "product_id": row_clean["product_id"],
                "category": row_clean["category"],
                "quantity": qty,
                "revenue": round(rev, 2),
                "is_holiday": is_holiday,
                "is_promo": is_promo,
                "row_hash": _row_hash(org_id, row_clean["store_id"], row_clean["product_id"], date_iso, qty, round(rev, 2)),
            })

        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})

    if not records and not errors:
        raise HTTPException(status_code=400, detail="CSV file contains no data rows")
    if not records:
        raise HTTPException(status_code=400, detail=f"All {len(errors)} rows failed validation — nothing was imported")

    # Idempotency: drop rows that duplicate an already-imported row for this org
    existing_hashes = await sales_repo.find_existing_hashes(org_id, [r["row_hash"] for r in records])
    new_records = [r for r in records if r["row_hash"] not in existing_hashes]
    skipped_duplicates = len(records) - len(new_records)

    import_doc = await imports_repo.insert(org_id, {
        "filename": file.filename,
        "file_hash": file_hash,
        "rows_total": row_num - 1,
        "rows_imported": 0,
        "rows_skipped_duplicate": skipped_duplicates,
        "rows_failed": len(errors),
        "status": "completed",
        "uploaded_by": user_id,
        "error_report": errors[:200],
        "created_at": datetime.now(timezone.utc),
    })
    import_id = str(import_doc["_id"])

    for r in new_records:
        r["import_id"] = import_id

    inserted = await sales_repo.insert_many(org_id, new_records)

    # Auto-register any store/product codes seen in this file as lightweight master records
    for r in new_records:
        await stores_repo.upsert(org_id, r["store_id"], {"is_active": True})
        await products_repo.upsert(org_id, r["product_id"], {"category": r["category"], "is_active": True})

    await imports_repo.mark_rows_imported(org_id, import_id, inserted)

    if errors:
        from app.services.alerts_service import notify_import_failed
        await notify_import_failed(org_id, file.filename, len(errors), import_id)

    await log_event(
        "sales_csv_uploaded",
        user_id=user_id,
        org_id=org_id,
        request=request,
        metadata={"filename": file.filename, "rows_imported": inserted, "rows_skipped": skipped_duplicates, "rows_failed": len(errors), "import_id": import_id}
    )

    message = f"Imported {inserted} rows"
    if skipped_duplicates:
        message += f", skipped {skipped_duplicates} duplicates"
    if errors:
        message += f", {len(errors)} rows failed validation"

    return {
        "status": "success",
        "message": message,
        "count": inserted,
        "import_id": import_id,
        "rows_imported": inserted,
        "rows_skipped_duplicate": skipped_duplicates,
        "rows_failed": len(errors),
        "errors": errors[:50],
    }


async def get_dashboard_summary(org_id: str, days: int = 30) -> dict:
    """Compute KPI metrics and charts for the main dashboard.

    `days` controls both the trailing actual-sales window and the forward
    forecast horizon, so the frontend range switcher (7D/30D/90D) reflects a
    real, differently-sized query rather than slicing a fixed 30-day payload.
    """
    latest_sale = await sales_repo.find_latest(org_id)

    if not latest_sale:
        return {
            "status": "empty",
            "kpis": {
                "total_sales": 0.0,
                "avg_daily_sales": 0.0,
                "forecast_sales_30d": 0.0,
                "variance_pct": 0.0,
                "active_stores": 0,
                "active_products": 0
            },
            "history_chart": [],
            "category_chart": [],
            "recent_transactions": []
        }

    anchor_date = latest_sale["date"]
    start_period = anchor_date - timedelta(days=days)
    prior_start = anchor_date - timedelta(days=days * 2)

    # 1. Total Net Sales (trailing `days`)
    pipeline_period = [
        {"$match": {"date": {"$gte": start_period, "$lte": anchor_date}}},
        {"$group": {
            "_id": None,
            "total_rev": {"$sum": "$revenue"},
            "avg_qty": {"$avg": "$quantity"},
            "stores": {"$addToSet": "$store_id"},
            "products": {"$addToSet": "$product_id"}
        }}
    ]
    res_list = await sales_repo.aggregate(org_id, pipeline_period, length=1)

    total_sales = 0.0
    active_stores = 0
    active_products = 0

    if res_list:
        summary_res = res_list[0]
        total_sales = float(summary_res.get("total_rev", 0.0))
        active_stores = len(summary_res.get("stores", []))
        active_products = len(summary_res.get("products", []))

    # 2. Forecast Sales (next `days`)
    from app.ml.predictor import ai_predictor
    try:
        preds = await ai_predictor.predict(org_id, horizon_days=days)
        forecast_sales_period = sum(p["revenue"] for p in preds)
    except Exception:
        preds = []
        forecast_sales_period = total_sales * 1.05  # Mock default if prediction fails

    # 3. Variance: Compare actual sales (trailing) vs predicted sales (forward)
    var_diff = total_sales - forecast_sales_period
    variance_pct = (var_diff / (forecast_sales_period + 1e-8)) * 100.0

    # 4. History Chart Data: Combine daily actual sales with future forecast
    daily_actuals_pipeline = [
        {"$match": {"date": {"$gte": start_period, "$lte": anchor_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
            "revenue": {"$sum": "$revenue"}
        }},
        {"$sort": {"_id": 1}}
    ]
    actuals_res = await sales_repo.aggregate(org_id, daily_actuals_pipeline, length=days + 5)

    history_chart = []
    for row in actuals_res:
        history_chart.append({
            "date": row["_id"],
            "actual": round(row["revenue"], 2),
            "forecast": None
        })

    # Daily forecast (forward `days`)
    if preds:
        daily_preds = {}
        for p in preds:
            date_str = p["date"].strftime("%Y-%m-%d")
            daily_preds[date_str] = daily_preds.get(date_str, 0.0) + p["revenue"]

        for date_str in sorted(daily_preds.keys()):
            history_chart.append({
                "date": date_str,
                "actual": None,
                "forecast": round(daily_preds[date_str], 2)
            })

    # 5. Category breakdown (trailing `days`) with delta vs the prior equal-length period
    cat_pipeline = [
        {"$match": {"date": {"$gte": start_period, "$lte": anchor_date}}},
        {"$group": {
            "_id": "$category",
            "value": {"$sum": "$revenue"}
        }},
        {"$sort": {"value": -1}}
    ]
    cat_res = await sales_repo.aggregate(org_id, cat_pipeline, length=10)

    prior_cat_pipeline = [
        {"$match": {"date": {"$gte": prior_start, "$lt": start_period}}},
        {"$group": {
            "_id": "$category",
            "value": {"$sum": "$revenue"}
        }}
    ]
    prior_cat_res = await sales_repo.aggregate(org_id, prior_cat_pipeline, length=10)
    prior_by_category = {r["_id"]: float(r["value"]) for r in prior_cat_res}

    category_total = sum(float(r["value"]) for r in cat_res) or 1e-8
    category_chart = []
    for r in cat_res:
        value = round(float(r["value"]), 2)
        prior_value = prior_by_category.get(r["_id"], 0.0)
        delta_pct = ((value - prior_value) / prior_value * 100.0) if prior_value > 0 else None
        category_chart.append({
            "name": r["_id"],
            "value": value,
            "share_pct": round(value / category_total * 100.0, 1),
            "delta_pct": round(delta_pct, 1) if delta_pct is not None else None
        })

    # 6. Recent Transactions
    recent_docs = await sales_repo.find_recent(org_id, limit=10)
    recent_transactions = [serialize(d) for d in recent_docs]

    return {
        "status": "success",
        "range_days": days,
        "kpis": {
            "total_sales": round(total_sales, 2),
            "avg_daily_sales": round(total_sales / days, 2),
            "forecast_sales_30d": round(forecast_sales_period, 2),
            "variance_pct": round(variance_pct, 2),
            "active_stores": active_stores,
            "active_products": active_products
        },
        "history_chart": history_chart,
        "category_chart": category_chart,
        "recent_transactions": recent_transactions
    }


async def get_sales_history(
    org_id: str,
    page: int = 1,
    limit: int = 50,
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Query paginated historical transactions from MongoDB."""
    query = {}

    if store_id:
        query["store_id"] = store_id
    if product_id:
        query["product_id"] = product_id
    if category:
        query["category"] = category

    date_query = {}
    if start_date:
        try:
            date_query["$gte"] = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if end_date:
        try:
            date_query["$lte"] = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    if date_query:
        query["date"] = date_query

    total = await sales_repo.count(org_id, query)

    skip = (page - 1) * limit
    docs = await sales_repo.find_paginated(org_id, query, skip, limit)

    # Unique values for filter dropdowns
    stores = await sales_repo.distinct_field(org_id, "store_id")
    products = await sales_repo.distinct_field(org_id, "product_id")
    categories = await sales_repo.distinct_field(org_id, "category")

    return {
        "status": "success",
        "total": total,
        "page": page,
        "limit": limit,
        "sales": [serialize(d) for d in docs],
        "filters": {
            "stores": sorted(stores),
            "products": sorted(products),
            "categories": sorted(categories)
        }
    }


async def get_import_history(org_id: str) -> dict:
    docs = await imports_repo.list_recent(org_id)
    return {"status": "success", "imports": [serialize(d) for d in docs]}


async def undo_import(org_id: str, import_id: str, request: Request) -> dict:
    """Soft-delete every transaction row inserted by this import batch."""
    batch = await imports_repo.find_by_id(org_id, import_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Import not found")
    if batch.get("status") == "undone":
        raise HTTPException(status_code=400, detail="This import has already been undone")

    removed = await sales_repo.soft_delete_by_import(org_id, import_id)
    await imports_repo.mark_undone(org_id, import_id, removed)
    await log_event(
        "import_undone",
        org_id=org_id,
        request=request,
        metadata={"import_id": import_id, "rows_removed": removed},
    )
    return {"status": "success", "message": f"Removed {removed} rows from this import", "rows_removed": removed}
