from fastapi import HTTPException
from redis.asyncio import Redis

from app.settings import Settings


async def enforce_rate_limit(redis: Redis, settings: Settings, client_id: str) -> None:
    rate_limit_key = f"ratelimit:{client_id}"
    current = await redis.incr(rate_limit_key)
    if current == 1:
        await redis.expire(rate_limit_key, settings.rate_limit_window_seconds)
    if current > settings.rate_limit_max_requests:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
