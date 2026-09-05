"""add expires_at to short_urls

Revision ID: 871cde74cfe6
Revises: 105ae4d5e123
Create Date: 2026-09-05 16:19:37.563314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '871cde74cfe6'
down_revision: Union[str, Sequence[str], None] = '105ae4d5e123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "short_urls",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    # 为 expires_at 加索引，加速过期判断查询
    op.create_index("ix_short_urls_expires_at", "short_urls", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_short_urls_expires_at", table_name="short_urls")
    op.drop_column("short_urls", "expires_at")