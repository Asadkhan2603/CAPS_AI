from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.services.background_jobs import (
    dispatch_scheduled_notice_notifications,
    run_daily_analytics_snapshot_job,
)

logger = logging.getLogger("caps_scheduler")


def _next_daily_run_utc(*, hour: int, minute: int) -> datetime:
    now = datetime.now(timezone.utc)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


class AppScheduler:
    def __init__(self) -> None:
        self._enabled = settings.scheduler_enabled
        self._running = False
        self._tasks: list[asyncio.Task[Any]] = []
        self._last_notice_dispatch_at: datetime | None = None
        self._last_snapshot_at: datetime | None = None
        self._last_notice_dispatch_count = 0

    async def start(self) -> None:
        if not self._enabled or self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._scheduled_notice_loop(), name="scheduled-notice-loop"),
            asyncio.create_task(self._daily_snapshot_loop(), name="daily-snapshot-loop"),
        ]
        logger.info(
            {
                "event": "scheduler.started",
                "scheduled_notice_poll_seconds": settings.scheduled_notice_poll_seconds,
                "snapshot_hour_utc": settings.analytics_snapshot_hour_utc,
                "snapshot_minute_utc": settings.analytics_snapshot_minute_utc,
            }
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info({"event": "scheduler.stopped"})

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "running": self._running,
            "scheduled_notice_poll_seconds": settings.scheduled_notice_poll_seconds,
            "snapshot_time_utc": f"{settings.analytics_snapshot_hour_utc:02d}:{settings.analytics_snapshot_minute_utc:02d}",
            "last_notice_dispatch_at": self._last_notice_dispatch_at,
            "last_notice_dispatch_count": self._last_notice_dispatch_count,
            "last_snapshot_at": self._last_snapshot_at,
        }

    async def _scheduled_notice_loop(self) -> None:
        sleep_for = max(15, settings.scheduled_notice_poll_seconds)
        while self._running:
            try:
                count = await dispatch_scheduled_notice_notifications()
                self._last_notice_dispatch_at = datetime.now(timezone.utc)
                self._last_notice_dispatch_count = count
            except Exception:
                logger.exception({"event": "scheduler.notice_dispatch.error"})
            await asyncio.sleep(sleep_for)

    async def _daily_snapshot_loop(self) -> None:
        while self._running:
            try:
                next_run = _next_daily_run_utc(
                    hour=max(0, min(23, settings.analytics_snapshot_hour_utc)),
                    minute=max(0, min(59, settings.analytics_snapshot_minute_utc)),
                )
                wait_seconds = max(1.0, (next_run - datetime.now(timezone.utc)).total_seconds())
                await asyncio.sleep(wait_seconds)
                if not self._running:
                    break
                await run_daily_analytics_snapshot_job()
                self._last_snapshot_at = datetime.now(timezone.utc)
            except Exception:
                logger.exception({"event": "scheduler.daily_snapshot.error"})
                await asyncio.sleep(30)


app_scheduler = AppScheduler()

