"""
Structural tests for the tenants router.
These tests verify the router module is correctly structured without requiring
a live database connection.
"""
import pytest


class TestTenantsRouterStructure:
    def test_router_is_importable(self):
        """Verify the router module imports without errors."""
        from open_webui.routers.tenants import router
        assert router is not None

    def test_router_has_correct_routes(self):
        """Verify all expected routes are registered."""
        from open_webui.routers.tenants import router

        routes = {(r.path, list(r.methods)) for r in router.routes}

        # Check all expected paths exist
        paths = {r.path for r in router.routes}
        assert "/" in paths
        assert "/{tenant_id}" in paths
        assert "/{tenant_id}/users" in paths
        assert "/{tenant_id}/users/{user_id}" in paths

    def test_users_model_has_get_users_by_tenant_id(self):
        """Verify Users model has the new method."""
        from open_webui.models.users import Users
        assert hasattr(Users, "get_users_by_tenant_id")
        assert callable(Users.get_users_by_tenant_id)

    def test_users_model_has_update_user_tenant(self):
        """Verify Users model has the new method."""
        from open_webui.models.users import Users
        assert hasattr(Users, "update_user_tenant")
        assert callable(Users.update_user_tenant)

    def test_router_endpoints_use_super_admin_dependency(self):
        """Verify all tenant routes are protected by get_super_admin_user."""
        from open_webui.routers.tenants import router
        from open_webui.utils.auth import get_super_admin_user

        for route in router.routes:
            dep_funcs = [d.dependency for d in route.dependencies]
            assert get_super_admin_user in dep_funcs, \
                f"Route {route.path} missing get_super_admin_user dependency"
