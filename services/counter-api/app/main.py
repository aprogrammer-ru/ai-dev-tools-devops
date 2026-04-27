import logging

from fastapi import Depends, FastAPI, Header, Request
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.counter_service import get_counter, increment_counter
from app.db import engine, get_session
from app.logging_config import configure_logging
from app.middleware import RequestIdMiddleware
from app.rate_limit import enforce_rate_limit
from app.redis_client import get_redis
from app.schemas import CounterResponse, HealthResponse, IncrementRequest
from app.settings import Settings, get_settings

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(RequestIdMiddleware)

if settings.metrics_enabled:
    Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await engine.dispose()


@app.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
async def readiness(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> HealthResponse:
    await session.execute(text("SELECT 1"))
    await redis.ping()
    return HealthResponse(status="ready")


@app.get("/v1/counters/{counter_key}", response_model=CounterResponse)
async def read_counter(
    counter_key: str,
    redis: Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_session),
) -> CounterResponse:
    return await get_counter(counter_key=counter_key, redis=redis, session=session)


@app.post("/v1/counters/{counter_key}/increment", response_model=CounterResponse)
async def change_counter(
    counter_key: str,
    payload: IncrementRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    redis: Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_session),
    app_settings: Settings = Depends(get_settings),
) -> CounterResponse:
    client_id = request.client.host if request.client else "unknown"
    await enforce_rate_limit(redis=redis, settings=app_settings, client_id=client_id)
    response = await increment_counter(
        counter_key=counter_key,
        delta=payload.delta,
        idempotency_key=idempotency_key,
        redis=redis,
        session=session,
        settings=app_settings,
    )
    logger.info(
        "counter incremented",
        extra={
            "counter_key": counter_key,
            "counter_value": response.value,
            "request_id": getattr(request.state, "request_id", "-"),
        },
    )
    return response
