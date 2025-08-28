import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from ..base import BaseWorker
from ...utils.database import DatabaseClient
from ...utils.storage import StorageClient
from ...models.patent import PatentClaim, PatentDocument

logger = logging.getLogger(__name__)


class EmbedWorker(BaseWorker):
    """Worker for generating embeddings for patent claims, clauses, and passages."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        super().__init__(nats_url)
        self.db = DatabaseClient()
        self.storage = StorageClient()
        
        # Initialize sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Embedding dimensions
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        
        logger.info(f"EmbedWorker initialized with model on {self.device}")
    
    async def start(self):
        """Start the embed worker."""
        await super().start()
        await self.db.connect()
        await self.storage.connect()
        
        # Subscribe to embedding requests
        await self.subscribe("patent.embed", self.handle_embed_request)
        await self.subscribe("index.upsert", self.handle_index_upsert)
        
        logger.info("EmbedWorker started and listening for requests")
    
    async def stop(self):
        """Stop the embed worker."""
        await self.db.disconnect()
        await self.storage.disconnect()
        await super().stop()
    
    async def handle_embed_request(self, msg):
        """Handle patent embedding requests."""
        try:
            data = json.loads(msg.data.decode())
            patent_id = data.get('patent_id')
            
            if not patent_id:
                logger.error("Missing patent_id in embed request")
                return
            
            logger.info(f"Processing embedding request for patent {patent_id}")
            
            # Generate embeddings for the patent
            await self.embed_patent(patent_id)
            
            # Publish completion event
            await self.publish("embed.complete", {
                "patent_id": patent_id,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error processing embed request: {e}")
            await self.publish("embed.error", {
                "patent_id": data.get('patent_id'),
                "error": str(e)
            })
    
    async def handle_index_upsert(self, msg):
        """Handle index upsert requests (from normalize worker)."""
        try:
            data = json.loads(msg.data.decode())
            patent_id = data.get('patent_id')
            
            if not patent_id:
                logger.error("Missing patent_id in index upsert request")
                return
            
            logger.info(f"Processing index upsert for patent {patent_id}")
            
            # Generate embeddings and update index
            await self.embed_patent(patent_id)
            
        except Exception as e:
            logger.error(f"Error processing index upsert: {e}")
    
    async def embed_patent(self, patent_id: str):
        """Generate embeddings for all claims, clauses, and passages of a patent."""
        try:
            # Get patent data from database
            patent = await self.db.get_patent(patent_id)
            if not patent:
                logger.error(f"Patent {patent_id} not found")
                return
            
            claims = await self.db.get_patent_claims(patent_id)
            
            # Generate embeddings for claims
            claim_embeddings = await self.embed_claims(claims)
            
            # Generate embeddings for individual clauses
            clause_embeddings = await self.embed_clauses(claims)
            
            # Generate embeddings for passages (abstract, description sections)
            passage_embeddings = await self.embed_passages(patent)
            
            # Update database with embeddings
            await self.db.update_patent_embeddings(
                patent_id=patent_id,
                claim_embeddings=claim_embeddings,
                clause_embeddings=clause_embeddings,
                passage_embeddings=passage_embeddings
            )
            
            # Store embeddings in vector database (pgvector)
            await self.db.upsert_vector_embeddings(
                patent_id=patent_id,
                embeddings={
                    'claims': claim_embeddings,
                    'clauses': clause_embeddings,
                    'passages': passage_embeddings
                }
            )
            
            logger.info(f"Successfully embedded patent {patent_id}")
            
        except Exception as e:
            logger.error(f"Error embedding patent {patent_id}: {e}")
            raise
    
    async def embed_claims(self, claims: List[Dict]) -> Dict[str, np.ndarray]:
        """Generate embeddings for patent claims."""
        claim_embeddings = {}
        
        for claim in claims:
            claim_id = claim['id']
            claim_text = claim['text']
            
            # Clean and prepare claim text
            cleaned_text = self.preprocess_text(claim_text)
            
            # Generate embedding
            embedding = self.model.encode(cleaned_text, convert_to_numpy=True)
            claim_embeddings[claim_id] = embedding
        
        return claim_embeddings
    
    async def embed_clauses(self, claims: List[Dict]) -> Dict[str, np.ndarray]:
        """Generate embeddings for individual claim clauses."""
        clause_embeddings = {}
        
        for claim in claims:
            claim_id = claim['id']
            clauses = claim.get('clauses', [])
            
            for i, clause in enumerate(clauses):
                clause_id = f"{claim_id}_clause_{i}"
                clause_text = clause.get('text', '')
                
                if clause_text.strip():
                    # Clean and prepare clause text
                    cleaned_text = self.preprocess_text(clause_text)
                    
                    # Generate embedding
                    embedding = self.model.encode(cleaned_text, convert_to_numpy=True)
                    clause_embeddings[clause_id] = embedding
        
        return clause_embeddings
    
    async def embed_passages(self, patent: Dict) -> Dict[str, np.ndarray]:
        """Generate embeddings for patent passages (abstract, description sections)."""
        passage_embeddings = {}
        
        # Abstract
        if patent.get('abstract'):
            abstract_text = self.preprocess_text(patent['abstract'])
            abstract_embedding = self.model.encode(abstract_text, convert_to_numpy=True)
            passage_embeddings['abstract'] = abstract_embedding
        
        # Description sections (if available)
        description = patent.get('description', '')
        if description:
            # Split description into chunks for better embedding
            chunks = self.chunk_text(description, max_length=512)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"description_chunk_{i}"
                cleaned_chunk = self.preprocess_text(chunk)
                chunk_embedding = self.model.encode(cleaned_chunk, convert_to_numpy=True)
                passage_embeddings[chunk_id] = chunk_embedding
        
        return passage_embeddings
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding generation."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters that might interfere with embedding
        # Keep alphanumeric, spaces, and basic punctuation
        import re
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', ' ', text)
        
        # Limit length to prevent token overflow
        max_tokens = 512
        words = text.split()
        if len(words) > max_tokens:
            text = ' '.join(words[:max_tokens])
        
        return text.strip()
    
    def chunk_text(self, text: str, max_length: int = 512) -> List[str]:
        """Split text into chunks for embedding."""
        words = text.split()
        chunks = []
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_length:
                current_chunk.append(word)
                current_length += len(word) + 1
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks


async def main():
    """Main entry point for the embed worker."""
    worker = EmbedWorker()
    
    try:
        await worker.start()
        
        # Keep the worker running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down embed worker...")
    finally:
        await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
