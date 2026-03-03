from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque

from fastapi import HTTPException, status
from jose import JWTError, jwt
from pymongo import ReturnDocument
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.database import db
from app.core.config import settings
from app.core.redis_store import redis_store


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._mongo_indexes_ready = False
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._last_local_prune_at = 0.0

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").strip()
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _user_actor(request: Request) -> str:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            if token:
                try:
                    payload = jwt.decode(
                        token,
                        settings.jwt_secret,
                        algorithms=[settings.jwt_algorithm],
                        options={"verify_aud": False},
                    )
                    subject = payload.get("sub")
                    if subject:
                        return f"user:{subject}"
                except JWTError:
                    pass
        ip = RateLimitMiddleware._client_ip(request)
        user_agent = request.headers.get("user-agent", "")[:80]
        return f"ip:{ip}:ua:{user_agent}"

    def _key(self, request: Request) -> str:
        actor = self._user_actor(request)
        method = request.method.upper()
        return f"{actor}:{method}:{request.url.path}"

    async def _increment_via_mongo(self, key: str) -> int | None:
        counters = getattr(db, "rate_limit_counters", None)
        if counters is None:
            return None

        if not self._mongo_indexes_ready:
            try:
                await counters.create_index("expires_at", expireAfterSeconds=0)
                await counters.create_index("created_at")
                self._mongo_indexes_ready = True
            except Exception:
                return None

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=max(2, self.window_seconds * 2))
        bucket_id = int(time.time() // self.window_seconds)
        doc_id = f"{bucket_id}:{key}"

        try:
            updated = await counters.find_one_and_update(
                {"_id": doc_id},
                {
                    "$inc": {"count": 1},
                    "$setOnInsert": {
                        "created_at": now,
                        "expires_at": expires_at,
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except Exception:
            return None

        if not updated:
            return None
        return int(updated.get("count") or 0)

    def _increment_via_local_memory(self, key: str) -> int:
        now = time.monotonic()
        events = self._events[key]

        while events and now - events[0] > self.window_seconds:
            events.popleft()

        events.append(now)
        self._prune_local_state(now)
        return len(events)

    def _prune_local_state(self, now: float) -> None:
        # Local fallback is only for non-production; prune aggressively to cap key growth.
        if now - self._last_local_prune_at < max(5, self.window_seconds):
            return
        stale_after = now - self.window_seconds
        stale_keys = [key for key, events in self._events.items() if not events or events[-1] < stale_after]
        for key in stale_keys:
            self._events.pop(key, None)
        self._last_local_prune_at = now

    def _assert_within_limit(self, count: int) -> None:
        if count > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests. Please retry shortly.',
            )

    async def dispatch(self, request: Request, call_next):
        # Only rate limit mutating routes and auth endpoints to reduce abuse risk.
        method = request.method.upper()
        path = request.url.path
        should_limit = method in {'POST', 'PUT', 'PATCH', 'DELETE'} or '/auth/' in path
        if not should_limit:
            return await call_next(request)

        key = self._key(request)
        redis_count = await redis_store.increment_with_ttl(
            f"ratelimit:{key}",
            self.window_seconds,
        )
        if redis_count is not None:
            self._assert_within_limit(redis_count)
            return await call_next(request)

        mongo_count = await self._increment_via_mongo(key)
        if mongo_count is not None:
            self._assert_within_limit(mongo_count)
            return await call_next(request)

        if settings.environment in {"production", "staging"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Rate limiter backend unavailable. Please retry shortly.',
            )

        local_count = self._increment_via_local_memory(key)
        self._assert_within_limit(local_count)
        return await call_next(request)
