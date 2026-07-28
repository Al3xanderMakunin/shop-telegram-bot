"""add catalog media

Revision ID: a4b5c6d7e8f9
Revises: f2a3b4c5d6e7
"""
from alembic import op
import sqlalchemy as sa

revision = 'a4b5c6d7e8f9'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'catalog_media',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('media_type', sa.String(length=8), nullable=False),
        sa.Column('file_id', sa.Text(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.CheckConstraint("media_type IN ('photo','video')", name='ck_catalog_media_type'),
        sa.CheckConstraint(
            '(category_id IS NOT NULL AND item_id IS NULL) OR '
            '(category_id IS NULL AND item_id IS NOT NULL)',
            name='ck_catalog_media_single_owner'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['goods.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('category_id', 'file_id', name='uq_category_media_file'),
        sa.UniqueConstraint('item_id', 'file_id', name='uq_item_media_file'),
    )
    op.create_index('ix_catalog_media_category_id', 'catalog_media', ['category_id'])
    op.create_index('ix_catalog_media_item_id', 'catalog_media', ['item_id'])
    op.create_index('ix_catalog_media_category_position', 'catalog_media', ['category_id', 'position', 'id'])
    op.create_index('ix_catalog_media_item_position', 'catalog_media', ['item_id', 'position', 'id'])


def downgrade():
    op.drop_table('catalog_media')
