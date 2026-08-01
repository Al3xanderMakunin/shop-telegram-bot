"""add platega settings

Revision ID: a1b2c3d4e5f6
Revises: f8b2d3a1c5e7
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f8b2d3a1c5e7"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("bot_settings", sa.Column("platega_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("bot_settings", sa.Column("platega_merchant", sa.String(length=128), nullable=True))
    op.add_column("bot_settings", sa.Column("platega_secret", sa.String(length=255), nullable=True))
    op.add_column("bot_settings", sa.Column("platega_return_url", sa.String(length=512), nullable=True))

def downgrade():
    for c in ("platega_return_url", "platega_secret", "platega_merchant", "platega_enabled"):
        op.drop_column("bot_settings", c)
