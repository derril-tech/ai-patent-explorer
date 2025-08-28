import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from ..base import BaseWorker
from ...utils.database import DatabaseClient
from ...utils.storage import StorageClient

logger = logging.getLogger(__name__)


class NoveltyWorker(BaseWorker):
    """Worker for calculating novelty scores and obviousness analysis."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        super().__init__(nats_url)
        self.db = DatabaseClient()
        self.storage = StorageClient()
        
        # Initialize models
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"NoveltyWorker initialized with models on {self.device}")
    
    async def start(self):
        """Start the novelty worker."""
        await super().start()
        await self.db.connect()
        await self.storage.connect()
        
        # Subscribe to novelty calculation requests
        await self.subscribe("patent.novelty", self.handle_novelty_request)
        
        logger.info("NoveltyWorker started and listening for requests")
    
    async def stop(self):
        """Stop the novelty worker."""
        await self.db.disconnect()
        await self.storage.disconnect()
        await super().stop()
    
    async def handle_novelty_request(self, msg):
        """Handle novelty calculation requests."""
        try:
            data = json.loads(msg.data.decode())
            novelty_id = data.get('novelty_id')
            patent_id = data.get('patent_id')
            claim_num = data.get('claim_num')
            
            if not all([novelty_id, patent_id, claim_num]):
                logger.error("Missing required fields in novelty request")
                return
            
            logger.info(f"Processing novelty request {novelty_id} for patent {patent_id}, claim {claim_num}")
            
            # Calculate novelty scores
            novelty_results = await self.calculate_novelty_scores(patent_id, claim_num)
            
            # Publish completion event
            await self.publish("novelty.complete", {
                "novelty_id": novelty_id,
                "patent_id": patent_id,
                "claim_num": claim_num,
                "results": novelty_results,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error processing novelty request: {e}")
            await self.publish("novelty.error", {
                "novelty_id": data.get('novelty_id'),
                "error": str(e)
            })
    
    async def calculate_novelty_scores(self, patent_id: str, claim_num: int) -> Dict[str, Any]:
        """Calculate novelty scores for a patent claim."""
        try:
            # Get the target claim and its alignments
            target_claim = await self.db.get_claim(patent_id, claim_num)
            if not target_claim:
                raise ValueError(f"Claim {claim_num} not found for patent {patent_id}")
            
            # Get alignments for this claim
            alignments = await self.db.get_claim_alignments(patent_id, claim_num)
            
            # Calculate clause-level novelty scores
            clause_novelty_scores = await self.calculate_clause_novelty(
                target_claim, alignments
            )
            
            # Calculate claim-level novelty score (weighted aggregate)
            claim_novelty_score = self.calculate_claim_novelty(clause_novelty_scores)
            
            # Calculate obviousness score
            obviousness_score = await self.calculate_obviousness_score(
                patent_id, claim_num, alignments
            )
            
            # Apply calibration by CPC/decade
            calibrated_scores = self.calibrate_scores(
                claim_novelty_score, obviousness_score, target_claim
            )
            
            # Store novelty scores in database
            await self.store_novelty_scores(
                patent_id, claim_num, clause_novelty_scores, 
                claim_novelty_score, obviousness_score, calibrated_scores
            )
            
            return {
                'patent_id': patent_id,
                'claim_num': claim_num,
                'clause_novelty_scores': clause_novelty_scores,
                'claim_novelty_score': claim_novelty_score,
                'obviousness_score': obviousness_score,
                'calibrated_scores': calibrated_scores,
                'confidence_band': self.calculate_confidence_band(calibrated_scores)
            }
            
        except Exception as e:
            logger.error(f"Error calculating novelty scores: {e}")
            raise
    
    async def calculate_clause_novelty(
        self, 
        target_claim: Dict, 
        alignments: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Calculate novelty scores for individual clauses."""
        clause_scores = []
        
        # Group alignments by clause index
        alignments_by_clause = {}
        for alignment in alignments:
            clause_idx = alignment['clause_index']
            if clause_idx not in alignments_by_clause:
                alignments_by_clause[clause_idx] = []
            alignments_by_clause[clause_idx].append(alignment)
        
        # Calculate novelty for each clause
        for clause_idx, clause_alignments in alignments_by_clause.items():
            if not clause_alignments:
                # No alignments found - high novelty
                clause_scores.append({
                    'clause_index': clause_idx,
                    'clause_text': clause_alignments[0]['clause_text'] if clause_alignments else '',
                    'novelty_score': 1.0,
                    'max_similarity': 0.0,
                    'alignment_count': 0,
                    'confidence': 'high'
                })
                continue
            
            # Calculate novelty as 1 - max_similarity
            max_similarity = max(align['similarity_score'] for align in clause_alignments)
            novelty_score = 1.0 - max_similarity
            
            # Calculate confidence based on alignment quality
            confidence = self.calculate_clause_confidence(clause_alignments)
            
            clause_scores.append({
                'clause_index': clause_idx,
                'clause_text': clause_alignments[0]['clause_text'],
                'novelty_score': novelty_score,
                'max_similarity': max_similarity,
                'alignment_count': len(clause_alignments),
                'confidence': confidence,
                'top_alignments': sorted(
                    clause_alignments, 
                    key=lambda x: x['similarity_score'], 
                    reverse=True
                )[:3]
            })
        
        return clause_scores
    
    def calculate_claim_novelty(self, clause_scores: List[Dict[str, Any]]) -> float:
        """Calculate claim-level novelty as weighted aggregate of clause scores."""
        if not clause_scores:
            return 1.0
        
        # Weight clauses by importance (independent claims get higher weight)
        total_weight = 0
        weighted_sum = 0
        
        for clause_score in clause_scores:
            # Simple weighting: first clause (preamble) gets higher weight
            weight = 2.0 if clause_score['clause_index'] == 0 else 1.0
            
            # Adjust weight by confidence
            confidence_multiplier = {
                'high': 1.0,
                'medium': 0.8,
                'low': 0.6
            }.get(clause_score['confidence'], 0.8)
            
            final_weight = weight * confidence_multiplier
            weighted_sum += clause_score['novelty_score'] * final_weight
            total_weight += final_weight
        
        return weighted_sum / total_weight if total_weight > 0 else 1.0
    
    async def calculate_obviousness_score(
        self, 
        patent_id: str, 
        claim_num: int, 
        alignments: List[Dict]
    ) -> float:
        """Calculate obviousness score using multiple factors."""
        try:
            # Get patent metadata
            patent = await self.db.get_patent(patent_id)
            if not patent:
                return 0.5  # Default score
            
            # Factor 1: Multi-document penalty
            unique_ref_patents = len(set(align['reference_patent_id'] for align in alignments))
            multi_doc_penalty = min(unique_ref_patents * 0.1, 0.5)
            
            # Factor 2: Co-citation analysis
            cocitation_score = await self.calculate_cocitation_score(patent_id, alignments)
            
            # Factor 3: Topic coherence
            topic_coherence = await self.calculate_topic_coherence(alignments)
            
            # Factor 4: Temporal proximity
            temporal_factor = self.calculate_temporal_factor(patent, alignments)
            
            # Combine factors
            obviousness_score = (
                0.3 * multi_doc_penalty +
                0.25 * cocitation_score +
                0.25 * topic_coherence +
                0.2 * temporal_factor
            )
            
            return min(obviousness_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating obviousness score: {e}")
            return 0.5
    
    async def calculate_cocitation_score(self, patent_id: str, alignments: List[Dict]) -> float:
        """Calculate co-citation score based on reference patent relationships."""
        try:
            # Get reference patent IDs
            ref_patent_ids = list(set(align['reference_patent_id'] for align in alignments))
            
            if len(ref_patent_ids) < 2:
                return 0.0
            
            # Check for co-citations (patents that cite each other)
            cocitation_count = 0
            total_pairs = 0
            
            for i, ref1 in enumerate(ref_patent_ids):
                for ref2 in ref_patent_ids[i+1:]:
                    total_pairs += 1
                    # Check if patents are in the same family or have similar citations
                    if await self.check_patent_relationship(ref1, ref2):
                        cocitation_count += 1
            
            return cocitation_count / total_pairs if total_pairs > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating co-citation score: {e}")
            return 0.0
    
    async def calculate_topic_coherence(self, alignments: List[Dict]) -> float:
        """Calculate topic coherence among aligned references."""
        try:
            if len(alignments) < 2:
                return 0.0
            
            # Extract reference clause texts
            ref_texts = [align['reference_clause_text'] for align in alignments]
            
            # Calculate pairwise similarities
            similarities = []
            for i, text1 in enumerate(ref_texts):
                for text2 in ref_texts[i+1:]:
                    similarity = await self.calculate_embedding_similarity(text1, text2)
                    similarities.append(similarity)
            
            return np.mean(similarities) if similarities else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating topic coherence: {e}")
            return 0.0
    
    def calculate_temporal_factor(self, patent: Dict, alignments: List[Dict]) -> float:
        """Calculate temporal factor based on patent dates."""
        try:
            if not patent.get('prio_date'):
                return 0.5
            
            target_date = patent['prio_date']
            
            # Calculate average time difference from references
            time_diffs = []
            for alignment in alignments:
                ref_patent = alignment.get('reference_patent')
                if ref_patent and ref_patent.get('prio_date'):
                    diff_days = abs((target_date - ref_patent['prio_date']).days)
                    time_diffs.append(diff_days)
            
            if not time_diffs:
                return 0.5
            
            avg_diff_days = np.mean(time_diffs)
            
            # Normalize: closer dates = higher obviousness
            # 0 days = 1.0, 10 years = 0.0
            max_days = 3650  # 10 years
            temporal_factor = max(0.0, 1.0 - (avg_diff_days / max_days))
            
            return temporal_factor
            
        except Exception as e:
            logger.error(f"Error calculating temporal factor: {e}")
            return 0.5
    
    async def calculate_embedding_similarity(self, text1: str, text2: str) -> float:
        """Calculate embedding similarity between two texts."""
        try:
            embedding1 = self.embedding_model.encode(text1, convert_to_numpy=True)
            embedding2 = self.embedding_model.encode(text2, convert_to_numpy=True)
            
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error calculating embedding similarity: {e}")
            return 0.0
    
    async def check_patent_relationship(self, patent1_id: str, patent2_id: str) -> bool:
        """Check if two patents have a relationship (same family, similar citations, etc.)."""
        try:
            # Get patent metadata
            patent1 = await self.db.get_patent(patent1_id)
            patent2 = await self.db.get_patent(patent2_id)
            
            if not patent1 or not patent2:
                return False
            
            # Check if same family
            if patent1.get('family_id') and patent2.get('family_id'):
                if patent1['family_id'] == patent2['family_id']:
                    return True
            
            # Check if same assignee
            if patent1.get('assignees') and patent2.get('assignees'):
                common_assignees = set(patent1['assignees']) & set(patent2['assignees'])
                if common_assignees:
                    return True
            
            # Check CPC overlap
            if patent1.get('cpc_codes') and patent2.get('cpc_codes'):
                common_cpcs = set(patent1['cpc_codes']) & set(patent2['cpc_codes'])
                if len(common_cpcs) >= 2:  # At least 2 common CPC codes
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking patent relationship: {e}")
            return False
    
    def calculate_clause_confidence(self, alignments: List[Dict]) -> str:
        """Calculate confidence level for a clause based on alignment quality."""
        if not alignments:
            return 'low'
        
        # Calculate average similarity score
        avg_similarity = np.mean([align['similarity_score'] for align in alignments])
        
        # Calculate alignment count
        alignment_count = len(alignments)
        
        # Determine confidence based on scores and count
        if avg_similarity > 0.7 and alignment_count >= 3:
            return 'high'
        elif avg_similarity > 0.5 and alignment_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def calibrate_scores(
        self, 
        novelty_score: float, 
        obviousness_score: float, 
        claim: Dict
    ) -> Dict[str, Any]:
        """Calibrate scores by CPC and decade."""
        try:
            # Get patent metadata for calibration
            patent = claim.get('patent', {})
            cpc_codes = patent.get('cpc_codes', [])
            prio_date = patent.get('prio_date')
            
            # CPC-based calibration factors
            cpc_factor = self.get_cpc_calibration_factor(cpc_codes)
            
            # Decade-based calibration factors
            decade_factor = self.get_decade_calibration_factor(prio_date)
            
            # Apply calibration
            calibrated_novelty = novelty_score * cpc_factor * decade_factor
            calibrated_obviousness = obviousness_score * cpc_factor * decade_factor
            
            return {
                'novelty_score': calibrated_novelty,
                'obviousness_score': calibrated_obviousness,
                'cpc_factor': cpc_factor,
                'decade_factor': decade_factor,
                'confidence_band': self.get_confidence_band(calibrated_novelty, calibrated_obviousness)
            }
            
        except Exception as e:
            logger.error(f"Error calibrating scores: {e}")
            return {
                'novelty_score': novelty_score,
                'obviousness_score': obviousness_score,
                'cpc_factor': 1.0,
                'decade_factor': 1.0,
                'confidence_band': 'medium'
            }
    
    def get_cpc_calibration_factor(self, cpc_codes: List[str]) -> float:
        """Get calibration factor based on CPC codes."""
        if not cpc_codes:
            return 1.0
        
        # Define calibration factors for different technology areas
        cpc_factors = {
            'G06F': 1.1,  # Computing - higher novelty expected
            'G06N': 1.2,  # AI/ML - very high novelty expected
            'A61B': 0.9,  # Medical devices - moderate novelty
            'A61K': 0.8,  # Pharmaceuticals - lower novelty
            'H04L': 1.0,  # Telecommunications - standard
            'H04W': 1.0,  # Wireless - standard
        }
        
        # Find matching CPC codes
        matching_factors = []
        for cpc in cpc_codes:
            for pattern, factor in cpc_factors.items():
                if cpc.startswith(pattern):
                    matching_factors.append(factor)
                    break
        
        return np.mean(matching_factors) if matching_factors else 1.0
    
    def get_decade_calibration_factor(self, prio_date) -> float:
        """Get calibration factor based on patent decade."""
        if not prio_date:
            return 1.0
        
        try:
            year = prio_date.year
            decade = (year // 10) * 10
            
            # Define factors by decade (older = higher novelty expected)
            decade_factors = {
                1980: 1.3,  # Very old - high novelty
                1990: 1.2,  # Old - high novelty
                2000: 1.1,  # Recent - moderate novelty
                2010: 1.0,  # Current - standard
                2020: 0.9,  # Very recent - lower novelty
            }
            
            return decade_factors.get(decade, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating decade factor: {e}")
            return 1.0
    
    def get_confidence_band(self, novelty_score: float, obviousness_score: float) -> str:
        """Get confidence band based on score consistency."""
        # Check if scores are consistent
        score_diff = abs(novelty_score - (1.0 - obviousness_score))
        
        if score_diff < 0.1:
            return 'high'
        elif score_diff < 0.2:
            return 'medium'
        else:
            return 'low'
    
    def calculate_confidence_band(self, calibrated_scores: Dict[str, Any]) -> str:
        """Calculate overall confidence band."""
        return calibrated_scores.get('confidence_band', 'medium')
    
    async def store_novelty_scores(
        self,
        patent_id: str,
        claim_num: int,
        clause_scores: List[Dict],
        claim_novelty: float,
        obviousness_score: float,
        calibrated_scores: Dict[str, Any]
    ) -> None:
        """Store novelty scores in the database."""
        try:
            # Store claim-level novelty score
            await self.db.create_novelty_score(
                patent_id=patent_id,
                claim_num=claim_num,
                novelty_score=calibrated_scores['novelty_score'],
                obviousness_score=calibrated_scores['obviousness_score'],
                confidence_band=calibrated_scores['confidence_band'],
                calibration_factors={
                    'cpc_factor': calibrated_scores['cpc_factor'],
                    'decade_factor': calibrated_scores['decade_factor']
                },
                clause_details=clause_scores
            )
            
            logger.info(f"Stored novelty scores for patent {patent_id}, claim {claim_num}")
            
        except Exception as e:
            logger.error(f"Error storing novelty scores: {e}")
            raise


async def main():
    """Main entry point for the novelty worker."""
    worker = NoveltyWorker()
    
    try:
        await worker.start()
        
        # Keep the worker running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down novelty worker...")
    finally:
        await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
