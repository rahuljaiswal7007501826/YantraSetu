"""add complaints table

Revision ID: a7c3f19b2e64
Revises: e9e811b0afcb
Create Date: 2026-08-19 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3f19b2e64'
down_revision: Union[str, Sequence[str], None] = 'e9e811b0afcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'complaints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=40), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('demand_request_id', sa.Integer(), nullable=True),
        sa.Column('machine_id', sa.Integer(), nullable=True),
        sa.Column('chc_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('staff_response', sa.Text(), nullable=True),
        sa.Column('responded_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['demand_request_id'], ['demand_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['chc_id'], ['chcs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['responded_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_complaints_farmer_id'), 'complaints', ['farmer_id'], unique=False)
    op.create_index(
        op.f('ix_complaints_demand_request_id'), 'complaints', ['demand_request_id'], unique=False
    )
    op.create_index(op.f('ix_complaints_status'), 'complaints', ['status'], unique=False)
    op.create_index('ix_complaints_chc_status', 'complaints', ['chc_id', 'status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_complaints_chc_status', table_name='complaints')
    op.drop_index(op.f('ix_complaints_status'), table_name='complaints')
    op.drop_index(op.f('ix_complaints_demand_request_id'), table_name='complaints')
    op.drop_index(op.f('ix_complaints_farmer_id'), table_name='complaints')
    op.drop_table('complaints')
