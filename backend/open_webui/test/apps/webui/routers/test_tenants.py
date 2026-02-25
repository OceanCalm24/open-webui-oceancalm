import uuid

import pytest


class TestTenantModel:
    def test_create_tenant(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        slug_suffix = str(uuid.uuid4())[:8]
        tenant = TenantTable().create_tenant(
            TenantForm(name="Acme Corp", slug=f"acme-corp-{slug_suffix}")
        )
        assert tenant is not None
        assert tenant.name == "Acme Corp"
        assert tenant.slug == f"acme-corp-{slug_suffix}"
        assert tenant.is_active is True

    def test_get_tenant_by_id(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        slug_suffix = str(uuid.uuid4())[:8]
        created = TenantTable().create_tenant(
            TenantForm(name="Beta Inc", slug=f"beta-inc-{slug_suffix}")
        )
        fetched = TenantTable().get_tenant_by_id(created.id)
        assert fetched.id == created.id
        assert fetched.slug == f"beta-inc-{slug_suffix}"

    def test_get_all_tenants(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        slug_suffix = str(uuid.uuid4())[:8]
        TenantTable().create_tenant(TenantForm(name="T1", slug=f"t1-{slug_suffix}"))
        TenantTable().create_tenant(TenantForm(name="T2", slug=f"t2-{slug_suffix}"))
        tenants = TenantTable().get_all_tenants()
        assert len(tenants) >= 2

    def test_slug_must_be_unique(self):
        from open_webui.models.tenants import TenantTable, TenantForm

        slug_suffix = str(uuid.uuid4())[:8]
        TenantTable().create_tenant(
            TenantForm(name="Dup", slug=f"dup-slug-{slug_suffix}")
        )
        result = TenantTable().create_tenant(
            TenantForm(name="Dup2", slug=f"dup-slug-{slug_suffix}")
        )
        assert result is None

    def test_user_has_tenant_id_field(self):
        from open_webui.models.users import UserModel

        fields = UserModel.model_fields
        assert "tenant_id" in fields
        assert "is_super_admin" in fields
