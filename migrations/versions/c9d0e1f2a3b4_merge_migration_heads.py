"""merge migration heads

Revision ID: c9d0e1f2a3b4
Revises: a4b5c6d7e8f9, b4c6d8e0f2a4
"""
from typing import Sequence, Union


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = (
    "a4b5c6d7e8f9",
    "b4c6d8e0f2a4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge the two existing migration branches."""
    pass


def downgrade() -> None:
    """Split the merged migration graph back into its two heads."""
    pass
