"""
app/services/scheduler.py
──────────────────────────
APScheduler-based automation for scheduled agent runs.
Runs the full LangGraph workflow on a configurable schedule.
"""

from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler | None = None


def _run_agent_job() -> None:
    """The scheduled job that invokes the full agent workflow."""
    from app.agents.email_agent import run_agent  # lazy import to avoid circular deps

    logger.info(f"[SCHEDULER] Starting scheduled agent run at {datetime.utcnow().isoformat()}")
    try:
        result = run_agent(
            source_file="data/sample_invoices.csv",
            dry_run=settings.email_dry_run,
        )
        logger.info(f"[SCHEDULER] Run complete: {result.get('run_stats', {})}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Agent run failed: {e}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    """
    Start the APScheduler with configured schedule.
    Returns the scheduler instance.
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("Scheduler already running.")
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)

    if settings.scheduler_interval_hours > 0:
        trigger = CronTrigger(
            hour=settings.scheduler_start_hour,
            timezone=settings.scheduler_timezone,
        )
    else:
        trigger = IntervalTrigger(hours=max(1, settings.scheduler_interval_hours))

    _scheduler.add_job(
        _run_agent_job,
        trigger=trigger,
        id="finance_agent_run",
        name="Finance Credit Follow-Up Agent",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    _scheduler.start()
    logger.info(
        f"[SCHEDULER] Started — next run at {settings.scheduler_start_hour}:00 {settings.scheduler_timezone}"
    )
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Stopped.")
    _scheduler = None


def get_scheduler_status() -> dict:
    """Return current scheduler status for dashboard display."""
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(next_run) if next_run else "N/A",
        })

    return {"running": True, "jobs": jobs}
