import pytest
import networkx as nx
import numpy as np
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
import json

# Import the worker we want to test
from src.workers.graph_worker.worker import GraphWorker


class TestGraphWorker:
    """Test cases for the GraphWorker."""
    
    @pytest.fixture
    def graph_worker(self):
        """Create a GraphWorker instance for testing."""
        return GraphWorker()
    
    @pytest.fixture
    def sample_graph(self):
        """Create a sample citation graph for testing."""
        graph = nx.DiGraph()
        
        # Add nodes (patents)
        patents = ['patent_1', 'patent_2', 'patent_3', 'patent_4', 'patent_5']
        for patent in patents:
            graph.add_node(patent)
        
        # Add edges (citations)
        citations = [
            ('patent_2', 'patent_1'),
            ('patent_3', 'patent_1'),
            ('patent_4', 'patent_2'),
            ('patent_5', 'patent_2'),
            ('patent_5', 'patent_3'),
        ]
        
        for citing, cited in citations:
            graph.add_edge(citing, cited, weight=1.0, date='2023-01-01')
        
        return graph
    
    @pytest.mark.asyncio
    async def test_build_citation_graph(self, graph_worker, sample_graph):
        """Test building citation graph from patent IDs."""
        patent_ids = ['patent_1', 'patent_2', 'patent_3', 'patent_4', 'patent_5']
        
        # Mock database responses
        mock_citations = [
            {
                'citing_patent_id': 'patent_2',
                'cited_patent_id': 'patent_1',
                'citation_date': '2023-01-01',
                'citation_strength': 1.0
            },
            {
                'citing_patent_id': 'patent_3',
                'cited_patent_id': 'patent_1',
                'citation_date': '2023-01-01',
                'citation_strength': 1.0
            }
        ]
        
        with patch.object(graph_worker.db, 'get_patent_citations', return_value=mock_citations):
            graph = await graph_worker.build_citation_graph(patent_ids, 'citations')
            
            assert len(graph.nodes()) == 5
            assert len(graph.edges()) == 2
            assert graph.has_edge('patent_2', 'patent_1')
            assert graph.has_edge('patent_3', 'patent_1')
    
    @pytest.mark.asyncio
    async def test_calculate_basic_metrics(self, graph_worker, sample_graph):
        """Test calculation of basic graph metrics."""
        metrics = await graph_worker.calculate_basic_metrics(sample_graph)
        
        assert metrics['node_count'] == 5
        assert metrics['edge_count'] == 5
        assert metrics['density'] > 0
        assert isinstance(metrics['is_connected'], bool)
        assert metrics['connected_components'] >= 1
    
    @pytest.mark.asyncio
    async def test_calculate_centrality_metrics(self, graph_worker, sample_graph):
        """Test calculation of centrality metrics."""
        metrics = await graph_worker.calculate_centrality_metrics(sample_graph)
        
        # Check that all centrality measures are calculated
        assert 'in_degree_centrality' in metrics
        assert 'out_degree_centrality' in metrics
        assert 'betweenness_centrality' in metrics
        assert 'closeness_centrality' in metrics
        assert 'pagerank' in metrics
        assert 'top_nodes' in metrics
        
        # Check that centrality values are reasonable
        for centrality_type in ['in_degree_centrality', 'out_degree_centrality', 
                               'betweenness_centrality', 'closeness_centrality', 'pagerank']:
            centrality_values = metrics[centrality_type]
            assert len(centrality_values) == 5  # 5 nodes
            assert all(0 <= value <= 1 for value in centrality_values.values())
    
    @pytest.mark.asyncio
    async def test_calculate_decay_metrics(self, graph_worker, sample_graph):
        """Test calculation of citation decay metrics."""
        metrics = await graph_worker.calculate_decay_metrics(sample_graph)
        
        # Check that decay metrics are calculated
        assert 'decay_scores' in metrics
        assert 'decay_pagerank' in metrics
        assert 'age_statistics' in metrics
        assert 'top_decay_nodes' in metrics
        
        # Check decay scores
        decay_scores = metrics['decay_scores']
        assert len(decay_scores) == 5  # 5 edges
        assert all(0 < score <= 1 for score in decay_scores.values())
        
        # Check age statistics
        age_stats = metrics['age_statistics']
        assert 'mean_age_days' in age_stats
        assert 'median_age_days' in age_stats
        assert 'oldest_citation_days' in age_stats
        assert 'newest_citation_days' in age_stats
    
    @pytest.mark.asyncio
    async def test_calculate_graph_metrics(self, graph_worker, sample_graph):
        """Test comprehensive graph metrics calculation."""
        metrics = await graph_worker.calculate_graph_metrics(sample_graph, 'citations')
        
        # Check that all metric types are included
        assert 'basic' in metrics
        assert 'centrality' in metrics
        assert 'decay' in metrics
        assert 'graph_type' in metrics
        assert 'calculated_at' in metrics
        
        # Check basic metrics
        basic = metrics['basic']
        assert basic['node_count'] == 5
        assert basic['edge_count'] == 5
        
        # Check centrality metrics
        centrality = metrics['centrality']
        assert 'pagerank' in centrality
        assert 'top_nodes' in centrality
        
        # Check decay metrics
        decay = metrics['decay']
        assert 'decay_pagerank' in decay
        assert 'age_statistics' in decay
    
    @pytest.mark.asyncio
    async def test_handle_graph_analysis(self, graph_worker):
        """Test handling of graph analysis requests."""
        # Mock message data
        msg = Mock()
        msg.data.decode.return_value = json.dumps({
            'analysis_id': 'test_analysis_1',
            'patent_ids': ['patent_1', 'patent_2', 'patent_3'],
            'graph_type': 'citations',
            'include_metrics': True
        })
        
        # Mock database and storage methods
        with patch.object(graph_worker.db, 'get_patent_citations', return_value=[]):
            with patch.object(graph_worker.db, 'store_graph_analysis', return_value=True):
                with patch.object(graph_worker, 'publish') as mock_publish:
                    await graph_worker.handle_graph_analysis(msg)
                    
                    # Check that completion event was published
                    mock_publish.assert_called_once()
                    call_args = mock_publish.call_args[0]
                    assert call_args[0] == "graph.analysis.complete"
                    assert call_args[1]['analysis_id'] == 'test_analysis_1'
                    assert call_args[1]['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_metrics_request(self, graph_worker):
        """Test handling of metrics calculation requests."""
        # Mock message data
        msg = Mock()
        msg.data.decode.return_value = json.dumps({
            'metrics_id': 'test_metrics_1',
            'patent_ids': ['patent_1', 'patent_2', 'patent_3'],
            'metric_types': ['centrality', 'decay']
        })
        
        # Mock database and storage methods
        with patch.object(graph_worker.db, 'get_patent_citations', return_value=[]):
            with patch.object(graph_worker.db, 'store_graph_metrics', return_value=True):
                with patch.object(graph_worker, 'publish') as mock_publish:
                    await graph_worker.handle_metrics_request(msg)
                    
                    # Check that completion event was published
                    mock_publish.assert_called_once()
                    call_args = mock_publish.call_args[0]
                    assert call_args[0] == "graph.metrics.complete"
                    assert call_args[1]['metrics_id'] == 'test_metrics_1'
                    assert call_args[1]['status'] == 'success'
    
    def test_graph_worker_initialization(self, graph_worker):
        """Test GraphWorker initialization."""
        assert graph_worker.db is not None
        assert graph_worker.storage is not None
        assert graph_worker.nats_url == "nats://localhost:4222"


def test_networkx_import():
    """Test that networkx is properly imported and functional."""
    # Test basic networkx functionality
    graph = nx.DiGraph()
    graph.add_edge('A', 'B')
    graph.add_edge('B', 'C')
    
    # Test centrality calculation
    pagerank = nx.pagerank(graph)
    assert len(pagerank) == 3
    assert all(0 <= score <= 1 for score in pagerank.values())
    
    # Test graph properties
    assert len(graph.nodes()) == 3
    assert len(graph.edges()) == 2
    assert nx.is_weakly_connected(graph)


if __name__ == "__main__":
    pytest.main([__file__])
