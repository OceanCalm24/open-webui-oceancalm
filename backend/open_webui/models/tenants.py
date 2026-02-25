import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, JSON, String

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
