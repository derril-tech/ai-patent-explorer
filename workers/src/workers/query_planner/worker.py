import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from ..base import BaseWorker
from ...utils.database import DatabaseClient

logger = logging.getLogger(__name__)


class QueryPlannerWorker(BaseWorker):
    """Worker for query planning with synonyms and CPC expansions."""
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        super().__init__(nats_url)
        self.db = DatabaseClient()
        
        # Synonym dictionary for patent terminology
        self.synonyms = self._load_synonyms()
        
        # CPC classification mappings
        self.cpc_mappings = self._load_cpc_mappings()
        
        logger.info("QueryPlannerWorker initialized")
    
    async def start(self):
        """Start the query planner worker."""
        await super().start()
        await self.db.connect()
        
        # Subscribe to query planning requests
        await self.subscribe("query.plan", self.handle_query_plan_request)
        
        logger.info("QueryPlannerWorker started and listening for requests")
    
    async def stop(self):
        """Stop the query planner worker."""
        await self.db.disconnect()
        await super().stop()
    
    async def handle_query_plan_request(self, msg):
        """Handle query planning requests."""
        try:
            data = json.loads(msg.data.decode())
            query_id = data.get('query_id')
            original_query = data.get('query')
            workspace_id = data.get('workspace_id')
            search_type = data.get('search_type', 'hybrid')
            
            if not all([query_id, original_query, workspace_id]):
                logger.error("Missing required fields in query plan request")
                return
            
            logger.info(f"Processing query plan request {query_id} for query: {original_query}")
            
            # Plan the query
            planned_query = await self.plan_query(original_query, workspace_id, search_type)
            
            # Publish planned query
            await self.publish("query.planned", {
                "query_id": query_id,
                "original_query": original_query,
                "planned_query": planned_query,
                "workspace_id": workspace_id,
                "search_type": search_type
            })
            
        except Exception as e:
            logger.error(f"Error processing query plan request: {e}")
            await self.publish("query.error", {
                "query_id": data.get('query_id'),
                "error": str(e)
            })
    
    async def plan_query(self, query: str, workspace_id: str, search_type: str) -> Dict[str, Any]:
        """Plan and expand a search query."""
        try:
            # Clean and normalize the query
            cleaned_query = self.clean_query(query)
            
            # Extract technical terms and concepts
            technical_terms = self.extract_technical_terms(cleaned_query)
            
            # Generate synonyms
            synonyms = self.generate_synonyms(technical_terms)
            
            # Extract potential CPC codes
            cpc_codes = self.extract_cpc_codes(cleaned_query)
            
            # Expand CPC codes
            expanded_cpcs = self.expand_cpc_codes(cpc_codes)
            
            # Generate alternative queries
            alternative_queries = self.generate_alternative_queries(cleaned_query, synonyms)
            
            # Create the planned query
            planned_query = {
                "original": query,
                "cleaned": cleaned_query,
                "technical_terms": technical_terms,
                "synonyms": synonyms,
                "cpc_codes": cpc_codes,
                "expanded_cpcs": expanded_cpcs,
                "alternative_queries": alternative_queries,
                "search_strategy": self.determine_search_strategy(cleaned_query, search_type)
            }
            
            return planned_query
            
        except Exception as e:
            logger.error(f"Error planning query: {e}")
            return {"original": query, "cleaned": query, "error": str(e)}
    
    def clean_query(self, query: str) -> str:
        """Clean and normalize the query text."""
        if not query:
            return ""
        
        # Convert to lowercase
        query = query.lower()
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Remove special characters but keep important ones
        query = re.sub(r'[^\w\s\-\.\,\;\:\!\?\(\)]', ' ', query)
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        return query.strip()
    
    def extract_technical_terms(self, query: str) -> List[str]:
        """Extract technical terms from the query."""
        terms = []
        
        # Split into words
        words = query.split()
        
        # Identify technical terms (longer words, compound terms)
        for i, word in enumerate(words):
            # Skip common words
            if word in self._get_stop_words():
                continue
            
            # Add single technical terms
            if len(word) > 4:
                terms.append(word)
            
            # Add compound terms
            if i < len(words) - 1:
                compound = f"{word} {words[i + 1]}"
                if self._is_technical_compound(compound):
                    terms.append(compound)
        
        return list(set(terms))
    
    def generate_synonyms(self, terms: List[str]) -> Dict[str, List[str]]:
        """Generate synonyms for technical terms."""
        synonyms = {}
        
        for term in terms:
            term_synonyms = []
            
            # Check our synonym dictionary
            if term in self.synonyms:
                term_synonyms.extend(self.synonyms[term])
            
            # Check for partial matches
            for key, values in self.synonyms.items():
                if term in key or key in term:
                    term_synonyms.extend(values)
            
            # Remove duplicates and the original term
            term_synonyms = list(set(term_synonyms) - {term})
            
            if term_synonyms:
                synonyms[term] = term_synonyms
        
        return synonyms
    
    def extract_cpc_codes(self, query: str) -> List[str]:
        """Extract potential CPC codes from the query."""
        cpc_codes = []
        
        # Look for CPC code patterns (e.g., A61B, G06F, etc.)
        cpc_pattern = r'\b[A-H]\d{2}[A-Z]\b'
        matches = re.findall(cpc_pattern, query.upper())
        cpc_codes.extend(matches)
        
        # Look for technical terms that might map to CPC codes
        words = query.split()
        for word in words:
            if word in self.cpc_mappings:
                cpc_codes.extend(self.cpc_mappings[word])
        
        return list(set(cpc_codes))
    
    def expand_cpc_codes(self, cpc_codes: List[str]) -> Dict[str, List[str]]:
        """Expand CPC codes to include related classifications."""
        expanded = {}
        
        for cpc in cpc_codes:
            related = []
            
            # Add the original code
            related.append(cpc)
            
            # Add parent codes (remove last character)
            if len(cpc) > 3:
                parent = cpc[:-1]
                related.append(parent)
            
            # Add sibling codes (same parent, different last character)
            if len(cpc) == 4:
                parent = cpc[:-1]
                for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    sibling = parent + char
                    if sibling != cpc:
                        related.append(sibling)
            
            expanded[cpc] = related
        
        return expanded
    
    def generate_alternative_queries(self, query: str, synonyms: Dict[str, List[str]]) -> List[str]:
        """Generate alternative queries using synonyms."""
        alternatives = [query]
        
        # Generate alternatives by replacing terms with synonyms
        for term, term_synonyms in synonyms.items():
            for synonym in term_synonyms[:3]:  # Limit to top 3 synonyms
                alternative = query.replace(term, synonym)
                if alternative != query:
                    alternatives.append(alternative)
        
        # Generate broader and narrower queries
        words = query.split()
        if len(words) > 2:
            # Broader query (remove some words)
            broader = ' '.join(words[:-1])
            alternatives.append(broader)
        
        # Add technical term combinations
        for term, term_synonyms in synonyms.items():
            if term_synonyms:
                # Add query with most relevant synonym
                alternative = query.replace(term, term_synonyms[0])
                alternatives.append(alternative)
        
        return list(set(alternatives))[:10]  # Limit to 10 alternatives
    
    def determine_search_strategy(self, query: str, search_type: str) -> Dict[str, Any]:
        """Determine the best search strategy for the query."""
        strategy = {
            "primary_method": search_type,
            "weight_bm25": 0.5,
            "weight_dense": 0.5,
            "use_synonyms": True,
            "use_cpc_expansion": True,
            "rerank": True
        }
        
        # Adjust strategy based on query characteristics
        words = query.split()
        
        # Short queries benefit more from dense search
        if len(words) <= 2:
            strategy["weight_dense"] = 0.7
            strategy["weight_bm25"] = 0.3
        
        # Long queries benefit more from BM25
        elif len(words) >= 8:
            strategy["weight_bm25"] = 0.7
            strategy["weight_dense"] = 0.3
        
        # Queries with technical terms benefit from synonyms
        technical_terms = self.extract_technical_terms(query)
        if len(technical_terms) > 2:
            strategy["use_synonyms"] = True
        
        # Queries with potential CPC codes benefit from expansion
        cpc_codes = self.extract_cpc_codes(query)
        if cpc_codes:
            strategy["use_cpc_expansion"] = True
        
        return strategy
    
    def _load_synonyms(self) -> Dict[str, List[str]]:
        """Load synonym dictionary for patent terminology."""
        return {
            # Technology terms
            "algorithm": ["method", "process", "technique", "procedure"],
            "device": ["apparatus", "system", "equipment", "instrument"],
            "method": ["process", "technique", "procedure", "algorithm"],
            "system": ["device", "apparatus", "equipment", "platform"],
            "apparatus": ["device", "system", "equipment", "instrument"],
            
            # Communication terms
            "transmit": ["send", "transfer", "communicate", "broadcast"],
            "receive": ["accept", "obtain", "collect", "acquire"],
            "communication": ["transmission", "exchange", "transfer", "broadcast"],
            
            # Computing terms
            "processor": ["cpu", "controller", "computing unit", "processing unit"],
            "memory": ["storage", "ram", "cache", "buffer"],
            "database": ["repository", "storage", "data store", "collection"],
            "network": ["connection", "link", "communication", "transmission"],
            
            # Medical terms
            "treatment": ["therapy", "intervention", "procedure", "care"],
            "diagnosis": ["detection", "identification", "assessment", "evaluation"],
            "patient": ["subject", "individual", "person", "user"],
            
            # Chemical terms
            "compound": ["molecule", "substance", "chemical", "material"],
            "reaction": ["process", "transformation", "conversion", "synthesis"],
            "catalyst": ["accelerator", "promoter", "activator", "initiator"],
            
            # Mechanical terms
            "mechanism": ["device", "apparatus", "system", "assembly"],
            "actuator": ["motor", "driver", "mover", "operator"],
            "sensor": ["detector", "transducer", "probe", "monitor"]
        }
    
    def _load_cpc_mappings(self) -> Dict[str, List[str]]:
        """Load mappings from technical terms to CPC codes."""
        return {
            # Computing and Information Technology
            "computer": ["G06F", "G06N", "G06T"],
            "algorithm": ["G06F", "G06N"],
            "database": ["G06F"],
            "network": ["H04L", "H04W"],
            "communication": ["H04L", "H04W", "H04B"],
            
            # Medical and Healthcare
            "medical": ["A61B", "A61M", "A61K"],
            "treatment": ["A61M", "A61K"],
            "diagnosis": ["A61B", "G01N"],
            "surgery": ["A61B"],
            "drug": ["A61K"],
            
            # Chemistry and Materials
            "chemical": ["C07", "C08", "C09"],
            "polymer": ["C08"],
            "catalyst": ["B01J"],
            "reaction": ["B01J", "C07"],
            
            # Mechanical Engineering
            "mechanical": ["F16", "F15", "F04"],
            "engine": ["F02"],
            "pump": ["F04"],
            "valve": ["F16K"],
            
            # Electrical Engineering
            "electrical": ["H01", "H02", "H03"],
            "circuit": ["H03K", "H03F"],
            "battery": ["H01M"],
            "motor": ["H02K"],
            
            # Biotechnology
            "dna": ["C12N", "C12Q"],
            "protein": ["C07K", "C12N"],
            "cell": ["C12N"],
            "gene": ["C12N", "C12Q"]
        }
    
    def _get_stop_words(self) -> Set[str]:
        """Get common stop words."""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
    
    def _is_technical_compound(self, compound: str) -> bool:
        """Check if a compound term is technical."""
        technical_compounds = {
            'machine learning', 'artificial intelligence', 'deep learning',
            'neural network', 'data processing', 'signal processing',
            'image processing', 'voice recognition', 'face recognition',
            'wireless communication', 'mobile device', 'cloud computing',
            'block chain', 'internet of things', 'virtual reality',
            'augmented reality', 'autonomous vehicle', 'electric vehicle'
        }
        return compound.lower() in technical_compounds


async def main():
    """Main entry point for the query planner worker."""
    worker = QueryPlannerWorker()
    
    try:
        await worker.start()
        
        # Keep the worker running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down query planner worker...")
    finally:
        await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
