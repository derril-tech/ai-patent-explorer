"""Observability utilities for tracing, metrics, and logging."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from functools import wraps

import structlog
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.registry import CollectorRegistry

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize OpenTelemetry
def setup_tracing(service_name: str, service_version: str = "1.0.0"):
    """Setup OpenTelemetry tracing."""
    try:
        # Create tracer provider
        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
        })
        
        provider = TracerProvider(resource=resource)
        
        # Add span processor
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument libraries
        AsyncioInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        AsyncPGInstrumentor().instrument()
        
        logger.info("OpenTelemetry tracing initialized", service_name=service_name)
        
    except Exception as e:
        logger.error("Failed to setup tracing", error=str(e))

# Prometheus metrics
class Metrics:
    """Prometheus metrics collection."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry
        
        # Request metrics
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=registry
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=registry
        )
        
        # Worker metrics
        self.worker_jobs_total = Counter(
            'worker_jobs_total',
            'Total worker jobs processed',
            ['worker_type', 'job_type', 'status'],
            registry=registry
        )
        
        self.worker_job_duration = Histogram(
            'worker_job_duration_seconds',
            'Worker job duration',
            ['worker_type', 'job_type'],
            registry=registry
        )
        
        # Patent processing metrics
        self.patents_processed = Counter(
            'patents_processed_total',
            'Total patents processed',
            ['processing_stage', 'status'],
            registry=registry
        )
        
        self.embeddings_generated = Counter(
            'embeddings_generated_total',
            'Total embeddings generated',
            ['embedding_type', 'model'],
            registry=registry
        )
        
        self.search_queries = Counter(
            'search_queries_total',
            'Total search queries',
            ['search_type', 'result_count'],
            registry=registry
        )
        
        self.alignments_created = Counter(
            'alignments_created_total',
            'Total alignments created',
            ['alignment_type', 'confidence_level'],
            registry=registry
        )
        
        self.novelty_scores_calculated = Counter(
            'novelty_scores_calculated_total',
            'Total novelty scores calculated',
            ['confidence_band'],
            registry=registry
        )
        
        self.charts_generated = Counter(
            'charts_generated_total',
            'Total charts generated',
            ['chart_type', 'format'],
            registry=registry
        )
        
        # System metrics
        self.active_connections = Gauge(
            'active_connections',
            'Number of active database connections',
            ['connection_type'],
            registry=registry
        )
        
        self.queue_size = Gauge(
            'queue_size',
            'Number of items in queue',
            ['queue_name'],
            registry=registry
        )
        
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=registry
        )

# Global metrics instance
metrics = Metrics()

# Tracing decorators
def trace_span(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Decorator to create a trace span."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name, attributes=attributes or {}) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name, attributes=attributes or {}) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

@asynccontextmanager
async def trace_operation(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager for tracing operations."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(operation_name, attributes=attributes or {}) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise

# Metrics decorators
def track_metrics(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track metrics."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Increment success counter
                getattr(metrics, f"{metric_name}_total").labels(
                    status="success", **(labels or {})
                ).inc()
                
                # Record duration
                getattr(metrics, f"{metric_name}_duration_seconds").labels(
                    **(labels or {})
                ).observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Increment error counter
                getattr(metrics, f"{metric_name}_total").labels(
                    status="error", **(labels or {})
                ).inc()
                
                # Record duration
                getattr(metrics, f"{metric_name}_duration_seconds").labels(
                    **(labels or {})
                ).observe(duration)
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Increment success counter
                getattr(metrics, f"{metric_name}_total").labels(
                    status="success", **(labels or {})
                ).inc()
                
                # Record duration
                getattr(metrics, f"{metric_name}_duration_seconds").labels(
                    **(labels or {})
                ).observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Increment error counter
                getattr(metrics, f"{metric_name}_total").labels(
                    status="error", **(labels or {})
                ).inc()
                
                # Record duration
                getattr(metrics, f"{metric_name}_duration_seconds").labels(
                    **(labels or {})
                ).observe(duration)
                
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Health check utilities
class HealthChecker:
    """Health check utilities."""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check."""
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all health checks."""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time
                
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "duration": duration,
                    "timestamp": time.time()
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.time()
                }
        
        return results

# Global health checker
health_checker = HealthChecker()

# Prometheus metrics endpoint
def get_metrics():
    """Get Prometheus metrics."""
    return generate_latest(metrics.registry), CONTENT_TYPE_LATEST

# Logging utilities
def log_event(event_type: str, **kwargs):
    """Log a structured event."""
    logger.info(f"Event: {event_type}", event_type=event_type, **kwargs)

def log_error(error_type: str, error: Exception, **kwargs):
    """Log a structured error."""
    logger.error(f"Error: {error_type}", 
                error_type=error_type, 
                error_message=str(error),
                error_class=error.__class__.__name__,
                **kwargs)

def log_performance(operation: str, duration: float, **kwargs):
    """Log performance metrics."""
    logger.info(f"Performance: {operation}", 
                operation=operation, 
                duration=duration,
                **kwargs)
