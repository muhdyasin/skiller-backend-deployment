import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class CreatorPayoutAccount(Base):
    __tablename__ = "creator_payout_accounts"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_creator_payout_account_user"
        ),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    payout_type: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    # bank_account / upi

    account_holder_name: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    account_number: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    ifsc_code: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    upi_id: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    razorpay_fund_account_id: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
