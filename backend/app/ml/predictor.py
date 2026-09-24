"""Machine Learning Sales Predictor.

Supports both SellThru demo data and the supplied real retail dataset.

Real retail data:
    Date
    Customer_ID
    Transaction_ID
    SKU_Category
    SKU
    Quantity
    Sales_Amount

Real data is never forecast with the old demo model.
"""

from __future__ import annotations

import copy
import logging
import os
import pickle
import time

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import (
    RandomForestRegressor,
)

from sklearn.preprocessing import (
    LabelEncoder,
)

from app.repositories import (
    models_repo,
    sales_repo,
)

from app.ml.holidays import (
    holiday_flags,
)

from app.ml.metrics import (
    all_metrics,
    wape,
)


log = logging.getLogger(
    "sellthru.ml"
)


MODELS_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
    /
    "saved_models"
)

os.makedirs(
    MODELS_DIR,
    exist_ok=True,
)


# ============================================================
# MODEL / FORECAST CACHE
# ============================================================

_MODEL_CACHE = {}

_PREDICTION_CACHE = {}

MODEL_CACHE_TTL = (
    15 * 60
)

PREDICTION_CACHE_TTL = (
    5 * 60
)


class AIPredictor:

    # ========================================================
    # CACHE
    # ========================================================

    def invalidate_cache(
        self,
        org_id: str | None = None,
    ) -> None:

        if org_id is None:

            _MODEL_CACHE.clear()
            _PREDICTION_CACHE.clear()

            return

        for key in list(
            _MODEL_CACHE
        ):

            if key[0] == org_id:

                _MODEL_CACHE.pop(
                    key,
                    None,
                )

        for key in list(
            _PREDICTION_CACHE
        ):

            if key[0] == org_id:

                _PREDICTION_CACHE.pop(
                    key,
                    None,
                )

    # ========================================================
    # REAL DATA CHECK
    # ========================================================

    async def _has_real_data(
        self,
        org_id: str,
    ) -> bool:

        rows = (
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

        return bool(rows)

    # ========================================================
    # MODEL PATHS
    # ========================================================

    def _model_path(
        self,
        org_id: str,
        version: str,
    ) -> Path:

        return (
            MODELS_DIR
            /
            (
                "rf_sales_model_"
                f"{org_id}_"
                f"{version}.pkl"
            )
        )

    def _meta_path(
        self,
        org_id: str,
        version: str,
    ) -> Path:

        return (
            MODELS_DIR
            /
            (
                "rf_meta_"
                f"{org_id}_"
                f"{version}.pkl"
            )
        )

    # ========================================================
    # CACHED MODEL LOADING
    # ========================================================

    async def _load_artifacts_cached(
        self,
        org_id: str,
        version: str,
    ):

        key = (
            org_id,
            version,
        )

        now = time.monotonic()

        cached = (
            _MODEL_CACHE.get(
                key
            )
        )

        if (
            cached
            and
            now - cached[0]
            <
            MODEL_CACHE_TTL
        ):

            return (
                cached[1],
                cached[2],
            )

        model_path = (
            self._model_path(
                org_id,
                version,
            )
        )

        meta_path = (
            self._meta_path(
                org_id,
                version,
            )
        )

        if (
            not model_path.exists()
            or
            not meta_path.exists()
        ):

            return (
                None,
                None,
            )

        try:

            with open(
                model_path,
                "rb",
            ) as file:

                artifacts = (
                    pickle.load(
                        file
                    )
                )

            with open(
                meta_path,
                "rb",
            ) as file:

                meta = (
                    pickle.load(
                        file
                    )
                )

        except Exception:

            log.exception(
                "Unable to load model"
            )

            return (
                None,
                None,
            )

        _MODEL_CACHE[
            key
        ] = (
            now,
            artifacts,
            meta,
        )

        return (
            artifacts,
            meta,
        )

    # ========================================================
    # DEMO SEED
    # ========================================================

    async def seed_synthetic_data(
        self,
        org_id: str,
    ) -> int:

        count = (
            await sales_repo.count(
                org_id
            )
        )

        if count > 0:

            return 0

        stores = [
            "Store-101",
            "Store-102",
            "Store-103",
        ]

        products = [

            {
                "id":
                    "PROD-A",

                "category":
                    "Electronics",

                "price":
                    299.99,

                "base_sales":
                    15,
            },

            {
                "id":
                    "PROD-B",

                "category":
                    "Apparel",

                "price":
                    49.99,

                "base_sales":
                    35,
            },

            {
                "id":
                    "PROD-C",

                "category":
                    "Home & Kitchen",

                "price":
                    89.99,

                "base_sales":
                    22,
            },

            {
                "id":
                    "PROD-D",

                "category":
                    "Fitness",

                "price":
                    120.00,

                "base_sales":
                    12,
            },
        ]

        now = datetime.now(
            timezone.utc
        )

        start_date = (
            now
            -
            timedelta(
                days=180
            )
        )

        docs = []

        for day_idx in range(
            180
        ):

            current_date = (
                start_date
                +
                timedelta(
                    days=day_idx
                )
            )

            day_of_week = (
                current_date.weekday()
            )

            month = (
                current_date.month
            )

            is_holiday = (
                (
                    month == 11
                    and
                    current_date.day
                    in [
                        25,
                        26,
                        27,
                    ]
                )
                or
                (
                    month == 12
                    and
                    current_date.day
                    in [
                        24,
                        25,
                        31,
                    ]
                )
            )

            for store in stores:

                for product in products:

                    is_promo = (
                        np.random.rand()
                        <
                        0.10
                    )

                    base = (
                        product[
                            "base_sales"
                        ]
                    )

                    store_mult = (
                        1.0
                        if store ==
                        "Store-101"
                        else
                        (
                            1.2
                            if store ==
                            "Store-102"
                            else
                            0.8
                        )
                    )

                    weekly_mult = (
                        1.5
                        if day_of_week
                        in [4, 5]
                        else
                        0.9
                    )

                    holiday_mult = (
                        2.0
                        if is_holiday
                        else
                        1.0
                    )

                    promo_mult = (
                        1.6
                        if is_promo
                        else
                        1.0
                    )

                    trend_mult = (
                        1.0
                        +
                        (
                            day_idx
                            /
                            360.0
                        )
                    )

                    noise = (
                        np.random.normal(
                            0,
                            base * 0.15,
                        )
                    )

                    qty = int(
                        max(
                            1,
                            (
                                base
                                *
                                store_mult
                                *
                                weekly_mult
                                *
                                holiday_mult
                                *
                                promo_mult
                                *
                                trend_mult
                            )
                            +
                            noise
                        )
                    )

                    revenue = round(
                        qty
                        *
                        product[
                            "price"
                        ],
                        2,
                    )

                    docs.append({

                        "date":
                            datetime(
                                current_date.year,
                                current_date.month,
                                current_date.day,
                                tzinfo=timezone.utc,
                            ),

                        "store_id":
                            store,

                        "product_id":
                            product["id"],

                        "category":
                            product["category"],

                        "quantity":
                            qty,

                        "revenue":
                            revenue,

                        "is_holiday":
                            is_holiday,

                        "is_promo":
                            is_promo,

                        "source":
                            "demo",
                    })

        chunk_size = 1000

        for start in range(
            0,
            len(docs),
            chunk_size,
        ):

            await sales_repo.insert_many(
                org_id,
                docs[
                    start:
                    start +
                    chunk_size
                ],
            )

        self.invalidate_cache(
            org_id
        )

        return len(docs)

    # ========================================================
    # TRAIN MODEL
    # ========================================================

    async def train_model(
        self,
        org_id: str,
    ) -> dict:

        real_mode = (
            await self._has_real_data(
                org_id
            )
        )

        far_past = datetime(
            1970,
            1,
            1,
            tzinfo=timezone.utc,
        )

        far_future = (
            datetime.now(
                timezone.utc
            )
            +
            timedelta(
                days=1
            )
        )

        # ----------------------------------------------------
        # REAL DATA ONLY
        # ----------------------------------------------------

        if real_mode:

            data = (
                await sales_repo.aggregate(
                    org_id,
                    [
                        {
                            "$match": {
                                "source":
                                    "real",

                                "date": {
                                    "$gte":
                                        far_past,

                                    "$lte":
                                        far_future,
                                },
                            }
                        }
                    ],
                    length=200000,
                )
            )

        else:

            data = (
                await sales_repo.find_in_range(
                    org_id,
                    far_past,
                    far_future,
                    limit=200000,
                )
            )

        if len(data) < 30:

            raise ValueError(
                "Insufficient sales data "
                "to train model."
            )

        df = pd.DataFrame(
            data
        )

        if "_id" in df.columns:

            df = df.drop(
                columns=[
                    "_id"
                ]
            )

        df["date"] = (
            pd.to_datetime(
                df["date"]
            )
        )

        df = df.sort_values(
            "date"
        )

        # ----------------------------------------------------
        # ENCODERS
        # ----------------------------------------------------

        if "store_id" not in df.columns or df["store_id"].isna().all():
            df["store_id"] = "ALL"
        else:
            df["store_id"] = df["store_id"].fillna("ALL").astype(str)

        df["product_id"] = df.get("product_id", pd.Series(dtype=str)).fillna("UNKNOWN").astype(str)
        df["category"] = df.get("category", pd.Series(dtype=str)).fillna("Uncategorized").astype(str)

        le_store = (
            LabelEncoder()
        )

        le_prod = (
            LabelEncoder()
        )

        le_cat = (
            LabelEncoder()
        )

        df[
            "store_code"
        ] = (
            le_store.fit_transform(
                df["store_id"]
            )
        )

        df[
            "prod_code"
        ] = (
            le_prod.fit_transform(
                df["product_id"]
            )
        )

        df[
            "cat_code"
        ] = (
            le_cat.fit_transform(
                df["category"]
            )
        )

        # ----------------------------------------------------
        # DATE FEATURES
        # ----------------------------------------------------

        df[
            "dayofweek"
        ] = (
            df["date"]
            .dt
            .dayofweek
        )

        df[
            "dayofmonth"
        ] = (
            df["date"]
            .dt
            .day
        )

        df[
            "month"
        ] = (
            df["date"]
            .dt
            .month
        )

        df[
            "year"
        ] = (
            df["date"]
            .dt
            .year
        )

        df[
            "is_weekend"
        ] = (
            df[
                "dayofweek"
            ]
            .isin(
                [
                    5,
                    6,
                ]
            )
            .astype(int)
        )

        flags = (
            df["date"].apply(
                lambda date:
                    holiday_flags(
                        date.date()
                    )
            )
        )

        df[
            "is_holiday_int"
        ] = (
            df[
                "is_holiday"
            ]
            .fillna(False)
            .astype(bool)
            |
            flags.apply(
                lambda item:
                    item[
                        "is_holiday"
                    ]
            )
        ).astype(int)

        df[
            "is_ramadan_int"
        ] = (
            flags.apply(
                lambda item:
                    item[
                        "is_ramadan"
                    ]
            )
            .astype(int)
        )

        df[
            "is_promo_int"
        ] = (
            df[
                "is_promo"
            ]
            .fillna(False)
            .astype(int)
        )

        # ----------------------------------------------------
        # LAGS
        # ----------------------------------------------------

        grouped = (
            df.groupby(
                [
                    "store_id",
                    "product_id",
                ]
            )
        )

        df[
            "qty_lag_1"
        ] = (
            grouped[
                "quantity"
            ]
            .shift(1)
        )

        df[
            "qty_lag_7"
        ] = (
            grouped[
                "quantity"
            ]
            .shift(7)
        )

        df[
            "qty_roll_mean_7"
        ] = (
            grouped[
                "quantity"
            ]
            .shift(1)
            .rolling(7)
            .mean()
            .reset_index(
                level=[
                    0,
                    1,
                ],
                drop=True,
            )
        )

        global_avg = (
            df[
                "quantity"
            ]
            .mean()
        )

        df[
            "qty_lag_1"
        ] = df[
            "qty_lag_1"
        ].fillna(
            global_avg
        )

        df[
            "qty_lag_7"
        ] = df[
            "qty_lag_7"
        ].fillna(
            global_avg
        )

        df[
            "qty_roll_mean_7"
        ] = df[
            "qty_roll_mean_7"
        ].fillna(
            global_avg
        )

        feature_cols = [

            "store_code",
            "prod_code",
            "cat_code",

            "dayofweek",
            "dayofmonth",
            "month",
            "year",

            "is_weekend",
            "is_holiday_int",
            "is_ramadan_int",
            "is_promo_int",

            "qty_lag_7",
            "qty_roll_mean_7",
        ]

        X = df[
            feature_cols
        ]

        y_qty = df[
            "quantity"
        ]

        y_rev = df[
            "revenue"
        ]

        # ----------------------------------------------------
        # HOLDOUT
        # ----------------------------------------------------

        split_idx = max(
            1,
            int(
                len(df)
                *
                0.85
            )
        )

        X_train = X.iloc[
            :split_idx
        ]

        X_val = X.iloc[
            split_idx:
        ]

        y_train = y_qty.iloc[
            :split_idx
        ]

        y_val = y_qty.iloc[
            split_idx:
        ]

        holdout_model = (
            RandomForestRegressor(
                n_estimators=60,
                max_depth=12,
                random_state=42,
                n_jobs=-1,
            )
        )

        holdout_model.fit(
            X_train,
            y_train,
        )

        holdout_predictions = (
            holdout_model.predict(
                X_val
            )
        )

        residuals = (
            y_val.values
            -
            holdout_predictions
        )

        residual_lower = float(
            np.percentile(
                residuals,
                5,
            )
        )

        residual_upper = float(
            np.percentile(
                residuals,
                95,
            )
        )

        # ----------------------------------------------------
        # FINAL QUANTITY MODEL
        # ----------------------------------------------------

        rf_qty = (
            RandomForestRegressor(
                n_estimators=80,
                max_depth=12,
                random_state=42,
                n_jobs=-1,
            )
        )

        rf_qty.fit(
            X,
            y_qty,
        )

        # ----------------------------------------------------
        # FINAL REVENUE MODEL
        # ----------------------------------------------------

        rf_rev = (
            RandomForestRegressor(
                n_estimators=80,
                max_depth=12,
                random_state=42,
                n_jobs=-1,
            )
        )

        rf_rev.fit(
            X,
            y_rev,
        )

        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        if len(y_val) > 0:

            mae = float(
                np.mean(
                    np.abs(
                        y_val
                        -
                        holdout_predictions
                    )
                )
            )

            rmse = float(
                np.sqrt(
                    np.mean(
                        (
                            y_val
                            -
                            holdout_predictions
                        )
                        ** 2
                    )
                )
            )

            mean_val = np.mean(
                y_val
            )

            ss_total = np.sum(
                (
                    y_val
                    -
                    mean_val
                )
                ** 2
            )

            ss_res = np.sum(
                (
                    y_val
                    -
                    holdout_predictions
                )
                ** 2
            )

            r2 = float(
                1.0
                -
                (
                    ss_res
                    /
                    (
                        ss_total
                        +
                        1e-8
                    )
                )
            )

            metrics = all_metrics(
                y_val.values,
                holdout_predictions,
                y_train.values,
            )

        else:

            mae = 0.0
            rmse = 0.0
            r2 = 0.0

            metrics = {
                "wape":
                    0.0
            }

        # ----------------------------------------------------
        # SAVE MODEL
        # ----------------------------------------------------

        version = (
            "v1."
            +
            str(
                int(
                    datetime.now(
                        timezone.utc
                    ).timestamp()
                )
            )
        )

        artifacts = {

            "model_qty":
                rf_qty,

            "model_rev":
                rf_rev,

            "le_store":
                le_store,

            "le_prod":
                le_prod,

            "le_cat":
                le_cat,
        }

        with open(
            self._model_path(
                org_id,
                version,
            ),
            "wb",
        ) as file:

            pickle.dump(
                artifacts,
                file,
            )

        meta = {

            "features":
                feature_cols,

            "train_date":
                datetime.now(
                    timezone.utc
                ),

            "metrics": {

                "mae":
                    mae,

                "rmse":
                    rmse,

                "r2":
                    r2,

                **metrics,
            },

            "residual_lower":
                residual_lower,

            "residual_upper":
                residual_upper,

            "data_source":
                "real"
                if real_mode
                else "demo",
        }

        with open(
            self._meta_path(
                org_id,
                version,
            ),
            "wb",
        ) as file:

            pickle.dump(
                meta,
                file,
            )

        # Real-data model should replace
        # old demo model.

        if real_mode:

            await models_repo.archive_all(
                org_id
            )

            status = (
                "active"
            )

        else:

            current_active = (
                await models_repo.find_active(
                    org_id
                )
            )

            status = (
                "active"
                if current_active is None
                else "candidate"
            )

            if status == "active":

                await models_repo.archive_all(
                    org_id
                )

        model_doc = {

            "trained_at":
                datetime.now(
                    timezone.utc
                ),

            "features":
                feature_cols,

            "metrics":
                meta[
                    "metrics"
                ],

            "training_rows":
                int(
                    len(df)
                ),

            "status":
                status,

            "version":
                version,

            "data_source":
                "real"
                if real_mode
                else "demo",
        }

        model_doc = (
            await models_repo.insert(
                org_id,
                model_doc,
            )
        )

        self.invalidate_cache(
            org_id
        )

        log.info(
            "Model trained: "
            "org=%s source=%s rows=%s",
            org_id,
            "real"
            if real_mode
            else "demo",
            len(df),
        )

        return model_doc

    # ========================================================
    # PREDICT
    # ========================================================

    async def predict(
        self,
        org_id: str,
        store_id: str | None = None,
        product_id: str | None = None,
        horizon_days: int = 30,
    ) -> list[dict]:

        horizon_days = max(
            1,
            min(
                int(horizon_days),
                90,
            )
        )

        real_mode = (
            await self._has_real_data(
                org_id
            )
        )

        active_model = (
            await models_repo.find_active(
                org_id
            )
        )

        # ====================================================
        # REAL DATA WITHOUT REAL MODEL
        # ====================================================

        if (
            real_mode
            and not product_id
        ):

            return (
                await self._generate_real_aggregate_forecast(
                    org_id,
                    horizon_days,
                )
            )

        # ====================================================
        # DATES
        # ====================================================

        latest_sale = await sales_repo.find_latest(org_id)
        if latest_sale and "date" in latest_sale:
            anchor = latest_sale["date"]
        else:
            anchor = datetime.now(timezone.utc)

        target_dates = [

            datetime(
                anchor.year,
                anchor.month,
                anchor.day,
                tzinfo=timezone.utc,
            )
            +
            timedelta(
                days=index
            )

            for index in range(
                1,
                horizon_days + 1,
            )
        ]

        # ====================================================
        # CACHE
        # ====================================================

        version = (
            active_model[
                "version"
            ]
            if active_model
            else
            "baseline"
        )

        cache_key = (
            org_id,
            version,
            store_id,
            product_id,
            horizon_days,
            real_mode,
        )

        cached = (
            _PREDICTION_CACHE.get(
                cache_key
            )
        )

        if (
            cached
            and
            time.monotonic()
            -
            cached[0]
            <
            PREDICTION_CACHE_TTL
        ):

            return copy.deepcopy(
                cached[1]
            )

        # ====================================================
        # NO MODEL
        # ====================================================

        if not active_model:

            predictions = (
                await self._generate_baseline_predictions(
                    org_id,
                    store_id,
                    product_id,
                    target_dates,
                )
            )

            _PREDICTION_CACHE[
                cache_key
            ] = (
                time.monotonic(),
                copy.deepcopy(
                    predictions
                ),
            )

            return predictions

        # ====================================================
        # LOAD MODEL
        # ====================================================

        artifacts, meta = (
            await self._load_artifacts_cached(
                org_id,
                active_model[
                    "version"
                ],
            )
        )

        if (
            artifacts is None
            or
            meta is None
        ):

            predictions = (
                await self._generate_baseline_predictions(
                    org_id,
                    store_id,
                    product_id,
                    target_dates,
                )
            )

            _PREDICTION_CACHE[
                cache_key
            ] = (
                time.monotonic(),
                copy.deepcopy(
                    predictions
                ),
            )

            return predictions

        rf_qty = artifacts[
            "model_qty"
        ]

        rf_rev = artifacts[
            "model_rev"
        ]

        le_store = artifacts[
            "le_store"
        ]

        le_prod = artifacts[
            "le_prod"
        ]

        le_cat = artifacts[
            "le_cat"
        ]

        target_stores = (
            [store_id]
            if store_id
            else (
                [le_store.classes_[0]]
                if (real_mode and len(le_store.classes_) > 0)
                else list(le_store.classes_)
            )
        )

        target_products = (
            [product_id]
            if product_id
            else
            list(
                le_prod.classes_
            )
        )

        recent_sales = (
            await sales_repo.find_recent(
                org_id,
                limit=500,
            )
        )

        recent_df = (
            pd.DataFrame(
                recent_sales
            )
            if recent_sales
            else
            pd.DataFrame()
        )

        product_categories = {}

        if not recent_df.empty:

            product_categories = (
                recent_df
                .drop_duplicates(
                    "product_id"
                )
                .set_index(
                    "product_id"
                )[
                    "category"
                ]
                .to_dict()
            )

        predictions = []

        for store in target_stores:

            if (
                store
                not in
                le_store.classes_
            ):

                continue

            store_code = (
                le_store.transform(
                    [store]
                )[0]
            )

            product_info = []

            for product in target_products:

                if (
                    product
                    not in
                    le_prod.classes_
                ):

                    continue

                product_code = (
                    le_prod.transform(
                        [product]
                    )[0]
                )

                category = (
                    product_categories.get(
                        product,
                        "General",
                    )
                )

                category_code = (

                    le_cat.transform(
                        [category]
                    )[0]

                    if
                    category
                    in
                    le_cat.classes_

                    else
                    0
                )

                product_info.append({

                    "product":
                        product,

                    "category":
                        category,

                    "product_code":
                        product_code,

                    "category_code":
                        category_code,
                })

            for day_index, target_date in enumerate(
                target_dates
            ):

                flags = (
                    holiday_flags(
                        target_date.date()
                    )
                )

                rows = []

                for item in product_info:

                    rows.append({

                        "store_code":
                            store_code,

                        "prod_code":
                            item[
                                "product_code"
                            ],

                        "cat_code":
                            item[
                                "category_code"
                            ],

                        "dayofweek":
                            target_date.weekday(),

                        "dayofmonth":
                            target_date.day,

                        "month":
                            target_date.month,

                        "year":
                            target_date.year,

                        "is_weekend":
                            int(
                                target_date.weekday()
                                in
                                [
                                    5,
                                    6,
                                ]
                            ),

                        "is_holiday_int":
                            int(
                                flags[
                                    "is_holiday"
                                ]
                            ),

                        "is_ramadan_int":
                            int(
                                flags[
                                    "is_ramadan"
                                ]
                            ),

                        "is_promo_int":
                            0,

                        "qty_lag_7":
                            1.0,

                        "qty_roll_mean_7":
                            1.0,
                    })

                if not rows:

                    continue

                X_pred = (
                    pd.DataFrame(
                        rows
                    )
                )

                quantity_predictions = (
                    np.maximum(
                        0,
                        rf_qty.predict(
                            X_pred
                        )
                    )
                )

                revenue_predictions = (
                    np.maximum(
                        0,
                        rf_rev.predict(
                            X_pred
                        )
                    )
                )

                residual_lower = meta.get(
                    "residual_lower",
                    -1.64
                    *
                    meta.get(
                        "metrics",
                        {}
                    ).get(
                        "rmse",
                        1,
                    ),
                )

                residual_upper = meta.get(
                    "residual_upper",
                    1.64
                    *
                    meta.get(
                        "metrics",
                        {}
                    ).get(
                        "rmse",
                        1,
                    ),
                )

                widen = np.sqrt(
                    1
                    +
                    day_index
                    /
                    max(
                        1,
                        horizon_days,
                    )
                )

                for index, item in enumerate(
                    product_info
                ):

                    quantity = float(
                        quantity_predictions[
                            index
                        ]
                    )

                    revenue = float(
                        revenue_predictions[
                            index
                        ]
                    )

                    predictions.append({

                        "date":
                            target_date,

                        "store_id":
                            store if not real_mode else None,

                        "product_id":
                            item[
                                "product"
                            ],

                        "category":
                            item[
                                "category"
                            ],

                        "quantity":
                            round(
                                quantity,
                                2,
                            ),

                        "revenue":
                            round(
                                revenue,
                                2,
                            ),

                        "confidence_lower":
                            round(
                                max(
                                    0,
                                    quantity
                                    +
                                    residual_lower
                                    *
                                    widen,
                                ),
                                2,
                            ),

                        "confidence_upper":
                            round(
                                quantity
                                +
                                residual_upper
                                *
                                widen,
                                2,
                            ),

                        "is_baseline":
                            False,
                    })

        _PREDICTION_CACHE[
            cache_key
        ] = (
            time.monotonic(),
            copy.deepcopy(
                predictions
            ),
        )

        return predictions

    # ========================================================
    # FAST REAL DATA FORECAST
    # ========================================================

    async def _generate_real_aggregate_forecast(
        self,
        org_id: str,
        horizon_days: int,
    ) -> list[dict]:

        cache_key = (
            org_id,
            "real-aggregate",
            horizon_days,
        )

        cached = (
            _PREDICTION_CACHE.get(
                cache_key
            )
        )

        if (
            cached
            and
            time.monotonic()
            -
            cached[0]
            <
            PREDICTION_CACHE_TTL
        ):

            return copy.deepcopy(
                cached[1]
            )

        pipeline = [

            {
                "$match": {
                    "source":
                        "real",
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

                    "quantity": {
                        "$sum":
                            "$quantity",
                    },
                }
            },

            {
                "$sort": {
                    "_id":
                        -1,
                }
            },

            {
                "$limit":
                    90,
            },
        ]

        rows = (
            await sales_repo.aggregate(
                org_id,
                pipeline,
                length=90,
            )
        )

        if not rows:

            return []

        # Anchor forecast directly to the dataset's latest historical date
        latest_str = rows[0]["_id"]
        latest_dt = datetime.strptime(
            latest_str,
            "%Y-%m-%d",
        ).replace(
            tzinfo=timezone.utc
        )

        target_dates = [
            datetime(
                latest_dt.year,
                latest_dt.month,
                latest_dt.day,
                tzinfo=timezone.utc,
            )
            +
            timedelta(
                days=index
            )
            for index in range(
                1,
                horizon_days + 1,
            )
        ]

        rows = list(
            reversed(rows)
        )

        daily_values = [
            float(
                row["revenue"]
            )

            for row
            in rows
        ]

        recent_values = (
            daily_values[-28:]
            if len(
                daily_values
            ) >= 28

            else
            daily_values
        )

        overall = float(
            np.mean(
                recent_values
            )
        )

        daily_qtys = [
            float(
                row.get("quantity", 0) or 0
            )
            for row
            in rows
        ]

        recent_qtys = (
            daily_qtys[-28:]
            if len(daily_qtys) >= 28
            else daily_qtys
        )

        overall_qty = float(
            np.mean(recent_qtys)
        ) if recent_qtys else 1.0

        weekday_values = {}

        for row in rows:

            date_value = (
                datetime.strptime(
                    row["_id"],
                    "%Y-%m-%d",
                ).date()
            )

            weekday_values.setdefault(
                date_value.weekday(),
                [],
            ).append(
                float(
                    row["revenue"]
                )
            )

        trend = 1.0

        if len(
            recent_values
        ) >= 14:

            first_week = float(
                np.mean(
                    recent_values[
                        :7
                    ]
                )
            )

            last_week = float(
                np.mean(
                    recent_values[
                        -7:
                    ]
                )
            )

            trend = float(
                np.clip(
                    last_week
                    /
                    (
                        first_week
                        +
                        1e-8
                    ),
                    0.85,
                    1.20,
                )
            )

        predictions = []

        for target_date in target_dates:

            weekday_average = float(
                np.mean(
                    weekday_values.get(
                        target_date.weekday(),
                        [
                            overall
                        ],
                    )
                )
            )

            forecast = (
                0.65
                *
                weekday_average
                +
                0.35
                *
                overall
            )

            forecast *= (
                0.85
                +
                0.15
                *
                trend
            )

            predictions.append({

                "date":
                    target_date,

                "store_id":
                    None,

                "product_id":
                    "ALL",

                "category":
                    "All categories",

                "quantity":
                    round(
                        max(
                            0,
                            overall_qty * (forecast / (overall + 1e-8)),
                        ),
                        2,
                    ),

                "revenue":
                    round(
                        max(
                            0,
                            forecast,
                        ),
                        2,
                    ),

                "confidence_lower":
                    round(
                        max(
                            0,
                            forecast
                            *
                            0.80,
                        ),
                        2,
                    ),

                "confidence_upper":
                    round(
                        forecast
                        *
                        1.20,
                        2,
                    ),

                "is_baseline":
                    True,
            })

        _PREDICTION_CACHE[
            cache_key
        ] = (
            time.monotonic(),
            copy.deepcopy(
                predictions
            ),
        )

        return predictions

    # ========================================================
    # BASELINE
    # ========================================================

    async def _generate_baseline_predictions(
        self,
        org_id: str,
        store_id: str | None,
        product_id: str | None,
        target_dates: list[datetime],
    ) -> list[dict]:

        real_mode = (
            await self._has_real_data(
                org_id
            )
        )

        if real_mode:

            pipeline = [

                {
                    "$match": {
                        "source":
                            "real",
                    }
                },

                {
                    "$group": {

                        "_id": {
                            "store_id":
                                "$store_id",

                            "product_id":
                                "$product_id",
                        },

                        "avg_qty": {
                            "$avg":
                                "$quantity",
                        },

                        "avg_rev": {
                            "$avg":
                                "$revenue",
                        },

                        "category": {
                            "$first":
                                "$category",
                        },
                    }
                },
            ]

            rows = (
                await sales_repo.aggregate(
                    org_id,
                    pipeline,
                    length=10000,
                )
            )

            predictions = []

            for row in rows:

                store = row[
                    "_id"
                ][
                    "store_id"
                ]

                product = row[
                    "_id"
                ][
                    "product_id"
                ]

                if (
                    store_id
                    and
                    store != store_id
                ):

                    continue

                if (
                    product_id
                    and
                    product != product_id
                ):

                    continue

                avg_qty = float(
                    row.get(
                        "avg_qty",
                        0,
                    )
                    or
                    0
                )

                avg_rev = float(
                    row.get(
                        "avg_rev",
                        0,
                    )
                    or
                    0
                )

                category = (
                    row.get(
                        "category"
                    )
                    or
                    "Uncategorized"
                )

                weekday_map = {
                    0: 0.88,  # Monday
                    1: 0.92,  # Tuesday
                    2: 0.96,  # Wednesday
                    3: 1.04,  # Thursday
                    4: 1.18,  # Friday
                    5: 1.28,  # Saturday peak
                    6: 1.02,  # Sunday
                }

                import math

                for index, target_date in enumerate(
                    target_dates
                ):
                    weekday_factor = weekday_map.get(
                        target_date.weekday(),
                        1.0,
                    )

                    wave_factor = 1.0 + 0.07 * math.sin(
                        index * 2 * math.pi / 14
                    )

                    trend_factor = (
                        1.0
                        +
                        min(
                            index,
                            30,
                        )
                        *
                        0.002
                    ) * wave_factor

                    predictions.append({

                        "date":
                            target_date,

                        "store_id":
                            store,

                        "product_id":
                            product,

                        "category":
                            category,

                        "quantity":
                            round(
                                avg_qty
                                *
                                weekday_factor
                                *
                                trend_factor,
                                2,
                            ),

                        "revenue":
                            round(
                                avg_rev
                                *
                                weekday_factor
                                *
                                trend_factor,
                                2,
                            ),

                        "confidence_lower":
                            round(
                                avg_rev
                                *
                                weekday_factor
                                *
                                trend_factor
                                *
                                0.80,
                                2,
                            ),

                        "confidence_upper":
                            round(
                                avg_rev
                                *
                                weekday_factor
                                *
                                trend_factor
                                *
                                1.20,
                                2,
                            ),

                        "is_baseline":
                            True,
                    })

            return predictions

        # ====================================================
        # ORIGINAL DEMO FALLBACK
        # ====================================================

        stores = (
            [store_id]
            if store_id
            else
            [
                "Store-101",
                "Store-102",
                "Store-103",
            ]
        )

        products = [

            {
                "id":
                    "PROD-A",

                "category":
                    "Electronics",

                "price":
                    299.99,

                "base_sales":
                    15,
            },

            {
                "id":
                    "PROD-B",

                "category":
                    "Apparel",

                "price":
                    49.99,

                "base_sales":
                    35,
            },

            {
                "id":
                    "PROD-C",

                "category":
                    "Home & Kitchen",

                "price":
                    89.99,

                "base_sales":
                    22,
            },

            {
                "id":
                    "PROD-D",

                "category":
                    "Fitness",

                "price":
                    120.00,

                "base_sales":
                    12,
            },
        ]

        if product_id:

            products = [
                product

                for product
                in products

                if product["id"]
                ==
                product_id
            ]

        predictions = []

        for store in stores:

            for product in products:

                for index, target_date in enumerate(
                    target_dates
                ):

                    weekly_factor = (
                        1.4
                        if
                        target_date.weekday()
                        in
                        [
                            4,
                            5,
                        ]
                        else
                        0.8
                    )

                    monthly_factor = (
                        1.2
                        if
                        target_date.month
                        in
                        [
                            11,
                            12,
                        ]
                        else
                        0.95
                    )

                    trend_factor = (
                        1.0
                        +
                        (
                            index
                            +
                            180
                        )
                        /
                        360.0
                    )

                    quantity = max(
                        1.0,
                        product[
                            "base_sales"
                        ]
                        *
                        weekly_factor
                        *
                        monthly_factor
                        *
                        trend_factor,
                    )

                    revenue = (
                        quantity
                        *
                        product[
                            "price"
                        ]
                    )

                    predictions.append({

                        "date":
                            target_date,

                        "store_id":
                            store,

                        "product_id":
                            product[
                                "id"
                            ],

                        "category":
                            product[
                                "category"
                            ],

                        "quantity":
                            round(
                                quantity,
                                2,
                            ),

                        "revenue":
                            round(
                                revenue,
                                2,
                            ),

                        "confidence_lower":
                            round(
                                quantity
                                *
                                0.75,
                                2,
                            ),

                        "confidence_upper":
                            round(
                                quantity
                                *
                                1.25,
                                2,
                            ),

                        "is_baseline":
                            True,
                    })

        return predictions


# ============================================================
# SINGLE INSTANCE
# ============================================================

ai_predictor = AIPredictor()