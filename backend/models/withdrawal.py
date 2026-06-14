import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime
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

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending"
    )
    # pending
    # approved
    # rejected
    # completed

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