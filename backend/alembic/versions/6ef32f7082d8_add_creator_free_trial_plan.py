"""add creator free trial plan

Revision ID: 6ef32f7082d8
Revises: 9667a3b3c004
Create Date: 2026-08-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6ef32f7082d8"
down_revision: Union[str, Sequence[str], None] = "9667a3b3c004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # Create the authoritative creator free-trial plan if it does not exist.
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
            SELECT
                'free_trial',
                'free_trial',
                'Free Trial',
                'creator',
                0,
                30,
                3,
                TRUE,
                CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1
                FROM subscription_plans
                WHERE code = 'free_trial'
            )
            """
        )
    )

    # Existing creator trial subscriptions used the legacy literal
    # "trial" instead of referencing the actual subscription plan.
    connection.execute(
        sa.text(
            """
            UPDATE subscriptions
            SET plan_id = 'free_trial'
            WHERE user_type = 'creator'
              AND plan_id = 'trial'
            """
        )
    )

    # Keep the legacy user-level plan field consistent where applicable.
    connection.execute(
        sa.text(
            """
            UPDATE users
            SET plan = 'free_trial'
            WHERE role = 'creator'
              AND plan = 'trial'
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()

    # Restore legacy creator trial references before removing the plan.
    connection.execute(
        sa.text(
            """
            UPDATE subscriptions
            SET plan_id = 'trial'
            WHERE user_type = 'creator'
              AND plan_id = 'free_trial'
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE users
            SET plan = 'trial'
            WHERE role = 'creator'
              AND plan = 'free_trial'
            """
        )
    )

    connection.execute(
        sa.text(
            """
            DELETE FROM subscription_plans
            WHERE code = 'free_trial'
            """
        )
    )