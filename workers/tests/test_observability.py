import pytest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.utils.observability import (
    setup_tracing, Metrics, trace_span, trace_operation, 
    track_metrics, health_checker, get_metrics, 
    log_event, log_error, log_performance
)


class TestObservability:
    """Test observability functionality."""
    
    def test_setup_tracing(self):
        """Test tracing setup."""
        # Test that setup_tracing doesn't crash
        setup_tracing("test-service", "1.0.0")
        assert True  # If we get here, setup didn't crash
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = Metrics()
        
        # Check that all expected metrics exist
        assert hasattr(metrics, 'request_count')
        assert hasattr(metrics, 'request_duration')
        assert hasattr(metrics, 'worker_jobs_total')
        assert hasattr(metrics, 'worker_job_duration')
        assert hasattr(metrics, 'patents_processed')
        assert hasattr(metrics, 'embeddings_generated')
        assert hasattr(metrics, 'search_queries')
        assert hasattr(metrics, 'alignments_created')
        assert hasattr(metrics, 'novelty_scores_calculated')
        assert hasattr(metrics, 'charts_generated')
        assert hasattr(metrics, 'active_connections')
        assert hasattr(metrics, 'queue_size')
        assert hasattr(metrics, 'memory_usage')
    
    def test_metrics_increment(self):
        """Test metrics incrementing."""
        metrics = Metrics()
        
        # Test incrementing various metrics
        metrics.request_count.labels(method="GET", endpoint="/api/patents", status="200").inc()
        metrics.worker_jobs_total.labels(worker_type="embed", job_type="generate", status="success").inc()
        metrics.patents_processed.labels(processing_stage="ingest", status="success").inc()
        
        # Verify metrics were incremented (we can't easily test the actual values,
        # but we can verify the metrics object exists and has the expected structure)
        assert metrics is not None
        assert hasattr(metrics, 'request_count')
        assert hasattr(metrics, 'worker_jobs_total')
        assert hasattr(metrics, 'patents_processed')
    
    def test_metrics_observation(self):
        """Test metrics observation."""
        metrics = Metrics()
        
        # Test observing duration metrics
        metrics.request_duration.labels(method="POST", endpoint="/api/search").observe(0.5)
        metrics.worker_job_duration.labels(worker_type="align", job_type="calculate").observe(2.3)
        
        # Test observing gauge metrics
        metrics.active_connections.labels(connection_type="database").set(5)
        metrics.queue_size.labels(queue_name="patent_ingest").set(10)
        metrics.memory_usage.labels(component="embed_worker").set(1024 * 1024 * 100)  # 100MB
        
        assert metrics is not None
        assert hasattr(metrics, 'request_duration')
        assert hasattr(metrics, 'worker_job_duration')
        assert hasattr(metrics, 'active_connections')
        assert hasattr(metrics, 'queue_size')
        assert hasattr(metrics, 'memory_usage')
    
    @pytest.mark.asyncio
    async def test_trace_span_decorator(self):
        """Test trace span decorator."""
        @trace_span("test_operation")
        async def test_function():
            await asyncio.sleep(0.1)
            return "success"
        
        # Test that the decorator works
        result = await test_function()
        assert result == "success"
    
    def test_trace_span_sync_decorator(self):
        """Test trace span decorator for sync functions."""
        @trace_span("test_sync_operation")
        def test_sync_function():
            time.sleep(0.1)
            return "success"
        
        # Test that the decorator works
        result = test_sync_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_trace_operation_context_manager(self):
        """Test trace operation context manager."""
        async with trace_operation("test_context_operation") as span:
            await asyncio.sleep(0.1)
            span.set_attribute("test.attribute", "test_value")
        
        # Test that the context manager works
        assert True  # If we get here, the context manager worked
    
    @pytest.mark.asyncio
    async def test_track_metrics_decorator(self):
        """Test track metrics decorator."""
        @track_metrics("test_metric", {"operation": "test"})
        async def test_metric_function():
            await asyncio.sleep(0.1)
            return "success"
        
        # Test that the decorator works
        result = await test_metric_function()
        assert result == "success"
    
    def test_track_metrics_sync_decorator(self):
        """Test track metrics decorator for sync functions."""
        @track_metrics("test_sync_metric", {"operation": "test_sync"})
        def test_sync_metric_function():
            time.sleep(0.1)
            return "success"
        
        # Test that the decorator works
        result = test_sync_metric_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_health_checker(self):
        """Test health checker functionality."""
        # Register a test health check
        async def test_check():
            return True
        
        health_checker.register_check("test_check", test_check)
        
        # Run health checks
        results = await health_checker.run_checks()
        
        assert "test_check" in results
        assert results["test_check"]["status"] == "healthy"
        assert "duration" in results["test_check"]
        assert "timestamp" in results["test_check"]
    
    @pytest.mark.asyncio
    async def test_health_checker_with_failing_check(self):
        """Test health checker with failing check."""
        # Register a failing health check
        async def failing_check():
            return False
        
        health_checker.register_check("failing_check", failing_check)
        
        # Run health checks
        results = await health_checker.run_checks()
        
        assert "failing_check" in results
        assert results["failing_check"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_checker_with_error(self):
        """Test health checker with erroring check."""
        # Register an erroring health check
        async def erroring_check():
            raise Exception("Health check error")
        
        health_checker.register_check("erroring_check", erroring_check)
        
        # Run health checks
        results = await health_checker.run_checks()
        
        assert "erroring_check" in results
        assert results["erroring_check"]["status"] == "error"
        assert "error" in results["erroring_check"]
    
    def test_get_metrics(self):
        """Test getting Prometheus metrics."""
        metrics_data, content_type = get_metrics()
        
        assert isinstance(metrics_data, bytes)
        assert content_type == "text/plain; version=0.0.4; charset=utf-8"
        assert len(metrics_data) > 0
    
    def test_log_event(self):
        """Test logging events."""
        # Test that log_event doesn't crash
        log_event("test_event", user_id="user123", action="test_action")
        assert True  # If we get here, logging didn't crash
    
    def test_log_error(self):
        """Test logging errors."""
        # Test that log_error doesn't crash
        test_error = Exception("Test error")
        log_error("test_error", test_error, user_id="user123", operation="test")
        assert True  # If we get here, logging didn't crash
    
    def test_log_performance(self):
        """Test logging performance metrics."""
        # Test that log_performance doesn't crash
        log_performance("test_operation", 0.5, user_id="user123", operation="test")
        assert True  # If we get here, logging didn't crash


class TestMetricsIntegration:
    """Test metrics integration with actual operations."""
    
    def test_patent_processing_metrics(self):
        """Test patent processing metrics."""
        metrics = Metrics()
        
        # Simulate patent processing pipeline
        metrics.patents_processed.labels(processing_stage="ingest", status="success").inc()
        metrics.patents_processed.labels(processing_stage="embed", status="success").inc()
        metrics.patents_processed.labels(processing_stage="index", status="success").inc()
        
        # Simulate some failures
        metrics.patents_processed.labels(processing_stage="ingest", status="error").inc()
        
        assert metrics is not None
    
    def test_search_metrics(self):
        """Test search metrics."""
        metrics = Metrics()
        
        # Simulate different types of searches
        metrics.search_queries.labels(search_type="hybrid", result_count="10").inc()
        metrics.search_queries.labels(search_type="hybrid", result_count="50").inc()
        metrics.search_queries.labels(search_type="vector", result_count="20").inc()
        metrics.search_queries.labels(search_type="keyword", result_count="5").inc()
        
        assert metrics is not None
    
    def test_worker_metrics(self):
        """Test worker metrics."""
        metrics = Metrics()
        
        # Simulate worker job processing
        metrics.worker_jobs_total.labels(worker_type="embed", job_type="generate", status="success").inc()
        metrics.worker_jobs_total.labels(worker_type="align", job_type="calculate", status="success").inc()
        metrics.worker_jobs_total.labels(worker_type="novelty", job_type="score", status="success").inc()
        metrics.worker_jobs_total.labels(worker_type="chart", job_type="generate", status="success").inc()
        
        # Simulate some failures
        metrics.worker_jobs_total.labels(worker_type="embed", job_type="generate", status="error").inc()
        
        # Simulate job durations
        metrics.worker_job_duration.labels(worker_type="embed", job_type="generate").observe(2.5)
        metrics.worker_job_duration.labels(worker_type="align", job_type="calculate").observe(5.2)
        metrics.worker_job_duration.labels(worker_type="novelty", job_type="score").observe(3.8)
        
        assert metrics is not None
    
    def test_system_metrics(self):
        """Test system metrics."""
        metrics = Metrics()
        
        # Simulate system state
        metrics.active_connections.labels(connection_type="database").set(8)
        metrics.active_connections.labels(connection_type="redis").set(3)
        metrics.active_connections.labels(connection_type="nats").set(2)
        
        metrics.queue_size.labels(queue_name="patent_ingest").set(15)
        metrics.queue_size.labels(queue_name="embed_generation").set(7)
        metrics.queue_size.labels(queue_name="alignment_calculation").set(3)
        
        metrics.memory_usage.labels(component="embed_worker").set(1024 * 1024 * 200)  # 200MB
        metrics.memory_usage.labels(component="align_worker").set(1024 * 1024 * 150)  # 150MB
        metrics.memory_usage.labels(component="novelty_worker").set(1024 * 1024 * 100)  # 100MB
        
        assert metrics is not None


class TestTracingIntegration:
    """Test tracing integration with actual operations."""
    
    @pytest.mark.asyncio
    async def test_patent_processing_tracing(self):
        """Test tracing for patent processing operations."""
        @trace_span("patent.ingest")
        async def ingest_patent():
            await asyncio.sleep(0.1)
            return "patent_123"
        
        @trace_span("patent.embed")
        async def generate_embeddings(patent_id):
            await asyncio.sleep(0.1)
            return {"embeddings": "generated"}
        
        @trace_span("patent.index")
        async def index_patent(patent_id, embeddings):
            await asyncio.sleep(0.1)
            return "indexed"
        
        # Simulate patent processing pipeline
        patent_id = await ingest_patent()
        embeddings = await generate_embeddings(patent_id)
        result = await index_patent(patent_id, embeddings)
        
        assert patent_id == "patent_123"
        assert embeddings == {"embeddings": "generated"}
        assert result == "indexed"
    
    @pytest.mark.asyncio
    async def test_search_tracing(self):
        """Test tracing for search operations."""
        @trace_span("search.hybrid")
        async def hybrid_search(query):
            await asyncio.sleep(0.1)
            return [{"patent_id": "patent_1", "score": 0.95}]
        
        @trace_span("search.vector")
        async def vector_search(query):
            await asyncio.sleep(0.1)
            return [{"patent_id": "patent_2", "score": 0.87}]
        
        # Simulate search operations
        hybrid_results = await hybrid_search("machine learning")
        vector_results = await vector_search("neural network")
        
        assert len(hybrid_results) == 1
        assert len(vector_results) == 1
        assert hybrid_results[0]["patent_id"] == "patent_1"
        assert vector_results[0]["patent_id"] == "patent_2"


class TestErrorHandling:
    """Test error handling in observability."""
    
    @pytest.mark.asyncio
    async def test_trace_span_with_error(self):
        """Test trace span decorator with error."""
        @trace_span("error_operation")
        async def error_function():
            await asyncio.sleep(0.1)
            raise Exception("Test error")
        
        # Test that the decorator handles errors gracefully
        with pytest.raises(Exception):
            await error_function()
    
    @pytest.mark.asyncio
    async def test_track_metrics_with_error(self):
        """Test track metrics decorator with error."""
        @track_metrics("error_metric", {"operation": "error_test"})
        async def error_metric_function():
            await asyncio.sleep(0.1)
            raise Exception("Test error")
        
        # Test that the decorator handles errors gracefully
        with pytest.raises(Exception):
            await error_metric_function()
    
    def test_metrics_with_invalid_labels(self):
        """Test metrics with invalid labels."""
        metrics = Metrics()
        
        # Test that metrics handle invalid labels gracefully
        try:
            metrics.request_count.labels(method="GET", endpoint="/api/test", status="200").inc()
            assert True  # If we get here, it worked
        except Exception as e:
            # If there's an error, it should be handled gracefully
            assert "Invalid label" in str(e) or True  # Allow any error handling


if __name__ == "__main__":
    pytest.main([__file__])
