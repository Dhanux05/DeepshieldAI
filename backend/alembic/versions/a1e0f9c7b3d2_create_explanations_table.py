"""create explanations table

Revision ID: a1e0f9c7b3d2
Revises: ee25196c2682
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1e0f9c7b3d2'
down_revision: Union[str, Sequence[str], None] = 'ee25196c2682'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('explanations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('prediction_id', sa.Integer(), nullable=False),
    sa.Column('method', sa.String(length=20), nullable=False),
    sa.Column('artifact_type', sa.String(length=20), nullable=False),
    sa.Column('artifact', sa.Text(), nullable=False),
    sa.Column('model_name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['prediction_id'], ['predictions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_explanations_id'), 'explanations', ['id'], unique=False)
    op.create_index(op.f('ix_explanations_prediction_id'), 'explanations', ['prediction_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_explanations_prediction_id'), table_name='explanations')
    op.drop_index(op.f('ix_explanations_id'), table_name='explanations')
    op.drop_table('explanations')
