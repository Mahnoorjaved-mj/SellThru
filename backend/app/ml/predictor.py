"""Machine Learning Sales Predictor.

Uses Scikit-Learn RandomForestRegressor to perform daily sales forecasting.
Features engineered: day of week, day of month, month, year, weekend flag,
holiday flag, promo flag, lag features (7-day lag), and rolling average features.
Includes a robust fallback to a statistical seasonal model and a database seeder.

Model artifacts and generated forecasts are cached in memory so the dashboard
does not repeatedly load pickle files or recalculate the same forecast.
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
    timezone
)

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

from app.repositories import (
    models_repo,
    sales_repo
)

from app.ml.holidays import (
    holiday_flags
)

from app.ml.metrics import (
    all_metrics,
    wape
)


log = logging.getLogger(
    "forecastiq.ml"
)


MODELS_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
    / "saved_models"
)

os.makedirs(
    MODELS_DIR,
    exist_ok=True
)


# ============================================================
# ML CACHE
# ============================================================

_MODEL_CACHE: dict[
    tuple[str, str],
    tuple[float, dict, dict]
] = {}

_PREDICTION_CACHE: dict[
    tuple,
    tuple[float, list[dict]]
] = {}

_ACTIVE_MODEL_CACHE: dict[
    str,
    tuple[float, dict | None]
] = {}


MODEL_CACHE_TTL_SECONDS = (
    15 * 60
)

PREDICTION_CACHE_TTL_SECONDS = (
    5 * 60
)

ACTIVE_MODEL_CACHE_TTL_SECONDS = (
    60
)


class AIPredictor:

    """Random Forest sales forecasting service.

    Model artifacts are stored per organization/version.
    Cached artifacts remain in memory until their TTL expires
    or the organization's model/data cache is invalidated.
    """

    # ========================================================
    # CACHE CONTROL
    # ========================================================

    def invalidate_cache(
        self,
        org_id: str | None = None
    ) -> None:
        """Invalidate model and forecast cache."""

        if org_id is None:

            _MODEL_CACHE.clear()
            _PREDICTION_CACHE.clear()
            _ACTIVE_MODEL_CACHE.clear()

            return

        for key in list(
            _MODEL_CACHE
        ):

            if key[0] == org_id:
                _MODEL_CACHE.pop(
                    key,
                    None
                )

        for key in list(
            _PREDICTION_CACHE
        ):

            if key[0] == org_id:
                _PREDICTION_CACHE.pop(
                    key,
                    None
                )

        _ACTIVE_MODEL_CACHE.pop(
            org_id,
            None
        )

    # ========================================================
    # ACTIVE MODEL CACHE
    # ========================================================

    async def _get_active_model_cached(
        self,
        org_id: str
    ):
        """Cache active model registry lookup."""

        now = time.monotonic()

        cached = (
            _ACTIVE_MODEL_CACHE.get(
                org_id
            )
        )

        if (
            cached
            and
            now - cached[0]
            <
            ACTIVE_MODEL_CACHE_TTL_SECONDS
        ):
            return cached[1]

        active_model = (
            await models_repo.find_active(
                org_id
            )
        )

        _ACTIVE_MODEL_CACHE[
            org_id
        ] = (
            now,
            active_model
        )

        return active_model

    # ========================================================
    # MODEL ARTIFACT CACHE
    # ========================================================

    async def _load_model_artifacts_cached(
        self,
        org_id: str,
        version: str
    ):
        """Load pickle model artifacts once and reuse them."""

        key = (
            org_id,
            version
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
            MODEL_CACHE_TTL_SECONDS
        ):
            return (
                cached[1],
                cached[2]
            )

        model_path = (
            self._model_path(
                org_id,
                version
            )
        )

        meta_path = (
            self._meta_path(
                org_id,
                version
            )
        )

        if (
            not os.path.exists(
                model_path
            )
            or
            not os.path.exists(
                meta_path
            )
        ):
            return None, None

        with open(
            model_path,
            "rb"
        ) as file:

            artifacts = pickle.load(
                file
            )

        with open(
            meta_path,
            "rb"
        ) as file:

            meta = pickle.load(
                file
            )

        _MODEL_CACHE[
            key
        ] = (
            now,
            artifacts,
            meta
        )

        return (
            artifacts,
            meta
        )

    # ========================================================
    # MODEL PATHS
    # ========================================================

    def _model_path(
        self,
        org_id: str,
        version: str
    ) -> Path:

        return (
            MODELS_DIR
            /
            f"rf_sales_model_{org_id}_{version}.pkl"
        )

    def _meta_path(
        self,
        org_id: str,
        version: str
    ) -> Path:

        return (
            MODELS_DIR
            /
            f"rf_meta_{org_id}_{version}.pkl"
        )

    # ========================================================
    # DEMO DATA
    # ========================================================

    async def seed_synthetic_data(
        self,
        org_id: str
    ) -> int:
        """Seed six months of synthetic daily sales."""

        count = await sales_repo.count(
            org_id
        )

        if count > 0:
            return 0

        log.info(
            "Seeding synthetic sales "
            "data for org=%s...",
            org_id
        )

        stores = [
            "Store-101",
            "Store-102",
            "Store-103"
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
                    15
            },
            {
                "id":
                    "PROD-B",
                "category":
                    "Apparel",
                "price":
                    49.99,
                "base_sales":
                    35
            },
            {
                "id":
                    "PROD-C",
                "category":
                    "Home & Kitchen",
                "price":
                    89.99,
                "base_sales":
                    22
            },
            {
                "id":
                    "PROD-D",
                "category":
                    "Fitness",
                "price":
                    120.00,
                "base_sales":
                    12
            }
        ]

        now = datetime.now(
            timezone.utc
        )

        start_date = (
            now -
            timedelta(days=180)
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

            is_holiday = False

            if (
                (
                    month == 11
                    and
                    current_date.day
                    in [25, 26, 27]
                )
                or
                (
                    month == 12
                    and
                    current_date.day
                    in [24, 25, 31]
                )
            ):
                is_holiday = True

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
                            base * 0.15
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

                    rev = round(
                        qty *
                        product["price"],
                        2
                    )

                    docs.append({
                        "date":
                            datetime(
                                current_date.year,
                                current_date.month,
                                current_date.day,
                                tzinfo=timezone.utc
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
                            rev,

                        "is_holiday":
                            is_holiday,

                        "is_promo":
                            is_promo
                    })

        chunk_size = 1000

        for i in range(
            0,
            len(docs),
            chunk_size
        ):

            await sales_repo.insert_many(
                org_id,
                docs[
                    i:
                    i + chunk_size
                ]
            )

        log.info(
            "Seeded %d sales records "
            "successfully for org=%s",
            len(docs),
            org_id
        )

        self.invalidate_cache(
            org_id
        )

        try:

            from app.services.sales_service import (
                invalidate_dashboard_cache
            )

            invalidate_dashboard_cache(
                org_id
            )

        except Exception:
            pass

        return len(docs)

    # ========================================================
    # TRAIN MODEL
    # ========================================================

    async def train_model(
        self,
        org_id: str
    ) -> dict:
        """Train Random Forest models using all available sales."""

        far_past = datetime(
            1970,
            1,
            1,
            tzinfo=timezone.utc
        )

        far_future = (
            datetime.now(
                timezone.utc
            )
            +
            timedelta(days=1)
        )

        data = (
            await sales_repo.find_in_range(
                org_id,
                far_past,
                far_future,
                limit=100000
            )
        )

        if len(data) < 30:
            raise ValueError(
                "Insufficient sales data "
                "to train model. "
                f"Need at least 30 records, "
                f"found {len(data)}"
            )

        df = pd.DataFrame(
            data
        )

        df["date"] = pd.to_datetime(
            df["date"]
        )

        df = df.sort_values(
            "date"
        )

        le_store = LabelEncoder()
        le_prod = LabelEncoder()
        le_cat = LabelEncoder()

        df["store_code"] = (
            le_store.fit_transform(
                df["store_id"]
            )
        )

        df["prod_code"] = (
            le_prod.fit_transform(
                df["product_id"]
            )
        )

        df["cat_code"] = (
            le_cat.fit_transform(
                df["category"]
            )
        )

        df["dayofweek"] = (
            df["date"].dt.dayofweek
        )

        df["dayofmonth"] = (
            df["date"].dt.day
        )

        df["month"] = (
            df["date"].dt.month
        )

        df["year"] = (
            df["date"].dt.year
        )

        df["is_weekend"] = (
            df["dayofweek"]
            .isin([5, 6])
            .astype(int)
        )

        pk_flags = (
            df["date"].apply(
                lambda d:
                    holiday_flags(
                        d.date()
                    )
            )
        )

        df[
            "is_holiday_int"
        ] = (
            df["is_holiday"].astype(
                bool
            )
            |
            pk_flags.apply(
                lambda f:
                    f["is_holiday"]
            )
        ).astype(int)

        df[
            "is_ramadan_int"
        ] = (
            pk_flags.apply(
                lambda f:
                    f["is_ramadan"]
            )
            .astype(int)
        )

        df[
            "is_promo_int"
        ] = (
            df["is_promo"]
            .astype(int)
        )

        df[
            "qty_lag_1"
        ] = (
            df.groupby(
                [
                    "store_id",
                    "product_id"
                ]
            )["quantity"]
            .shift(1)
        )

        df[
            "qty_lag_7"
        ] = (
            df.groupby(
                [
                    "store_id",
                    "product_id"
                ]
            )["quantity"]
            .shift(7)
        )

        df[
            "qty_roll_mean_7"
        ] = (
            df.groupby(
                [
                    "store_id",
                    "product_id"
                ]
            )["quantity"]
            .shift(1)
            .rolling(7)
            .mean()
        )

        global_avg = (
            df["quantity"].mean()
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
            "qty_roll_mean_7"
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

        backtest = (
            self._rolling_origin_backtest(
                df,
                feature_cols
            )
        )

        split_idx = int(
            len(df) * 0.85
        )

        X_train = X.iloc[
            :split_idx
        ]

        X_val = X.iloc[
            split_idx:
        ]

        y_qty_train = (
            y_qty.iloc[
                :split_idx
            ]
        )

        y_qty_val = (
            y_qty.iloc[
                split_idx:
            ]
        )

        y_rev_train = (
            y_rev.iloc[
                :split_idx
            ]
        )

        y_rev_val = (
            y_rev.iloc[
                split_idx:
            ]
        )

        holdout_rf = (
            RandomForestRegressor(
                n_estimators=100,
                max_depth=12,
                random_state=42
            )
        )

        holdout_rf.fit(
            X_train,
            y_qty_train
        )

        holdout_preds = (
            holdout_rf.predict(
                X_val
            )
        )

        residuals = (
            y_qty_val.values
            -
            holdout_preds
        )

        residual_lower = float(
            np.percentile(
                residuals,
                5
            )
        )

        residual_upper = float(
            np.percentile(
                residuals,
                95
            )
        )

        # Final production quantity model
        rf_qty = (
            RandomForestRegressor(
                n_estimators=100,
                max_depth=12,
                random_state=42
            )
        )

        rf_qty.fit(
            X,
            y_qty
        )

        # Final production revenue model
        rf_rev = (
            RandomForestRegressor(
                n_estimators=100,
                max_depth=12,
                random_state=42
            )
        )

        rf_rev.fit(
            X,
            y_rev
        )

        qty_mae = float(
            np.mean(
                np.abs(
                    y_qty_val
                    -
                    holdout_preds
                )
            )
        )

        qty_rmse = float(
            np.sqrt(
                np.mean(
                    (
                        y_qty_val
                        -
                        holdout_preds
                    ) ** 2
                )
            )
        )

        y_val_mean = (
            np.mean(
                y_qty_val
            )
        )

        ss_tot = np.sum(
            (
                y_qty_val
                -
                y_val_mean
            ) ** 2
        )

        ss_res = np.sum(
            (
                y_qty_val
                -
                holdout_preds
            ) ** 2
        )

        r2 = float(
            1.0
            -
            (
                ss_res
                /
                (
                    ss_tot
                    +
                    1e-8
                )
            )
        )

        accuracy_metrics = (
            all_metrics(
                y_qty_val.values,
                holdout_preds,
                y_qty_train.values
            )
        )

        model_artifacts = {
            "model_qty":
                rf_qty,

            "model_rev":
                rf_rev,

            "le_store":
                le_store,

            "le_prod":
                le_prod,

            "le_cat":
                le_cat
        }

        version = (
            f"v1."
            f"{int(datetime.now(timezone.utc).timestamp())}"
        )

        with open(
            self._model_path(
                org_id,
                version
            ),
            "wb"
        ) as file:

            pickle.dump(
                model_artifacts,
                file
            )

        avg_prices = (
            df.groupby(
                "product_id"
            )["revenue"].sum()
            /
            (
                df.groupby(
                    "product_id"
                )["quantity"].sum()
                +
                1e-8
            )
        )

        avg_prices = (
            avg_prices.to_dict()
        )

        meta_artifacts = {

            "features":
                feature_cols,

            "avg_prices":
                avg_prices,

            "train_date":
                datetime.now(
                    timezone.utc
                ),

            "metrics": {
                "mae":
                    qty_mae,

                "rmse":
                    qty_rmse,

                "r2":
                    r2,

                **accuracy_metrics
            },

            "residual_lower":
                residual_lower,

            "residual_upper":
                residual_upper
        }

        with open(
            self._meta_path(
                org_id,
                version
            ),
            "wb"
        ) as file:

            pickle.dump(
                meta_artifacts,
                file
            )

        beats_baseline = (
            backtest["rf_wape"]
            <
            backtest[
                "best_baseline_wape"
            ]
        )

        # ====================================================
        # ACTIVE MODEL GUARDRAIL
        # ====================================================

        current_active = (
            await models_repo.find_active(
                org_id
            )
        )

        if current_active is not None:

            active_version = (
                current_active.get(
                    "version"
                )
            )

            active_artifact_exists = (
                active_version
                and
                os.path.exists(
                    self._model_path(
                        org_id,
                        active_version
                    )
                )
            )

            if not active_artifact_exists:
                current_active = None

        promote_margin = 0.02

        if current_active is None:

            status = "active"

        else:

            current_wape = (
                current_active
                .get(
                    "metrics",
                    {}
                )
                .get(
                    "wape"
                )
            )

            if (
                current_wape
                is not None
                and
                accuracy_metrics[
                    "wape"
                ]
                <
                current_wape
                *
                (
                    1 -
                    promote_margin
                )
            ):

                status = "active"

                await models_repo.archive_all(
                    org_id
                )

            else:

                status = "candidate"

        model_doc = {

            "trained_at":
                datetime.now(
                    timezone.utc
                ),

            "features":
                feature_cols,

            "metrics":
                meta_artifacts[
                    "metrics"
                ],

            "backtest":
                backtest,

            "beats_seasonal_naive_baseline":
                beats_baseline,

            "training_rows":
                int(
                    len(df)
                ),

            "status":
                status,

            "version":
                version
        }

        model_doc = (
            await models_repo.insert(
                org_id,
                model_doc
            )
        )

        log.info(
            "Model trained for org=%s! "
            "status=%s R2=%.4f "
            "WAPE=%.2f%% "
            "beats_baseline=%s",
            org_id,
            status,
            r2,
            accuracy_metrics[
                "wape"
            ],
            beats_baseline
        )

        # Model changed -> remove old
        # cached model and forecasts.

        self.invalidate_cache(
            org_id
        )

        try:

            from app.services.sales_service import (
                invalidate_dashboard_cache
            )

            invalidate_dashboard_cache(
                org_id
            )

        except Exception:
            pass

        return model_doc

    # ========================================================
    # BACKTEST
    # ========================================================

    def _rolling_origin_backtest(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        n_folds: int = 3
    ) -> dict:
        """Walk-forward validation."""

        n = len(df)

        chunk = (
            n //
            (
                n_folds + 1
            )
        )

        if chunk < 5:

            n_folds = 1

            chunk = max(
                1,
                n // 2
            )

        fold_results = {
            "rf": [],
            "naive": [],
            "seasonal_naive": [],
            "moving_avg": []
        }

        for fold in range(
            1,
            n_folds + 1
        ):

            train_end = (
                chunk * fold
            )

            val_end = min(
                n,
                chunk *
                (
                    fold + 1
                )
            )

            if val_end <= train_end:
                continue

            train_df = df.iloc[
                :train_end
            ]

            val_df = df.iloc[
                train_end:
                val_end
            ]

            if (
                len(train_df) < 10
                or
                len(val_df) < 1
            ):
                continue

            X_train = (
                train_df[
                    feature_cols
                ]
            )

            y_train = (
                train_df[
                    "quantity"
                ]
            )

            X_val = (
                val_df[
                    feature_cols
                ]
            )

            y_val = (
                val_df[
                    "quantity"
                ]
            )

            rf = (
                RandomForestRegressor(
                    n_estimators=60,
                    max_depth=10,
                    random_state=42
                )
            )

            rf.fit(
                X_train,
                y_train
            )

            rf_preds = (
                rf.predict(
                    X_val
                )
            )

            fold_results[
                "rf"
            ].append(
                wape(
                    y_val.values,
                    rf_preds
                )
            )

            fold_results[
                "naive"
            ].append(
                wape(
                    y_val.values,
                    val_df[
                        "qty_lag_1"
                    ].values
                )
            )

            fold_results[
                "seasonal_naive"
            ].append(
                wape(
                    y_val.values,
                    val_df[
                        "qty_lag_7"
                    ].values
                )
            )

            fold_results[
                "moving_avg"
            ].append(
                wape(
                    y_val.values,
                    val_df[
                        "qty_roll_mean_7"
                    ].values
                )
            )

        avg = {
            key:
                round(
                    float(
                        np.mean(value)
                    ),
                    2
                )
                if value
                else None

            for key, value
            in fold_results.items()
        }

        baseline_scores = {
            key: value

            for key, value
            in avg.items()

            if (
                key != "rf"
                and
                value is not None
            )
        }

        best_baseline = (
            min(
                baseline_scores,
                key=baseline_scores.get
            )
            if baseline_scores
            else None
        )

        return {

            "folds":
                n_folds,

            "rf_wape":
                avg["rf"],

            "naive_wape":
                avg[
                    "naive"
                ],

            "seasonal_naive_wape":
                avg[
                    "seasonal_naive"
                ],

            "moving_avg_wape":
                avg[
                    "moving_avg"
                ],

            "best_baseline":
                best_baseline,

            "best_baseline_wape":
                (
                    baseline_scores.get(
                        best_baseline
                    )
                    if best_baseline
                    else
                    float("inf")
                )
        }

    # ========================================================
    # PREDICT
    # ========================================================

    async def predict(
        self,
        org_id: str,
        store_id: str | None = None,
        product_id: str | None = None,
        horizon_days: int = 30
    ) -> list[dict]:
        """Generate next-N-day forecasts using cached model artifacts."""

        horizon_days = max(
            1,
            min(
                int(horizon_days),
                365
            )
        )

        now = datetime.now(
            timezone.utc
        )

        target_dates = [

            datetime(
                now.year,
                now.month,
                now.day,
                tzinfo=timezone.utc
            )
            +
            timedelta(
                days=i
            )

            for i in range(
                1,
                horizon_days + 1
            )
        ]

        # ====================================================
        # ACTIVE MODEL
        # ====================================================

        active_model = (
            await self._get_active_model_cached(
                org_id
            )
        )

        version = (
            active_model.get(
                "version"
            )
            if active_model
            else
            "baseline"
        )

        # ====================================================
        # FORECAST CACHE KEY
        # ====================================================

        cache_key = (
            org_id,
            version,
            store_id,
            product_id,
            horizon_days,
            target_dates[
                0
            ].date().isoformat()
        )

        cached_prediction = (
            _PREDICTION_CACHE.get(
                cache_key
            )
        )

        if (
            cached_prediction
            and
            time.monotonic()
            -
            cached_prediction[0]
            <
            PREDICTION_CACHE_TTL_SECONDS
        ):

            return copy.deepcopy(
                cached_prediction[1]
            )

        # ====================================================
        # NO MODEL -> BASELINE
        # ====================================================

        if not active_model:

            log.warning(
                "No active ML model "
                "for org=%s. "
                "Falling back to "
                "statistical baseline.",
                org_id
            )

            predictions = (
                await self._generate_baseline_predictions(
                    org_id,
                    store_id,
                    product_id,
                    target_dates
                )
            )

            _PREDICTION_CACHE[
                cache_key
            ] = (
                time.monotonic(),
                copy.deepcopy(
                    predictions
                )
            )

            return predictions

        version = (
            active_model[
                "version"
            ]
        )

        # ====================================================
        # LOAD CACHED MODEL
        # ====================================================

        try:

            artifacts, meta = (
                await self._load_model_artifacts_cached(
                    org_id,
                    version
                )
            )

        except Exception as exc:

            log.error(
                "Failed to load ML "
                "model files for "
                "org=%s version=%s: %s. "
                "Using baseline.",
                org_id,
                version,
                exc
            )

            artifacts = None
            meta = None

        if (
            artifacts is None
            or
            meta is None
        ):

            log.warning(
                "Active model artifact "
                "missing on disk for "
                "org=%s version=%s. "
                "Falling back to baseline.",
                org_id,
                version
            )

            predictions = (
                await self._generate_baseline_predictions(
                    org_id,
                    store_id,
                    product_id,
                    target_dates
                )
            )

            _PREDICTION_CACHE[
                cache_key
            ] = (
                time.monotonic(),
                copy.deepcopy(
                    predictions
                )
            )

            return predictions

        # ====================================================
        # MODEL OBJECTS
        # ====================================================

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
            else
            list(
                le_store.classes_
            )
        )

        target_prods = (
            [product_id]
            if product_id
            else
            list(
                le_prod.classes_
            )
        )

        # ====================================================
        # RECENT SALES
        # ====================================================

        recent_sales = (
            await sales_repo.find_recent(
                org_id,
                limit=200
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

        predictions = []

        # ====================================================
        # FORECAST EACH STORE / PRODUCT
        # ====================================================

        for store in target_stores:

            for prod in target_prods:

                if (
                    store
                    not in
                    le_store.classes_
                    or
                    prod
                    not in
                    le_prod.classes_
                ):
                    continue

                store_code = (
                    le_store.transform(
                        [store]
                    )[0]
                )

                prod_code = (
                    le_prod.transform(
                        [prod]
                    )[0]
                )

                prod_cat = "General"

                if recent_sales:

                    matches = (
                        recent_df[
                            recent_df[
                                "product_id"
                            ]
                            ==
                            prod
                        ]
                    )

                    if not matches.empty:

                        prod_cat = (
                            matches.iloc[
                                0
                            ][
                                "category"
                            ]
                        )

                cat_code = (
                    le_cat.transform(
                        [prod_cat]
                    )[0]
                    if
                    prod_cat
                    in
                    le_cat.classes_
                    else
                    0
                )

                hist_series = []

                if not recent_df.empty:

                    match_series = (
                        recent_df[
                            (
                                recent_df[
                                    "store_id"
                                ]
                                ==
                                store
                            )
                            &
                            (
                                recent_df[
                                    "product_id"
                                ]
                                ==
                                prod
                            )
                        ]
                    )

                    if not match_series.empty:

                        hist_series = list(
                            match_series
                            .sort_values(
                                "date"
                            )[
                                "quantity"
                            ]
                            .tail(7)
                        )

                while len(
                    hist_series
                ) < 7:

                    hist_series.append(
                        15.0
                    )

                current_history = (
                    hist_series.copy()
                )

                residual_lower = meta.get(
                    "residual_lower",
                    -1.64 *
                    meta[
                        "metrics"
                    ][
                        "rmse"
                    ]
                )

                residual_upper = meta.get(
                    "residual_upper",
                    1.64 *
                    meta[
                        "metrics"
                    ][
                        "rmse"
                    ]
                )

                for (
                    d_idx,
                    target_date
                ) in enumerate(
                    target_dates
                ):

                    day_of_week = (
                        target_date.weekday()
                    )

                    day_of_month = (
                        target_date.day
                    )

                    month = (
                        target_date.month
                    )

                    year = (
                        target_date.year
                    )

                    is_weekend = int(
                        day_of_week
                        in [5, 6]
                    )

                    flags = holiday_flags(
                        target_date.date()
                    )

                    is_holiday = int(
                        flags[
                            "is_holiday"
                        ]
                    )

                    is_ramadan = int(
                        flags[
                            "is_ramadan"
                        ]
                    )

                    is_promo = 0

                    qty_lag_7 = (
                        current_history[
                            -7
                        ]
                    )

                    qty_roll_mean_7 = (
                        np.mean(
                            current_history[
                                -7:
                            ]
                        )
                    )

                    feat_dict = {

                        "store_code":
                            store_code,

                        "prod_code":
                            prod_code,

                        "cat_code":
                            cat_code,

                        "dayofweek":
                            day_of_week,

                        "dayofmonth":
                            day_of_month,

                        "month":
                            month,

                        "year":
                            year,

                        "is_weekend":
                            is_weekend,

                        "is_holiday_int":
                            is_holiday,

                        "is_ramadan_int":
                            is_ramadan,

                        "is_promo_int":
                            is_promo,

                        "qty_lag_7":
                            qty_lag_7,

                        "qty_roll_mean_7":
                            qty_roll_mean_7
                    }

                    X_pred = pd.DataFrame([
                        feat_dict
                    ])

                    pred_qty = float(
                        rf_qty.predict(
                            X_pred
                        )[0]
                    )

                    pred_qty = max(
                        0.0,
                        pred_qty
                    )

                    pred_rev = float(
                        rf_rev.predict(
                            X_pred
                        )[0]
                    )

                    pred_rev = max(
                        0.0,
                        pred_rev
                    )

                    current_history.append(
                        pred_qty
                    )

                    widen = np.sqrt(
                        1
                        +
                        (
                            d_idx
                            /
                            max(
                                1,
                                horizon_days
                            )
                        )
                    )

                    confidence_lower = max(
                        0.0,
                        pred_qty
                        +
                        residual_lower
                        *
                        widen
                    )

                    confidence_upper = (
                        pred_qty
                        +
                        residual_upper
                        *
                        widen
                    )

                    predictions.append({

                        "date":
                            target_date,

                        "store_id":
                            store,

                        "product_id":
                            prod,

                        "category":
                            prod_cat,

                        "quantity":
                            round(
                                pred_qty,
                                2
                            ),

                        "revenue":
                            round(
                                pred_rev,
                                2
                            ),

                        "confidence_lower":
                            round(
                                confidence_lower,
                                2
                            ),

                        "confidence_upper":
                            round(
                                confidence_upper,
                                2
                            ),

                        "is_baseline":
                            False
                    })

        # ====================================================
        # SAVE FORECAST CACHE
        # ====================================================

        _PREDICTION_CACHE[
            cache_key
        ] = (
            time.monotonic(),
            copy.deepcopy(
                predictions
            )
        )

        return predictions

    # ========================================================
    # BASELINE FORECAST
    # ========================================================

    async def _generate_baseline_predictions(
        self,
        org_id: str,
        store_id: str | None,
        product_id: str | None,
        target_dates: list[datetime]
    ) -> list[dict]:
        """Statistical baseline used when no active RF model exists."""

        stores = (
            [store_id]
            if store_id
            else
            [
                "Store-101",
                "Store-102",
                "Store-103"
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
                    15
            },

            {
                "id":
                    "PROD-B",

                "category":
                    "Apparel",

                "price":
                    49.99,

                "base_sales":
                    35
            },

            {
                "id":
                    "PROD-C",

                "category":
                    "Home & Kitchen",

                "price":
                    89.99,

                "base_sales":
                    22
            },

            {
                "id":
                    "PROD-D",

                "category":
                    "Fitness",

                "price":
                    120.00,

                "base_sales":
                    12
            }
        ]

        if product_id:

            products = [
                product
                for product in products
                if product["id"]
                ==
                product_id
            ]

        db_averages = {}

        count = await sales_repo.count(
            org_id
        )

        if count > 0:

            pipeline = [

                {
                    "$group": {

                        "_id": {
                            "store_id":
                                "$store_id",

                            "product_id":
                                "$product_id"
                        },

                        "avg_qty": {
                            "$avg":
                                "$quantity"
                        },

                        "avg_rev": {
                            "$avg":
                                "$revenue"
                        },

                        "category": {
                            "$first":
                                "$category"
                        }
                    }
                }
            ]

            aggregate_results = (
                await sales_repo.aggregate(
                    org_id,
                    pipeline,
                    length=10000
                )
            )

            for result in (
                aggregate_results
            ):

                key = (
                    result["_id"][
                        "store_id"
                    ],
                    result["_id"][
                        "product_id"
                    ]
                )

                db_averages[
                    key
                ] = {

                    "avg_qty":
                        result[
                            "avg_qty"
                        ],

                    "avg_rev":
                        result[
                            "avg_rev"
                        ],

                    "category":
                        result.get(
                            "category",
                            "General"
                        )
                }

        predictions = []

        for store in stores:

            for product_item in products:

                product = (
                    product_item["id"]
                )

                category = (
                    product_item[
                        "category"
                    ]
                )

                price = (
                    product_item[
                        "price"
                    ]
                )

                base = (
                    product_item[
                        "base_sales"
                    ]
                )

                db_match = (
                    db_averages.get(
                        (
                            store,
                            product
                        )
                    )
                )

                if db_match:

                    base = (
                        db_match[
                            "avg_qty"
                        ]
                    )

                    category = (
                        db_match[
                            "category"
                        ]
                    )

                    price = (
                        db_match[
                            "avg_rev"
                        ]
                        /
                        (
                            base
                            +
                            1e-8
                        )
                    )

                for idx, target_date in (
                    enumerate(
                        target_dates
                    )
                ):

                    day_of_week = (
                        target_date.weekday()
                    )

                    month = (
                        target_date.month
                    )

                    weekly_mult = (
                        1.4
                        if day_of_week
                        in [4, 5]
                        else
                        0.8
                    )

                    monthly_mult = (
                        1.2
                        if month
                        in [11, 12]
                        else
                        0.95
                    )

                    trend_mult = (
                        1.0
                        +
                        (
                            (
                                idx
                                +
                                180
                            )
                            /
                            360.0
                        )
                    )

                    pred_qty = (
                        base
                        *
                        weekly_mult
                        *
                        monthly_mult
                        *
                        trend_mult
                    )

                    pred_qty = max(
                        1.0,
                        pred_qty
                        +
                        np.sin(
                            idx * 0.5
                        )
                        *
                        2.0
                    )

                    pred_rev = (
                        pred_qty
                        *
                        price
                    )

                    confidence_lower = max(
                        0.0,
                        pred_qty
                        *
                        0.75
                    )

                    confidence_upper = (
                        pred_qty
                        *
                        1.25
                    )

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
                                pred_qty,
                                2
                            ),

                        "revenue":
                            round(
                                pred_rev,
                                2
                            ),

                        "confidence_lower":
                            round(
                                confidence_lower,
                                2
                            ),

                        "confidence_upper":
                            round(
                                confidence_upper,
                                2
                            ),

                        "is_baseline":
                            True
                    })

        return predictions


# ============================================================
# SINGLE PREDICTOR INSTANCE
# ============================================================

ai_predictor = AIPredictor()