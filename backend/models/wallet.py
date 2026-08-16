import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    owner_id: Mapped[str] = mapped_column(String, nullable=False)

    owner_type: Mapped[str] = mapped_column(String, nullable=False)

    balance: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)

    pending_balance: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)

    lifetime_earned: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)

    lifetime_withdrawn: Mapped[Decimal] = mapped_column(Numeric( 12,2), default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )