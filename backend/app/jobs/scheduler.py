"""Lightweight background scheduler for periodic tasks (e.g. retraining, cleaning cache)."""
from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = structlog.get_logger("forecastiq.scheduler")
_scheduler: AsyncIOScheduler | None = None


async def run_weekly_retraining():
    """Retrain the model for every organization. One org's failure doesn't block the rest."""
    from app.repositories import organizations_repo, sales_repo
    from app.ml.predictor import ai_predictor

    log.info("weekly_retraining_started")
    orgs = await organizations_repo.list_all()
    for org in orgs:
        org_id = str(org["_id"])
        try:
            count = await sales_repo.count(org_id)
            if count < 30:
                log.info("weekly_retraining_skipped_insufficient_data", org_id=org_id, rows=count)
                continue
            await ai_predictor.train_model(org_id)
            log.info("weekly_retraining_completed", org_id=org_id)
        except Exception as e:
            log.error("weekly_retraining_failed", org_id=org_id, error=str(e))


async def run_daily_alert_evaluation():
    """Evaluate every org's enabled alert rules. One org's failure doesn't block the rest."""
    from app.repositories import organizations_repo
    from app.services.alerts_service import evaluate_rules

    log.info("daily_alert_evaluation_started")
    orgs = await organizations_repo.list_all()
    for org in orgs:
        org_id = str(org["_id"])
        try:
            result = await evaluate_rules(org_id)
            log.info("daily_alert_evaluation_completed", org_id=org_id, **result)
        except Exception as e:
            log.error("daily_alert_evaluation_failed", org_id=org_id, error=str(e))


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = AsyncIOScheduler()

    # Retrain models every Sunday at 00:00
    sched.add_job(
        run_weekly_retraining,
        CronTrigger(day_of_week="sun", hour=0, minute=0),
        id="weekly_retraining",
        replace_existing=True,
    )

    # Evaluate alert rules daily at 06:00
    sched.add_job(
        run_daily_alert_evaluation,
        CronTrigger(hour=6, minute=0),
        id="daily_alert_evaluation",
        replace_existing=True,
    )

    sched.start()
    _scheduler = sched
    log.info("scheduler_started", schedule="weekly retraining (Sun) + daily alert evaluation (06:00)")
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler_stopped")


def is_running() -> bool:
    return bool(_scheduler and _scheduler.running)
