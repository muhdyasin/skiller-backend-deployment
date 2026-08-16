import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12,2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending"
    )
    # pending = funds reserved and awaiting payout
    # processing = payout provider is processing
    # successful = payout confirmed
    # failed = payout failed and funds released

    requested_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )

    remarks: Mapped[str] = mapped_column(
        String,
        nullable=True
    )
    
    idempotency_key: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    payout_provider: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    payout_reference: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    failure_reason: Mapped[str] = mapped_column(
        String,
        nullable=True
    )