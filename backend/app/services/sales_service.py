"""Sales data service.

Handles CSV parsing/upload, paginated historical querying, and dashboard
summaries. Real retail datasets are normalized into SellThru's internal
schema while preserving customer and transaction identifiers.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import logging
import time

from datetime import (
    datetime,
    timezone,
    timedelta,
)

from typing import Optional

from fastapi import (
    HTTPException,
    UploadFile,
    Request,
)

from app.repositories import (
    imports_repo,
    products_repo,
    sales_repo,
    stores_repo,
)

from app.schemas.common import serialize

from app.services.audit_service import (
    log_event,
)


log = logging.getLogger(
    "sellthru.sales"
)

MAX_UPLOAD_ROWS = 200_000
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


# ============================================================
# DASHBOARD CACHE
# ============================================================

_DASHBOARD_CACHE: dict[
    tuple[str, int],
    tuple[float, dict],
] = {}

DASHBOARD_CACHE_TTL_SECONDS = 300


def invalidate_dashboard_cache(
    org_id: str,
) -> None:
    """Clear all cached dashboard ranges for an organization."""

    for key in list(
        _DASHBOARD_CACHE
    ):

        if key[0] == org_id:

            _DASHBOARD_CACHE.pop(
                key,
                None,
            )


# ============================================================
# ROW HASH
# ============================================================

def _row_hash(
    org_id: str,
    store_id: str | None,
    product_id: str,
    date_iso: str,
    qty: float,
    rev: float,
    customer_id: str | None = None,
    transaction_id: str | None = None,
) -> str:
    raw = (
        f"{org_id}|"
        f"{store_id or ''}|"
        f"{product_id}|"
        f"{date_iso}|"
        f"{qty}|"
        f"{rev}|"
        f"{customer_id or ''}|"
        f"{transaction_id or ''}"
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
    request: Request,
) -> dict:
    """Import SellThru CSV or the supplied retail dataset."""

    contents = await file.read()

    if len(contents) > MAX_UPLOAD_BYTES:

        raise HTTPException(
            status_code=400,
            detail=(
                "File exceeds the "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)}MB "
                "upload limit"
            ),
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
                detail=(
                    f"Invalid file encoding: "
                    f"{exc}"
                ),
            )

    reader = csv.DictReader(
        io.StringIO(
            csv_text
        )
    )

    headers = {
        h.strip().lower()
        for h in (
            reader.fieldnames
            or []
        )
        if h
    }

    # ========================================================
    # STANDARD SELLTHRU FORMAT
    # ========================================================

    standard_required = {
        "date",
        "store_id",
        "product_id",
        "category",
        "quantity",
        "revenue",
    }

    # ========================================================
    # YOUR REAL DATASET FORMAT
    # ========================================================

    retail_required = {
        "date",
        "customer_id",
        "transaction_id",
        "sku_category",
        "sku",
        "quantity",
        "sales_amount",
    }

    is_retail_dataset = (
        retail_required
        .issubset(headers)
    )

    if (
        not is_retail_dataset
        and
        not standard_required.issubset(
            headers
        )
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "CSV format not recognized. "
                "Expected either SellThru format "
                "or the retail dataset format: "
                "Date, Customer_ID, Transaction_ID, "
                "SKU_Category, SKU, Quantity, "
                "Sales_Amount."
            ),
        )

    records = []
    errors = []

    row_num = 1

    # ========================================================
    # PARSE ROWS
    # ========================================================

    for row in reader:

        row_num += 1

        if (
            row_num - 1
            >
            MAX_UPLOAD_ROWS
        ):

            errors.append({
                "row":
                    row_num,

                "error":
                    (
                        f"Row cap of "
                        f"{MAX_UPLOAD_ROWS} "
                        "exceeded"
                    ),
            })

            break

        row_clean = {
            key.strip().lower():
                (
                    value.strip()
                    if isinstance(
                        value,
                        str,
                    )
                    else ""
                )

            for key, value
            in row.items()
            if key
        }

        try:

            # ==================================================
            # REAL RETAIL DATASET
            # ==================================================

            if is_retail_dataset:

                date_text = (
                    row_clean["date"]
                )

                store_id = None

                product_id = (
                    row_clean["sku"]
                )

                category = (
                    row_clean[
                        "sku_category"
                    ]
                )

                quantity = float(
                    row_clean[
                        "quantity"
                    ]
                )

                revenue = float(
                    row_clean[
                        "sales_amount"
                    ]
                )

                customer_id = (
                    row_clean[
                        "customer_id"
                    ]
                )

                transaction_id = (
                    row_clean[
                        "transaction_id"
                    ]
                )

                source = "real"

            # ==================================================
            # EXISTING SELLTHRU FORMAT
            # ==================================================

            else:

                date_text = (
                    row_clean["date"]
                )

                store_id = (
                    row_clean[
                        "store_id"
                    ]
                )

                product_id = (
                    row_clean[
                        "product_id"
                    ]
                )

                category = (
                    row_clean[
                        "category"
                    ]
                )

                quantity = float(
                    row_clean[
                        "quantity"
                    ]
                )

                revenue = float(
                    row_clean[
                        "revenue"
                    ]
                )

                customer_id = (
                    row_clean.get(
                        "customer_id"
                    )
                    or None
                )

                transaction_id = (
                    row_clean.get(
                        "transaction_id"
                    )
                    or None
                )

                source = "uploaded"

            # ==================================================
            # DATE PARSING
            # ==================================================

            parsed_date = None

            for fmt in (
                "%d/%m/%Y",
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
            ):

                try:

                    parsed_date = (
                        datetime.strptime(
                            date_text,
                            fmt,
                        ).replace(
                            tzinfo=timezone.utc
                        )
                    )

                    break

                except ValueError:

                    continue

            if not parsed_date:

                raise ValueError(
                    f"Unrecognized date: "
                    f"{date_text}"
                )

            # ==================================================
            # VALIDATION
            # ==================================================

            if quantity < 0:

                raise ValueError(
                    "Quantity cannot be negative"
                )

            if revenue < 0:

                raise ValueError(
                    "Revenue cannot be negative"
                )

            if not product_id:

                raise ValueError(
                    "Product/SKU is required"
                )

            # ==================================================
            # OPTIONAL FLAGS
            # ==================================================

            is_holiday = (
                row_clean.get(
                    "is_holiday",
                    "false",
                ).lower()
                in (
                    "true",
                    "1",
                    "yes",
                )
            )

            is_promo = (
                row_clean.get(
                    "is_promo",
                    "false",
                ).lower()
                in (
                    "true",
                    "1",
                    "yes",
                )
            )

            quantity = round(
                quantity,
                4,
            )

            revenue = round(
                revenue,
                2,
            )

            date_iso = (
                parsed_date.strftime(
                    "%Y-%m-%d"
                )
            )

            document = {

                "date":
                    parsed_date,

                "store_id":
                    store_id,

                "product_id":
                    product_id,

                "category":
                    category
                    or
                    "Uncategorized",

                "quantity":
                    quantity,

                "revenue":
                    revenue,

                "is_holiday":
                    is_holiday,

                "is_promo":
                    is_promo,

                "source":
                    source,

                "row_hash":
                    _row_hash(
                        org_id,
                        store_id,
                        product_id,
                        date_iso,
                        quantity,
                        revenue,
                        customer_id=customer_id,
                        transaction_id=transaction_id,
                    ),
            }

            if customer_id:

                document[
                    "customer_id"
                ] = customer_id

            if transaction_id:

                document[
                    "transaction_id"
                ] = transaction_id

            records.append(
                document
            )

        except Exception as exc:

            errors.append({
                "row":
                    row_num,

                "error":
                    str(exc),
            })

    # ========================================================
    # EMPTY FILE
    # ========================================================

    if (
        not records
        and
        not errors
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "CSV file contains "
                "no data rows"
            ),
        )

    if not records:

        raise HTTPException(
            status_code=400,
            detail=(
                f"All {len(errors)} rows "
                "failed validation"
            ),
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
            ],
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
        -
        len(new_records)
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

                "dataset_type":
                    (
                        "retail_real"
                        if is_retail_dataset
                        else "standard"
                    ),

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
            },
        )
    )

    import_id = str(
        import_doc["_id"]
    )

    for row in new_records:

        row["import_id"] = (
            import_id
        )

    # ========================================================
    # INSERT DATA
    # ========================================================

    inserted = (
        await sales_repo.insert_many(
            org_id,
            new_records,
        )
    )

    # ========================================================
    # REGISTER PRODUCTS / STORES (BULK & DEDUPLICATED)
    # ========================================================

    product_map = {}
    for row in new_records:
        pid = row.get("product_id")
        if pid and pid not in product_map:
            product_map[pid] = {
                "product_id": pid,
                "category": row.get("category", "Uncategorized"),
            }

    if product_map:
        await products_repo.bulk_upsert(
            org_id,
            list(product_map.values()),
        )

    # For standard format only: register stores if store_id exists
    if not is_retail_dataset:
        store_ids = {
            row["store_id"]
            for row in new_records
            if row.get("store_id")
        }
        for sid in store_ids:
            await stores_repo.upsert(
                org_id,
                sid,
                {"is_active": True},
            )

    await imports_repo.mark_rows_imported(
        org_id,
        import_id,
        inserted,
    )

    # ========================================================
    # LOG
    # ========================================================

    await log_event(
        "sales_csv_uploaded",
        user_id=user_id,
        org_id=org_id,
        request=request,
        metadata={
            "filename":
                file.filename,

            "dataset_type":
                (
                    "retail_real"
                    if is_retail_dataset
                    else "standard"
                ),

            "rows_imported":
                inserted,

            "rows_skipped":
                skipped_duplicates,

            "rows_failed":
                len(errors),

            "import_id":
                import_id,
        },
    )

    # ========================================================
    # CACHE INVALIDATION
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

        import asyncio

        asyncio.create_task(
            ai_predictor.train_model(
                org_id
            )
        )

    except Exception:

        log.exception(
            "ML cache invalidation or training trigger failed"
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    message = (
        f"Imported {inserted} rows"
    )

    if is_retail_dataset:

        message += (
            " from real retail dataset"
        )

    if skipped_duplicates:

        message += (
            f", skipped "
            f"{skipped_duplicates} duplicates"
        )

    if errors:

        message += (
            f", {len(errors)} rows failed"
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

        "dataset_type":
            (
                "retail_real"
                if is_retail_dataset
                else "standard"
            ),

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
# DASHBOARD
# ============================================================

async def get_dashboard_summary(
    org_id: str,
    days: int = 30,
) -> dict:
    """Return real retail data when a real dataset exists."""

    days = max(
        7,
        min(
            int(days),
            365,
        ),
    )

    cache_key = (
        org_id,
        days,
    )

    now = time.monotonic()

    cached = _DASHBOARD_CACHE.get(
        cache_key
    )

    if (
        cached
        and
        now - cached[0]
        <
        DASHBOARD_CACHE_TTL_SECONDS
    ):

        return copy.deepcopy(
            cached[1]
        )

    # ========================================================
    # REAL DATA DETECTION
    # ========================================================

    real_probe = (
        await sales_repo.aggregate(
            org_id,
            [
                {
                    "$match": {
                        "source":
                            "real",
                    }
                },
                {
                    "$limit":
                        1,
                },
            ],
            length=1,
        )
    )

    real_mode = bool(
        real_probe
    )

    source_match = (
        {
            "source":
                "real",
        }
        if real_mode
        else {}
    )

    # ========================================================
    # LATEST REAL DATE
    # ========================================================

    latest_rows = (
        await sales_repo.aggregate(
            org_id,
            [
                {
                    "$match":
                        source_match,
                },
                {
                    "$sort": {
                        "date":
                            -1,
                    }
                },
                {
                    "$limit":
                        1,
                },
            ],
            length=1,
        )
    )

    latest_sale = (
        latest_rows[0]
        if latest_rows
        else None
    )

    if not latest_sale:

        result = {

            "status":
                "empty",

            "data_source":
                "real"
                if real_mode
                else "demo",

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
                    0,

                "active_customers":
                    0,

                "transactions":
                    0,
            },

            "history_chart":
                [],

            "category_chart":
                [],

            "recent_transactions":
                [],
        }

        _DASHBOARD_CACHE[
            cache_key
        ] = (
            now,
            result,
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

    # ========================================================
    # KPI QUERY
    # ========================================================

    summary_pipeline = [

        {
            "$match": {
                **source_match,

                "date": {
                    "$gte":
                        start_period,

                    "$lte":
                        anchor_date,
                },
            }
        },

        {
            "$group": {

                "_id":
                    None,

                "total_rev": {
                    "$sum":
                        "$revenue",
                },

                "stores": {
                    "$addToSet":
                        "$store_id",
                },

                "products": {
                    "$addToSet":
                        "$product_id",
                },

                "customers": {
                    "$addToSet":
                        "$customer_id",
                },

                "transactions": {
                    "$sum":
                        1,
                },
            }
        },
    ]

    summary_rows = (
        await sales_repo.aggregate(
            org_id,
            summary_pipeline,
            length=1,
        )
    )

    summary = (
        summary_rows[0]
        if summary_rows
        else {}
    )

    total_sales = float(
        summary.get(
            "total_rev",
            0.0,
        )
    )

    active_stores = len([
        value
        for value
        in summary.get(
            "stores",
            [],
        )
        if value
    ])

    active_products = len([
        value
        for value
        in summary.get(
            "products",
            [],
        )
        if value
    ])

    active_customers = len([
        value
        for value
        in summary.get(
            "customers",
            [],
        )
        if value
    ])

    transactions = int(
        summary.get(
            "transactions",
            0,
        )
    )

    # ========================================================
    # FORECAST
    # ========================================================

    from app.ml.predictor import (
        ai_predictor
    )

    try:

        predictions = (
            await ai_predictor.predict(
                org_id,
                horizon_days=days,
            )
        )

        forecast_sales = sum(
            float(
                prediction.get(
                    "revenue",
                    0.0,
                )
            )

            for prediction
            in predictions
        )

    except Exception as exc:

        log.exception(
            "Dashboard forecast failed: %s",
            exc,
        )

        predictions = []

        forecast_sales = (
            total_sales
            *
            1.05
        )

    # ========================================================
    # VARIANCE
    # ========================================================

    variance_pct = (

        (
            forecast_sales
            -
            total_sales
        )

        /

        (
            total_sales
            +
            1e-8
        )

        *

        100.0
    )

    # ========================================================
    # ACTUAL DAILY SALES
    # ========================================================

    actual_pipeline = [

        {
            "$match": {
                **source_match,

                "date": {
                    "$gte":
                        start_period,

                    "$lte":
                        anchor_date,
                },
            }
        },

        {
            "$group": {

                "_id": {
                    "$dateToString": {
                        "format":
                            "%Y-%m-%d",

                        "date":
                            "$date",
                    }
                },

                "revenue": {
                    "$sum":
                        "$revenue",
                },
            }
        },

        {
            "$sort": {
                "_id":
                    1,
            }
        },
    ]

    actual_rows = (
        await sales_repo.aggregate(
            org_id,
            actual_pipeline,
            length=days + 5,
        )
    )

    history_chart = [

        {
            "date":
                row["_id"],

            "actual":
                round(
                    float(
                        row["revenue"]
                    ),
                    2,
                ),

            "forecast":
                None,
        }

        for row
        in actual_rows
    ]

    # ========================================================
    # FORECAST BY DATE
    # ========================================================

    forecast_by_date = {}

    for prediction in predictions:

        date_value = (
            prediction.get(
                "date"
            )
        )

        if hasattr(
            date_value,
            "strftime",
        ):

            date_key = (
                date_value.strftime(
                    "%Y-%m-%d"
                )
            )

        else:

            date_key = str(
                date_value
            )[:10]

        forecast_by_date[
            date_key
        ] = (
            forecast_by_date.get(
                date_key,
                0.0,
            )
            +
            float(
                prediction.get(
                    "revenue",
                    0.0,
                )
            )
        )
    if history_chart and history_chart[-1].get("actual") is not None:
        history_chart[-1]["forecast"] = history_chart[-1]["actual"]

    for (
        date_key,
        value,
    ) in sorted(
        forecast_by_date.items()
    ):

        history_chart.append({

            "date":
                date_key,

            "actual":
                None,

            "forecast":
                round(
                    value,
                    2,
                ),
        })

    # ========================================================
    # CATEGORY MIX
    # ========================================================

    category_pipeline = [

        {
            "$match": {
                **source_match,

                "date": {
                    "$gte":
                        start_period,

                    "$lte":
                        anchor_date,
                },
            }
        },

        {
            "$group": {

                "_id":
                    "$category",

                "value": {
                    "$sum":
                        "$revenue",
                },
            }
        },

        {
            "$sort": {
                "value":
                    -1,
            }
        },
    ]

    category_rows = (
        await sales_repo.aggregate(
            org_id,
            category_pipeline,
            length=10,
        )
    )

    category_total = (
        sum(
            float(
                row["value"]
            )
            for row
            in category_rows
        )
        or
        1e-8
    )

    category_chart = [

        {
            "name":
                row["_id"]
                or
                "Uncategorized",

            "value":
                round(
                    float(
                        row["value"]
                    ),
                    2,
                ),

            "share_pct":
                round(
                    float(
                        row["value"]
                    )
                    /
                    category_total
                    *
                    100.0,
                    1,
                ),
        }

        for row
        in category_rows
    ]

    # ========================================================
    # RECENT TRANSACTIONS
    # ========================================================

    recent_rows = (
        await sales_repo.aggregate(
            org_id,
            [
                {
                    "$match":
                        source_match,
                },
                {
                    "$sort": {
                        "date":
                            -1,
                    }
                },
                {
                    "$limit":
                        10,
                },
            ],
            length=10,
        )
    )

    recent_transactions = [
        serialize(row)
        for row
        in recent_rows
    ]

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        "status":
            "success",

        "range_days":
            days,

        "data_source":
            "real"
            if real_mode
            else "demo",

        "kpis": {

            "total_sales":
                round(
                    total_sales,
                    2,
                ),

            "avg_daily_sales":
                round(
                    total_sales
                    /
                    max(
                        days,
                        1,
                    ),
                    2,
                ),

            "forecast_sales_30d":
                round(
                    forecast_sales,
                    2,
                ),

            "variance_pct":
                round(
                    variance_pct,
                    2,
                ),

            "active_stores":
                None if real_mode else active_stores,

            "active_products":
                active_products,

            "active_customers":
                active_customers,

            "transactions":
                transactions,
        },

        "history_chart":
            history_chart,

        "category_chart":
            category_chart,

        "recent_transactions":
            recent_transactions,
    }

    _DASHBOARD_CACHE[
        cache_key
    ] = (
        time.monotonic(),
        copy.deepcopy(
            result
        ),
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

    query = {}

    if store_id:
        query["store_id"] = (
            store_id
        )

    if product_id:
        query["product_id"] = (
            product_id
        )

    if category:
        query["category"] = (
            category
        )

    date_query = {}

    if start_date:

        try:

            date_query["$gte"] = (
                datetime.strptime(
                    start_date,
                    "%Y-%m-%d",
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
                    "%Y-%m-%d",
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
        query,
    )

    skip = (
        page - 1
    ) * limit

    docs = (
        await sales_repo.find_paginated(
            org_id,
            query,
            skip,
            limit,
        )
    )

    stores = (
        await sales_repo.distinct_field(
            org_id,
            "store_id",
        )
    )

    products = (
        await sales_repo.distinct_field(
            org_id,
            "product_id",
        )
    )

    categories = (
        await sales_repo.distinct_field(
            org_id,
            "category",
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
            for doc
            in docs
        ],

        "filters": {

            "stores":
                sorted([s for s in stores if s]),

            "products":
                sorted([p for p in products if p]),

            "categories":
                sorted([c for c in categories if c]),
        },
    }


# ============================================================
# IMPORT HISTORY
# ============================================================

async def get_import_history(
    org_id: str,
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
            for doc
            in docs
        ],
    }


# ============================================================
# UNDO IMPORT
# ============================================================

async def undo_import(
    org_id: str,
    import_id: str,
    request: Request,
) -> dict:

    batch = (
        await imports_repo.find_by_id(
            org_id,
            import_id,
        )
    )

    if not batch:

        raise HTTPException(
            status_code=404,
            detail="Import not found",
        )

    if (
        batch.get(
            "status"
        )
        ==
        "undone"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "This import has "
                "already been undone"
            ),
        )

    removed = (
        await sales_repo.soft_delete_by_import(
            org_id,
            import_id,
        )
    )

    await imports_repo.mark_undone(
        org_id,
        import_id,
        removed,
    )

    await log_event(
        "import_undone",
        org_id=org_id,
        request=request,
        metadata={
            "import_id":
                import_id,

            "rows_removed":
                removed,
        },
    )

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

        log.exception(
            "ML cache invalidation failed"
        )

    return {

        "status":
            "success",

        "message":
            (
                f"Removed {removed} rows "
                "from this import"
            ),

        "rows_removed":
            removed,
    }