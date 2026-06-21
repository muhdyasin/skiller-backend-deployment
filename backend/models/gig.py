import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class Gig(Base):
    __tablename__ = "gigs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    owner_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    owner_username: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    owner_name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    budget: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String,
        default="INR"
    )

    location: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    category: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    skills: Mapped[list] = mapped_column(
        ARRAY(String),
        default=[]
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )