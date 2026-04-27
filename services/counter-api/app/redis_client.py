from redis.asyncio import Redis

from app.settings import get_settings

settings = get_settings()
redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> Redis:
    return redis
