import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    owner_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    instructor: Mapped[str] = mapped_column(
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

    price: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    lessons: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    thumbnail: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    category: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    rating: Mapped[float] = mapped_column(
        Float,
        default=5.0
    )

    students: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )