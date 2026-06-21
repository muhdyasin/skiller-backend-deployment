import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class UserFollow(Base):
    __tablename__ = "user_follows"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    follower_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    following_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )