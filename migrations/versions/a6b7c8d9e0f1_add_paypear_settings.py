"""add PayPear payment settings

Revision ID: a6b7c8d9e0f1
Revises: c9d0e1f2a3b4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bot_settings", sa.Column("paypear_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("bot_settings", sa.Column("paypear_shop_id", sa.String(64), nullable=True))
    op.add_column("bot_settings", sa.Column("paypear_secret_key", sa.String(255), nullable=True))
    op.add_column("bot_settings", sa.Column("paypear_payment_method", sa.String(32), server_default="sbp", nullable=False))
    op.add_column("bot_settings", sa.Column("paypear_return_url", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("bot_settings", "paypear_return_url")
    op.drop_column("bot_settings", "paypear_payment_method")
    op.drop_column("bot_settings", "paypear_secret_key")
    op.drop_column("bot_settings", "paypear_shop_id")
    op.drop_column("bot_settings", "paypear_enabled")
