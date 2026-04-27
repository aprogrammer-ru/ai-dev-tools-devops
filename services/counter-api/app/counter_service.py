from datetime import datetime, timezone

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Counter, IdempotencyRecord
from app.schemas import CounterResponse
from app.settings import Settings


async def _persist_counter(session: AsyncSession, counter_key: str, value: int) -> Counter:
    row = await session.get(Counter, counter_key)
    if row is None:
        row = Counter(key=counter_key, value=value)
        session.add(row)
    else:
        row.value = value
        row.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return row


async def get_counter(counter_key: str, redis: Redis, session: AsyncSession) -> CounterResponse:
    redis_value = await redis.get(f"counter:{counter_key}")
    if redis_value is not None:
        return CounterResponse(key=counter_key, value=int(redis_value))

    row = await session.get(Counter, counter_key)
    if row is None:
        raise HTTPException(status_code=404, detail="counter not found")

    await redis.set(f"counter:{counter_key}", row.value)
    return CounterResponse(key=row.key, value=row.value, updated_at=row.updated_at)


async def increment_counter(
    counter_key: str,
    delta: int,
    idempotency_key: str | None,
    redis: Redis,
    session: AsyncSession,
    settings: Settings,
) -> CounterResponse:
    if idempotency_key:
        redis_idem_key = f"idem:{counter_key}:{idempotency_key}"
        cached = await redis.get(redis_idem_key)
        if cached is not None:
            return CounterResponse(key=counter_key, value=int(cached))

        stmt = select(IdempotencyRecord).where(IdempotencyRecord.request_key == redis_idem_key)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            await redis.setex(redis_idem_key, settings.idempotency_ttl_seconds, existing.response_value)
            return CounterResponse(key=counter_key, value=existing.response_value)

    value = await redis.incrby(f"counter:{counter_key}", delta)
    db_row = await _persist_counter(session, counter_key, int(value))

    if idempotency_key:
        redis_idem_key = f"idem:{counter_key}:{idempotency_key}"
        record = IdempotencyRecord(
            request_key=redis_idem_key,
            counter_key=counter_key,
            response_value=int(value),
        )
        session.add(record)
        await redis.setex(redis_idem_key, settings.idempotency_ttl_seconds, int(value))

    await session.commit()
    return CounterResponse(key=db_row.key, value=db_row.value, updated_at=db_row.updated_at)
