from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException


class TestGetTenantContext:
    def test_returns_tenant_id_for_normal_user(self):
        from open_webui.utils.auth import get_tenant_context
        from open_webui.models.users import UserModel

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


class TestGetSuperAdminUser:
    def test_returns_user_if_super_admin(self):
        from open_webui.utils.auth import get_super_admin_user
        from open_webui.models.users import UserModel

        user = MagicMock(spec=UserModel)
        user.is_super_admin = True

        result = get_super_admin_user(user=user)
        assert result is user

    def test_raises_403_if_not_super_admin(self):
        from open_webui.utils.auth import get_super_admin_user
        from open_webui.models.users import UserModel

        user = MagicMock(spec=UserModel)
        user.is_super_admin = False

        with pytest.raises(HTTPException) as exc_info:
            get_super_admin_user(user=user)
        assert exc_info.value.status_code == 403
