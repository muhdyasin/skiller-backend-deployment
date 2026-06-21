import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    JSON
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from db.session import Base


class XPEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )

    reason: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    meta: Mapped[dict] = mapped_column(
        JSON,
        default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )