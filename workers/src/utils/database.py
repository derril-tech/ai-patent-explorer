"""Database client for PostgreSQL operations."""

import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

import asyncpg
import structlog

from ..models.patent import PatentMetadata, PatentClaim

logger = structlog.get_logger(__name__)


class DatabaseClient:
    """Client for PostgreSQL database operations."""

    def __init__(self):
        self.pool = None
        self.connection_string = "postgresql://postgres:postgres@localhost:5432/ai_patent_explorer"

    async def connect(self):
        """Connect to the database."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20
            )
            logger.info("Connected to database")
        except Exception as e:
            logger.error("Database connection failed", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from the database."""
        try:
            if self.pool:
                await self.pool.close()
                logger.info("Disconnected from database")
        except Exception as e:
            logger.error("Database disconnection failed", error=str(e))

    async def get_patent_by_pub_number(self, workspace_id: str, pub_number: str):
        """Get patent by publication number."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM patents 
                    WHERE workspace_id = $1 AND pub_number = $2
                    """,
                    workspace_id, pub_number
                )
                return row
        except Exception as e:
            logger.error("Failed to get patent by pub number", error=str(e))
            return None

    async def get_patent_by_content_hash(self, workspace_id: str, content_hash: str):
        """Get patent by content hash."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM patents 
                    WHERE workspace_id = $1 AND content_hash = $2
                    """,
                    workspace_id, content_hash
                )
                return row
        except Exception as e:
            logger.error("Failed to get patent by content hash", error=str(e))
            return None

    async def create_patent(self, workspace_id: str, metadata: PatentMetadata, text: str, claims: List[PatentClaim]) -> str:
        """Create a new patent record."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Insert patent
                    patent_id = await conn.fetchval(
                        """
                        INSERT INTO patents (
                            workspace_id, pub_number, app_number, prio_date, family_id,
                            title, abstract, assignees, inventors, cpc_codes, ipc_codes,
                            lang, s3_xml_path, s3_pdf_path
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        RETURNING id
                        """,
                        workspace_id,
                        metadata.pub_number,
                        metadata.app_number,
                        metadata.prio_date,
                        metadata.family_id,
                        metadata.title,
                        metadata.abstract,
                        metadata.assignees,
                        metadata.inventors,
                        metadata.cpc_codes,
                        metadata.ipc_codes,
                        metadata.lang,
                        None,  # s3_xml_path
                        None   # s3_pdf_path
                    )
                    
                    logger.info("Created patent", patent_id=patent_id, pub_number=metadata.pub_number)
                    return patent_id
        except Exception as e:
            logger.error("Failed to create patent", error=str(e))
            raise

    async def create_claim(self, patent_id: str, claim_number: int, text: str, is_independent: bool) -> str:
        """Create a new claim record."""
        try:
            async with self.pool.acquire() as conn:
                claim_id = await conn.fetchval(
                    """
                    INSERT INTO claims (patent_id, claim_number, is_independent, text)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    patent_id, claim_number, is_independent, text
                )
                
                logger.info("Created claim", claim_id=claim_id, patent_id=patent_id, claim_number=claim_number)
                return claim_id
        except Exception as e:
            logger.error("Failed to create claim", error=str(e))
            raise

    async def update_patent_embeddings(self, patent_id: str, embeddings: Dict[str, List[float]]):
        """Update patent embeddings."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Update claim embeddings
                    for claim_id, embedding in embeddings.get('claims', {}).items():
                        await conn.execute(
                            """
                            UPDATE claims SET embedding = $1 WHERE id = $2
                            """,
                            embedding, claim_id
                        )
                    
                    # Update clause embeddings
                    for clause_id, embedding in embeddings.get('clauses', {}).items():
                        await conn.execute(
                            """
                            UPDATE clauses SET embedding = $1 WHERE id = $2
                            """,
                            embedding, clause_id
                        )
                    
                    logger.info("Updated patent embeddings", patent_id=patent_id)
        except Exception as e:
            logger.error("Failed to update patent embeddings", error=str(e))
            raise

    async def get_patent_with_claims(self, patent_id: str):
        """Get patent with all its claims."""
        try:
            async with self.pool.acquire() as conn:
                # Get patent
                patent = await conn.fetchrow(
                    """
                    SELECT * FROM patents WHERE id = $1
                    """,
                    patent_id
                )
                
                if not patent:
                    return None
                
                # Get claims
                claims = await conn.fetch(
                    """
                    SELECT * FROM claims WHERE patent_id = $1 ORDER BY claim_number
                    """,
                    patent_id
                )
                
                return {
                    'patent': patent,
                    'claims': claims
                }
        except Exception as e:
            logger.error("Failed to get patent with claims", error=str(e))
            return None

    async def search_patents_by_text(self, workspace_id: str, query: str, limit: int = 10):
        """Search patents by text similarity."""
        try:
            async with self.pool.acquire() as conn:
                # Simple text search for now - can be enhanced with vector similarity
                rows = await conn.fetch(
                    """
                    SELECT p.*, 
                           ts_rank(to_tsvector('english', p.title || ' ' || COALESCE(p.abstract, '')), plainto_tsquery('english', $2)) as rank
                    FROM patents p
                    WHERE p.workspace_id = $1
                    AND to_tsvector('english', p.title || ' ' || COALESCE(p.abstract, '')) @@ plainto_tsquery('english', $2)
                    ORDER BY rank DESC
                    LIMIT $3
                    """,
                    workspace_id, query, limit
                )
                
                return rows
        except Exception as e:
            logger.error("Failed to search patents by text", error=str(e))
            return []

    async def get_patent_family(self, family_id: str, workspace_id: str):
        """Get all patents in a family."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM patents 
                    WHERE family_id = $1 AND workspace_id = $2
                    ORDER BY prio_date
                    """,
                    family_id, workspace_id
                )
                
                return rows
        except Exception as e:
            logger.error("Failed to get patent family", error=str(e))
            return []

    async def create_search_session(self, workspace_id: str, user_id: str, query: str, filters: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Create a search session record."""
        try:
            async with self.pool.acquire() as conn:
                session_id = await conn.fetchval(
                    """
                    INSERT INTO search_sessions (workspace_id, user_id, query, filters, results)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    workspace_id, user_id, query, filters, results
                )
                
                logger.info("Created search session", session_id=session_id)
                return session_id
        except Exception as e:
            logger.error("Failed to create search session", error=str(e))
            raise

    async def create_audit_log(self, workspace_id: str, user_id: str, action: str, resource_type: str, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Create an audit log entry."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_log (workspace_id, user_id, action, resource_type, resource_id, details)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    workspace_id, user_id, action, resource_type, resource_id, details
                )
                
                logger.info("Created audit log", action=action, resource_type=resource_type)
        except Exception as e:
            logger.error("Failed to create audit log", error=str(e))
            raise

    async def update_patent_embeddings(self, patent_id: str, claim_embeddings: Dict[str, np.ndarray], 
                                     clause_embeddings: Dict[str, np.ndarray], 
                                     passage_embeddings: Dict[str, np.ndarray]) -> bool:
        """Update patent embeddings in the database."""
        try:
            async with self.pool.acquire() as conn:
                # Update claim embeddings
                for claim_id, embedding in claim_embeddings.items():
                    await conn.execute(
                        """
                        UPDATE claims 
                        SET embedding = $2, updated_at = NOW()
                        WHERE id = $1
                        """,
                        claim_id, embedding.tobytes()
                    )
                
                # Update clause embeddings
                for clause_id, embedding in clause_embeddings.items():
                    await conn.execute(
                        """
                        UPDATE clauses 
                        SET embedding = $2, updated_at = NOW()
                        WHERE id = $1
                        """,
                        clause_id, embedding.tobytes()
                    )
                
                # Update passage embeddings
                for passage_id, embedding in passage_embeddings.items():
                    await conn.execute(
                        """
                        UPDATE passages 
                        SET embedding = $2, updated_at = NOW()
                        WHERE id = $1
                        """,
                        passage_id, embedding.tobytes()
                    )
                
                return True
        except Exception as e:
            logger.error(f"Error updating patent embeddings: {e}")
            return False

    async def upsert_vector_embeddings(self, patent_id: str, embeddings: Dict[str, Dict[str, np.ndarray]]) -> bool:
        """Upsert embeddings into pgvector for similarity search."""
        try:
            async with self.pool.acquire() as conn:
                # Upsert claim embeddings
                for claim_id, embedding in embeddings.get('claims', {}).items():
                    await conn.execute(
                        """
                        INSERT INTO claims (id, patent_id, embedding)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (id) 
                        DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = NOW()
                        """,
                        claim_id, patent_id, embedding.tobytes()
                    )
                
                # Upsert clause embeddings
                for clause_id, embedding in embeddings.get('clauses', {}).items():
                    await conn.execute(
                        """
                        INSERT INTO clauses (id, patent_id, embedding)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (id) 
                        DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = NOW()
                        """,
                        clause_id, patent_id, embedding.tobytes()
                    )
                
                # Upsert passage embeddings
                for passage_id, embedding in embeddings.get('passages', {}).items():
                    await conn.execute(
                        """
                        INSERT INTO passages (id, patent_id, embedding)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (id) 
                        DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = NOW()
                        """,
                        passage_id, patent_id, embedding.tobytes()
                    )
                
                return True
        except Exception as e:
            logger.error(f"Error upserting vector embeddings: {e}")
            return False

    async def search_by_embedding(self, query_embedding: np.ndarray, workspace_id: str, 
                                search_type: str = 'claims', limit: int = 10) -> List[Dict[str, Any]]:
        """Search by embedding similarity using pgvector."""
        try:
            async with self.pool.acquire() as conn:
                if search_type == 'claims':
                    table = 'claims'
                    select_fields = 'id, patent_id, claim_number, text, embedding'
                elif search_type == 'clauses':
                    table = 'clauses'
                    select_fields = 'id, patent_id, clause_number, text, embedding'
                elif search_type == 'passages':
                    table = 'passages'
                    select_fields = 'id, patent_id, passage_type, text, embedding'
                else:
                    raise ValueError(f"Invalid search_type: {search_type}")
                
                # Use cosine similarity for embedding search
                rows = await conn.fetch(
                    f"""
                    SELECT {select_fields}, 
                           1 - (embedding <=> $1) as similarity
                    FROM {table} c
                    JOIN patents p ON c.patent_id = p.id
                    WHERE p.workspace_id = $2
                    AND embedding IS NOT NULL
                    ORDER BY embedding <=> $1
                    LIMIT $3
                    """,
                    query_embedding.tobytes(), workspace_id, limit
                )
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching by embedding: {e}")
            return []

    async def get_all_patents_for_search(self) -> List[Dict[str, Any]]:
        """Get all patents for building search corpus."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, title, abstract, workspace_id, cpc_codes, assignees, prio_date
                    FROM patents
                    WHERE title IS NOT NULL OR abstract IS NOT NULL
                    """
                )
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting patents for search: {e}")
            return []

    async def get_claim(self, patent_id: str, claim_num: int) -> Optional[Dict[str, Any]]:
        """Get a specific claim by patent ID and claim number."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM claims 
                    WHERE patent_id = $1 AND claim_number = $2
                    """,
                    patent_id, claim_num
                )
                
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting claim: {e}")
            return None

    async def get_patent_claims(self, patent_id: str) -> List[Dict[str, Any]]:
        """Get all claims for a patent."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM claims 
                    WHERE patent_id = $1 
                    ORDER BY claim_number
                    """,
                    patent_id
                )
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting patent claims: {e}")
            return []

    async def create_alignment(
        self,
        patent_id: str,
        claim_num: int,
        clause_index: int,
        clause_text: str,
        reference_patent_id: str,
        reference_claim_id: str,
        reference_clause_index: int,
        reference_clause_text: str,
        similarity_score: float,
        alignment_type: str,
        overlap_details: Dict[str, Any]
    ) -> str:
        """Create an alignment record."""
        try:
            async with self.pool.acquire() as conn:
                alignment_id = await conn.fetchval(
                    """
                    INSERT INTO alignments (
                        patent_id, claim_num, clause_index, clause_text,
                        reference_patent_id, reference_claim_id, reference_clause_index,
                        reference_clause_text, similarity_score, alignment_type, overlap_details
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING id
                    """,
                    patent_id, claim_num, clause_index, clause_text,
                    reference_patent_id, reference_claim_id, reference_clause_index,
                    reference_clause_text, similarity_score, alignment_type, json.dumps(overlap_details)
                )
                
                logger.info("Created alignment", alignment_id=alignment_id)
                return alignment_id
        except Exception as e:
            logger.error("Failed to create alignment", error=str(e))
            raise

    async def get_claim_alignments(self, patent_id: str, claim_num: int) -> List[Dict[str, Any]]:
        """Get all alignments for a specific claim."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT a.*, p.title as reference_patent_title, p.prio_date as reference_prio_date
                    FROM alignments a
                    LEFT JOIN patents p ON a.reference_patent_id = p.id
                    WHERE a.patent_id = $1 AND a.claim_num = $2
                    ORDER BY a.similarity_score DESC
                    """,
                    patent_id, claim_num
                )
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting claim alignments: {e}")
            return []

    async def get_patent(self, patent_id: str) -> Optional[Dict[str, Any]]:
        """Get a patent by ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM patents 
                    WHERE id = $1
                    """,
                    patent_id
                )
                
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting patent: {e}")
            return None

    async def create_novelty_score(
        self,
        patent_id: str,
        claim_num: int,
        novelty_score: float,
        obviousness_score: float,
        confidence_band: str,
        calibration_factors: Dict[str, Any],
        clause_details: List[Dict[str, Any]]
    ) -> str:
        """Create a novelty score record."""
        try:
            async with self.pool.acquire() as conn:
                novelty_id = await conn.fetchval(
                    """
                    INSERT INTO novelty_scores (
                        patent_id, claim_num, novelty_score, obviousness_score,
                        confidence_band, calibration_factors, clause_details, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (patent_id, claim_num) 
                    DO UPDATE SET
                        novelty_score = EXCLUDED.novelty_score,
                        obviousness_score = EXCLUDED.obviousness_score,
                        confidence_band = EXCLUDED.confidence_band,
                        calibration_factors = EXCLUDED.calibration_factors,
                        clause_details = EXCLUDED.clause_details,
                        updated_at = $8
                    RETURNING id
                    """,
                    patent_id, claim_num, novelty_score, obviousness_score,
                    confidence_band, json.dumps(calibration_factors), 
                    json.dumps(clause_details), datetime.utcnow()
                )
                
                logger.info("Created/updated novelty score", novelty_id=novelty_id)
                return novelty_id
        except Exception as e:
            logger.error("Failed to create novelty score", error=str(e))
            raise

    async def get_novelty_score(self, patent_id: str, claim_num: int) -> Optional[Dict[str, Any]]:
        """Get novelty score for a specific claim."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM novelty_scores 
                    WHERE patent_id = $1 AND claim_num = $2
                    """,
                    patent_id, claim_num
                )
                
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting novelty score: {e}")
            return None

    async def get_patent_citations(self, patent_ids: List[str]) -> List[Dict[str, Any]]:
        """Get citation relationships for patents."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT citing_patent_id, cited_patent_id, citation_date, citation_strength
                    FROM citations
                    WHERE citing_patent_id = ANY($1) AND cited_patent_id = ANY($1)
                    """,
                    patent_ids
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting patent citations: {e}")
            return []

    async def get_patent_families(self, patent_ids: List[str]) -> List[Dict[str, Any]]:
        """Get patent family relationships."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT family_id, array_agg(id) as patent_ids
                    FROM patents
                    WHERE id = ANY($1) AND family_id IS NOT NULL
                    GROUP BY family_id
                    """,
                    patent_ids
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting patent families: {e}")
            return []

    async def store_graph_analysis(self, analysis_id: str, graph_data: Dict[str, Any]) -> bool:
        """Store graph analysis results."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO graph_analyses (id, graph_data, created_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        graph_data = $2,
                        updated_at = NOW()
                    """,
                    analysis_id, json.dumps(graph_data)
                )
                return True
        except Exception as e:
            logger.error(f"Error storing graph analysis: {e}")
            return False

    async def store_graph_metrics(self, metrics_id: str, metrics_data: Dict[str, Any]) -> bool:
        """Store graph metrics results."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO graph_metrics (id, metrics_data, created_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        metrics_data = $2,
                        updated_at = NOW()
                    """,
                    metrics_id, json.dumps(metrics_data)
                )
                return True
        except Exception as e:
            logger.error(f"Error storing graph metrics: {e}")
            return False
