"""Placeholder migration for Railway DB compatibility

Revision ID: de8c7f6b5a4b
Revises: c1d2e3f4a5b6
Create Date: 2026-03-14 00:00:00.000000

The Railway PostgreSQL database has this revision stamped in alembic_version
from a previous deployment. This no-op migration exists solely so Alembic
can locate the revision and avoid 'Can't locate revision' errors on startup.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "de8c7f6b5a4b"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
