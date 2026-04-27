from datetime import datetime

from pydantic import BaseModel, Field


class IncrementRequest(BaseModel):
    delta: int = Field(default=1, ge=1, le=1_000_000)


class CounterResponse(BaseModel):
    key: str
    value: int
    updated_at: datetime | None = None


class HealthResponse(BaseModel):
    status: str
