"""Add tenant table and tenant_id columns (Restored as no-op to fix startup)

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a7
Create Date: 2026-02-25 00:00:00.000000

This migration is restored as a no-op to prevent Alembic "Can't locate revision" errors
after the multitenancy feature removal.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op since feature is removed in code
    pass


def downgrade() -> None:
    # No-op
    pass
