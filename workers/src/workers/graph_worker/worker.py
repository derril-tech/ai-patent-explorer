import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import networkx as nx
import numpy as np
from datetime import datetime, timedelta

from ..base import BaseWorker
from ...utils.database import DatabaseClient
from ...utils.storage import StorageClient

logger = logging.getLogger(__name__)


class GraphWorker(BaseWorker):
    """Worker for citation graph analysis and metrics."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        super().__init__(nats_url)
        self.db = DatabaseClient()
        self.storage = StorageClient()
        
        logger.info("GraphWorker initialized")
    
    async def start(self):
        """Start the graph worker."""
        await super().start()
        await self.db.connect()
        await self.storage.connect()
        
        # Subscribe to graph analysis requests
        await self.subscribe("graph.analyze", self.handle_graph_analysis)
        await self.subscribe("graph.metrics", self.handle_metrics_request)
        
        logger.info("GraphWorker started and listening for requests")
    
    async def stop(self):
        """Stop the graph worker."""
        await self.db.disconnect()
        await self.storage.disconnect()
        await super().stop()
    
    async def handle_graph_analysis(self, msg):
        """Handle citation graph analysis requests."""
        try:
            data = json.loads(msg.data.decode())
            analysis_id = data.get('analysis_id')
            patent_ids = data.get('patent_ids', [])
            graph_type = data.get('graph_type', 'citations')  # citations or family
            include_metrics = data.get('include_metrics', True)
            
            if not all([analysis_id, patent_ids]):
                logger.error("Missing required fields in graph analysis request")
                return
            
            logger.info(f"Processing graph analysis {analysis_id} for {len(patent_ids)} patents")
            
            # Build citation graph
            graph = await self.build_citation_graph(patent_ids, graph_type)
            
            # Calculate metrics if requested
            metrics = None
            if include_metrics:
                metrics = await self.calculate_graph_metrics(graph, graph_type)
            
            # Store analysis results
            await self.store_graph_analysis(analysis_id, patent_ids, graph_type, graph, metrics)
            
            # Publish completion event
            await self.publish("graph.analysis.complete", {
                "analysis_id": analysis_id,
                "patent_ids": patent_ids,
                "graph_type": graph_type,
                "node_count": len(graph.nodes()),
                "edge_count": len(graph.edges()),
                "metrics": metrics,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error processing graph analysis: {e}")
            await self.publish("graph.analysis.error", {
                "analysis_id": data.get('analysis_id'),
                "error": str(e)
            })
    
    async def handle_metrics_request(self, msg):
        """Handle graph metrics calculation requests."""
        try:
            data = json.loads(msg.data.decode())
            metrics_id = data.get('metrics_id')
            patent_ids = data.get('patent_ids', [])
            metric_types = data.get('metric_types', ['centrality', 'decay'])
            
            if not all([metrics_id, patent_ids]):
                logger.error("Missing required fields in metrics request")
                return
            
            logger.info(f"Processing metrics request {metrics_id} for {len(patent_ids)} patents")
            
            # Build graph
            graph = await self.build_citation_graph(patent_ids, 'citations')
            
            # Calculate requested metrics
            metrics = {}
            if 'centrality' in metric_types:
                metrics['centrality'] = await self.calculate_centrality_metrics(graph)
            
            if 'decay' in metric_types:
                metrics['decay'] = await self.calculate_decay_metrics(graph)
            
            # Store metrics
            await self.store_graph_metrics(metrics_id, patent_ids, metrics)
            
            # Publish completion event
            await self.publish("graph.metrics.complete", {
                "metrics_id": metrics_id,
                "patent_ids": patent_ids,
                "metrics": metrics,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error processing metrics request: {e}")
            await self.publish("graph.metrics.error", {
                "metrics_id": data.get('metrics_id'),
                "error": str(e)
            })
    
    async def build_citation_graph(self, patent_ids: List[str], graph_type: str) -> nx.DiGraph:
        """Build citation graph from patent IDs."""
        try:
            graph = nx.DiGraph()
            
            # Add nodes for all patents
            for patent_id in patent_ids:
                graph.add_node(patent_id)
            
            # Get citation relationships
            if graph_type == 'citations':
                citations = await self.db.get_patent_citations(patent_ids)
                
                for citation in citations:
                    citing_patent = citation['citing_patent_id']
                    cited_patent = citation['cited_patent_id']
                    
                    if citing_patent in patent_ids and cited_patent in patent_ids:
                        graph.add_edge(citing_patent, cited_patent, 
                                     weight=citation.get('citation_strength', 1.0),
                                     date=citation.get('citation_date'))
            
            elif graph_type == 'family':
                families = await self.db.get_patent_families(patent_ids)
                
                for family in families:
                    family_patents = family['patent_ids']
                    for i, patent1 in enumerate(family_patents):
                        for patent2 in family_patents[i+1:]:
                            if patent1 in patent_ids and patent2 in patent_ids:
                                graph.add_edge(patent1, patent2, 
                                             weight=1.0,
                                             relationship='family')
            
            logger.info(f"Built {graph_type} graph with {len(graph.nodes())} nodes and {len(graph.edges())} edges")
            return graph
            
        except Exception as e:
            logger.error(f"Error building citation graph: {e}")
            raise
    
    async def calculate_graph_metrics(self, graph: nx.DiGraph, graph_type: str) -> Dict[str, Any]:
        """Calculate comprehensive graph metrics."""
        try:
            metrics = {
                'basic': await self.calculate_basic_metrics(graph),
                'centrality': await self.calculate_centrality_metrics(graph),
                'decay': await self.calculate_decay_metrics(graph),
                'graph_type': graph_type,
                'calculated_at': datetime.utcnow().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating graph metrics: {e}")
            raise
    
    async def calculate_basic_metrics(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Calculate basic graph metrics."""
        try:
            return {
                'node_count': len(graph.nodes()),
                'edge_count': len(graph.edges()),
                'density': nx.density(graph),
                'is_connected': nx.is_weakly_connected(graph),
                'connected_components': nx.number_weakly_connected_components(graph),
                'average_clustering': nx.average_clustering(graph),
                'average_shortest_path': nx.average_shortest_path_length(graph) if nx.is_weakly_connected(graph) else None
            }
        except Exception as e:
            logger.error(f"Error calculating basic metrics: {e}")
            return {}
    
    async def calculate_centrality_metrics(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Calculate centrality metrics for nodes."""
        try:
            # In-degree centrality (how many patents cite this one)
            in_degree_centrality = nx.in_degree_centrality(graph)
            
            # Out-degree centrality (how many patents this one cites)
            out_degree_centrality = nx.out_degree_centrality(graph)
            
            # Betweenness centrality (importance as a bridge)
            betweenness_centrality = nx.betweenness_centrality(graph)
            
            # Closeness centrality (average distance to other nodes)
            closeness_centrality = nx.closeness_centrality(graph)
            
            # PageRank (importance based on citations)
            pagerank = nx.pagerank(graph)
            
            # Find top nodes for each metric
            top_nodes = {
                'in_degree': sorted(in_degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10],
                'out_degree': sorted(out_degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10],
                'betweenness': sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:10],
                'closeness': sorted(closeness_centrality.items(), key=lambda x: x[1], reverse=True)[:10],
                'pagerank': sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:10]
            }
            
            return {
                'in_degree_centrality': in_degree_centrality,
                'out_degree_centrality': out_degree_centrality,
                'betweenness_centrality': betweenness_centrality,
                'closeness_centrality': closeness_centrality,
                'pagerank': pagerank,
                'top_nodes': top_nodes
            }
            
        except Exception as e:
            logger.error(f"Error calculating centrality metrics: {e}")
            return {}
    
    async def calculate_decay_metrics(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Calculate citation decay metrics."""
        try:
            # Get edge dates if available
            edge_dates = {}
            for edge in graph.edges(data=True):
                if 'date' in edge[2]:
                    edge_dates[edge[:2]] = edge[2]['date']
            
            if not edge_dates:
                return {'error': 'No date information available for decay analysis'}
            
            # Calculate time-based decay
            current_date = datetime.utcnow()
            decay_scores = {}
            
            for edge, date_str in edge_dates.items():
                try:
                    edge_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    days_old = (current_date - edge_date).days
                    
                    # Exponential decay: older citations have lower weight
                    decay_factor = np.exp(-days_old / 365.25)  # 1 year half-life
                    decay_scores[edge] = decay_factor
                    
                except (ValueError, TypeError):
                    decay_scores[edge] = 1.0  # Default weight for invalid dates
            
            # Calculate decay-weighted centrality
            decay_weighted_graph = graph.copy()
            for edge in decay_weighted_graph.edges():
                if edge in decay_scores:
                    decay_weighted_graph[edge[0]][edge[1]]['weight'] *= decay_scores[edge]
            
            decay_pagerank = nx.pagerank(decay_weighted_graph)
            
            # Calculate citation age distribution
            citation_ages = []
            for date_str in edge_dates.values():
                try:
                    edge_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    days_old = (current_date - edge_date).days
                    citation_ages.append(days_old)
                except (ValueError, TypeError):
                    continue
            
            age_stats = {
                'mean_age_days': np.mean(citation_ages) if citation_ages else 0,
                'median_age_days': np.median(citation_ages) if citation_ages else 0,
                'oldest_citation_days': max(citation_ages) if citation_ages else 0,
                'newest_citation_days': min(citation_ages) if citation_ages else 0
            }
            
            return {
                'decay_scores': decay_scores,
                'decay_pagerank': decay_pagerank,
                'age_statistics': age_stats,
                'top_decay_nodes': sorted(decay_pagerank.items(), key=lambda x: x[1], reverse=True)[:10]
            }
            
        except Exception as e:
            logger.error(f"Error calculating decay metrics: {e}")
            return {'error': str(e)}
    
    async def store_graph_analysis(self, analysis_id: str, patent_ids: List[str], 
                                 graph_type: str, graph: nx.DiGraph, metrics: Dict[str, Any]):
        """Store graph analysis results."""
        try:
            # Convert graph to serializable format
            graph_data = {
                'nodes': list(graph.nodes()),
                'edges': list(graph.edges(data=True)),
                'graph_type': graph_type,
                'patent_ids': patent_ids,
                'metrics': metrics,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Store in database
            await self.db.store_graph_analysis(analysis_id, graph_data)
            
            # Store graph data in storage for larger graphs
            if len(graph.nodes()) > 1000:
                graph_json = json.dumps(graph_data)
                await self.storage.upload_file(
                    f"graphs/{analysis_id}.json",
                    graph_json.encode(),
                    "application/json"
                )
            
            logger.info(f"Stored graph analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error storing graph analysis: {e}")
            raise
    
    async def store_graph_metrics(self, metrics_id: str, patent_ids: List[str], 
                                metrics: Dict[str, Any]):
        """Store graph metrics results."""
        try:
            metrics_data = {
                'metrics_id': metrics_id,
                'patent_ids': patent_ids,
                'metrics': metrics,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Store in database
            await self.db.store_graph_metrics(metrics_id, metrics_data)
            
            logger.info(f"Stored graph metrics {metrics_id}")
            
        except Exception as e:
            logger.error(f"Error storing graph metrics: {e}")
            raise


async def main():
    """Main entry point for the graph worker."""
    worker = GraphWorker()
    
    try:
        await worker.start()
        
        # Keep the worker running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down graph worker...")
    finally:
        await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
