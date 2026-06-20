import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    course_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    payment_transaction_id: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    amount_paid: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )