from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Counter(Base):
    __tablename__ = "counters"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("request_key", name="uq_idempotency_request_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_key: Mapped[str] = mapped_column(String(255), nullable=False)
    counter_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    response_value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
