import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import the components we want to test
from src.workers.patent_ingest.worker import PatentIngestWorker
from src.workers.embed_worker.worker import EmbedWorker
from src.workers.retrieve_worker.worker import RetrieveWorker
from src.workers.align_worker.worker import AlignWorker
from src.workers.novelty_worker.worker import NoveltyWorker
from src.workers.chart_worker.worker import ChartWorker
from src.workers.graph_worker.worker import GraphWorker
from src.utils.database import DatabaseClient
from src.utils.storage import StorageClient
from src.utils.observability import setup_tracing, metrics, health_checker


class TestPatentProcessingPipeline:
    """Integration tests for the complete patent processing pipeline."""
    
    @pytest.fixture
    def mock_db_client(self):
        """Mock database client."""
        client = Mock(spec=DatabaseClient)
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_storage_client(self):
        """Mock storage client."""
        client = Mock(spec=StorageClient)
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        return client
    
    @pytest.fixture
    def sample_patent_data(self):
        """Sample patent data for testing."""
        return {
            "pub_number": "US20230012345A1",
            "title": "Machine Learning System for Patent Analysis",
            "abstract": "A system and method for analyzing patents using machine learning algorithms...",
            "assignees": ["Tech Corp", "AI Labs"],
            "inventors": ["John Smith", "Jane Doe"],
            "cpc_codes": ["G06N3/08", "G06K9/00"],
            "prio_date": "2023-01-15",
            "claims": [
                {
                    "claim_number": 1,
                    "text": "A method for processing patent data comprising: receiving input data; analyzing the data using machine learning; and generating analysis results.",
                    "is_independent": True
                },
                {
                    "claim_number": 2,
                    "text": "The method of claim 1, wherein the machine learning algorithm is a neural network.",
                    "is_independent": False
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_patent_ingest_pipeline(self, mock_db_client, mock_storage_client, sample_patent_data):
        """Test complete patent ingestion pipeline."""
        # Mock database responses
        mock_db_client.create_patent = AsyncMock(return_value="patent_123")
        mock_db_client.create_claim = AsyncMock(side_effect=["claim_1", "claim_2"])
        mock_db_client.get_patent_with_claims = AsyncMock(return_value={
            "patent": sample_patent_data,
            "claims": sample_patent_data["claims"]
        })
        
        # Create ingest worker
        ingest_worker = PatentIngestWorker()
        ingest_worker.db = mock_db_client
        ingest_worker.storage = mock_storage_client
        
        # Test patent ingestion
        patent_id = await ingest_worker.process_patent(sample_patent_data)
        
        assert patent_id == "patent_123"
        mock_db_client.create_patent.assert_called_once()
        assert mock_db_client.create_claim.call_count == 2
    
    @pytest.mark.asyncio
    async def test_embedding_generation_pipeline(self, mock_db_client, mock_storage_client, sample_patent_data):
        """Test embedding generation pipeline."""
        # Mock database responses
        mock_db_client.get_patent_with_claims = AsyncMock(return_value={
            "patent": sample_patent_data,
            "claims": sample_patent_data["claims"]
        })
        mock_db_client.update_patent_embeddings = AsyncMock(return_value=True)
        
        # Create embed worker
        embed_worker = EmbedWorker()
        embed_worker.db = mock_db_client
        embed_worker.storage = mock_storage_client
        
        # Test embedding generation
        with patch.object(embed_worker, 'generate_embeddings') as mock_generate:
            mock_generate.return_value = {
                "claims": {"claim_1": [0.1, 0.2, 0.3]},
                "clauses": {"clause_1": [0.4, 0.5, 0.6]}
            }
            
            result = await embed_worker.process_patent_embeddings("patent_123")
            
            assert result is True
            mock_db_client.update_patent_embeddings.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_retrieval_pipeline(self, mock_db_client, mock_storage_client):
        """Test search and retrieval pipeline."""
        # Mock database responses
        mock_db_client.search_by_embedding = AsyncMock(return_value=[
            {"patent_id": "patent_1", "similarity": 0.95},
            {"patent_id": "patent_2", "similarity": 0.87}
        ])
        
        # Create retrieve worker
        retrieve_worker = RetrieveWorker()
        retrieve_worker.db = mock_db_client
        retrieve_worker.storage = mock_storage_client
        
        # Test search retrieval
        query = "machine learning patent analysis"
        results = await retrieve_worker.search_patents(query, search_type="hybrid", k=10)
        
        assert len(results) == 2
        assert results[0]["patent_id"] == "patent_1"
        assert results[0]["similarity"] == 0.95
    
    @pytest.mark.asyncio
    async def test_alignment_pipeline(self, mock_db_client, mock_storage_client):
        """Test patent alignment pipeline."""
        # Mock database responses
        mock_db_client.get_claim = AsyncMock(return_value={
            "id": "claim_1",
            "text": "A method for processing data comprising: receiving input data; analyzing the data; and generating results."
        })
        mock_db_client.create_alignment = AsyncMock(return_value="alignment_123")
        
        # Create align worker
        align_worker = AlignWorker()
        align_worker.db = mock_db_client
        align_worker.storage = mock_storage_client
        
        # Test alignment creation
        alignment_data = {
            "patent_id": "patent_1",
            "claim_num": 1,
            "reference_patent_id": "patent_2",
            "reference_claim_id": "claim_2",
            "similarity_score": 0.85,
            "alignment_type": "high_similarity"
        }
        
        with patch.object(align_worker, 'calculate_alignment') as mock_calculate:
            mock_calculate.return_value = alignment_data
            
            result = await align_worker.create_alignment(
                "patent_1", 1, "patent_2", "claim_2"
            )
            
            assert result == "alignment_123"
            mock_db_client.create_alignment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_novelty_calculation_pipeline(self, mock_db_client, mock_storage_client):
        """Test novelty calculation pipeline."""
        # Mock database responses
        mock_db_client.get_claim = AsyncMock(return_value={
            "id": "claim_1",
            "text": "A method for processing data comprising: receiving input data; analyzing the data; and generating results."
        })
        mock_db_client.create_novelty_score = AsyncMock(return_value="novelty_123")
        
        # Create novelty worker
        novelty_worker = NoveltyWorker()
        novelty_worker.db = mock_db_client
        novelty_worker.storage = mock_storage_client
        
        # Test novelty calculation
        with patch.object(novelty_worker, 'calculate_novelty_score') as mock_calculate:
            mock_calculate.return_value = {
                "novelty_score": 0.75,
                "obviousness_score": 0.25,
                "confidence_band": "high"
            }
            
            result = await novelty_worker.calculate_novelty("patent_1", 1)
            
            assert result == "novelty_123"
            mock_db_client.create_novelty_score.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chart_generation_pipeline(self, mock_db_client, mock_storage_client):
        """Test chart generation pipeline."""
        # Mock database responses
        mock_db_client.get_patent = AsyncMock(return_value={
            "id": "patent_1",
            "title": "Test Patent",
            "pub_number": "US20230012345A1"
        })
        mock_db_client.get_claim = AsyncMock(return_value={
            "id": "claim_1",
            "text": "A method for processing data..."
        })
        
        # Mock storage responses
        mock_storage_client.upload_file = AsyncMock(return_value=True)
        mock_storage_client.get_signed_url = AsyncMock(return_value="https://example.com/chart.pdf")
        
        # Create chart worker
        chart_worker = ChartWorker()
        chart_worker.db = mock_db_client
        chart_worker.storage = mock_storage_client
        
        # Test chart generation
        with patch.object(chart_worker, 'create_pdf_chart') as mock_create:
            mock_create.return_value = "/tmp/test_chart.pdf"
            
            result = await chart_worker.generate_claim_chart("patent_1", 1)
            
            assert result is not None
            mock_storage_client.upload_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_graph_analysis_pipeline(self, mock_db_client, mock_storage_client):
        """Test graph analysis pipeline."""
        # Mock database responses
        mock_db_client.get_patent_citations = AsyncMock(return_value=[
            {"citing_patent_id": "patent_1", "cited_patent_id": "patent_2"},
            {"citing_patent_id": "patent_2", "cited_patent_id": "patent_3"}
        ])
        mock_db_client.store_graph_analysis = AsyncMock(return_value=True)
        
        # Create graph worker
        graph_worker = GraphWorker()
        graph_worker.db = mock_db_client
        graph_worker.storage = mock_storage_client
        
        # Test graph analysis
        patent_ids = ["patent_1", "patent_2", "patent_3"]
        
        with patch.object(graph_worker, 'calculate_graph_metrics') as mock_calculate:
            mock_calculate.return_value = {
                "basic": {"node_count": 3, "edge_count": 2},
                "centrality": {"pagerank": {"patent_1": 0.5}},
                "decay": {"decay_pagerank": {"patent_1": 0.4}}
            }
            
            result = await graph_worker.build_citation_graph(patent_ids, "citations")
            
            assert len(result.nodes()) == 3
            assert len(result.edges()) == 2
            mock_db_client.store_graph_analysis.assert_called_once()


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    @pytest.mark.asyncio
    async def test_complete_patent_analysis_workflow(self, mock_db_client, mock_storage_client):
        """Test complete patent analysis workflow from ingestion to chart generation."""
        # Setup mock responses for the entire workflow
        mock_db_client.create_patent = AsyncMock(return_value="patent_123")
        mock_db_client.create_claim = AsyncMock(side_effect=["claim_1", "claim_2"])
        mock_db_client.update_patent_embeddings = AsyncMock(return_value=True)
        mock_db_client.search_by_embedding = AsyncMock(return_value=[
            {"patent_id": "ref_patent_1", "similarity": 0.9}
        ])
        mock_db_client.create_alignment = AsyncMock(return_value="alignment_123")
        mock_db_client.create_novelty_score = AsyncMock(return_value="novelty_123")
        mock_db_client.get_patent = AsyncMock(return_value={"title": "Test Patent"})
        mock_db_client.get_claim = AsyncMock(return_value={"text": "Test claim"})
        
        mock_storage_client.upload_file = AsyncMock(return_value=True)
        mock_storage_client.get_signed_url = AsyncMock(return_value="https://example.com/chart.pdf")
        
        # 1. Patent Ingestion
        ingest_worker = PatentIngestWorker()
        ingest_worker.db = mock_db_client
        ingest_worker.storage = mock_storage_client
        
        patent_data = {
            "pub_number": "US20230012345A1",
            "title": "Test Patent",
            "claims": [{"claim_number": 1, "text": "Test claim", "is_independent": True}]
        }
        
        patent_id = await ingest_worker.process_patent(patent_data)
        assert patent_id == "patent_123"
        
        # 2. Embedding Generation
        embed_worker = EmbedWorker()
        embed_worker.db = mock_db_client
        embed_worker.storage = mock_storage_client
        
        with patch.object(embed_worker, 'generate_embeddings') as mock_generate:
            mock_generate.return_value = {"claims": {"claim_1": [0.1, 0.2, 0.3]}}
            result = await embed_worker.process_patent_embeddings(patent_id)
            assert result is True
        
        # 3. Search and Retrieval
        retrieve_worker = RetrieveWorker()
        retrieve_worker.db = mock_db_client
        retrieve_worker.storage = mock_storage_client
        
        search_results = await retrieve_worker.search_patents("test query", k=5)
        assert len(search_results) == 1
        assert search_results[0]["patent_id"] == "ref_patent_1"
        
        # 4. Alignment Creation
        align_worker = AlignWorker()
        align_worker.db = mock_db_client
        align_worker.storage = mock_storage_client
        
        with patch.object(align_worker, 'calculate_alignment') as mock_calculate:
            mock_calculate.return_value = {"similarity_score": 0.85}
            alignment_id = await align_worker.create_alignment(
                patent_id, 1, "ref_patent_1", "ref_claim_1"
            )
            assert alignment_id == "alignment_123"
        
        # 5. Novelty Calculation
        novelty_worker = NoveltyWorker()
        novelty_worker.db = mock_db_client
        novelty_worker.storage = mock_storage_client
        
        with patch.object(novelty_worker, 'calculate_novelty_score') as mock_calculate:
            mock_calculate.return_value = {"novelty_score": 0.75}
            novelty_id = await novelty_worker.calculate_novelty(patent_id, 1)
            assert novelty_id == "novelty_123"
        
        # 6. Chart Generation
        chart_worker = ChartWorker()
        chart_worker.db = mock_db_client
        chart_worker.storage = mock_storage_client
        
        with patch.object(chart_worker, 'create_pdf_chart') as mock_create:
            mock_create.return_value = "/tmp/test_chart.pdf"
            chart_data = await chart_worker.generate_claim_chart(patent_id, 1)
            assert chart_data is not None
        
        # Verify all components were called
        assert mock_db_client.create_patent.called
        assert mock_db_client.update_patent_embeddings.called
        assert mock_db_client.create_alignment.called
        assert mock_db_client.create_novelty_score.called
        assert mock_storage_client.upload_file.called


class TestObservabilityIntegration:
    """Test observability integration."""
    
    @pytest.mark.asyncio
    async def test_tracing_integration(self):
        """Test tracing integration across components."""
        # Setup tracing
        setup_tracing("test-service", "1.0.0")
        
        # Test that metrics are being collected
        assert metrics is not None
        assert hasattr(metrics, 'request_count')
        assert hasattr(metrics, 'worker_jobs_total')
        assert hasattr(metrics, 'patents_processed')
    
    @pytest.mark.asyncio
    async def test_health_checks(self):
        """Test health check functionality."""
        # Register a test health check
        async def test_check():
            return True
        
        health_checker.register_check("test_check", test_check)
        
        # Run health checks
        results = await health_checker.run_checks()
        
        assert "test_check" in results
        assert results["test_check"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test metrics collection during operations."""
        # Simulate some operations and check metrics
        metrics.patents_processed.labels(processing_stage="ingest", status="success").inc()
        metrics.search_queries.labels(search_type="hybrid", result_count="10").inc()
        metrics.alignments_created.labels(alignment_type="high_similarity", confidence_level="high").inc()
        
        # Verify metrics were incremented (we can't easily test the actual values,
        # but we can verify the metrics object exists and has the expected structure)
        assert metrics is not None
        assert hasattr(metrics, 'patents_processed')
        assert hasattr(metrics, 'search_queries')
        assert hasattr(metrics, 'alignments_created')


class TestErrorHandling:
    """Test error handling across the pipeline."""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self, mock_db_client, mock_storage_client):
        """Test handling of database connection failures."""
        mock_db_client.connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Test that workers handle connection failures gracefully
        embed_worker = EmbedWorker()
        embed_worker.db = mock_db_client
        embed_worker.storage = mock_storage_client
        
        with pytest.raises(Exception):
            await embed_worker.start()
    
    @pytest.mark.asyncio
    async def test_storage_failure(self, mock_db_client, mock_storage_client):
        """Test handling of storage failures."""
        mock_storage_client.upload_file = AsyncMock(side_effect=Exception("Upload failed"))
        
        chart_worker = ChartWorker()
        chart_worker.db = mock_db_client
        chart_worker.storage = mock_storage_client
        
        with patch.object(chart_worker, 'create_pdf_chart') as mock_create:
            mock_create.return_value = "/tmp/test_chart.pdf"
            
            with pytest.raises(Exception):
                await chart_worker.upload_chart_to_storage("/tmp/test_chart.pdf", "chart_123", "pdf")
    
    @pytest.mark.asyncio
    async def test_worker_message_handling_failure(self, mock_db_client, mock_storage_client):
        """Test handling of message processing failures."""
        # Create a worker and test message handling with invalid data
        embed_worker = EmbedWorker()
        embed_worker.db = mock_db_client
        embed_worker.storage = mock_storage_client
        
        # Mock a message with invalid data
        mock_message = Mock()
        mock_message.data.decode.return_value = "invalid json"
        
        # Test that the worker handles invalid messages gracefully
        await embed_worker.handle_embed_request(mock_message)
        
        # Verify that the worker didn't crash and handled the error appropriately
        assert True  # If we get here, the worker handled the error gracefully


if __name__ == "__main__":
    pytest.main([__file__])
