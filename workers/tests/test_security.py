import pytest
import time
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.utils.security import (
    RBACManager, AuditLogger, DataProtection, JWTManager, 
    SignedURLManager, SecurityMiddleware, Permission, Role
)


class TestRBACManager:
    """Test RBAC functionality."""
    
    @pytest.fixture
    def rbac_manager(self):
        return RBACManager()
    
    def test_viewer_permissions(self, rbac_manager):
        """Test viewer role permissions."""
        viewer_permissions = rbac_manager.get_user_permissions(Role.VIEWER)
        
        assert Permission.READ_PATENT in viewer_permissions
        assert Permission.SEARCH_PATENTS in viewer_permissions
        assert Permission.WRITE_PATENT not in viewer_permissions
        assert Permission.DELETE_PATENT not in viewer_permissions
    
    def test_analyst_permissions(self, rbac_manager):
        """Test analyst role permissions."""
        analyst_permissions = rbac_manager.get_user_permissions(Role.ANALYST)
        
        assert Permission.READ_PATENT in analyst_permissions
        assert Permission.WRITE_PATENT in analyst_permissions
        assert Permission.SEARCH_PATENTS in analyst_permissions
        assert Permission.CREATE_ALIGNMENT in analyst_permissions
        assert Permission.CALCULATE_NOVELTY in analyst_permissions
        assert Permission.GENERATE_CHART in analyst_permissions
        assert Permission.EXPORT_DATA in analyst_permissions
        assert Permission.MANAGE_USERS not in analyst_permissions
    
    def test_admin_permissions(self, rbac_manager):
        """Test admin role permissions."""
        admin_permissions = rbac_manager.get_user_permissions(Role.ADMIN)
        
        assert Permission.READ_PATENT in admin_permissions
        assert Permission.WRITE_PATENT in admin_permissions
        assert Permission.DELETE_PATENT in admin_permissions
        assert Permission.MANAGE_USERS in admin_permissions
        assert Permission.MANAGE_WORKSPACE in admin_permissions
        assert Permission.VIEW_AUDIT_LOGS in admin_permissions
    
    def test_has_permission(self, rbac_manager):
        """Test permission checking."""
        assert rbac_manager.has_permission(Role.VIEWER, Permission.READ_PATENT)
        assert not rbac_manager.has_permission(Role.VIEWER, Permission.WRITE_PATENT)
        assert rbac_manager.has_permission(Role.ADMIN, Permission.MANAGE_USERS)
    
    def test_validate_access(self, rbac_manager):
        """Test access validation."""
        # Viewer should have access to read operations
        assert rbac_manager.validate_access(Role.VIEWER, [Permission.READ_PATENT])
        
        # Viewer should not have access to write operations
        assert not rbac_manager.validate_access(Role.VIEWER, [Permission.WRITE_PATENT])
        
        # Analyst should have access to analysis operations
        assert rbac_manager.validate_access(Role.ANALYST, [
            Permission.READ_PATENT,
            Permission.CREATE_ALIGNMENT,
            Permission.CALCULATE_NOVELTY
        ])
        
        # Admin should have access to all operations
        assert rbac_manager.validate_access(Role.ADMIN, [
            Permission.READ_PATENT,
            Permission.WRITE_PATENT,
            Permission.DELETE_PATENT,
            Permission.MANAGE_USERS
        ])


class TestJWTManager:
    """Test JWT token management."""
    
    @pytest.fixture
    def jwt_manager(self):
        return JWTManager("test-secret-key")
    
    def test_create_token(self, jwt_manager):
        """Test JWT token creation."""
        token = jwt_manager.create_token(
            user_id="user123",
            workspace_id="workspace456",
            role=Role.ANALYST,
            expires_in=3600
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self, jwt_manager):
        """Test valid token verification."""
        token = jwt_manager.create_token(
            user_id="user123",
            workspace_id="workspace456",
            role=Role.ANALYST
        )
        
        payload = jwt_manager.verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["workspace_id"] == "workspace456"
        assert payload["role"] == Role.ANALYST.value
    
    def test_verify_expired_token(self, jwt_manager):
        """Test expired token verification."""
        # Create token with very short expiration
        token = jwt_manager.create_token(
            user_id="user123",
            workspace_id="workspace456",
            role=Role.ANALYST,
            expires_in=1  # 1 second
        )
        
        # Wait for token to expire
        time.sleep(2)
        
        payload = jwt_manager.verify_token(token)
        assert payload is None
    
    def test_verify_invalid_token(self, jwt_manager):
        """Test invalid token verification."""
        # Invalid token
        payload = jwt_manager.verify_token("invalid.token.here")
        assert payload is None
        
        # Tampered token
        token = jwt_manager.create_token(
            user_id="user123",
            workspace_id="workspace456",
            role=Role.ANALYST
        )
        tampered_token = token[:-5] + "XXXXX"
        payload = jwt_manager.verify_token(tampered_token)
        assert payload is None
    
    def test_refresh_token(self, jwt_manager):
        """Test token refresh."""
        original_token = jwt_manager.create_token(
            user_id="user123",
            workspace_id="workspace456",
            role=Role.ANALYST,
            expires_in=3600
        )
        
        refreshed_token = jwt_manager.refresh_token(original_token, expires_in=7200)
        
        assert refreshed_token is not None
        assert refreshed_token != original_token
        
        # Verify refreshed token
        payload = jwt_manager.verify_token(refreshed_token)
        assert payload is not None
        assert payload["user_id"] == "user123"


class TestDataProtection:
    """Test data protection utilities."""
    
    @pytest.fixture
    def data_protection(self):
        # Generate a test encryption key
        import base64
        key = base64.b64encode(b"test-encryption-key-32-bytes-long!")
        return DataProtection(key.decode())
    
    def test_encrypt_decrypt(self, data_protection):
        """Test data encryption and decryption."""
        original_data = "sensitive information"
        
        # Encrypt
        encrypted_data = data_protection.encrypt_data(original_data)
        assert encrypted_data != original_data
        assert isinstance(encrypted_data, str)
        
        # Decrypt
        decrypted_data = data_protection.decrypt_data(encrypted_data)
        assert decrypted_data == original_data
    
    def test_hash_data(self, data_protection):
        """Test data hashing."""
        original_data = "password123"
        
        # Hash with default salt
        hashed_data1 = data_protection.hash_data(original_data)
        assert ":" in hashed_data1  # Should contain salt:hash format
        
        # Hash with custom salt
        custom_salt = "custom_salt"
        hashed_data2 = data_protection.hash_data(original_data, custom_salt)
        assert hashed_data2.startswith(custom_salt + ":")
    
    def test_verify_hash(self, data_protection):
        """Test hash verification."""
        original_data = "password123"
        
        # Create hash
        hashed_data = data_protection.hash_data(original_data)
        
        # Verify correct data
        assert data_protection.verify_hash(original_data, hashed_data)
        
        # Verify incorrect data
        assert not data_protection.verify_hash("wrong_password", hashed_data)
    
    def test_encrypt_large_data(self, data_protection):
        """Test encryption of larger data."""
        large_data = "x" * 10000  # 10KB of data
        
        encrypted_data = data_protection.encrypt_data(large_data)
        decrypted_data = data_protection.decrypt_data(encrypted_data)
        
        assert decrypted_data == large_data


class TestSignedURLManager:
    """Test signed URL management."""
    
    @pytest.fixture
    def url_manager(self):
        return SignedURLManager("test-secret-key")
    
    def test_create_signed_url(self, url_manager):
        """Test signed URL creation."""
        original_url = "https://example.com/file.pdf"
        
        signed_url = url_manager.create_signed_url(original_url, expires_in=3600)
        
        assert signed_url != original_url
        assert "signature=" in signed_url
        assert "exp=" in signed_url
        assert original_url in signed_url
    
    def test_verify_valid_signed_url(self, url_manager):
        """Test valid signed URL verification."""
        original_url = "https://example.com/file.pdf"
        signed_url = url_manager.create_signed_url(original_url, expires_in=3600)
        
        result = url_manager.verify_signed_url(signed_url)
        
        assert result is not None
        assert result["url"] == original_url
        assert "permissions" in result
        assert "expires_at" in result
    
    def test_verify_expired_signed_url(self, url_manager):
        """Test expired signed URL verification."""
        original_url = "https://example.com/file.pdf"
        signed_url = url_manager.create_signed_url(original_url, expires_in=1)  # 1 second
        
        # Wait for URL to expire
        time.sleep(2)
        
        result = url_manager.verify_signed_url(signed_url)
        assert result is None
    
    def test_verify_invalid_signed_url(self, url_manager):
        """Test invalid signed URL verification."""
        # URL without signature
        result = url_manager.verify_signed_url("https://example.com/file.pdf")
        assert result is None
        
        # URL with invalid signature
        invalid_url = "https://example.com/file.pdf?signature=invalid&exp=1234567890"
        result = url_manager.verify_signed_url(invalid_url)
        assert result is None
    
    def test_signed_url_with_permissions(self, url_manager):
        """Test signed URL with custom permissions."""
        original_url = "https://example.com/file.pdf"
        permissions = ["read", "write"]
        
        signed_url = url_manager.create_signed_url(
            original_url, 
            expires_in=3600, 
            permissions=permissions
        )
        
        result = url_manager.verify_signed_url(signed_url)
        assert result is not None
        assert result["url"] == original_url


class TestSecurityMiddleware:
    """Test security middleware."""
    
    @pytest.fixture
    def security_middleware(self):
        rbac_manager = RBACManager()
        jwt_manager = JWTManager("test-secret-key")
        return SecurityMiddleware(rbac_manager, jwt_manager)
    
    def test_validate_request_with_valid_token(self, security_middleware):
        """Test request validation with valid token."""
        # Create valid token
        jwt_manager = JWTManager("test-secret-key")
        token = jwt_manager.create_token(
            user_id="user123",
            workspace_id="workspace456",
            role=Role.ANALYST
        )
        
        headers = {"Authorization": f"Bearer {token}"}
        required_permissions = [Permission.READ_PATENT, Permission.SEARCH_PATENTS]
        
        result = security_middleware.validate_request(headers, required_permissions)
        
        assert result is not None
        assert result["user_id"] == "user123"
        assert result["workspace_id"] == "workspace456"
        assert result["role"] == Role.ANALYST
        assert "permissions" in result
    
    def test_validate_request_with_invalid_token(self, security_middleware):
        """Test request validation with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        required_permissions = [Permission.READ_PATENT]
        
        result = security_middleware.validate_request(headers, required_permissions)
        assert result is None
    
    def test_validate_request_without_token(self, security_middleware):
        """Test request validation without token."""
        headers = {}
        required_permissions = [Permission.READ_PATENT]
        
        result = security_middleware.validate_request(headers, required_permissions)
        assert result is None
    
    def test_validate_request_insufficient_permissions(self, security_middleware):
        """Test request validation with insufficient permissions."""
        # Create token for viewer (limited permissions)
        jwt_manager = JWTManager("test-secret-key")
        token = jwt_manager.create_token(
            user_id="user123",
            workspace_id="workspace456",
            role=Role.VIEWER
        )
        
        headers = {"Authorization": f"Bearer {token}"}
        # Require permission that viewer doesn't have
        required_permissions = [Permission.WRITE_PATENT]
        
        result = security_middleware.validate_request(headers, required_permissions)
        assert result is None
    
    def test_sanitize_input(self, security_middleware):
        """Test input sanitization."""
        # Test XSS prevention
        malicious_input = "<script>alert('xss')</script>"
        sanitized = security_middleware.sanitize_input(malicious_input)
        assert "<script>" not in sanitized
        
        # Test javascript: prevention
        malicious_url = "javascript:alert('xss')"
        sanitized = security_middleware.sanitize_input(malicious_url)
        assert "javascript:" not in sanitized
        
        # Test dictionary sanitization
        malicious_dict = {
            "name": "<script>alert('xss')</script>",
            "url": "javascript:alert('xss')"
        }
        sanitized = security_middleware.sanitize_input(malicious_dict)
        assert "<script>" not in sanitized["name"]
        assert "javascript:" not in sanitized["url"]
        
        # Test list sanitization
        malicious_list = ["<script>alert('xss')</script>", "javascript:alert('xss')"]
        sanitized = security_middleware.sanitize_input(malicious_list)
        assert "<script>" not in sanitized[0]
        assert "javascript:" not in sanitized[1]


class TestAuditLogger:
    """Test audit logging functionality."""
    
    @pytest.fixture
    def mock_db_client(self):
        return Mock()
    
    @pytest.fixture
    def audit_logger(self, mock_db_client):
        return AuditLogger(mock_db_client)
    
    @pytest.mark.asyncio
    async def test_log_event(self, audit_logger, mock_db_client):
        """Test audit event logging."""
        mock_db_client.create_audit_log = AsyncMock()
        
        await audit_logger.log_event(
            user_id="user123",
            workspace_id="workspace456",
            action="patent_read",
            resource_type="patent",
            resource_id="patent789",
            details={"ip": "192.168.1.1"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        mock_db_client.create_audit_log.assert_called_once()
        call_args = mock_db_client.create_audit_log.call_args
        assert call_args[1]["user_id"] == "user123"
        assert call_args[1]["action"] == "patent_read"
        assert call_args[1]["resource_type"] == "patent"
    
    @pytest.mark.asyncio
    async def test_log_event_with_error(self, audit_logger, mock_db_client):
        """Test audit event logging with database error."""
        mock_db_client.create_audit_log = AsyncMock(side_effect=Exception("DB Error"))
        
        # Should not raise exception, just log error
        await audit_logger.log_event(
            user_id="user123",
            workspace_id="workspace456",
            action="patent_read",
            resource_type="patent"
        )
        
        mock_db_client.create_audit_log.assert_called_once()


def test_permission_enum():
    """Test Permission enum values."""
    assert Permission.READ_PATENT.value == "read_patent"
    assert Permission.WRITE_PATENT.value == "write_patent"
    assert Permission.SEARCH_PATENTS.value == "search_patents"
    assert Permission.CREATE_ALIGNMENT.value == "create_alignment"
    assert Permission.CALCULATE_NOVELTY.value == "calculate_novelty"


def test_role_enum():
    """Test Role enum values."""
    assert Role.VIEWER.value == "viewer"
    assert Role.ANALYST.value == "analyst"
    assert Role.ADMIN.value == "admin"
    assert Role.OWNER.value == "owner"


if __name__ == "__main__":
    pytest.main([__file__])
