import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import torch

from ..base import BaseWorker
from ...utils.database import DatabaseClient
from ...utils.storage import StorageClient

logger = logging.getLogger(__name__)


class RetrieveWorker(BaseWorker):
    """Worker for hybrid retrieval combining BM25 and dense embeddings with reranking."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        super().__init__(nats_url)
        self.db = DatabaseClient()
        self.storage = StorageClient()
        
        # Initialize models
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # BM25 corpus and model
        self.bm25_corpus = {}
        self.bm25_model = None
        
        logger.info(f"RetrieveWorker initialized with models on {self.device}")
    
    async def start(self):
        """Start the retrieve worker."""
        await super().start()
        await self.db.connect()
        await self.storage.connect()
        
        # Subscribe to search requests
        await self.subscribe("search.request", self.handle_search_request)
        
        # Initialize BM25 corpus
        await self.build_bm25_corpus()
        
        logger.info("RetrieveWorker started and listening for requests")
    
    async def stop(self):
        """Stop the retrieve worker."""
        await self.db.disconnect()
        await self.storage.disconnect()
        await super().stop()
    
    async def handle_search_request(self, msg):
        """Handle search requests."""
        try:
            data = json.loads(msg.data.decode())
            search_id = data.get('search_id')
            query = data.get('query')
            workspace_id = data.get('workspace_id')
            filters = data.get('filters', {})
            k = data.get('k', 10)
            search_type = data.get('search_type', 'hybrid')
            
            if not all([search_id, query, workspace_id]):
                logger.error("Missing required fields in search request")
                return
            
            logger.info(f"Processing search request {search_id} for query: {query}")
            
            # Perform search based on type
            if search_type == 'hybrid':
                results = await self.hybrid_search(query, workspace_id, filters, k)
            elif search_type == 'bm25':
                results = await self.bm25_search(query, workspace_id, filters, k)
            elif search_type == 'dense':
                results = await self.dense_search(query, workspace_id, filters, k)
            else:
                logger.error(f"Invalid search type: {search_type}")
                return
            
            # Rerank results
            reranked_results = await self.rerank_results(query, results)
            
            # Publish results
            await self.publish("search.complete", {
                "search_id": search_id,
                "query": query,
                "results": reranked_results,
                "total": len(reranked_results)
            })
            
        except Exception as e:
            logger.error(f"Error processing search request: {e}")
            await self.publish("search.error", {
                "search_id": data.get('search_id'),
                "error": str(e)
            })
    
    async def build_bm25_corpus(self):
        """Build BM25 corpus from all patents in the database."""
        try:
            # Get all patent texts for BM25 indexing
            patents = await self.db.get_all_patents_for_search()
            
            corpus = []
            doc_ids = []
            
            for patent in patents:
                # Combine title, abstract, and claims for BM25
                text = f"{patent.get('title', '')} {patent.get('abstract', '')}"
                
                # Add claims text
                claims = await self.db.get_patent_claims(patent['id'])
                for claim in claims:
                    text += f" {claim.get('text', '')}"
                
                # Tokenize text
                tokens = self.tokenize_text(text)
                if tokens:
                    corpus.append(tokens)
                    doc_ids.append(patent['id'])
            
            # Build BM25 model
            if corpus:
                self.bm25_model = BM25Okapi(corpus)
                self.bm25_corpus = {doc_id: tokens for doc_id, tokens in zip(doc_ids, corpus)}
                
                logger.info(f"Built BM25 corpus with {len(corpus)} documents")
            
        except Exception as e:
            logger.error(f"Error building BM25 corpus: {e}")
    
    async def hybrid_search(self, query: str, workspace_id: str, filters: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        """Perform hybrid search combining BM25 and dense retrieval."""
        try:
            # Get BM25 results
            bm25_results = await self.bm25_search(query, workspace_id, filters, k * 2)
            
            # Get dense results
            dense_results = await self.dense_search(query, workspace_id, filters, k * 2)
            
            # Combine and deduplicate results
            combined_results = self.combine_results(bm25_results, dense_results, k)
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []
    
    async def bm25_search(self, query: str, workspace_id: str, filters: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search."""
        try:
            if not self.bm25_model:
                logger.warning("BM25 model not initialized")
                return []
            
            # Tokenize query
            query_tokens = self.tokenize_text(query)
            if not query_tokens:
                return []
            
            # Get BM25 scores
            scores = self.bm25_model.get_scores(query_tokens)
            
            # Get top k document indices
            top_indices = np.argsort(scores)[::-1][:k]
            
            # Get patent details for top results
            results = []
            doc_ids = list(self.bm25_corpus.keys())
            
            for idx in top_indices:
                if idx < len(doc_ids):
                    patent_id = doc_ids[idx]
                    patent = await self.db.get_patent(patent_id)
                    
                    if patent and patent.get('workspace_id') == workspace_id:
                        # Apply filters
                        if self.apply_filters(patent, filters):
                            results.append({
                                'patent_id': patent_id,
                                'score': float(scores[idx]),
                                'search_type': 'bm25',
                                'patent': patent
                            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in BM25 search: {e}")
            return []
    
    async def dense_search(self, query: str, workspace_id: str, filters: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        """Perform dense vector search."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query, convert_to_numpy=True)
            
            # Search by embedding
            results = await self.db.search_by_embedding(
                query_embedding=query_embedding,
                workspace_id=workspace_id,
                search_type='claims',
                limit=k * 2
            )
            
            # Get full patent details and apply filters
            filtered_results = []
            for result in results:
                patent = await self.db.get_patent(result['patent_id'])
                
                if patent and self.apply_filters(patent, filters):
                    filtered_results.append({
                        'patent_id': result['patent_id'],
                        'score': result['similarity'],
                        'search_type': 'dense',
                        'patent': patent,
                        'claim': result
                    })
            
            return filtered_results[:k]
            
        except Exception as e:
            logger.error(f"Error in dense search: {e}")
            return []
    
    async def rerank_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank results using cross-encoder."""
        try:
            if not results:
                return []
            
            # Prepare pairs for cross-encoder
            pairs = []
            for result in results:
                patent = result['patent']
                text = f"{patent.get('title', '')} {patent.get('abstract', '')}"
                
                # Add claim text if available
                if 'claim' in result:
                    text += f" {result['claim'].get('text', '')}"
                
                pairs.append([query, text])
            
            # Get cross-encoder scores
            scores = self.cross_encoder.predict(pairs)
            
            # Update results with reranked scores
            for i, result in enumerate(results):
                result['rerank_score'] = float(scores[i])
                result['final_score'] = (result.get('score', 0) + result['rerank_score']) / 2
            
            # Sort by final score
            results.sort(key=lambda x: x['final_score'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in reranking: {e}")
            return results
    
    def combine_results(self, bm25_results: List[Dict[str, Any]], dense_results: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """Combine and deduplicate BM25 and dense results."""
        try:
            # Create a map of patent_id to results
            combined_map = {}
            
            # Add BM25 results
            for result in bm25_results:
                patent_id = result['patent_id']
                if patent_id not in combined_map:
                    combined_map[patent_id] = result
                else:
                    # Average scores if patent appears in both
                    existing = combined_map[patent_id]
                    combined_map[patent_id]['score'] = (existing['score'] + result['score']) / 2
                    combined_map[patent_id]['search_type'] = 'hybrid'
            
            # Add dense results
            for result in dense_results:
                patent_id = result['patent_id']
                if patent_id not in combined_map:
                    combined_map[patent_id] = result
                else:
                    # Average scores if patent appears in both
                    existing = combined_map[patent_id]
                    combined_map[patent_id]['score'] = (existing['score'] + result['score']) / 2
                    combined_map[patent_id]['search_type'] = 'hybrid'
            
            # Convert back to list and sort by score
            combined_results = list(combined_map.values())
            combined_results.sort(key=lambda x: x['score'], reverse=True)
            
            return combined_results[:k]
            
        except Exception as e:
            logger.error(f"Error combining results: {e}")
            return bm25_results[:k] if bm25_results else dense_results[:k]
    
    def tokenize_text(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        if not text:
            return []
        
        # Convert to lowercase and split on whitespace
        tokens = text.lower().split()
        
        # Remove short tokens and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tokens = [token for token in tokens if len(token) > 2 and token not in stop_words]
        
        return tokens
    
    def apply_filters(self, patent: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Apply search filters to patent."""
        try:
            # Date range filter
            if 'date_from' in filters and patent.get('prio_date'):
                if patent['prio_date'] < filters['date_from']:
                    return False
            
            if 'date_to' in filters and patent.get('prio_date'):
                if patent['prio_date'] > filters['date_to']:
                    return False
            
            # CPC filter
            if 'cpc_codes' in filters and patent.get('cpc_codes'):
                patent_cpcs = set(patent['cpc_codes'])
                filter_cpcs = set(filters['cpc_codes'])
                if not patent_cpcs.intersection(filter_cpcs):
                    return False
            
            # Assignee filter
            if 'assignees' in filters and patent.get('assignees'):
                patent_assignees = set(patent['assignees'])
                filter_assignees = set(filters['assignees'])
                if not patent_assignees.intersection(filter_assignees):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return True


async def main():
    """Main entry point for the retrieve worker."""
    worker = RetrieveWorker()
    
    try:
        await worker.start()
        
        # Keep the worker running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down retrieve worker...")
    finally:
        await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
