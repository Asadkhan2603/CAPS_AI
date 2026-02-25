from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

try:  # pragma: no cover - import availability depends on environment
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None


class RedisStore:
    def __init__(self) -> None:
        self._client: Redis | None = None
        self._ready = False
        self._next_retry_at = 0.0

    async def _get_client(self) -> Redis | None:
        if not settings.redis_enabled or Redis is None:
            return None
        import time
        if not self._ready and time.monotonic() < self._next_retry_at:
            return None
        if self._ready and self._client is not None:
            return self._client
        try:
            client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
                retry_on_timeout=False,
            )
            await client.ping()
            self._client = client
            self._ready = True
            return self._client
        except Exception:
            self._client = None
            self._ready = False
            self._next_retry_at = time.monotonic() + 10
            return None

    async def available(self) -> bool:
        return await self._get_client() is not None

    async def get_json(self, key: str) -> Any | None:
        client = await self._get_client()
        if client is None:
            return None
        value = await client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        await client.set(key, json.dumps(value, default=str), ex=max(1, ttl_seconds))
        return True

    async def increment_with_ttl(self, key: str, ttl_seconds: int) -> int | None:
        client = await self._get_client()
        if client is None:
            return None
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, max(1, ttl_seconds))
        return int(count)

    async def mark_blacklisted(self, *, jti: str, expires_at: datetime | None) -> bool:
        client = await self._get_client()
        if client is None or not jti:
            return False
        ttl = 60
        if expires_at:
            aware = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
            ttl = max(60, int((aware - datetime.now(timezone.utc)).total_seconds()))
        await client.set(f"blacklist:{jti}", "1", ex=ttl)
        return True

    async def is_blacklisted(self, jti: str | None) -> bool:
        if not jti:
            return False
        client = await self._get_client()
        if client is None:
            return False
        return (await client.exists(f"blacklist:{jti}")) > 0


redis_store = RedisStore()
