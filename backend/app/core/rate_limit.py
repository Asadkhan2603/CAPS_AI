from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.redis_store import redis_store


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, Deque[float]] = defaultdict(deque)

    def _key(self, request: Request) -> str:
        client = request.client.host if request.client else 'unknown'
        return f"{client}:{request.url.path}"

    async def dispatch(self, request: Request, call_next):
        # Only rate limit mutating routes and auth endpoints to reduce abuse risk.
        method = request.method.upper()
        path = request.url.path
        should_limit = method in {'POST', 'PUT', 'PATCH', 'DELETE'} or '/auth/' in path
        if not should_limit:
            return await call_next(request)

        now = time.monotonic()
        key = self._key(request)
        redis_count = await redis_store.increment_with_ttl(
            f"ratelimit:{key}",
            self.window_seconds,
        )
        if redis_count is not None:
            if redis_count > self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail='Too many requests. Please retry shortly.',
                )
            return await call_next(request)

        events = self._events[key]

        while events and now - events[0] > self.window_seconds:
            events.popleft()

        if len(events) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests. Please retry shortly.',
            )

        events.append(now)
        return await call_next(request)
