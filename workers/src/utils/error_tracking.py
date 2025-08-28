"""Sentry error tracking configuration."""

import asyncio
import os
import logging
from typing import Optional, Dict, Any
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

logger = logging.getLogger(__name__)


def setup_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    service_name: str = "ai-patent-explorer",
    service_version: str = "1.0.0",
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1
):
    """Setup Sentry error tracking."""
    try:
        # Get DSN from environment if not provided
        if not dsn:
            dsn = os.getenv("SENTRY_DSN")
        
        if not dsn:
            logger.warning("Sentry DSN not provided, error tracking disabled")
            return
        
        # Configure Sentry
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            service_name=service_name,
            service_version=service_version,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            integrations=[
                AsyncioIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
                RedisIntegration(),
                SqlalchemyIntegration()
            ],
            # Configure before_send to filter sensitive data
            before_send=filter_sensitive_data,
            # Configure before_breadcrumb to add context
            before_breadcrumb=add_context_to_breadcrumbs,
            # Enable debug mode in development
            debug=environment == "development"
        )
        
        logger.info("Sentry error tracking initialized", 
                   environment=environment, 
                   service_name=service_name)
        
    except Exception as e:
        logger.error("Failed to setup Sentry", error=str(e))


def filter_sensitive_data(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter sensitive data from Sentry events."""
    try:
        # Remove sensitive headers
        if "request" in event and "headers" in event["request"]:
            sensitive_headers = [
                "authorization", "cookie", "x-api-key", 
                "x-auth-token", "x-workspace-id"
            ]
            for header in sensitive_headers:
                if header in event["request"]["headers"]:
                    event["request"]["headers"][header] = "[REDACTED]"
        
        # Remove sensitive data from extra context
        if "extra" in event:
            sensitive_keys = ["password", "token", "secret", "key"]
            for key in sensitive_keys:
                if key in event["extra"]:
                    event["extra"][key] = "[REDACTED]"
        
        # Remove sensitive data from tags
        if "tags" in event:
            sensitive_tags = ["user_id", "workspace_id"]
            for tag in sensitive_tags:
                if tag in event["tags"]:
                    event["tags"][tag] = "[REDACTED]"
        
        return event
        
    except Exception as e:
        logger.error("Error filtering sensitive data", error=str(e))
        return event


def add_context_to_breadcrumbs(breadcrumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Add context to Sentry breadcrumbs."""
    try:
        # Add service context
        breadcrumb["data"] = breadcrumb.get("data", {})
        breadcrumb["data"]["service"] = "ai-patent-explorer"
        
        # Add timestamp if not present
        if "timestamp" not in breadcrumb:
            import time
            breadcrumb["timestamp"] = time.time()
        
        return breadcrumb
        
    except Exception as e:
        logger.error("Error adding context to breadcrumb", error=str(e))
        return breadcrumb


def capture_exception(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Capture an exception with additional context."""
    try:
        if context:
            with sentry_sdk.push_scope() as scope:
                # Add context data
                for key, value in context.items():
                    scope.set_tag(key, value)
                
                # Capture the exception
                sentry_sdk.capture_exception(error)
        else:
            sentry_sdk.capture_exception(error)
        
        logger.info("Exception captured in Sentry", 
                   error_type=type(error).__name__,
                   error_message=str(error))
        
    except Exception as e:
        logger.error("Failed to capture exception in Sentry", error=str(e))


def capture_message(message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
    """Capture a message with additional context."""
    try:
        if context:
            with sentry_sdk.push_scope() as scope:
                # Add context data
                for key, value in context.items():
                    scope.set_tag(key, value)
                
                # Capture the message
                sentry_sdk.capture_message(message, level=level)
        else:
            sentry_sdk.capture_message(message, level=level)
        
        logger.info("Message captured in Sentry", 
                   message=message,
                   level=level)
        
    except Exception as e:
        logger.error("Failed to capture message in Sentry", error=str(e))


def set_user_context(user_id: str, workspace_id: str, role: str):
    """Set user context for Sentry."""
    try:
        sentry_sdk.set_user({
            "id": user_id,
            "workspace_id": workspace_id,
            "role": role
        })
        
        logger.debug("User context set for Sentry", 
                    user_id=user_id,
                    workspace_id=workspace_id,
                    role=role)
        
    except Exception as e:
        logger.error("Failed to set user context in Sentry", error=str(e))


def set_tag(key: str, value: str):
    """Set a tag for Sentry."""
    try:
        sentry_sdk.set_tag(key, value)
        
        logger.debug("Tag set for Sentry", key=key, value=value)
        
    except Exception as e:
        logger.error("Failed to set tag in Sentry", error=str(e))


def set_context(name: str, data: Dict[str, Any]):
    """Set context data for Sentry."""
    try:
        sentry_sdk.set_context(name, data)
        
        logger.debug("Context set for Sentry", name=name, data=data)
        
    except Exception as e:
        logger.error("Failed to set context in Sentry", error=str(e))


def start_transaction(name: str, operation: str = "default"):
    """Start a Sentry transaction."""
    try:
        transaction = sentry_sdk.start_transaction(
            name=name,
            op=operation
        )
        
        logger.debug("Transaction started in Sentry", 
                    name=name,
                    operation=operation)
        
        return transaction
        
    except Exception as e:
        logger.error("Failed to start transaction in Sentry", error=str(e))
        return None


def add_performance_monitoring():
    """Add performance monitoring to Sentry."""
    try:
        # Enable performance monitoring
        sentry_sdk.init(
            # This would be called after the main init
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1
        )
        
        logger.info("Performance monitoring enabled in Sentry")
        
    except Exception as e:
        logger.error("Failed to enable performance monitoring in Sentry", error=str(e))


# Context managers for automatic error tracking
class SentryTransaction:
    """Context manager for Sentry transactions."""
    
    def __init__(self, name: str, operation: str = "default"):
        self.name = name
        self.operation = operation
        self.transaction = None
    
    def __enter__(self):
        self.transaction = start_transaction(self.name, self.operation)
        return self.transaction
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.transaction:
            self.transaction.finish()


class SentrySpan:
    """Context manager for Sentry spans."""
    
    def __init__(self, name: str, operation: str = "default"):
        self.name = name
        self.operation = operation
        self.span = None
    
    def __enter__(self):
        self.span = sentry_sdk.start_span(
            name=self.name,
            op=self.operation
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            self.span.finish()


# Decorators for automatic error tracking
def track_errors(func):
    """Decorator to automatically track errors in Sentry."""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            capture_exception(e, {
                "function": func.__name__,
                "module": func.__module__
            })
            raise
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            capture_exception(e, {
                "function": func.__name__,
                "module": func.__module__
            })
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return wrapper


def track_performance(name: str, operation: str = "default"):
    """Decorator to track performance in Sentry."""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with SentryTransaction(name, operation):
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with SentryTransaction(name, operation):
                return await func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator
