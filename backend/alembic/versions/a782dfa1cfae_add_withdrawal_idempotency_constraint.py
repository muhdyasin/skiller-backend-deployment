"""add withdrawal idempotency constraint

Revision ID: a782dfa1cfae
Revises: 94cd4fd7a9cf
Create Date: 2026-08-21 22:39:40.917885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a782dfa1cfae'
down_revision: Union[str, Sequence[str], None] = '94cd4fd7a9cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_withdrawals_user_idempotency",
        "withdrawals",
        ["user_id","idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_withdrawals_user_idempotency",
        "withdrawals",
        type_ = "unique",
    )
