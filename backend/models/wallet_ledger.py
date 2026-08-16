import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class WalletLedger(Base):
    __tablename__ = "wallet_ledger"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    wallet_id: Mapped[str] = mapped_column(String, nullable=False)

    transaction_type: Mapped[str] = mapped_column(String, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)

    reference_type: Mapped[str] = mapped_column(String, nullable=True)

    reference_id: Mapped[str] = mapped_column(String, nullable=True)

    description: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )