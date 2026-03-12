from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import db
from app.core.observability import observability_state
from app.core.schema_versions import SCHEDULER_LOCK_SCHEMA_VERSION
from app.services.ai_jobs import process_ai_jobs_once, sample_ai_queue_metrics
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
        self._instance_id = (os.getenv("HOSTNAME") or "").strip() or f"scheduler-{os.getpid()}"
        self._lock_id = (settings.scheduler_lock_id or "caps_ai_scheduler_primary").strip()
        self._lock_ttl_seconds = max(30, settings.scheduler_lock_ttl_seconds)
        self._lock_renew_seconds = max(
            5,
            min(settings.scheduler_lock_renew_seconds, max(5, self._lock_ttl_seconds // 2)),
        )
        self._running = False
        self._is_leader = False
        self._leader_task: asyncio.Task[Any] | None = None
        self._job_tasks: list[asyncio.Task[Any]] = []
        self._last_notice_dispatch_at: datetime | None = None
        self._last_snapshot_at: datetime | None = None
        self._last_notice_dispatch_count = 0

    async def start(self) -> None:
        if not self._enabled or self._running:
            return
        self._running = True
        self._leader_task = asyncio.create_task(self._leader_election_loop(), name="scheduler-leader-loop")
        logger.info(
            {
                "event": "scheduler.started",
                "instance_id": self._instance_id,
                "lock_id": self._lock_id,
                "lock_ttl_seconds": self._lock_ttl_seconds,
                "lock_renew_seconds": self._lock_renew_seconds,
                "scheduled_notice_poll_seconds": settings.scheduled_notice_poll_seconds,
                "ai_job_poll_seconds": settings.ai_job_poll_seconds,
                "snapshot_hour_utc": settings.analytics_snapshot_hour_utc,
                "snapshot_minute_utc": settings.analytics_snapshot_minute_utc,
            }
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._leader_task is not None:
            self._leader_task.cancel()
            await asyncio.gather(self._leader_task, return_exceptions=True)
            self._leader_task = None
        await self._stop_job_tasks()
        await self._release_leader_lock()
        self._is_leader = False
        logger.info({"event": "scheduler.stopped"})

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "running": self._running,
            "is_leader": self._is_leader,
            "instance_id": self._instance_id,
            "lock_id": self._lock_id,
            "lock_ttl_seconds": self._lock_ttl_seconds,
            "lock_renew_seconds": self._lock_renew_seconds,
            "scheduled_notice_poll_seconds": settings.scheduled_notice_poll_seconds,
            "ai_job_poll_seconds": settings.ai_job_poll_seconds,
            "snapshot_time_utc": f"{settings.analytics_snapshot_hour_utc:02d}:{settings.analytics_snapshot_minute_utc:02d}",
            "last_notice_dispatch_at": self._last_notice_dispatch_at,
            "last_notice_dispatch_count": self._last_notice_dispatch_count,
            "last_snapshot_at": self._last_snapshot_at,
        }

    async def _leader_election_loop(self) -> None:
        while self._running:
            is_leader = False
            try:
                is_leader = await self._try_acquire_or_renew_leadership()
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                raise
            except Exception:
                observability_state.record_scheduler_election_error()
                logger.exception(
                    {
                        "event": "scheduler.leader_election.error",
                        "instance_id": self._instance_id,
                    }
                )

            if is_leader and not self._is_leader:
                self._is_leader = True
                await self._start_job_tasks()
                observability_state.record_scheduler_leadership(acquired=True)
                logger.info(
                    {
                        "event": "scheduler.leader_acquired",
                        "instance_id": self._instance_id,
                        "lock_id": self._lock_id,
                    }
                )
            elif not is_leader and self._is_leader:
                self._is_leader = False
                await self._stop_job_tasks()
                observability_state.record_scheduler_leadership(acquired=False)
                logger.warning(
                    {
                        "event": "scheduler.leader_lost",
                        "instance_id": self._instance_id,
                        "lock_id": self._lock_id,
                    }
                )

            await asyncio.sleep(self._lock_renew_seconds)

    async def _start_job_tasks(self) -> None:
        if self._job_tasks:
            return
        self._job_tasks = [
            asyncio.create_task(self._scheduled_notice_loop(), name="scheduled-notice-loop"),
            asyncio.create_task(self._ai_job_loop(), name="ai-job-loop"),
            asyncio.create_task(self._daily_snapshot_loop(), name="daily-snapshot-loop"),
        ]
        logger.info({"event": "scheduler.jobs_started", "instance_id": self._instance_id})

    async def _stop_job_tasks(self) -> None:
        if not self._job_tasks:
            return
        for task in self._job_tasks:
            task.cancel()
        await asyncio.gather(*self._job_tasks, return_exceptions=True)
        self._job_tasks.clear()
        logger.info({"event": "scheduler.jobs_stopped", "instance_id": self._instance_id})

    async def _try_acquire_or_renew_leadership(self) -> bool:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._lock_ttl_seconds)
        lock_collection = db.scheduler_locks

        doc = await lock_collection.find_one_and_update(
            {
                "_id": self._lock_id,
                "$or": [
                    {"owner_id": self._instance_id},
                    {"expires_at": {"$lte": now}},
                ],
            },
            {
                "$set": {
                    "owner_id": self._instance_id,
                    "expires_at": expires_at,
                    "heartbeat_at": now,
                    "schema_version": SCHEDULER_LOCK_SCHEMA_VERSION,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if doc and doc.get("owner_id") == self._instance_id:
            return True

        try:
            await lock_collection.insert_one(
                {
                    "_id": self._lock_id,
                    "owner_id": self._instance_id,
                    "expires_at": expires_at,
                    "heartbeat_at": now,
                    "schema_version": SCHEDULER_LOCK_SCHEMA_VERSION,
                    "created_at": now,
                }
            )
            return True
        except DuplicateKeyError:
            return False

    async def _release_leader_lock(self) -> None:
        try:
            await db.scheduler_locks.delete_one({"_id": self._lock_id, "owner_id": self._instance_id})
        except Exception:
            logger.exception(
                {
                    "event": "scheduler.release_lock.error",
                    "instance_id": self._instance_id,
                    "lock_id": self._lock_id,
                }
            )

    async def _scheduled_notice_loop(self) -> None:
        sleep_for = max(15, settings.scheduled_notice_poll_seconds)
        while self._running and self._is_leader:
            started = datetime.now(timezone.utc)
            try:
                count = await dispatch_scheduled_notice_notifications()
                self._last_notice_dispatch_at = datetime.now(timezone.utc)
                self._last_notice_dispatch_count = count
                observability_state.record_scheduler_job_run(
                    job_name="notice_dispatch",
                    success=True,
                    duration_ms=int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                    processed_count=count,
                )
            except Exception:
                observability_state.record_scheduler_job_run(
                    job_name="notice_dispatch",
                    success=False,
                    duration_ms=int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                )
                logger.exception({"event": "scheduler.notice_dispatch.error"})
            await asyncio.sleep(sleep_for)

    async def _daily_snapshot_loop(self) -> None:
        while self._running and self._is_leader:
            try:
                next_run = _next_daily_run_utc(
                    hour=max(0, min(23, settings.analytics_snapshot_hour_utc)),
                    minute=max(0, min(59, settings.analytics_snapshot_minute_utc)),
                )
                wait_seconds = max(1.0, (next_run - datetime.now(timezone.utc)).total_seconds())
                await asyncio.sleep(wait_seconds)
                if not self._running or not self._is_leader:
                    break
                started = datetime.now(timezone.utc)
                await run_daily_analytics_snapshot_job()
                self._last_snapshot_at = datetime.now(timezone.utc)
                observability_state.record_scheduler_job_run(
                    job_name="daily_snapshot",
                    success=True,
                    duration_ms=int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                )
            except Exception:
                observability_state.record_scheduler_job_run(
                    job_name="daily_snapshot",
                    success=False,
                    duration_ms=0,
                )
                logger.exception({"event": "scheduler.daily_snapshot.error"})
                await asyncio.sleep(30)

    async def _ai_job_loop(self) -> None:
        sleep_for = max(5, settings.ai_job_poll_seconds)
        while self._running and self._is_leader:
            started = datetime.now(timezone.utc)
            processed = None
            success = True
            try:
                processed = await process_ai_jobs_once(max_jobs=3)
            except Exception:
                success = False
                logger.exception({"event": "scheduler.ai_jobs.error"})
            try:
                await sample_ai_queue_metrics()
            except Exception:
                logger.exception({"event": "scheduler.ai_jobs.metrics.error"})
            observability_state.record_scheduler_job_run(
                job_name="ai_jobs",
                success=success,
                duration_ms=int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                processed_count=processed,
            )
            await asyncio.sleep(sleep_for)


app_scheduler = AppScheduler()
