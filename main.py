import os
import random
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Numeric,
    create_engine,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = os.getenv("DB_URL", "sqlite:///./payments.db")
FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.30"))

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title="Idempotent Payments Simulator", version="1.0.0")


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(16), nullable=False, default=PaymentStatus.PENDING.value)
    result_code = Column(String(32), nullable=True)
    error_message = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))


init_db()


class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)


class PaymentResponse(BaseModel):
    id: int
    idempotency_key: str
    amount: float
    currency: str
    status: PaymentStatus
    result_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


def to_response(p: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=p.id,
        idempotency_key=p.idempotency_key,
        amount=float(p.amount),
        currency=p.currency,
        status=PaymentStatus(p.status),
        result_code=p.result_code,
        error_message=p.error_message,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def simulate_processor() -> tuple[bool, str, Optional[str]]:
    if random.random() < FAILURE_RATE:
        return (False, "DECLINED", "Simulated processor failure (e.g., timeout/insufficient funds)")
    return (True, "APPROVED", None)


@app.post("/payments", response_model=PaymentResponse)
def create_payment(
    payload: PaymentRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=400, detail="Missing required header: Idempotency-Key")

    idempotency_key = idempotency_key.strip()

    db = SessionLocal()
    try:
        existing = db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        ).scalar_one_or_none()

        if existing:
            return to_response(existing)

        now = datetime.now(timezone.utc)
        p = Payment(
            idempotency_key=idempotency_key,
            amount=round(payload.amount, 2),
            currency=payload.currency.upper(),
            status=PaymentStatus.PENDING.value,
            created_at=now,
            updated_at=now,
        )
        db.add(p)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.execute(
                select(Payment).where(Payment.idempotency_key == idempotency_key)
            ).scalar_one()
            return to_response(existing)

        success, result_code, err = simulate_processor()
        p.status = PaymentStatus.SUCCESS.value if success else PaymentStatus.FAILED.value
        p.result_code = result_code
        p.error_message = err
        p.updated_at = datetime.now(timezone.utc)

        db.add(p)
        db.commit()
        db.refresh(p)

        return to_response(p)

    finally:
        db.close()


@app.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int):
    db = SessionLocal()
    try:
        p = db.execute(select(Payment).where(Payment.id == payment_id)).scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Payment not found")
        return to_response(p)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True, "failure_rate": FAILURE_RATE}
