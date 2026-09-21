"""Sales data service.

Handles CSV parsing/upload, paginated historical querying, and dashboard
summaries. Every read/write is scoped to the caller's org_id.

Dashboard reads use a short server-side cache. The cache is invalidated
whenever sales are uploaded or an import is undone, so new real data becomes
visible without forcing an expensive recalculation on every dashboard visit.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, UploadFile, Request

from app.repositories import (
    imports_repo,
    products_repo,
    sales_repo,
    stores_repo
)
from app.schemas.common import serialize
from app.services.audit_service import log_event

log = logging.getLogger("sellthru.sales")

MAX_UPLOAD_ROWS = 100_000
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB


# ============================================================
# DASHBOARD SERVER CACHE
# ============================================================

_DASHBOARD_CACHE: dict[
    tuple[str, int],
    tuple[float, dict]
] = {}

DASHBOARD_CACHE_TTL_SECONDS = 45


def invalidate_dashboard_cache(
    org_id: str
) -> None:
    """Invalidate every cached dashboard range for an organization."""

    for key in list(_DASHBOARD_CACHE):
        if key[0] == org_id:
            _DASHBOARD_CACHE.pop(
                key,
                None
            )


def _row_hash(
    org_id: str,
    store_id: str,
    product_id: str,
    date_iso: str,
    qty: int,
    rev: float
) -> str:

    raw = (
        f"{org_id}|"
        f"{store_id}|"
        f"{product_id}|"
        f"{date_iso}|"
        f"{qty}|"
        f"{rev}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# CSV UPLOAD
# ============================================================

async def upload_sales_csv(
    org_id: str,
    user_id: str,
    file: UploadFile,
    request: Request
) -> dict:
    """Parse, validate and idempotently bulk-load sales CSV data."""

    contents = await file.read()

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File exceeds the "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)}MB "
                f"upload limit"
            )
        )

    file_hash = hashlib.sha256(
        contents
    ).hexdigest()

    try:
        csv_text = contents.decode(
            "utf-8"
        )

    except UnicodeDecodeError:

        try:
            csv_text = contents.decode(
                "latin-1"
            )

        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file encoding: {exc}"
            )

    reader = csv.DictReader(
        io.StringIO(csv_text)
    )

    required_cols = {
        "date",
        "store_id",
        "product_id",
        "category",
        "quantity",
        "revenue"
    }

    headers = {
        h.strip().lower()
        for h in (
            reader.fieldnames
            or []
        )
    }

    missing = (
        required_cols - headers
    )

    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV is missing required "
                "columns: "
                +
                ", ".join(missing)
            )
        )

    records = []
    errors = []
    row_num = 1

    for row in reader:

        row_num += 1

        if (
            row_num - 1
            > MAX_UPLOAD_ROWS
        ):
            errors.append({
                "row": row_num,
                "error": (
                    f"Row cap of "
                    f"{MAX_UPLOAD_ROWS} "
                    "exceeded — remaining "
                    "rows skipped"
                )
            })
            break

        row_clean = {
            key.strip().lower():
                value.strip()
            for key, value in row.items()
            if key
        }

        try:
            dt_str = row_clean[
                "date"
            ]

            dt = None

            for fmt in (
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%m/%d/%Y"
            ):

                try:
                    dt = datetime.strptime(
                        dt_str,
                        fmt
                    ).replace(
                        tzinfo=timezone.utc
                    )
                    break

                except ValueError:
                    continue

            if not dt:
                raise ValueError(
                    f"Unrecognized date format: "
                    f"'{dt_str}'"
                )

            qty = int(
                row_clean["quantity"]
            )

            rev = float(
                row_clean["revenue"]
            )

            if qty < 0 or rev < 0:
                raise ValueError(
                    "Quantity and Revenue "
                    "must be non-negative values"
                )

            if (
                not row_clean.get(
                    "store_id"
                )
                or
                not row_clean.get(
                    "product_id"
                )
            ):
                raise ValueError(
                    "store_id and product_id "
                    "are required"
                )

            is_holiday = (
                row_clean.get(
                    "is_holiday",
                    "false"
                ).lower()
                in (
                    "true",
                    "1",
                    "yes"
                )
            )

            is_promo = (
                row_clean.get(
                    "is_promo",
                    "false"
                ).lower()
                in (
                    "true",
                    "1",
                    "yes"
                )
            )

            date_iso = dt.strftime(
                "%Y-%m-%d"
            )

            store_id = row_clean[
                "store_id"
            ]

            product_id = row_clean[
                "product_id"
            ]

            revenue = round(
                rev,
                2
            )

            records.append({
                "date": dt,
                "store_id": store_id,
                "product_id": product_id,
                "category": row_clean[
                    "category"
                ],
                "quantity": qty,
                "revenue": revenue,
                "is_holiday": is_holiday,
                "is_promo": is_promo,
                "row_hash": _row_hash(
                    org_id,
                    store_id,
                    product_id,
                    date_iso,
                    qty,
                    revenue
                ),
            })

        except Exception as exc:

            errors.append({
                "row": row_num,
                "error": str(exc)
            })

    if not records and not errors:
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV file contains "
                "no data rows"
            )
        )

    if not records:
        raise HTTPException(
            status_code=400,
            detail=(
                f"All {len(errors)} rows "
                "failed validation — "
                "nothing was imported"
            )
        )

    # ========================================================
    # IDEMPOTENCY
    # ========================================================

    existing_hashes = (
        await sales_repo.find_existing_hashes(
            org_id,
            [
                row["row_hash"]
                for row in records
            ]
        )
    )

    new_records = [
        row
        for row in records
        if row["row_hash"]
        not in existing_hashes
    ]

    skipped_duplicates = (
        len(records)
        - len(new_records)
    )

    # ========================================================
    # IMPORT RECORD
    # ========================================================

    import_doc = (
        await imports_repo.insert(
            org_id,
            {
                "filename":
                    file.filename,

                "file_hash":
                    file_hash,

                "rows_total":
                    row_num - 1,

                "rows_imported":
                    0,

                "rows_skipped_duplicate":
                    skipped_duplicates,

                "rows_failed":
                    len(errors),

                "status":
                    "completed",

                "uploaded_by":
                    user_id,

                "error_report":
                    errors[:200],

                "created_at":
                    datetime.now(
                        timezone.utc
                    ),
            }
        )
    )

    import_id = str(
        import_doc["_id"]
    )

    for row in new_records:
        row["import_id"] = import_id

    inserted = (
        await sales_repo.insert_many(
            org_id,
            new_records
        )
    )

    # ========================================================
    # AUTO REGISTER STORES / PRODUCTS
    # ========================================================

    for row in new_records:

        await stores_repo.upsert(
            org_id,
            row["store_id"],
            {
                "is_active": True
            }
        )

        await products_repo.upsert(
            org_id,
            row["product_id"],
            {
                "category":
                    row["category"],

                "is_active":
                    True
            }
        )

    await imports_repo.mark_rows_imported(
        org_id,
        import_id,
        inserted
    )

    if errors:

        from app.services.alerts_service import (
            notify_import_failed
        )

        await notify_import_failed(
            org_id,
            file.filename,
            len(errors),
            import_id
        )

    await log_event(
        "sales_csv_uploaded",
        user_id=user_id,
        org_id=org_id,
        request=request,
        metadata={
            "filename":
                file.filename,

            "rows_imported":
                inserted,

            "rows_skipped":
                skipped_duplicates,

            "rows_failed":
                len(errors),

            "import_id":
                import_id
        }
    )

    # ========================================================
    # IMPORTANT:
    # NEW DATA INVALIDATES BOTH DASHBOARD AND FORECAST CACHE
    # ========================================================

    invalidate_dashboard_cache(
        org_id
    )

    try:

        from app.ml.predictor import (
            ai_predictor
        )

        ai_predictor.invalidate_cache(
            org_id
        )

    except Exception:
        pass

    # ========================================================
    # RESPONSE
    # ========================================================

    message = (
        f"Imported {inserted} rows"
    )

    if skipped_duplicates:
        message += (
            f", skipped "
            f"{skipped_duplicates} duplicates"
        )

    if errors:
        message += (
            f", {len(errors)} rows "
            "failed validation"
        )

    return {
        "status":
            "success",

        "message":
            message,

        "count":
            inserted,

        "import_id":
            import_id,

        "rows_imported":
            inserted,

        "rows_skipped_duplicate":
            skipped_duplicates,

        "rows_failed":
            len(errors),

        "errors":
            errors[:50],
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

async def get_dashboard_summary(
    org_id: str,
    days: int = 30
) -> dict:
    """Compute dashboard metrics with short-lived caching."""

    days = max(
        7,
        min(
            int(days),
            365
        )
    )

    cache_key = (
        org_id,
        days
    )

    now = time.monotonic()

    # ========================================================
    # SERVER CACHE
    # ========================================================

    cached = _DASHBOARD_CACHE.get(
        cache_key
    )

    if (
    cached
    and
    now - cached[0]
    < DASHBOARD_CACHE_TTL_SECONDS
):
        return copy.deepcopy(
            cached[1]
        )

    # ========================================================
    # LATEST SALE
    # ========================================================

    latest_sale = (
        await sales_repo.find_latest(
            org_id
        )
    )

    if not latest_sale:

        result = {
            "status":
                "empty",

            "kpis": {
                "total_sales":
                    0.0,

                "avg_daily_sales":
                    0.0,

                "forecast_sales_30d":
                    0.0,

                "variance_pct":
                    0.0,

                "active_stores":
                    0,

                "active_products":
                    0
            },

            "history_chart":
                [],

            "category_chart":
                [],

            "recent_transactions":
                []
        }

        _DASHBOARD_CACHE[
            cache_key
        ] = (
            now,
            result
        )

        return copy.deepcopy(
            result
        )

    anchor_date = (
        latest_sale["date"]
    )

    start_period = (
        anchor_date
        -
        timedelta(
            days=days
        )
    )

    prior_start = (
        anchor_date
        -
        timedelta(
            days=days * 2
        )
    )

    # ========================================================
    # TOTAL SALES
    # ========================================================

    pipeline_period = [

        {
            "$match": {
                "date": {
                    "$gte":
                        start_period,

                    "$lte":
                        anchor_date
                }
            }
        },

        {
            "$group": {
                "_id": None,

                "total_rev": {
                    "$sum":
                        "$revenue"
                },

                "stores": {
                    "$addToSet":
                        "$store_id"
                },

                "products": {
                    "$addToSet":
                        "$product_id"
                }
            }
        }
    ]

    res_list = (
        await sales_repo.aggregate(
            org_id,
            pipeline_period,
            length=1
        )
    )

    total_sales = 0.0
    active_stores = 0
    active_products = 0

    if res_list:

        summary = res_list[0]

        total_sales = float(
            summary.get(
                "total_rev",
                0.0
            )
        )

        active_stores = len(
            summary.get(
                "stores",
                []
            )
        )

        active_products = len(
            summary.get(
                "products",
                []
            )
        )

    # ========================================================
    # AI FORECAST
    # ========================================================

    from app.ml.predictor import (
        ai_predictor
    )

    try:

        preds = await ai_predictor.predict(
            org_id,
            horizon_days=days
        )

        forecast_sales_period = sum(
            float(
                prediction.get(
                    "revenue",
                    0.0
                )
            )
            for prediction in preds
        )

    except Exception as exc:

        log.exception(
            "Dashboard forecast failed "
            "for org=%s: %s",
            org_id,
            exc
        )

        preds = []

        forecast_sales_period = (
            total_sales * 1.05
        )

    # ========================================================
    # VARIANCE
    # ========================================================

    variance_pct = (
        (
            total_sales
            -
            forecast_sales_period
        )
        /
        (
            forecast_sales_period
            +
            1e-8
        )
    ) * 100.0

    # ========================================================
    # ACTUAL DAILY SALES
    # ========================================================

    daily_actuals_pipeline = [

        {
            "$match": {
                "date": {
                    "$gte":
                        start_period,

                    "$lte":
                        anchor_date
                }
            }
        },

        {
            "$group": {

                "_id": {
                    "$dateToString": {
                        "format":
                            "%Y-%m-%d",

                        "date":
                            "$date"
                    }
                },

                "revenue": {
                    "$sum":
                        "$revenue"
                }
            }
        },

        {
            "$sort": {
                "_id": 1
            }
        }
    ]

    actuals_res = (
        await sales_repo.aggregate(
            org_id,
            daily_actuals_pipeline,
            length=days + 5
        )
    )

    history_chart = []

    for row in actuals_res:

        history_chart.append({
            "date":
                row["_id"],

            "actual":
                round(
                    float(
                        row["revenue"]
                    ),
                    2
                ),

            "forecast":
                None
        })

    # ========================================================
    # FUTURE FORECAST
    # ========================================================

    if preds:

        daily_preds = {}

        for prediction in preds:

            date_value = (
                prediction["date"]
            )

            if hasattr(
                date_value,
                "strftime"
            ):
                date_str = (
                    date_value.strftime(
                        "%Y-%m-%d"
                    )
                )
            else:
                date_str = str(
                    date_value
                )[:10]

            daily_preds[
                date_str
            ] = (
                daily_preds.get(
                    date_str,
                    0.0
                )
                +
                float(
                    prediction.get(
                        "revenue",
                        0.0
                    )
                )
            )

        for date_str, value in sorted(
            daily_preds.items()
        ):

            history_chart.append({
                "date":
                    date_str,

                "actual":
                    None,

                "forecast":
                    round(
                        value,
                        2
                    )
            })

    # ========================================================
    # CATEGORY BREAKDOWN
    # ========================================================

    cat_pipeline = [

        {
            "$match": {
                "date": {
                    "$gte":
                        start_period,

                    "$lte":
                        anchor_date
                }
            }
        },

        {
            "$group": {
                "_id":
                    "$category",

                "value": {
                    "$sum":
                        "$revenue"
                }
            }
        },

        {
            "$sort": {
                "value": -1
            }
        }
    ]

    cat_res = (
        await sales_repo.aggregate(
            org_id,
            cat_pipeline,
            length=10
        )
    )

    prior_cat_pipeline = [

        {
            "$match": {
                "date": {
                    "$gte":
                        prior_start,

                    "$lt":
                        start_period
                }
            }
        },

        {
            "$group": {
                "_id":
                    "$category",

                "value": {
                    "$sum":
                        "$revenue"
                }
            }
        }
    ]

    prior_cat_res = (
        await sales_repo.aggregate(
            org_id,
            prior_cat_pipeline,
            length=10
        )
    )

    prior_by_category = {
        row["_id"]:
            float(
                row["value"]
            )

        for row in prior_cat_res
    }

    category_total = (
        sum(
            float(
                row["value"]
            )
            for row in cat_res
        )
        or 1e-8
    )

    category_chart = []

    for row in cat_res:

        value = round(
            float(
                row["value"]
            ),
            2
        )

        previous = (
            prior_by_category.get(
                row["_id"],
                0.0
            )
        )

        delta_pct = (
            (
                value
                -
                previous
            )
            /
            previous
            *
            100.0
        ) if previous > 0 else None

        category_chart.append({

            "name":
                row["_id"],

            "value":
                value,

            "share_pct":
                round(
                    value /
                    category_total *
                    100.0,
                    1
                ),

            "delta_pct":
                round(
                    delta_pct,
                    1
                )
                if delta_pct
                is not None
                else None
        })

    # ========================================================
    # RECENT TRANSACTIONS
    # ========================================================

    recent_docs = (
        await sales_repo.find_recent(
            org_id,
            limit=10
        )
    )

    recent_transactions = [
        serialize(doc)
        for doc in recent_docs
    ]

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        "status":
            "success",

        "range_days":
            days,

        "kpis": {

            "total_sales":
                round(
                    total_sales,
                    2
                ),

            "avg_daily_sales":
                round(
                    total_sales /
                    days,
                    2
                ),

            "forecast_sales_30d":
                round(
                    forecast_sales_period,
                    2
                ),

            "variance_pct":
                round(
                    variance_pct,
                    2
                ),

            "active_stores":
                active_stores,

            "active_products":
                active_products
        },

        "history_chart":
            history_chart,

        "category_chart":
            category_chart,

        "recent_transactions":
            recent_transactions
    }

    # ========================================================
    # SAVE SERVER CACHE
    # ========================================================

    _DASHBOARD_CACHE[
        cache_key
    ] = (
        time.monotonic(),
        copy.deepcopy(
            result
        )
    )

    return result


# ============================================================
# SALES HISTORY
# ============================================================

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
    """Query paginated historical transactions."""

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
            date_query["$gte"] = (
                datetime.strptime(
                    start_date,
                    "%Y-%m-%d"
                ).replace(
                    tzinfo=timezone.utc
                )
            )
        except ValueError:
            pass

    if end_date:
        try:
            date_query["$lte"] = (
                datetime.strptime(
                    end_date,
                    "%Y-%m-%d"
                ).replace(
                    tzinfo=timezone.utc
                )
            )
        except ValueError:
            pass

    if date_query:
        query["date"] = date_query

    total = await sales_repo.count(
        org_id,
        query
    )

    skip = (
        page - 1
    ) * limit

    docs = await sales_repo.find_paginated(
        org_id,
        query,
        skip,
        limit
    )

    stores = (
        await sales_repo.distinct_field(
            org_id,
            "store_id"
        )
    )

    products = (
        await sales_repo.distinct_field(
            org_id,
            "product_id"
        )
    )

    categories = (
        await sales_repo.distinct_field(
            org_id,
            "category"
        )
    )

    return {
        "status":
            "success",

        "total":
            total,

        "page":
            page,

        "limit":
            limit,

        "sales": [
            serialize(doc)
            for doc in docs
        ],

        "filters": {
            "stores":
                sorted(stores),

            "products":
                sorted(products),

            "categories":
                sorted(categories)
        }
    }


# ============================================================
# IMPORT HISTORY
# ============================================================

async def get_import_history(
    org_id: str
) -> dict:

    docs = (
        await imports_repo.list_recent(
            org_id
        )
    )

    return {
        "status":
            "success",

        "imports": [
            serialize(doc)
            for doc in docs
        ]
    }


# ============================================================
# UNDO IMPORT
# ============================================================

async def undo_import(
    org_id: str,
    import_id: str,
    request: Request
) -> dict:
    """Soft-delete every transaction from an import."""

    batch = (
        await imports_repo.find_by_id(
            org_id,
            import_id
        )
    )

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Import not found"
        )

    if batch.get(
        "status"
    ) == "undone":
        raise HTTPException(
            status_code=400,
            detail=(
                "This import has "
                "already been undone"
            )
        )

    removed = (
        await sales_repo.soft_delete_by_import(
            org_id,
            import_id
        )
    )

    await imports_repo.mark_undone(
        org_id,
        import_id,
        removed
    )

    await log_event(
        "import_undone",
        org_id=org_id,
        request=request,
        metadata={
            "import_id":
                import_id,

            "rows_removed":
                removed
        }
    )

    # Clear dashboard and forecast cache
    # after undoing sales data.

    invalidate_dashboard_cache(
        org_id
    )

    try:

        from app.ml.predictor import (
            ai_predictor
        )

        ai_predictor.invalidate_cache(
            org_id
        )

    except Exception:
        pass

    return {
        "status":
            "success",

        "message":
            f"Removed {removed} rows "
            "from this import",

        "rows_removed":
            removed
    }