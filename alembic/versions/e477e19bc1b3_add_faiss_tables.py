"""add faiss tables

Revision ID: <keep_generated_id>
Revises: b14cacc1d34c
Create Date: 2026-06-16 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e477e19bc1b3'
down_revision: Union[str, None] = 'b14cacc1d34c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to prediction_logs table
    op.add_column('prediction_logs', sa.Column('faiss_distance', sa.Float(), nullable=True))
    op.add_column('prediction_logs', sa.Column('novelty_flag', sa.Boolean(), nullable=True, server_default=sa.text('false')))

    # 2. Create faiss_indexes table
    op.create_table(
        'faiss_indexes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('model_id', sa.String(length=36), nullable=False),
        sa.Column('index_file_path', sa.String(length=255), nullable=False),
        sa.Column('vector_dim', sa.Integer(), nullable=False),
        sa.Column('vector_count', sa.Integer(), nullable=False),
        sa.Column('baseline_mean_distance', sa.Float(), nullable=False),
        sa.Column('baseline_std_distance', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('faiss_indexes')
    op.drop_column('prediction_logs', 'novelty_flag')
    op.drop_column('prediction_logs', 'faiss_distance')
