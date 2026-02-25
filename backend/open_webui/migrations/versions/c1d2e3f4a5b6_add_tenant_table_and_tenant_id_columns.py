"""Add tenant table and tenant_id columns

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a7
Create Date: 2026-02-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from open_webui.migrations.util import get_existing_tables

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that get tenant_id added
TABLES_TO_SCOPE = [
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

    # 1. Create tenant table
    if "tenant" not in existing_tables:
        op.create_table(
            "tenant",
            sa.Column("id", sa.String(), nullable=False, primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("settings", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.UniqueConstraint("slug", name="uq_tenant_slug"),
        )

    # 2. Add is_super_admin to user table
    if "user" in existing_tables:
        with op.batch_alter_table("user") as batch_op:
            try:
                batch_op.add_column(
                    sa.Column(
                        "is_super_admin",
                        sa.Boolean(),
                        nullable=False,
                        server_default="false",
                    )
                )
            except Exception:
                pass  # Column already exists

    # 3. Add tenant_id to all scoped tables
    for table_name in TABLES_TO_SCOPE:
        if table_name in existing_tables:
            with op.batch_alter_table(table_name) as batch_op:
                try:
                    batch_op.add_column(
                        sa.Column("tenant_id", sa.String(), nullable=True)
                    )
                except Exception:
                    pass  # Column already exists

    # 4. Add indexes on tenant_id for query performance
    try:
        op.create_index("chat_tenant_id_idx", "chat", ["tenant_id"])
    except Exception:
        pass  # Index already exists

    for table_name in ["memory", "group", "knowledge", "tool", "function", "model", "prompt", "file"]:
        try:
            op.create_index(f"{table_name}_tenant_id_idx", table_name, ["tenant_id"])
        except Exception:
            pass  # Index already exists


def downgrade() -> None:
    # Remove indexes on remaining tables
    for table_name in ["memory", "group", "knowledge", "tool", "function", "model", "prompt", "file"]:
        try:
            op.drop_index(f"{table_name}_tenant_id_idx", table_name=table_name)
        except Exception:
            pass

    # Remove chat index
    try:
        op.drop_index("chat_tenant_id_idx", table_name="chat")
    except Exception:
        pass

    # Remove tenant_id columns
    for table_name in TABLES_TO_SCOPE:
        with op.batch_alter_table(table_name) as batch_op:
            try:
                batch_op.drop_column("tenant_id")
            except Exception:
                pass

    # Remove is_super_admin
    with op.batch_alter_table("user") as batch_op:
        try:
            batch_op.drop_column("is_super_admin")
        except Exception:
            pass

    # Drop tenant table
    try:
        op.drop_table("tenant")
    except Exception:
        pass
