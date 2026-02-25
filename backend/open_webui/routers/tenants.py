import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.models.tenants import TenantForm, TenantModel, TenantTable, TenantUpdateForm
from open_webui.models.users import UserModel, Users
from open_webui.utils.auth import get_super_admin_user

log = logging.getLogger(__name__)
router = APIRouter()


####################
# Tenant CRUD
####################


@router.get("/", response_model=list[TenantModel])
async def list_tenants(user=Depends(get_super_admin_user)):
    return TenantTable().get_all_tenants()


@router.post("/", response_model=TenantModel)
async def create_tenant(form: TenantForm, user=Depends(get_super_admin_user)):
    existing = TenantTable().get_tenant_by_slug(form.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with slug '{form.slug}' already exists",
        )
    tenant = TenantTable().create_tenant(form)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant",
        )
    return tenant


@router.get("/{tenant_id}", response_model=TenantModel)
async def get_tenant(tenant_id: str, user=Depends(get_super_admin_user)):
    tenant = TenantTable().get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantModel)
async def update_tenant(
    tenant_id: str, form: TenantUpdateForm, user=Depends(get_super_admin_user)
):
    tenant = TenantTable().update_tenant(tenant_id, form)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str, user=Depends(get_super_admin_user)):
    success = TenantTable().delete_tenant(tenant_id)
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
    role: str = "user"


@router.get("/{tenant_id}/users")
async def list_tenant_users(tenant_id: str, user=Depends(get_super_admin_user)):
    return Users.get_users_by_tenant_id(tenant_id)


@router.post("/{tenant_id}/users")
async def add_tenant_user(
    tenant_id: str, form: AddTenantUserForm, user=Depends(get_super_admin_user)
):
    tenant = TenantTable().get_tenant_by_id(tenant_id)
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

    Users.update_user_tenant(new_user.id, tenant_id)
    return Users.get_user_by_id(new_user.id)


@router.delete("/{tenant_id}/users/{user_id}")
async def remove_tenant_user(
    tenant_id: str, user_id: str, admin=Depends(get_super_admin_user)
):
    u = Users.get_user_by_id(user_id)
    if not u or u.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="User not found in this tenant")
    Users.update_user_tenant(user_id, None)
    return {"success": True}


####################
# Agency Team (Super Admin) Management
####################


class AgencyUserForm(BaseModel):
    email: str


@router.get("/agency/users")
async def list_agency_users(admin=Depends(get_super_admin_user)):
    """List all super admins (agency team members)."""
    all_users = Users.get_users()
    return [u for u in all_users if getattr(u, "is_super_admin", False)]


@router.post("/agency/users")
async def add_agency_user(form: AgencyUserForm, admin=Depends(get_super_admin_user)):
    """Promote an existing user to super admin."""
    user = Users.get_user_by_email(form.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = Users.update_user_by_id(user.id, {"is_super_admin": True, "tenant_id": None})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update user")
    return updated


@router.delete("/agency/users/{user_id}")
async def remove_agency_user(user_id: str, admin=Depends(get_super_admin_user)):
    """Demote a super admin back to regular user."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot remove your own super admin status")
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = Users.update_user_by_id(user_id, {"is_super_admin": False})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update user")
    return {"success": True}
