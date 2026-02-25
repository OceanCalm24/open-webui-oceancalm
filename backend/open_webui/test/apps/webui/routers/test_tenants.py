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
