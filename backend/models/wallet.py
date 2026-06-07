import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime
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

    balance: Mapped[int] = mapped_column(Integer, default=0)

    pending_balance: Mapped[int] = mapped_column(Integer, default=0)

    lifetime_earned: Mapped[int] = mapped_column(Integer, default=0)

    lifetime_withdrawn: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )