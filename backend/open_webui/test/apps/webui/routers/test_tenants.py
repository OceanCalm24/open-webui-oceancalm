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

    def test_chat_has_tenant_id_field(self):
        from open_webui.models.chats import Chat
        from sqlalchemy import inspect

        mapper = inspect(Chat)
        col_names = [c.key for c in mapper.columns]
        assert "tenant_id" in col_names

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

    def test_chat_scoping_methods_accept_tenant_id(self):
        """Verify Chat CRUD methods accept tenant_id parameter."""
        import inspect
        from open_webui.models.chats import Chats

        # insert_new_chat should accept tenant_id
        sig = inspect.signature(Chats.insert_new_chat)
        assert "tenant_id" in sig.parameters, "insert_new_chat missing tenant_id param"

        # get_chat_title_id_list_by_user_id should accept tenant_id
        sig2 = inspect.signature(Chats.get_chat_title_id_list_by_user_id)
        assert "tenant_id" in sig2.parameters, "get_chat_title_id_list_by_user_id missing tenant_id param"

        # get_chats_by_user_id should accept tenant_id
        sig3 = inspect.signature(Chats.get_chats_by_user_id)
        assert "tenant_id" in sig3.parameters, "get_chats_by_user_id missing tenant_id param"

        print("Chat CRUD methods accept tenant_id: OK")
