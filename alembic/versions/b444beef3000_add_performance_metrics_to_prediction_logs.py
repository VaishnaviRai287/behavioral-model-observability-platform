"""add performance metrics to prediction logs

Revision ID: b444beef3000
Revises: f671a100beef
Create Date: 2026-06-19 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b444beef3000'
down_revision: Union[str, Sequence[str], None] = 'f671a100beef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prediction_logs', sa.Column('cpu_utilization', sa.Float(), nullable=True))
    op.add_column('prediction_logs', sa.Column('memory_mb', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('prediction_logs', 'memory_mb')
    op.drop_column('prediction_logs', 'cpu_utilization')
