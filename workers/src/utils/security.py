"""Security utilities for RBAC, audit logging, and data protection."""

import json
import hashlib
import hmac
import base64
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog
import os

logger = structlog.get_logger(__name__)

class Permission(Enum):
    """Permission types."""
    READ_PATENT = "read_patent"
    WRITE_PATENT = "write_patent"
    DELETE_PATENT = "delete_patent"
    SEARCH_PATENTS = "search_patents"
    CREATE_ALIGNMENT = "create_alignment"
    CALCULATE_NOVELTY = "calculate_novelty"
    GENERATE_CHART = "generate_chart"
    EXPORT_DATA = "export_data"
    MANAGE_USERS = "manage_users"
    MANAGE_WORKSPACE = "manage_workspace"
    VIEW_AUDIT_LOGS = "view_audit_logs"

class Role(Enum):
    """User roles."""
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"
    OWNER = "owner"

class RBACManager:
    """Role-Based Access Control manager."""
    
    def __init__(self):
        # Define role permissions
        self.role_permissions = {
            Role.VIEWER: {
                Permission.READ_PATENT,
                Permission.SEARCH_PATENTS,
            },
            Role.ANALYST: {
                Permission.READ_PATENT,
                Permission.WRITE_PATENT,
                Permission.SEARCH_PATENTS,
                Permission.CREATE_ALIGNMENT,
                Permission.CALCULATE_NOVELTY,
                Permission.GENERATE_CHART,
                Permission.EXPORT_DATA,
            },
            Role.ADMIN: {
                Permission.READ_PATENT,
                Permission.WRITE_PATENT,
                Permission.DELETE_PATENT,
                Permission.SEARCH_PATENTS,
                Permission.CREATE_ALIGNMENT,
                Permission.CALCULATE_NOVELTY,
                Permission.GENERATE_CHART,
                Permission.EXPORT_DATA,
                Permission.MANAGE_USERS,
                Permission.MANAGE_WORKSPACE,
                Permission.VIEW_AUDIT_LOGS,
            },
            Role.OWNER: {
                Permission.READ_PATENT,
                Permission.WRITE_PATENT,
                Permission.DELETE_PATENT,
                Permission.SEARCH_PATENTS,
                Permission.CREATE_ALIGNMENT,
                Permission.CALCULATE_NOVELTY,
                Permission.GENERATE_CHART,
                Permission.EXPORT_DATA,
                Permission.MANAGE_USERS,
                Permission.MANAGE_WORKSPACE,
                Permission.VIEW_AUDIT_LOGS,
            }
        }
    
    def has_permission(self, user_role: Role, permission: Permission) -> bool:
        """Check if user has permission."""
        if user_role not in self.role_permissions:
            return False
        
        return permission in self.role_permissions[user_role]
    
    def get_user_permissions(self, user_role: Role) -> Set[Permission]:
        """Get all permissions for a user role."""
        return self.role_permissions.get(user_role, set())
    
    def validate_access(self, user_role: Role, required_permissions: List[Permission]) -> bool:
        """Validate if user has all required permissions."""
        user_permissions = self.get_user_permissions(user_role)
        return all(perm in user_permissions for perm in required_permissions)

# Global RBAC manager
rbac_manager = RBACManager()

class AuditLogger:
    """Audit logging for security events."""
    
    def __init__(self, db_client):
        self.db = db_client
    
    async def log_event(self, 
                       user_id: str, 
                       workspace_id: str, 
                       action: str, 
                       resource_type: str, 
                       resource_id: Optional[str] = None, 
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None):
        """Log an audit event."""
        try:
            audit_entry = {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            await self.db.create_audit_log(
                workspace_id=workspace_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=audit_entry
            )
            
            logger.info("Audit event logged", 
                       user_id=user_id, 
                       action=action, 
                       resource_type=resource_type)
            
        except Exception as e:
            logger.error("Failed to log audit event", 
                        error=str(e), 
                        user_id=user_id, 
                        action=action)
    
    async def get_audit_logs(self, 
                           workspace_id: str, 
                           user_id: Optional[str] = None,
                           action: Optional[str] = None,
                           resource_type: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs with filters."""
        try:
            # This would be implemented in the database client
            # For now, return empty list
            return []
        except Exception as e:
            logger.error("Failed to get audit logs", error=str(e))
            return []

class DataProtection:
    """Data protection utilities."""
    
    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key.encode()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Failed to encrypt data", error=str(e))
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Failed to decrypt data", error=str(e))
            raise
    
    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """Hash data with optional salt."""
        if salt is None:
            salt = base64.b64encode(os.urandom(16)).decode()
        
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256', 
            data.encode(), 
            salt.encode(), 
            100000
        )
        
        return f"{salt}:{base64.b64encode(hash_obj).decode()}"
    
    def verify_hash(self, data: str, hashed_data: str) -> bool:
        """Verify hashed data."""
        try:
            salt, hash_value = hashed_data.split(':')
            expected_hash = self.hash_data(data, salt)
            return hmac.compare_digest(hashed_data, expected_hash)
        except Exception as e:
            logger.error("Failed to verify hash", error=str(e))
            return False

class JWTManager:
    """JWT token management."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, 
                    user_id: str, 
                    workspace_id: str, 
                    role: Role,
                    expires_in: int = 3600) -> str:
        """Create a JWT token."""
        try:
            payload = {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "role": role.value,
                "exp": datetime.utcnow() + timedelta(seconds=expires_in),
                "iat": datetime.utcnow(),
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error("Failed to create JWT token", error=str(e))
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token", error=str(e))
            return None
        except Exception as e:
            logger.error("Failed to verify JWT token", error=str(e))
            return None
    
    def refresh_token(self, token: str, expires_in: int = 3600) -> Optional[str]:
        """Refresh a JWT token."""
        try:
            payload = self.verify_token(token)
            if payload is None:
                return None
            
            # Create new token with updated expiration
            new_payload = {
                "user_id": payload["user_id"],
                "workspace_id": payload["workspace_id"],
                "role": payload["role"],
                "exp": datetime.utcnow() + timedelta(seconds=expires_in),
                "iat": datetime.utcnow(),
            }
            
            new_token = jwt.encode(new_payload, self.secret_key, algorithm=self.algorithm)
            return new_token
        except Exception as e:
            logger.error("Failed to refresh JWT token", error=str(e))
            return None

class SignedURLManager:
    """Signed URL management for secure file access."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()
    
    def create_signed_url(self, 
                         url: str, 
                         expires_in: int = 3600,
                         permissions: Optional[List[str]] = None) -> str:
        """Create a signed URL with expiration and permissions."""
        try:
            timestamp = int(time.time())
            expiration = timestamp + expires_in
            
            # Create signature data
            signature_data = {
                "url": url,
                "exp": expiration,
                "permissions": permissions or ["read"],
                "timestamp": timestamp
            }
            
            # Create signature
            signature = hmac.new(
                self.secret_key,
                json.dumps(signature_data, sort_keys=True).encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Add signature to URL
            separator = "&" if "?" in url else "?"
            signed_url = f"{url}{separator}signature={signature}&exp={expiration}"
            
            return signed_url
        except Exception as e:
            logger.error("Failed to create signed URL", error=str(e))
            raise
    
    def verify_signed_url(self, signed_url: str) -> Optional[Dict[str, Any]]:
        """Verify a signed URL and return the original URL and permissions."""
        try:
            # Parse URL parameters
            if "?" not in signed_url:
                return None
            
            base_url, params = signed_url.split("?", 1)
            param_dict = dict(param.split("=") for param in params.split("&"))
            
            signature = param_dict.get("signature")
            expiration = int(param_dict.get("exp", 0))
            
            if not signature or not expiration:
                return None
            
            # Check expiration
            if time.time() > expiration:
                logger.warning("Signed URL expired")
                return None
            
            # Recreate signature data
            signature_data = {
                "url": base_url,
                "exp": expiration,
                "permissions": ["read"],  # Default permissions
                "timestamp": 0  # Will be ignored in verification
            }
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                json.dumps(signature_data, sort_keys=True).encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Invalid signature in signed URL")
                return None
            
            return {
                "url": base_url,
                "permissions": signature_data["permissions"],
                "expires_at": expiration
            }
        except Exception as e:
            logger.error("Failed to verify signed URL", error=str(e))
            return None

class SecurityMiddleware:
    """Security middleware for request validation."""
    
    def __init__(self, rbac_manager: RBACManager, jwt_manager: JWTManager):
        self.rbac_manager = rbac_manager
        self.jwt_manager = jwt_manager
    
    def validate_request(self, 
                        request_headers: Dict[str, str],
                        required_permissions: List[Permission]) -> Optional[Dict[str, Any]]:
        """Validate request and return user context."""
        try:
            # Extract JWT token
            auth_header = request_headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                logger.warning("Missing or invalid Authorization header")
                return None
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Verify JWT token
            payload = self.jwt_manager.verify_token(token)
            if payload is None:
                return None
            
            # Extract user information
            user_id = payload.get("user_id")
            workspace_id = payload.get("workspace_id")
            role_str = payload.get("role")
            
            if not all([user_id, workspace_id, role_str]):
                logger.warning("Invalid JWT payload")
                return None
            
            # Validate role
            try:
                role = Role(role_str)
            except ValueError:
                logger.warning("Invalid role in JWT token")
                return None
            
            # Check permissions
            if not self.rbac_manager.validate_access(role, required_permissions):
                logger.warning("Insufficient permissions", 
                             user_id=user_id, 
                             role=role.value, 
                             required_permissions=[p.value for p in required_permissions])
                return None
            
            return {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "role": role,
                "permissions": list(self.rbac_manager.get_user_permissions(role))
            }
        except Exception as e:
            logger.error("Failed to validate request", error=str(e))
            return None
    
    def sanitize_input(self, data: Any) -> Any:
        """Sanitize user input to prevent injection attacks."""
        if isinstance(data, str):
            # Basic XSS prevention
            return data.replace("<script>", "").replace("javascript:", "")
        elif isinstance(data, dict):
            return {k: self.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        else:
            return data
