# Multi-Tenant Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fork Open WebUI into a multi-tenant SaaS platform where all clients share one Railway deployment but have fully isolated row-level data.

**Architecture:** Single FastAPI + SvelteKit app on Railway with PostgreSQL. A new `tenant` table scopes every core table via `tenant_id`. Three user tiers: super admin (agency), tenant admin (client admin), tenant user (client user). Tenant context is resolved from `user.tenant_id` after JWT auth — no JWT changes needed.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, SvelteKit 5, PostgreSQL (Railway), OpenAI API

---

## Pre-flight Checklist

Before starting, verify:

```bash
# From repo root
cd backend
pip install -e ".[all]"
python -c "from open_webui.internal.db import Base; print('DB OK')"

# Start a local PostgreSQL for testing
docker run -d --name pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=webui -p 5432:5432 postgres:16
export DATABASE_URL="postgresql://postgres:test@localhost:5432/webui"
```

Tests live in `backend/open_webui/test/apps/webui/routers/`. Run from `backend/` directory.
Tests require `AbstractPostgresTest` — check `backend/test/util/` for the base class setup. If missing, tests can be run as plain pytest with a real DB.

---

## Phase 1: Database Models

### Task 1: Create Tenant model

**Files:**
- Create: `backend/open_webui/models/tenants.py`
- Test: `backend/open_webui/test/apps/webui/routers/test_tenants.py`

**Step 1: Write the failing test**

```python
# backend/open_webui/test/apps/webui/routers/test_tenants.py
import pytest
import time
import uuid


class TestTenantModel:
    def test_create_tenant(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        tenant = TenantTable.create_tenant(
            TenantForm(name="Acme Corp", slug="acme-corp")
        )
        assert tenant is not None
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.is_active is True

    def test_get_tenant_by_id(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        created = TenantTable.create_tenant(
            TenantForm(name="Beta Inc", slug="beta-inc")
        )
        fetched = TenantTable.get_tenant_by_id(created.id)
        assert fetched.id == created.id
        assert fetched.slug == "beta-inc"

    def test_get_all_tenants(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        TenantTable.create_tenant(TenantForm(name="T1", slug="t1"))
        TenantTable.create_tenant(TenantForm(name="T2", slug="t2"))
        tenants = TenantTable.get_all_tenants()
        assert len(tenants) >= 2

    def test_slug_must_be_unique(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        TenantTable.create_tenant(TenantForm(name="Dup", slug="dup-slug"))
        with pytest.raises(Exception):
            TenantTable.create_tenant(TenantForm(name="Dup2", slug="dup-slug"))
```

**Step 2: Run to verify it fails**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py -v
```

Expected: `ModuleNotFoundError: No module named 'open_webui.models.tenants'`

**Step 3: Create the model**

```python
# backend/open_webui/models/tenants.py
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, JSON, String, Text
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context


####################
# Tenant DB Schema
####################


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(String, primary_key=True, unique=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)


####################
# Pydantic Models
####################


class TenantModel(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    settings: Optional[dict] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class TenantForm(BaseModel):
    name: str
    slug: str
    settings: Optional[dict] = None


class TenantUpdateForm(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[dict] = None


####################
# CRUD
####################


class TenantTable:
    @staticmethod
    def create_tenant(form: TenantForm) -> Optional[TenantModel]:
        with get_db_context() as db:
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name=form.name,
                slug=form.slug,
                is_active=True,
                settings=form.settings,
                created_at=int(time.time()),
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            return TenantModel.model_validate(tenant)

    @staticmethod
    def get_tenant_by_id(tenant_id: str) -> Optional[TenantModel]:
        with get_db_context() as db:
            tenant = db.query(Tenant).filter_by(id=tenant_id).first()
            return TenantModel.model_validate(tenant) if tenant else None

    @staticmethod
    def get_tenant_by_slug(slug: str) -> Optional[TenantModel]:
        with get_db_context() as db:
            tenant = db.query(Tenant).filter_by(slug=slug).first()
            return TenantModel.model_validate(tenant) if tenant else None

    @staticmethod
    def get_all_tenants() -> list[TenantModel]:
        with get_db_context() as db:
            tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
            return [TenantModel.model_validate(t) for t in tenants]

    @staticmethod
    def update_tenant(
        tenant_id: str, form: TenantUpdateForm
    ) -> Optional[TenantModel]:
        with get_db_context() as db:
            tenant = db.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return None
            if form.name is not None:
                tenant.name = form.name
            if form.is_active is not None:
                tenant.is_active = form.is_active
            if form.settings is not None:
                tenant.settings = form.settings
            db.commit()
            db.refresh(tenant)
            return TenantModel.model_validate(tenant)

    @staticmethod
    def delete_tenant(tenant_id: str) -> bool:
        with get_db_context() as db:
            deleted = db.query(Tenant).filter_by(id=tenant_id).delete()
            db.commit()
            return deleted > 0


Tenants = TenantTable()
```

**Step 4: Run tests to verify they pass**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py -v
```

Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add backend/open_webui/models/tenants.py backend/open_webui/test/apps/webui/routers/test_tenants.py
git commit -m "feat: add Tenant model and TenantTable CRUD"
```

---

### Task 2: Add `tenant_id` and `is_super_admin` to User model

**Files:**
- Modify: `backend/open_webui/models/users.py`

**Step 1: Write the failing test**

Add to `backend/open_webui/test/apps/webui/routers/test_tenants.py`:

```python
    def test_user_has_tenant_id_field(self):
        from open_webui.models.users import UserModel

        # UserModel must have tenant_id and is_super_admin
        fields = UserModel.model_fields
        assert "tenant_id" in fields
        assert "is_super_admin" in fields
```

**Step 2: Run to verify it fails**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_user_has_tenant_id_field -v
```

Expected: `AssertionError: assert 'tenant_id' in {...}`

**Step 3: Add fields to User and UserModel**

In `backend/open_webui/models/users.py`, add to the `User` SQLAlchemy class (after the existing columns, before `last_active_at`):

```python
    tenant_id = Column(String, nullable=True)   # NULL = super admin
    is_super_admin = Column(Boolean, default=False, nullable=False, server_default="false")
```

In the `UserModel` Pydantic class (after `scim`):

```python
    tenant_id: Optional[str] = None
    is_super_admin: bool = False
```

**Step 4: Run to verify it passes**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_user_has_tenant_id_field -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/open_webui/models/users.py
git commit -m "feat: add tenant_id and is_super_admin to User model"
```

---

### Task 3: Add `tenant_id` to Chat model

**Files:**
- Modify: `backend/open_webui/models/chats.py`

**Step 1: Write the failing test**

Add to `test_tenants.py`:

```python
    def test_chat_has_tenant_id_field(self):
        from open_webui.models.chats import Chat
        from sqlalchemy import inspect

        mapper = inspect(Chat)
        col_names = [c.key for c in mapper.columns]
        assert "tenant_id" in col_names
```

**Step 2: Run to verify it fails**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_chat_has_tenant_id_field -v
```

Expected: `AssertionError`

**Step 3: Add column to Chat**

In `backend/open_webui/models/chats.py`, add to the `Chat` class (after `folder_id`):

```python
    tenant_id = Column(String, nullable=True)
```

Also add an index for performance (inside `__table_args__`):

```python
        Index("chat_tenant_id_idx", "tenant_id"),
```

**Step 4: Run to verify it passes**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_chat_has_tenant_id_field -v
```

**Step 5: Commit**

```bash
git add backend/open_webui/models/chats.py
git commit -m "feat: add tenant_id to Chat model"
```

---

### Task 4: Add `tenant_id` to remaining models

**Files:**
- Modify: `backend/open_webui/models/memories.py`
- Modify: `backend/open_webui/models/groups.py`
- Modify: `backend/open_webui/models/knowledge.py`
- Modify: `backend/open_webui/models/tools.py`
- Modify: `backend/open_webui/models/functions.py`
- Modify: `backend/open_webui/models/models.py`
- Modify: `backend/open_webui/models/prompts.py`
- Modify: `backend/open_webui/models/files.py`

**Step 1: Write the failing test**

Add to `test_tenants.py`:

```python
    def test_all_core_models_have_tenant_id(self):
        from sqlalchemy import inspect
        from open_webui.models.memories import Memory
        from open_webui.models.groups import Group
        from open_webui.models.knowledge import Knowledge
        from open_webui.models.tools import Tool
        from open_webui.models.functions import Function
        from open_webui.models.models import Model
        from open_webui.models.prompts import Prompt
        from open_webui.models.files import File

        models_to_check = [Memory, Group, Knowledge, Tool, Function, Model, Prompt, File]
        for model_class in models_to_check:
            mapper = inspect(model_class)
            col_names = [c.key for c in mapper.columns]
            assert "tenant_id" in col_names, f"{model_class.__name__} missing tenant_id"
```

**Step 2: Run to verify it fails**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_all_core_models_have_tenant_id -v
```

**Step 3: Add `tenant_id` to each model**

In each file listed above, find the SQLAlchemy model class (the one inheriting from `Base`) and add:

```python
tenant_id = Column(String, nullable=True)
```

Place it as the last column before any `__table_args__`. The column name and type is identical in all files.

To quickly check where to add in each file:
```bash
grep -n "class.*Base" backend/open_webui/models/memories.py
grep -n "class.*Base" backend/open_webui/models/groups.py
# etc.
```

**Step 4: Run to verify it passes**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_all_core_models_have_tenant_id -v
```

**Step 5: Commit**

```bash
git add backend/open_webui/models/memories.py backend/open_webui/models/groups.py \
        backend/open_webui/models/knowledge.py backend/open_webui/models/tools.py \
        backend/open_webui/models/functions.py backend/open_webui/models/models.py \
        backend/open_webui/models/prompts.py backend/open_webui/models/files.py
git commit -m "feat: add tenant_id to all core models"
```

---

## Phase 2: Database Migration

### Task 5: Write Alembic migration

**Files:**
- Create: `backend/open_webui/migrations/versions/a1b2c3d4e5f6_add_tenant_table_and_tenant_id_columns.py`

**Step 1: Check the current head migration**

```bash
cd backend
python -m alembic -c open_webui/migrations/alembic.ini current
# Note the revision ID shown — this becomes down_revision below
```

**Step 2: Create the migration file**

Replace `<PREVIOUS_REVISION>` with the output from the command above.

```python
# backend/open_webui/migrations/versions/a1b2c3d4e5f6_add_tenant_table_and_tenant_id_columns.py
"""Add tenant table and tenant_id columns

Revision ID: a1b2c3d4e5f6
Revises: <PREVIOUS_REVISION>
Create Date: 2026-02-25 00:00:00.000000
"""

from typing import Sequence, Union
import time
import uuid

from alembic import op
import sqlalchemy as sa
from open_webui.migrations.util import get_existing_tables

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "<PREVIOUS_REVISION>"
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

    # 4. Add index on chat.tenant_id for query performance
    try:
        op.create_index("chat_tenant_id_idx", "chat", ["tenant_id"])
    except Exception:
        pass


def downgrade() -> None:
    # Remove indexes
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
    op.drop_table("tenant")
```

**Step 3: Run the migration**

```bash
cd backend
export DATABASE_URL="postgresql://postgres:test@localhost:5432/webui"
python -m alembic -c open_webui/migrations/alembic.ini upgrade head
```

Expected: Migration applies without errors. Output ends with `Running upgrade ... -> a1b2c3d4e5f6`.

**Step 4: Verify schema**

```bash
python -c "
from open_webui.internal.db import engine
from sqlalchemy import inspect
insp = inspect(engine)
print('tenant table:', 'tenant' in insp.get_table_names())
print('user.tenant_id:', any(c['name']=='tenant_id' for c in insp.get_columns('user')))
print('chat.tenant_id:', any(c['name']=='tenant_id' for c in insp.get_columns('chat')))
"
```

Expected: all three print `True`.

**Step 5: Commit**

```bash
git add backend/open_webui/migrations/versions/a1b2c3d4e5f6_add_tenant_table_and_tenant_id_columns.py
git commit -m "feat: migration — add tenant table and tenant_id columns to all core tables"
```

---

## Phase 3: Auth & Tenant Context

### Task 6: Add `get_tenant_context` and `get_super_admin_user` dependencies

**Files:**
- Modify: `backend/open_webui/utils/auth.py`

**Step 1: Write the failing test**

Create `backend/open_webui/test/apps/webui/routers/test_tenant_context.py`:

```python
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException


class TestGetTenantContext:
    def test_returns_tenant_id_for_normal_user(self):
        from open_webui.utils.auth import get_tenant_context
        from open_webui.models.users import UserModel
        import time

        user = MagicMock(spec=UserModel)
        user.tenant_id = "tenant-abc"
        user.is_super_admin = False

        request = MagicMock()
        request.headers = {}

        result = get_tenant_context(request=request, user=user)
        assert result == "tenant-abc"

    def test_raises_if_no_tenant_assigned(self):
        from open_webui.utils.auth import get_tenant_context
        from open_webui.models.users import UserModel

        user = MagicMock(spec=UserModel)
        user.tenant_id = None
        user.is_super_admin = False

        request = MagicMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            get_tenant_context(request=request, user=user)
        assert exc_info.value.status_code == 403

    def test_super_admin_can_override_tenant(self):
        from open_webui.utils.auth import get_tenant_context
        from open_webui.models.users import UserModel

        user = MagicMock(spec=UserModel)
        user.tenant_id = None
        user.is_super_admin = True

        request = MagicMock()
        request.headers = {"x-tenant-id": "tenant-override"}

        result = get_tenant_context(request=request, user=user)
        assert result == "tenant-override"

    def test_super_admin_without_override_raises(self):
        from open_webui.utils.auth import get_tenant_context
        from open_webui.models.users import UserModel

        user = MagicMock(spec=UserModel)
        user.tenant_id = None
        user.is_super_admin = True

        request = MagicMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            get_tenant_context(request=request, user=user)
        assert exc_info.value.status_code == 403
```

**Step 2: Run to verify it fails**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenant_context.py -v
```

Expected: `ImportError: cannot import name 'get_tenant_context'`

**Step 3: Add the dependencies to `auth.py`**

At the bottom of `backend/open_webui/utils/auth.py`, add:

```python
####################
# Tenant Context
####################


def get_tenant_context(
    request: Request,
    user=Depends(get_verified_user),
) -> str:
    """
    Returns the tenant_id for the current request.
    - Normal users: returns their user.tenant_id
    - Super admins: returns X-Tenant-ID header value (required when acting on a tenant)
    - Raises 403 if tenant context cannot be determined
    """
    if user.is_super_admin:
        override_id = request.headers.get("x-tenant-id") or request.headers.get(
            "X-Tenant-ID"
        )
        if override_id:
            return override_id
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admins must provide X-Tenant-ID header",
        )

    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant assigned to this user",
        )

    return user.tenant_id


def get_super_admin_user(user=Depends(get_current_user)):
    """Dependency that allows only super admins."""
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return user
```

**Step 4: Run to verify it passes**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenant_context.py -v
```

Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add backend/open_webui/utils/auth.py backend/open_webui/test/apps/webui/routers/test_tenant_context.py
git commit -m "feat: add get_tenant_context and get_super_admin_user dependencies"
```

---

## Phase 4: Tenant API Router

### Task 7: Create the tenants router

**Files:**
- Create: `backend/open_webui/routers/tenants.py`

**Step 1: Write the failing test**

Create `backend/open_webui/test/apps/webui/routers/test_tenants_router.py`:

```python
from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestTenantsRouter(AbstractPostgresTest):
    BASE_PATH = "/api/v1/tenants"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.tenants import TenantTable
        cls.tenants = TenantTable

    def test_list_tenants_requires_super_admin(self):
        with mock_webui_user(role="admin"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 403

    def test_create_tenant(self):
        with mock_webui_user(role="admin", is_super_admin=True):
            response = self.fast_api_client.post(
                self.create_url("/"),
                json={"name": "Test Corp", "slug": "test-corp"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Corp"
        assert data["slug"] == "test-corp"
        assert data["is_active"] is True

    def test_get_tenant(self):
        from open_webui.models.tenants import TenantForm

        tenant = self.tenants.create_tenant(TenantForm(name="Get Me", slug="get-me"))
        with mock_webui_user(role="admin", is_super_admin=True):
            response = self.fast_api_client.get(self.create_url(f"/{tenant.id}"))
        assert response.status_code == 200
        assert response.json()["id"] == tenant.id

    def test_deactivate_tenant(self):
        from open_webui.models.tenants import TenantForm

        tenant = self.tenants.create_tenant(TenantForm(name="Deact Me", slug="deact-me"))
        with mock_webui_user(role="admin", is_super_admin=True):
            response = self.fast_api_client.patch(
                self.create_url(f"/{tenant.id}"),
                json={"is_active": False},
            )
        assert response.status_code == 200
        assert response.json()["is_active"] is False
```

**Step 2: Run to verify it fails**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants_router.py -v
```

Expected: 404 errors (router not mounted yet)

**Step 3: Create the router**

```python
# backend/open_webui/routers/tenants.py
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.models.tenants import TenantForm, TenantModel, TenantTable, TenantUpdateForm
from open_webui.models.users import UserModel, Users
from open_webui.utils.auth import get_super_admin_user, get_verified_user

log = logging.getLogger(__name__)
router = APIRouter()


####################
# Tenant CRUD
####################


@router.get("/", response_model=list[TenantModel])
async def list_tenants(user=Depends(get_super_admin_user)):
    return TenantTable.get_all_tenants()


@router.post("/", response_model=TenantModel)
async def create_tenant(form: TenantForm, user=Depends(get_super_admin_user)):
    existing = TenantTable.get_tenant_by_slug(form.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with slug '{form.slug}' already exists",
        )
    return TenantTable.create_tenant(form)


@router.get("/{tenant_id}", response_model=TenantModel)
async def get_tenant(tenant_id: str, user=Depends(get_super_admin_user)):
    tenant = TenantTable.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantModel)
async def update_tenant(
    tenant_id: str, form: TenantUpdateForm, user=Depends(get_super_admin_user)
):
    tenant = TenantTable.update_tenant(tenant_id, form)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str, user=Depends(get_super_admin_user)):
    success = TenantTable.delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"success": True}


####################
# Tenant User Management
####################


class AddTenantUserForm(BaseModel):
    email: str
    name: str
    password: str
    role: str = "user"  # "user" or "admin"


@router.get("/{tenant_id}/users")
async def list_tenant_users(tenant_id: str, user=Depends(get_super_admin_user)):
    users = Users.get_users_by_tenant_id(tenant_id)
    return users


@router.post("/{tenant_id}/users")
async def add_tenant_user(
    tenant_id: str, form: AddTenantUserForm, user=Depends(get_super_admin_user)
):
    tenant = TenantTable.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from open_webui.models.auths import Auths
    from open_webui.utils.auth import get_password_hash

    new_user = Auths.insert_new_auth(
        email=form.email,
        password=get_password_hash(form.password),
        name=form.name,
        role=form.role,
    )
    if not new_user:
        raise HTTPException(status_code=400, detail="Email already in use")

    # Assign tenant
    Users.update_user_tenant(new_user.id, tenant_id)
    return Users.get_user_by_id(new_user.id)


@router.delete("/{tenant_id}/users/{user_id}")
async def remove_tenant_user(
    tenant_id: str, user_id: str, admin=Depends(get_super_admin_user)
):
    user = Users.get_user_by_id(user_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="User not found in this tenant")
    Users.update_user_tenant(user_id, None)
    return {"success": True}
```

**Step 4: Mount the router in `main.py`**

In `backend/open_webui/main.py`, find where other routers are included (search for `app.include_router`) and add:

```python
from open_webui.routers import tenants

# Add alongside other router includes:
app.include_router(
    tenants.router, prefix="/api/v1/tenants", tags=["tenants"]
)
```

**Step 5: Add `get_users_by_tenant_id` and `update_user_tenant` to Users**

In `backend/open_webui/models/users.py`, find the `UsersTable` class and add:

```python
    def get_users_by_tenant_id(self, tenant_id: str) -> list[UserModel]:
        with get_db_context() as db:
            users = db.query(User).filter_by(tenant_id=tenant_id).all()
            return [UserModel.model_validate(u) for u in users]

    def update_user_tenant(
        self, user_id: str, tenant_id: Optional[str]
    ) -> Optional[UserModel]:
        with get_db_context() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return None
            user.tenant_id = tenant_id
            db.commit()
            db.refresh(user)
            return UserModel.model_validate(user)
```

**Step 6: Run to verify tests pass**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants_router.py -v
```

Expected: 4 tests PASS

**Step 7: Commit**

```bash
git add backend/open_webui/routers/tenants.py \
        backend/open_webui/models/users.py \
        backend/open_webui/main.py \
        backend/open_webui/test/apps/webui/routers/test_tenants_router.py
git commit -m "feat: add tenants router with CRUD and user management endpoints"
```

---

## Phase 5: Query Scoping

### Task 8: Scope Chat queries by tenant_id

**Files:**
- Modify: `backend/open_webui/models/chats.py`

**Step 1: Write the failing test**

Add to `test_tenants.py`:

```python
    def test_chats_are_scoped_by_tenant(self):
        from open_webui.models.chats import Chats
        import time, uuid

        tenant_a = "tenant-aaa"
        tenant_b = "tenant-bbb"
        user_id = str(uuid.uuid4())

        # Create a chat in tenant A
        Chats.insert_new_chat(
            user_id,
            {"title": "Chat A", "models": [], "messages": [], "history": {"messages": {}}, "params": {}},
            tenant_id=tenant_a,
        )

        # Fetch chats for tenant B — should be empty
        chats_b = Chats.get_chats_by_user_id(user_id, tenant_id=tenant_b)
        assert chats_b == []

        # Fetch chats for tenant A — should have the chat
        chats_a = Chats.get_chats_by_user_id(user_id, tenant_id=tenant_a)
        assert len(chats_a) == 1
```

**Step 2: Run to verify it fails**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_chats_are_scoped_by_tenant -v
```

Expected: `TypeError: insert_new_chat() got an unexpected keyword argument 'tenant_id'`

**Step 3: Update Chat CRUD methods**

In `backend/open_webui/models/chats.py`, find `insert_new_chat` and add `tenant_id` parameter:

```python
def insert_new_chat(self, user_id: str, form_data: dict, tenant_id: str = None) -> Optional[ChatModel]:
    with get_db_context() as db:
        chat = Chat(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=form_data.get("title", "New Chat"),
            chat=form_data,
            tenant_id=tenant_id,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return ChatModel.model_validate(chat)
```

Find `get_chats_by_user_id` and scope it:

```python
def get_chats_by_user_id(self, user_id: str, tenant_id: str = None) -> list[ChatModel]:
    with get_db_context() as db:
        query = db.query(Chat).filter_by(user_id=user_id, archived=False)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        chats = query.order_by(Chat.updated_at.desc()).all()
        return [ChatModel.model_validate(c) for c in chats]
```

Apply the same pattern (add optional `tenant_id` parameter + `.filter_by(tenant_id=tenant_id)` when provided) to these additional methods:
- `get_chats` (admin list all chats)
- `get_chat_by_id`
- `delete_chat_by_id`

**Step 4: Run to verify it passes**

```bash
cd backend
pytest open_webui/test/apps/webui/routers/test_tenants.py::TestTenantModel::test_chats_are_scoped_by_tenant -v
```

**Step 5: Update the chats router to pass tenant context**

In `backend/open_webui/routers/chats.py`, find where `Chats.get_chats_by_user_id` is called and update the route to inject tenant context:

```python
from open_webui.utils.auth import get_tenant_context

@router.get("/", ...)
async def get_chats(
    ...
    user=Depends(get_verified_user),
    tenant_id: str = Depends(get_tenant_context),
):
    return Chats.get_chats_by_user_id(user.id, tenant_id=tenant_id)
```

Apply the same pattern to other routes in `chats.py` that call Chats CRUD methods.

**Step 6: Commit**

```bash
git add backend/open_webui/models/chats.py backend/open_webui/routers/chats.py
git commit -m "feat: scope Chat CRUD and routes by tenant_id"
```

---

### Task 9: Scope remaining CRUD methods

**Files:**
- Modify: `backend/open_webui/models/memories.py`, `groups.py`, `knowledge.py`, `tools.py`, `functions.py`, `models.py`, `prompts.py`, `files.py`
- Modify: corresponding routers in `backend/open_webui/routers/`

**Pattern to apply** (identical for every model):

1. In the CRUD class, add `tenant_id: str = None` to all list/create/get/delete methods
2. In list queries: add `if tenant_id: query = query.filter_by(tenant_id=tenant_id)`
3. In create methods: pass `tenant_id=tenant_id` to the ORM object
4. In the corresponding router file: add `tenant_id: str = Depends(get_tenant_context)` and pass it through

**Check each model's CRUD class name:**

```bash
grep -n "class.*Table\|class.*s:" backend/open_webui/models/memories.py
grep -n "class.*Table\|class.*s:" backend/open_webui/models/tools.py
# etc.
```

**Run existing tests after each model to catch regressions:**

```bash
cd backend
pytest open_webui/test/ -v -x  # -x stops on first failure
```

**Commit after all are done:**

```bash
git add backend/open_webui/models/ backend/open_webui/routers/
git commit -m "feat: scope all remaining CRUD and routes by tenant_id"
```

---

## Phase 6: Frontend Admin UI

### Task 10: Add Tenants API client

**Files:**
- Create: `src/lib/apis/tenants.ts`

**Step 1: Create the API client**

```typescript
// src/lib/apis/tenants.ts

export type Tenant = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  settings: Record<string, unknown> | null;
  created_at: number;
};

export type TenantForm = {
  name: string;
  slug: string;
  settings?: Record<string, unknown>;
};

export type TenantUpdateForm = {
  name?: string;
  is_active?: boolean;
  settings?: Record<string, unknown>;
};

export const getTenants = async (token: string): Promise<Tenant[]> => {
  const res = await fetch('/api/v1/tenants/', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch tenants');
  return res.json();
};

export const createTenant = async (
  token: string,
  form: TenantForm
): Promise<Tenant> => {
  const res = await fetch('/api/v1/tenants/', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(form),
  });
  if (!res.ok) throw new Error('Failed to create tenant');
  return res.json();
};

export const updateTenant = async (
  token: string,
  tenantId: string,
  form: TenantUpdateForm
): Promise<Tenant> => {
  const res = await fetch(`/api/v1/tenants/${tenantId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(form),
  });
  if (!res.ok) throw new Error('Failed to update tenant');
  return res.json();
};

export const getTenantUsers = async (
  token: string,
  tenantId: string
): Promise<unknown[]> => {
  const res = await fetch(`/api/v1/tenants/${tenantId}/users`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch tenant users');
  return res.json();
};

export const addTenantUser = async (
  token: string,
  tenantId: string,
  form: { email: string; name: string; password: string; role?: string }
): Promise<unknown> => {
  const res = await fetch(`/api/v1/tenants/${tenantId}/users`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(form),
  });
  if (!res.ok) throw new Error('Failed to add user');
  return res.json();
};
```

**Step 2: Run type check**

```bash
npm run check
```

Expected: No errors in `tenants.ts`

**Step 3: Commit**

```bash
git add src/lib/apis/tenants.ts
git commit -m "feat: add tenants API client"
```

---

### Task 11: Add Tenants admin page

**Files:**
- Create: `src/routes/(app)/admin/tenants/+page.svelte`
- Create: `src/routes/(app)/admin/tenants/[id]/+page.svelte`

**Step 1: Check how existing admin pages are structured**

```bash
ls src/routes/\(app\)/admin/
cat src/routes/\(app\)/admin/users/+page.svelte | head -60
```

**Step 2: Create the tenants list page**

```svelte
<!-- src/routes/(app)/admin/tenants/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import { getTenants, createTenant, updateTenant } from '$lib/apis/tenants';
  import type { Tenant } from '$lib/apis/tenants';

  let tenants: Tenant[] = [];
  let loading = true;
  let showCreateForm = false;
  let newName = '';
  let newSlug = '';
  let error = '';

  onMount(async () => {
    if (!$user?.is_super_admin) {
      goto('/');
      return;
    }
    await loadTenants();
  });

  async function loadTenants() {
    try {
      tenants = await getTenants(localStorage.token);
    } catch (e) {
      error = 'Failed to load tenants';
    } finally {
      loading = false;
    }
  }

  async function handleCreate() {
    if (!newName || !newSlug) return;
    try {
      await createTenant(localStorage.token, { name: newName, slug: newSlug });
      newName = '';
      newSlug = '';
      showCreateForm = false;
      await loadTenants();
    } catch (e) {
      error = 'Failed to create tenant';
    }
  }

  async function toggleActive(tenant: Tenant) {
    try {
      await updateTenant(localStorage.token, tenant.id, {
        is_active: !tenant.is_active,
      });
      await loadTenants();
    } catch (e) {
      error = 'Failed to update tenant';
    }
  }

  function slugify(name: string) {
    return name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  }
</script>

<div class="p-6 max-w-5xl mx-auto">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-bold">Tenants</h1>
    <button
      class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      on:click={() => (showCreateForm = !showCreateForm)}
    >
      + New Tenant
    </button>
  </div>

  {#if error}
    <div class="mb-4 p-3 bg-red-100 text-red-700 rounded">{error}</div>
  {/if}

  {#if showCreateForm}
    <div class="mb-6 p-4 border rounded bg-gray-50 dark:bg-gray-800">
      <h2 class="font-semibold mb-3">Create Tenant</h2>
      <div class="flex gap-3 flex-wrap">
        <input
          bind:value={newName}
          on:input={() => (newSlug = slugify(newName))}
          placeholder="Tenant name"
          class="border rounded px-3 py-2 flex-1"
        />
        <input
          bind:value={newSlug}
          placeholder="slug (auto-filled)"
          class="border rounded px-3 py-2 flex-1"
        />
        <button
          class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          on:click={handleCreate}
        >
          Create
        </button>
      </div>
    </div>
  {/if}

  {#if loading}
    <p class="text-gray-500">Loading...</p>
  {:else if tenants.length === 0}
    <p class="text-gray-500">No tenants yet. Create your first one above.</p>
  {:else}
    <table class="w-full border-collapse">
      <thead>
        <tr class="border-b text-left text-sm text-gray-500">
          <th class="py-2 pr-4">Name</th>
          <th class="py-2 pr-4">Slug</th>
          <th class="py-2 pr-4">Status</th>
          <th class="py-2 pr-4">Created</th>
          <th class="py-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each tenants as tenant}
          <tr class="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
            <td class="py-3 pr-4 font-medium">{tenant.name}</td>
            <td class="py-3 pr-4 text-gray-500 text-sm">{tenant.slug}</td>
            <td class="py-3 pr-4">
              <span
                class="px-2 py-1 text-xs rounded-full {tenant.is_active
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-500'}"
              >
                {tenant.is_active ? 'Active' : 'Inactive'}
              </span>
            </td>
            <td class="py-3 pr-4 text-sm text-gray-500">
              {new Date(tenant.created_at * 1000).toLocaleDateString()}
            </td>
            <td class="py-3 flex gap-2">
              <a
                href="/admin/tenants/{tenant.id}"
                class="text-sm text-blue-600 hover:underline"
              >
                Manage
              </a>
              <button
                class="text-sm text-gray-500 hover:underline"
                on:click={() => toggleActive(tenant)}
              >
                {tenant.is_active ? 'Deactivate' : 'Activate'}
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>
```

**Step 3: Create the tenant detail page**

```svelte
<!-- src/routes/(app)/admin/tenants/[id]/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { user } from '$lib/stores';
  import { goto } from '$app/navigation';
  import { getTenantUsers, addTenantUser } from '$lib/apis/tenants';

  let tenantId = $page.params.id;
  let users: any[] = [];
  let loading = true;
  let showAddUser = false;
  let newEmail = '';
  let newName = '';
  let newPassword = '';
  let newRole = 'user';
  let error = '';

  onMount(async () => {
    if (!$user?.is_super_admin) {
      goto('/');
      return;
    }
    await loadUsers();
  });

  async function loadUsers() {
    try {
      users = await getTenantUsers(localStorage.token, tenantId);
    } catch (e) {
      error = 'Failed to load users';
    } finally {
      loading = false;
    }
  }

  async function handleAddUser() {
    if (!newEmail || !newName || !newPassword) return;
    try {
      await addTenantUser(localStorage.token, tenantId, {
        email: newEmail,
        name: newName,
        password: newPassword,
        role: newRole,
      });
      newEmail = '';
      newName = '';
      newPassword = '';
      showAddUser = false;
      await loadUsers();
    } catch (e) {
      error = 'Failed to add user';
    }
  }
</script>

<div class="p-6 max-w-4xl mx-auto">
  <a href="/admin/tenants" class="text-sm text-gray-500 hover:underline mb-4 block">
    ← Back to Tenants
  </a>

  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-bold">Tenant Users</h1>
    <button
      class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      on:click={() => (showAddUser = !showAddUser)}
    >
      + Add User
    </button>
  </div>

  {#if error}
    <div class="mb-4 p-3 bg-red-100 text-red-700 rounded">{error}</div>
  {/if}

  {#if showAddUser}
    <div class="mb-6 p-4 border rounded bg-gray-50 dark:bg-gray-800 space-y-3">
      <h2 class="font-semibold">Add User to Tenant</h2>
      <div class="grid grid-cols-2 gap-3">
        <input bind:value={newName} placeholder="Full name" class="border rounded px-3 py-2" />
        <input bind:value={newEmail} placeholder="Email" type="email" class="border rounded px-3 py-2" />
        <input bind:value={newPassword} placeholder="Password" type="password" class="border rounded px-3 py-2" />
        <select bind:value={newRole} class="border rounded px-3 py-2">
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <button
        class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        on:click={handleAddUser}
      >
        Add User
      </button>
    </div>
  {/if}

  {#if loading}
    <p class="text-gray-500">Loading users...</p>
  {:else if users.length === 0}
    <p class="text-gray-500">No users in this tenant yet.</p>
  {:else}
    <table class="w-full border-collapse">
      <thead>
        <tr class="border-b text-left text-sm text-gray-500">
          <th class="py-2 pr-4">Name</th>
          <th class="py-2 pr-4">Email</th>
          <th class="py-2">Role</th>
        </tr>
      </thead>
      <tbody>
        {#each users as u}
          <tr class="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
            <td class="py-3 pr-4">{u.name}</td>
            <td class="py-3 pr-4 text-gray-500">{u.email}</td>
            <td class="py-3">
              <span class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600">{u.role}</span>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>
```

**Step 4: Run type check**

```bash
npm run check
```

Expected: No errors in new files.

**Step 5: Commit**

```bash
git add src/routes/\(app\)/admin/tenants/
git commit -m "feat: add Tenants admin pages (list + detail)"
```

---

### Task 12: Add Tenants link to admin navigation

**Files:**
- Modify: the admin sidebar/nav component (check `src/lib/components/admin/` for the nav file)

**Step 1: Find the admin nav file**

```bash
ls src/lib/components/admin/
grep -rn "Users\|Settings\|href.*admin" src/lib/components/admin/ | grep -i "nav\|side\|menu" | head -10
```

**Step 2: Add the Tenants nav entry**

Find where `/admin/users` is linked and add a Tenants entry immediately after it using the same pattern as the existing items.

**Step 3: Verify it renders**

```bash
npm run dev
# Open http://localhost:5173/admin — confirm "Tenants" appears in nav
# It should only be visible when user.is_super_admin is true
```

**Step 4: Guard the nav item**

Wrap the Tenants link with `{#if $user?.is_super_admin}...{/if}` so it only shows for super admins.

**Step 5: Commit**

```bash
git add src/lib/components/admin/
git commit -m "feat: add Tenants link to admin navigation (super admin only)"
```

---

## Phase 7: Railway Configuration

### Task 13: Configure for Railway deployment

**Files:**
- Modify: `.env.example`
- Create: `railway.json`

**Step 1: Update `.env.example`**

Add the new required variables:

```bash
# .env.example additions — add after existing entries:

# Multi-tenant configuration
# Set to false to disable self-registration (required for multi-tenant)
ENABLE_SIGNUP=false

# Automatic database migrations on startup
ENABLE_DB_MIGRATIONS=true

# PostgreSQL (Railway provides this automatically via DATABASE_URL)
# DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

**Step 2: Create `railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "bash start.sh",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

**Step 3: Set Railway environment variables**

In Railway dashboard → your service → Variables, set:

```
OPENAI_API_KEY          = sk-...
OPENAI_API_BASE_URL     = https://api.openai.com/v1
WEBUI_SECRET_KEY        = (generate: python -c "import secrets; print(secrets.token_hex(32))")
ENABLE_SIGNUP           = false
ENABLE_DB_MIGRATIONS    = true
CORS_ALLOW_ORIGIN       = https://yourdomain.com
```

`DATABASE_URL` is auto-injected by the Railway PostgreSQL plugin — do not set it manually.

**Step 4: Add Railway PostgreSQL plugin**

In Railway dashboard → your project → + New → Database → PostgreSQL.
Railway automatically sets `DATABASE_URL` as a shared variable.

**Step 5: Add Railway Volume**

In Railway dashboard → your service → Volumes → Add Volume:
- Mount path: `/app/backend/data`
- This persists uploaded files across deployments.

**Step 6: Deploy and verify**

```bash
git push origin main
# Railway auto-deploys on push

# After deploy completes, check logs in Railway dashboard:
# Should see: "Running upgrade ... -> a1b2c3d4e5f6"
# And: "Application startup complete"
```

**Step 7: Create the first super admin**

In Railway → your service → Shell (or via local `DATABASE_URL`):

```python
python -c "
from open_webui.models.auths import Auths
from open_webui.models.users import Users
from open_webui.utils.auth import get_password_hash

user = Auths.insert_new_auth(
    email='admin@youragency.com',
    password=get_password_hash('your-secure-password'),
    name='Agency Admin',
    role='admin',
)
Users.update_user_by_id(user.id, {'is_super_admin': True})
print(f'Super admin created: {user.id}')
"
```

**Step 8: Commit**

```bash
git add .env.example railway.json
git commit -m "chore: add Railway configuration and deployment instructions"
```

---

## Phase 8: End-to-End Smoke Test

### Task 14: Manual smoke test checklist

Run after deployment with a real PostgreSQL database.

**Create a tenant:**
- [ ] Log in as super admin
- [ ] Navigate to Admin → Tenants
- [ ] Create tenant "Test Client" with slug "test-client"
- [ ] Confirm tenant appears in list

**Add users to tenant:**
- [ ] Click Manage on "Test Client"
- [ ] Add a tenant admin user
- [ ] Add a regular tenant user

**Verify data isolation:**
- [ ] Log in as tenant user → can see only their chats
- [ ] Create a chat as tenant user
- [ ] Log in as a user from a different tenant (create a second tenant first)
- [ ] Confirm the second tenant cannot see the first tenant's chats

**Super admin override:**
- [ ] Log in as super admin
- [ ] Make API call with `X-Tenant-ID` header → confirm access to tenant data
- [ ] Remove header → confirm 403 response

**Run the full backend test suite:**

```bash
cd backend
pytest open_webui/test/ -v
```

Expected: All tests pass.

---

## Appendix: Key Files Reference

| Area | File |
|---|---|
| Tenant model | `backend/open_webui/models/tenants.py` |
| User model (modified) | `backend/open_webui/models/users.py` |
| Chat model (modified) | `backend/open_webui/models/chats.py` |
| Auth dependencies | `backend/open_webui/utils/auth.py` |
| Tenants router | `backend/open_webui/routers/tenants.py` |
| App entry point | `backend/open_webui/main.py` |
| Migration | `backend/open_webui/migrations/versions/a1b2c3d4e5f6_*.py` |
| Tenants API client | `src/lib/apis/tenants.ts` |
| Tenants admin page | `src/routes/(app)/admin/tenants/+page.svelte` |
| Tenant detail page | `src/routes/(app)/admin/tenants/[id]/+page.svelte` |
| Railway config | `railway.json` |
