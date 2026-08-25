"""configure creator subscription plans

Revision ID: 9667a3b3c004
Revises: a782dfa1cfae
Create Date: 2026-08-23 08:41:50.380950

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9667a3b3c004"
down_revision: Union[str, Sequence[str], None] = "a782dfa1cfae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Configure subscription plans."""

    plans = [
        {
            "code": "creator_monthly",
            "name": "Creator Monthly",
            "user_type": "creator",
            "price": 999,
            "duration_days": 30,
            "max_courses": 15,
        },
        {
            "code": "creator_yearly",
            "name": "Creator Yearly",
            "user_type": "creator",
            "price": 9999,
            "duration_days": 365,
            "max_courses": 50,
        },
    ]

    connection = op.get_bind()

    for plan in plans:
        existing = connection.execute(
            sa.text(
                """
                SELECT id
                FROM subscription_plans
                WHERE code = :code
                """
            ),
            {"code": plan["code"]},
        ).fetchone()

        if existing:
            connection.execute(
                sa.text(
                    """
                    UPDATE subscription_plans
                    SET
                        name = :name,
                        user_type = :user_type,
                        price = :price,
                        duration_days = :duration_days,
                        max_courses = :max_courses,
                        is_active = TRUE
                    WHERE code = :code
                    """
                ),
                plan,
            )
        else:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO subscription_plans (
                        id,
                        code,
                        name,
                        user_type,
                        price,
                        duration_days,
                        max_courses,
                        is_active,
                        created_at
                    )
                    VALUES (
                        :id,
                        :code,
                        :name,
                        :user_type,
                        :price,
                        :duration_days,
                        :max_courses,
                        TRUE,
                        CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    **plan,
                    "id": str(uuid.uuid4()),
                },
            )


def downgrade() -> None:
    """Remove configured creator subscription plans."""

    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            DELETE FROM subscription_plans
            WHERE code IN (
                'creator_monthly',
                'creator_yearly'
            )
            """
        )
    )