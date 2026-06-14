import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    payer_id: Mapped[str] = mapped_column(String, nullable=False)

    payee_id: Mapped[str] = mapped_column(String, nullable=True)

    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    commission_amount: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    transaction_type: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    # subscription
    # course_purchase
    # gig_purchase

    payment_provider: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    # razorpay

    provider_order_id: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    provider_payment_id: Mapped[str] = mapped_column(
        String,
        nullable=True
    )
    
    plan_id: Mapped[str] = mapped_column(
    String,
    nullable=True
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    # created
    # pending
    # paid
    # failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )