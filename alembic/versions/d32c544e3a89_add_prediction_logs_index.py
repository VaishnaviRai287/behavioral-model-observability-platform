"""add prediction logs index

Revision ID: d32c544e3a89
Revises: cc574da0ddd2
Create Date: 2026-06-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd32c544e3a89'
down_revision: Union[str, Sequence[str], None] = 'cc574da0ddd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_prediction_logs_model_id_created_at',
        'prediction_logs',
        ['model_id', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_prediction_logs_model_id_created_at', table_name='prediction_logs')
