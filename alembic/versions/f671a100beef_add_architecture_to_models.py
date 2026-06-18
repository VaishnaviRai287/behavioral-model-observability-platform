"""add architecture to models

Revision ID: f671a100beef
Revises: d32c544e3a89
Create Date: 2026-06-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f671a100beef'
down_revision: Union[str, Sequence[str], None] = 'd32c544e3a89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('models', sa.Column('architecture', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('models', 'architecture')
