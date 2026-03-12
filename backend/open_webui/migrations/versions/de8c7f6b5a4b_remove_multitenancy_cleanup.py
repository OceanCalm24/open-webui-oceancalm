"""Remove multitenancy cleanup

Revision ID: de8c7f6b5a4b
Revises: c1d2e3f4a5b6
Create Date: 2026-03-11 15:00:00.000000

This migration cleans up the database after the multitenancy feature removal.
It drops the tenant table and removes tenant_id columns from all scoped tables.
It also removes the is_super_admin column from the user table.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from open_webui.migrations.util import get_existing_tables

revision: str = "de8c7f6b5a4b"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES_TO_CLEAN = [
    "user",
    "chat",
    "memory",
    "group",
    "knowledge",
    "tool",
    "function",
    "model",
    "prompt",
    "file",
]


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    # 1. Remove indexes on tenant_id
    for table_name in ["chat", "memory", "group", "knowledge", "tool", "function", "model", "prompt", "file"]:
        if table_name in existing_tables:
            try:
                op.drop_index(f"{table_name}_tenant_id_idx", table_name=table_name)
            except Exception:
                pass

    # 2. Remove tenant_id columns
    for table_name in TABLES_TO_CLEAN:
        if table_name in existing_tables:
            with op.batch_alter_table(table_name) as batch_op:
                try:
                    batch_op.drop_column("tenant_id")
                except Exception:
                    pass

    # 3. Remove is_super_admin from user table
    if "user" in existing_tables:
        with op.batch_alter_table("user") as batch_op:
            try:
                batch_op.drop_column("is_super_admin")
            except Exception:
                pass

    # 4. Drop tenant table
    if "tenant" in existing_tables:
        try:
            op.drop_table("tenant")
        except Exception:
            pass


def downgrade() -> None:
    # No-op: we are removing the feature, we don't want to go back to a broken state
    pass
