"""
Permission Management Module Tests
Tests for role-based access control and permission checking
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.auth.permissions import (
    PermissionManager,
    Role,
    Permission,
    ROLE_PERMISSIONS,
    get_permission_manager,
    require_permission,
    require_role,
)


class TestPermissionManager:
    """Tests for PermissionManager class."""
    
    def setup_method(self):
        """Get fresh permission manager instance."""
        self.manager = get_permission_manager()
        # Clear any existing data for test users
        for uid in range(1, 100):
            self.manager.clear_user(uid)
    
    def teardown_method(self):
        """Clean up after tests."""
        for uid in range(1, 100):
            self.manager.clear_user(uid)


class TestRolePermissions:
    """Tests for default role permissions."""
    
    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        
        # Admin should have key permissions
        assert Permission.USER_CREATE in admin_perms
        assert Permission.USER_DELETE in admin_perms
        assert Permission.ADMIN_ACCESS in admin_perms
        assert Permission.SYSTEM_CONFIG in admin_perms
    
    def test_user_has_limited_permissions(self):
        """Test that user role has limited permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]
        
        # User should have basic permissions
        assert Permission.USER_READ in user_perms
        assert Permission.USER_UPDATE in user_perms
        assert Permission.API_READ in user_perms
        assert Permission.API_WRITE in user_perms
        
        # User should NOT have admin permissions
        assert Permission.ADMIN_ACCESS not in user_perms
        assert Permission.USER_DELETE not in user_perms
    
    def test_readonly_has_read_only(self):
        """Test that readonly role has only read permissions."""
        readonly_perms = ROLE_PERMISSIONS[Role.READONLY]
        
        # Readonly should have read permissions
        assert Permission.USER_READ in readonly_perms
        assert Permission.API_READ in readonly_perms
        assert Permission.DATA_READ in readonly_perms
        
        # Readonly should NOT have write permissions
        assert Permission.USER_CREATE not in readonly_perms
        assert Permission.API_WRITE not in readonly_perms
        assert Permission.DATA_WRITE not in readonly_perms


class TestCheckPermission:
    """Tests for permission checking."""
    
    def test_check_permission_with_role(self):
        """Test checking permission based on user role."""
        manager = get_permission_manager()
        
        # Assign admin role to user
        manager.assign_role(1, "admin")
        
        user = {"id": 1, "role": "admin"}
        
        # Admin should have admin access
        assert manager.check_permission(user, "admin:access") is True
        
        # Admin should have user read
        assert manager.check_permission(user, "user:read") is True
    
    def test_check_permission_with_explicit_permission(self):
        """Test checking explicitly assigned permission."""
        manager = get_permission_manager()
        
        # Assign specific permission to user
        manager.assign_permission(2, "user:read")
        
        user = {"id": 2}
        
        # Should have explicitly granted permission
        assert manager.check_permission(user, "user:read") is True
        
        # Should NOT have other permissions
        assert manager.check_permission(user, "user:write") is False
    
    def test_check_permission_without_any_permissions(self):
        """Test that user without permissions is denied."""
        manager = get_permission_manager()
        
        user = {"id": 999}
        
        # User with no role or permissions should be denied
        assert manager.check_permission(user, "admin:access") is False
        assert manager.check_permission(user, "user:read") is False
    
    def test_check_permission_invalid_user(self):
        """Test checking permission for invalid user."""
        manager = get_permission_manager()
        
        user = {"id": None}
        
        assert manager.check_permission(user, "user:read") is False
    
    def test_check_permission_invalid_permission(self):
        """Test checking invalid permission string."""
        manager = get_permission_manager()
        
        user = {"id": 1, "role": "admin"}
        
        # Invalid permission should be denied
        assert manager.check_permission(user, "invalid:permission") is False
    
    def test_check_permission_with_user_dict_role(self):
        """Test checking permission using role from user dict."""
        manager = get_permission_manager()
        
        # Use a fresh user ID and ensure no explicit permissions
        manager.clear_user(50)
        
        # Don't assign role in manager, use user dict
        user = {"id": 50, "role": "readonly"}
        
        # Should have readonly permissions
        assert manager.check_permission(user, "user:read") is True
        assert manager.check_permission(user, "api:read") is True
        
        # Should NOT have write permissions
        assert manager.check_permission(user, "api:write") is False


class TestAssignPermission:
    """Tests for assigning permissions."""
    
    def test_assign_permission_success(self):
        """Test successfully assigning a permission."""
        manager = get_permission_manager()
        
        result = manager.assign_permission(1, "user:read")
        
        assert result is True
        
        # Verify permission was assigned
        permissions = manager.get_user_permissions(1)
        assert "user:read" in permissions
    
    def test_assign_permission_invalid(self):
        """Test assigning invalid permission."""
        manager = get_permission_manager()
        
        result = manager.assign_permission(1, "invalid:permission")
        
        assert result is False
    
    def test_assign_multiple_permissions(self):
        """Test assigning multiple permissions to same user."""
        manager = get_permission_manager()
        
        # Use a fresh user ID
        manager.clear_user(51)
        
        manager.assign_permission(51, "user:read")
        manager.assign_permission(51, "data:write")  # Use valid permission
        manager.assign_permission(51, "api:read")
        
        permissions = manager.get_user_permissions(51)
        
        assert "user:read" in permissions
        assert "data:write" in permissions
        assert "api:read" in permissions


class TestRevokePermission:
    """Tests for revoking permissions."""
    
    def test_revoke_permission_success(self):
        """Test successfully revoking a permission."""
        manager = get_permission_manager()
        
        # Use a fresh user ID with no role
        manager.clear_user(52)
        
        # First assign permission
        manager.assign_permission(52, "user:read")
        assert manager.check_permission({"id": 52}, "user:read") is True
        
        # Revoke it
        result = manager.revoke_permission(52, "user:read")
        
        assert result is True
        
        # Verify permission was revoked
        assert manager.check_permission({"id": 52}, "user:read") is False
    
    def test_revoke_permission_not_assigned(self):
        """Test revoking permission that wasn't assigned."""
        manager = get_permission_manager()
        
        result = manager.revoke_permission(1, "user:read")
        
        # Should return True (idempotent operation)
        assert result is True
    
    def test_revoke_permission_invalid(self):
        """Test revoking invalid permission."""
        manager = get_permission_manager()
        
        result = manager.revoke_permission(1, "invalid:permission")
        
        assert result is False


class TestAssignRole:
    """Tests for assigning roles."""
    
    def test_assign_role_success(self):
        """Test successfully assigning a role."""
        manager = get_permission_manager()
        
        result = manager.assign_role(1, "admin")
        
        assert result is True
        
        # Verify role was assigned
        role = manager.get_user_role(1)
        assert role == "admin"
    
    def test_assign_role_invalid(self):
        """Test assigning invalid role."""
        manager = get_permission_manager()
        
        result = manager.assign_role(1, "invalid_role")
        
        assert result is False
    
    def test_assign_role_grants_permissions(self):
        """Test that assigning role grants appropriate permissions."""
        manager = get_permission_manager()
        
        manager.assign_role(1, "admin")
        
        user = {"id": 1}
        
        # Should have admin permissions
        assert manager.check_permission(user, "admin:access") is True
        assert manager.check_permission(user, "user:create") is True
    
    def test_change_role(self):
        """Test changing user's role."""
        manager = get_permission_manager()
        
        # Start with readonly
        manager.assign_role(1, "readonly")
        assert manager.get_user_role(1) == "readonly"
        
        # Change to admin
        manager.assign_role(1, "admin")
        assert manager.get_user_role(1) == "admin"


class TestRevokeRole:
    """Tests for revoking roles."""
    
    def test_revoke_role_success(self):
        """Test successfully revoking a role."""
        manager = get_permission_manager()
        
        # Assign role first
        manager.assign_role(1, "admin")
        assert manager.get_user_role(1) == "admin"
        
        # Revoke it
        result = manager.revoke_role(1)
        
        assert result is True
        
        # Verify role was revoked
        assert manager.get_user_role(1) is None
    
    def test_revoke_role_not_assigned(self):
        """Test revoking role that wasn't assigned."""
        manager = get_permission_manager()
        
        result = manager.revoke_role(1)
        
        # Should return False (no role to revoke)
        assert result is False


class TestHasRole:
    """Tests for role checking."""
    
    def test_has_role_true(self):
        """Test has_role returns True for assigned role."""
        manager = get_permission_manager()
        
        manager.assign_role(1, "admin")
        
        assert manager.has_role(1, "admin") is True
    
    def test_has_role_false(self):
        """Test has_role returns False for different role."""
        manager = get_permission_manager()
        
        manager.assign_role(1, "user")
        
        assert manager.has_role(1, "admin") is False
    
    def test_has_role_not_assigned(self):
        """Test has_role returns False for no role."""
        manager = get_permission_manager()
        
        assert manager.has_role(1, "admin") is False


class TestPermissionDecorators:
    """Tests for permission decorators."""
    
    def test_require_permission_success(self):
        """Test require_permission decorator allows access."""
        manager = get_permission_manager()
        manager.assign_permission(1, "user:read")
        
        @require_permission("user:read")
        def protected_function(user):
            return "access granted"
        
        user = {"id": 1}
        result = protected_function(user)
        
        assert result == "access granted"
    
    def test_require_permission_failure(self):
        """Test require_permission decorator denies access."""
        manager = get_permission_manager()
        
        @require_permission("admin:access")
        def protected_function(user):
            return "access granted"
        
        user = {"id": 1}  # No permissions
        
        with pytest.raises(PermissionError):
            protected_function(user)
    
    def test_require_role_success(self):
        """Test require_role decorator allows access."""
        manager = get_permission_manager()
        manager.assign_role(1, "admin")
        
        @require_role("admin")
        def admin_function(user):
            return "admin access granted"
        
        user = {"id": 1}
        result = admin_function(user)
        
        assert result == "admin access granted"
    
    def test_require_role_failure(self):
        """Test require_role decorator denies access."""
        manager = get_permission_manager()
        
        # Ensure user has no role
        manager.clear_user(53)
        
        @require_role("admin")
        def admin_function(user):
            return "admin access granted"
        
        user = {"id": 53}  # No role
        
        with pytest.raises(PermissionError):
            admin_function(user)


class TestPermissionManagerSingleton:
    """Tests for PermissionManager singleton behavior."""
    
    def test_singleton_instance(self):
        """Test that get_permission_manager returns same instance."""
        manager1 = get_permission_manager()
        manager2 = get_permission_manager()
        
        assert manager1 is manager2
    
    def test_singleton_state_persistence(self):
        """Test that singleton maintains state."""
        manager1 = get_permission_manager()
        manager2 = get_permission_manager()
        
        # Modify state through first instance
        manager1.assign_permission(1, "user:read")
        
        # Second instance should see the change
        permissions = manager2.get_user_permissions(1)
        assert "user:read" in permissions


class TestGetUserPermissions:
    """Tests for getting user permissions."""
    
    def test_get_user_permissions_explicit(self):
        """Test getting explicitly assigned permissions."""
        manager = get_permission_manager()
        
        manager.assign_permission(1, "user:read")
        manager.assign_permission(1, "api:write")
        
        permissions = manager.get_user_permissions(1)
        
        assert "user:read" in permissions
        assert "api:write" in permissions
    
    def test_get_user_permissions_from_role(self):
        """Test getting permissions from role."""
        manager = get_permission_manager()
        
        manager.assign_role(1, "readonly")
        
        permissions = manager.get_user_permissions(1)
        
        assert "user:read" in permissions
        assert "api:read" in permissions
    
    def test_get_user_permissions_combined(self):
        """Test getting combined permissions from role and explicit."""
        manager = get_permission_manager()
        
        # Give user role
        manager.assign_role(1, "readonly")
        
        # Also give explicit permission
        manager.assign_permission(1, "api:write")
        
        permissions = manager.get_user_permissions(1)
        
        # Should have both role-based and explicit
        assert "user:read" in permissions  # From readonly role
        assert "api:read" in permissions   # From readonly role
        assert "api:write" in permissions  # Explicit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
