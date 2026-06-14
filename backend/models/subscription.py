import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    user_type: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    # creator | institution

    plan_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    # trial | active | expired | cancelled

    auto_renew: Mapped[bool] = mapped_column(
    Boolean,
    default=False
    )

    payment_provider: Mapped[str] = mapped_column(
    String,
    nullable=True
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )