import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import torch

from ..base import BaseWorker
from ...utils.database import DatabaseClient
from ...utils.storage import StorageClient

logger = logging.getLogger(__name__)


class AlignWorker(BaseWorker):
    """Worker for per-clause alignment using soft-TFIDF and embedding dynamic programming."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        super().__init__(nats_url)
        self.db = DatabaseClient()
        self.storage = StorageClient()
        
        # Initialize models
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=10000,
            stop_words='english',
            min_df=2
        )
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"AlignWorker initialized with models on {self.device}")
    
    async def start(self):
        """Start the align worker."""
        await super().start()
        await self.db.connect()
        await self.storage.connect()
        
        # Subscribe to alignment requests
        await self.subscribe("patent.align", self.handle_align_request)
        
        logger.info("AlignWorker started and listening for requests")
    
    async def stop(self):
        """Stop the align worker."""
        await self.db.disconnect()
        await self.storage.disconnect()
        await super().stop()
    
    async def handle_align_request(self, msg):
        """Handle patent alignment requests."""
        try:
            data = json.loads(msg.data.decode())
            align_id = data.get('align_id')
            patent_id = data.get('patent_id')
            claim_num = data.get('claim_num')
            reference_patents = data.get('reference_patents', [])
            
            if not all([align_id, patent_id, claim_num]):
                logger.error("Missing required fields in align request")
                return
            
            logger.info(f"Processing alignment request {align_id} for patent {patent_id}, claim {claim_num}")
            
            # Perform alignment
            alignment_results = await self.align_claim_clauses(
                patent_id, claim_num, reference_patents
            )
            
            # Publish completion event
            await self.publish("align.complete", {
                "align_id": align_id,
                "patent_id": patent_id,
                "claim_num": claim_num,
                "results": alignment_results,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error processing align request: {e}")
            await self.publish("align.error", {
                "align_id": data.get('align_id'),
                "error": str(e)
            })
    
    async def align_claim_clauses(
        self, 
        patent_id: str, 
        claim_num: int, 
        reference_patents: List[str]
    ) -> Dict[str, Any]:
        """Align clauses of a claim with reference patents."""
        try:
            # Get the target claim
            target_claim = await self.db.get_claim(patent_id, claim_num)
            if not target_claim:
                raise ValueError(f"Claim {claim_num} not found for patent {patent_id}")
            
            # Segment the claim into clauses
            target_clauses = self.segment_claim_into_clauses(target_claim['text'])
            
            # Get reference claims from reference patents
            reference_claims = []
            for ref_patent_id in reference_patents:
                ref_patent_claims = await self.db.get_patent_claims(ref_patent_id)
                for claim in ref_patent_claims:
                    reference_claims.append({
                        'patent_id': ref_patent_id,
                        'claim_id': claim['id'],
                        'claim_number': claim['claim_number'],
                        'text': claim['text'],
                        'clauses': self.segment_claim_into_clauses(claim['text'])
                    })
            
            # Perform alignment for each target clause
            alignment_results = []
            for i, target_clause in enumerate(target_clauses):
                clause_alignments = await self.align_single_clause(
                    target_clause, reference_claims, i
                )
                alignment_results.append({
                    'clause_index': i,
                    'clause_text': target_clause,
                    'alignments': clause_alignments
                })
            
            # Store alignment results in database
            await self.store_alignment_results(
                patent_id, claim_num, alignment_results
            )
            
            return {
                'patent_id': patent_id,
                'claim_num': claim_num,
                'target_clauses': target_clauses,
                'reference_patents': reference_patents,
                'alignments': alignment_results
            }
            
        except Exception as e:
            logger.error(f"Error aligning claim clauses: {e}")
            raise
    
    async def align_single_clause(
        self, 
        target_clause: str, 
        reference_claims: List[Dict], 
        clause_index: int
    ) -> List[Dict[str, Any]]:
        """Align a single clause with all reference claims."""
        alignments = []
        
        for ref_claim in reference_claims:
            # Get best alignment for each reference claim
            best_alignment = await self.find_best_alignment(
                target_clause, ref_claim['clauses'], ref_claim
            )
            
            if best_alignment:
                alignments.append({
                    'reference_patent_id': ref_claim['patent_id'],
                    'reference_claim_id': ref_claim['claim_id'],
                    'reference_claim_number': ref_claim['claim_number'],
                    'reference_clause_index': best_alignment['clause_index'],
                    'reference_clause_text': best_alignment['clause_text'],
                    'similarity_score': best_alignment['similarity_score'],
                    'alignment_type': best_alignment['alignment_type'],
                    'overlap_details': best_alignment['overlap_details']
                })
        
        # Sort by similarity score
        alignments.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return alignments
    
    async def find_best_alignment(
        self, 
        target_clause: str, 
        reference_clauses: List[str], 
        ref_claim: Dict
    ) -> Optional[Dict[str, Any]]:
        """Find the best alignment for a target clause among reference clauses."""
        best_alignment = None
        best_score = 0.0
        
        for i, ref_clause in enumerate(reference_clauses):
            # Calculate multiple similarity metrics
            tfidf_similarity = self.calculate_tfidf_similarity(target_clause, ref_clause)
            embedding_similarity = await self.calculate_embedding_similarity(target_clause, ref_clause)
            
            # Combined similarity score (weighted average)
            combined_score = 0.6 * embedding_similarity + 0.4 * tfidf_similarity
            
            if combined_score > best_score:
                best_score = combined_score
                best_alignment = {
                    'clause_index': i,
                    'clause_text': ref_clause,
                    'similarity_score': combined_score,
                    'tfidf_score': tfidf_similarity,
                    'embedding_score': embedding_similarity,
                    'alignment_type': self.determine_alignment_type(combined_score),
                    'overlap_details': self.analyze_overlap(target_clause, ref_clause)
                }
        
        return best_alignment
    
    def calculate_tfidf_similarity(self, text1: str, text2: str) -> float:
        """Calculate TF-IDF similarity between two texts."""
        try:
            # Prepare texts for TF-IDF
            texts = [text1, text2]
            
            # Fit and transform
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error calculating TF-IDF similarity: {e}")
            return 0.0
    
    async def calculate_embedding_similarity(self, text1: str, text2: str) -> float:
        """Calculate embedding similarity between two texts."""
        try:
            # Generate embeddings
            embedding1 = self.embedding_model.encode(text1, convert_to_numpy=True)
            embedding2 = self.embedding_model.encode(text2, convert_to_numpy=True)
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error calculating embedding similarity: {e}")
            return 0.0
    
    def determine_alignment_type(self, similarity_score: float) -> str:
        """Determine the type of alignment based on similarity score."""
        if similarity_score >= 0.8:
            return "exact_match"
        elif similarity_score >= 0.6:
            return "high_similarity"
        elif similarity_score >= 0.4:
            return "moderate_similarity"
        elif similarity_score >= 0.2:
            return "low_similarity"
        else:
            return "no_match"
    
    def analyze_overlap(self, text1: str, text2: str) -> Dict[str, Any]:
        """Analyze overlap between two texts."""
        # Tokenize texts
        tokens1 = set(self.tokenize_text(text1))
        tokens2 = set(self.tokenize_text(text2))
        
        # Calculate overlap metrics
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        # Find overlapping phrases
        overlapping_phrases = self.find_overlapping_phrases(text1, text2)
        
        return {
            'jaccard_similarity': jaccard_similarity,
            'overlapping_tokens': list(intersection),
            'overlapping_phrases': overlapping_phrases,
            'text1_unique': list(tokens1 - tokens2),
            'text2_unique': list(tokens2 - tokens1)
        }
    
    def find_overlapping_phrases(self, text1: str, text2: str) -> List[str]:
        """Find overlapping phrases between two texts."""
        phrases = []
        
        # Extract n-grams from both texts
        ngrams1 = self.extract_ngrams(text1, 2, 4)
        ngrams2 = self.extract_ngrams(text2, 2, 4)
        
        # Find common n-grams
        common_ngrams = set(ngrams1).intersection(set(ngrams2))
        
        # Sort by length (longer phrases first)
        phrases = sorted(common_ngrams, key=len, reverse=True)
        
        return phrases[:10]  # Return top 10 overlapping phrases
    
    def extract_ngrams(self, text: str, min_n: int, max_n: int) -> List[str]:
        """Extract n-grams from text."""
        tokens = self.tokenize_text(text)
        ngrams = []
        
        for n in range(min_n, max_n + 1):
            for i in range(len(tokens) - n + 1):
                ngram = ' '.join(tokens[i:i+n])
                ngrams.append(ngram)
        
        return ngrams
    
    def segment_claim_into_clauses(self, claim_text: str) -> List[str]:
        """Segment a patent claim into individual clauses."""
        clauses = []
        
        # Split by common clause separators
        separators = [
            r'\s*;\s*',  # Semicolon
            r'\s*,\s*(?=wherein|wherein\s+the|wherein\s+said|wherein\s+each|wherein\s+at\s+least)',  # Comma before "wherein"
            r'\s*,\s*(?=and\s+wherein|and\s+wherein\s+the|and\s+wherein\s+said)',  # Comma before "and wherein"
            r'\s*,\s*(?=further\s+wherein|further\s+wherein\s+the|further\s+wherein\s+said)',  # Comma before "further wherein"
        ]
        
        # Start with the full claim
        remaining_text = claim_text.strip()
        
        for separator in separators:
            parts = re.split(separator, remaining_text)
            if len(parts) > 1:
                clauses.extend([part.strip() for part in parts if part.strip()])
                break
        else:
            # If no separators found, treat as single clause
            clauses.append(remaining_text)
        
        # Clean up clauses
        cleaned_clauses = []
        for clause in clauses:
            # Remove common prefixes
            clause = re.sub(r'^(\d+\.\s*)?', '', clause)
            clause = clause.strip()
            
            if clause and len(clause) > 10:  # Minimum clause length
                cleaned_clauses.append(clause)
        
        return cleaned_clauses if cleaned_clauses else [claim_text]
    
    def tokenize_text(self, text: str) -> List[str]:
        """Tokenize text for analysis."""
        # Convert to lowercase and remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into tokens
        tokens = text.split()
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
        
        tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
        
        return tokens
    
    async def store_alignment_results(
        self, 
        patent_id: str, 
        claim_num: int, 
        alignment_results: List[Dict]
    ) -> None:
        """Store alignment results in the database."""
        try:
            for alignment in alignment_results:
                clause_index = alignment['clause_index']
                clause_text = alignment['clause_text']
                
                for ref_alignment in alignment['alignments']:
                    # Store alignment record
                    await self.db.create_alignment(
                        patent_id=patent_id,
                        claim_num=claim_num,
                        clause_index=clause_index,
                        clause_text=clause_text,
                        reference_patent_id=ref_alignment['reference_patent_id'],
                        reference_claim_id=ref_alignment['reference_claim_id'],
                        reference_clause_index=ref_alignment['reference_clause_index'],
                        reference_clause_text=ref_alignment['reference_clause_text'],
                        similarity_score=ref_alignment['similarity_score'],
                        alignment_type=ref_alignment['alignment_type'],
                        overlap_details=ref_alignment['overlap_details']
                    )
            
            logger.info(f"Stored alignment results for patent {patent_id}, claim {claim_num}")
            
        except Exception as e:
            logger.error(f"Error storing alignment results: {e}")
            raise


async def main():
    """Main entry point for the align worker."""
    worker = AlignWorker()
    
    try:
        await worker.start()
        
        # Keep the worker running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down align worker...")
    finally:
        await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
