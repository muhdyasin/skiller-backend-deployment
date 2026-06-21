import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    Text
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    bio: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    avatar_url: Mapped[str] = mapped_column(
        String,
        default=""
    )

    role: Mapped[str] = mapped_column(
        String,
        default="student"
    )

    xp: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    streak: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    badges: Mapped[list] = mapped_column(
        ARRAY(String),
        default=[]
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    referral_code: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    referred_by: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    plan: Mapped[str] = mapped_column(
        String,
        default="trial"
    )

    premium_until: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )

    last_login_date: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )