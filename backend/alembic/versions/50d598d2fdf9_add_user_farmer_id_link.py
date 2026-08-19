"""add user farmer_id link

Revision ID: 50d598d2fdf9
Revises: 427fbc47dd56
Create Date: 2026-08-19 04:52:54.002569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50d598d2fdf9'
down_revision: Union[str, Sequence[str], None] = '427fbc47dd56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Hand-adjusted from the autogenerate output to use batch_alter_table with a
    NAMED foreign key. This is portable: PostgreSQL runs plain ALTERs, and SQLite
    (which cannot ALTER-add a foreign key) rebuilds the table via batch mode. The
    explicit name also lets downgrade drop the constraint reliably.
    """
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("farmer_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_farmer_id"), ["farmer_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_users_farmer_id_farmers", "farmers", ["farmer_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_farmer_id_farmers", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_users_farmer_id"))
        batch_op.drop_column("farmer_id")
