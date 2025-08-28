"""Normalize worker for standardizing patent data."""

import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from pydantic import BaseModel
import structlog

from ..base import BaseWorker
from ...models.patent import PatentMetadata
from ...utils.database import DatabaseClient
from ...utils.normalizer import PatentNormalizer

logger = structlog.get_logger(__name__)


class NormalizeRequest(BaseModel):
    """Request model for patent normalization."""
    patent_id: str
    metadata: PatentMetadata


class NormalizeResponse(BaseModel):
    """Response model for patent normalization."""
    patent_id: str
    status: str
    message: str
    normalized_data: Dict[str, Any]


class NormalizeWorker(BaseWorker):
    """Worker for normalizing patent data."""

    def __init__(self):
        super().__init__()
        self.normalizer = PatentNormalizer()
        self.db_client = DatabaseClient()

    async def process_message(self, message: NormalizeRequest) -> NormalizeResponse:
        """Process a patent normalization request."""
        try:
            logger.info("Starting patent normalization", 
                       patent_id=message.patent_id)

            # Normalize family ID
            normalized_family_id = await self._normalize_family_id(message.metadata)
            
            # Normalize assignees
            normalized_assignees = await self._normalize_assignees(message.metadata.assignees)
            
            # Normalize inventors
            normalized_inventors = await self._normalize_inventors(message.metadata.inventors)
            
            # Normalize dates
            normalized_dates = await self._normalize_dates(message.metadata)
            
            # Normalize CPC/IPC codes
            normalized_codes = await self._normalize_codes(message.metadata)
            
            # Update database with normalized data
            await self._update_patent_metadata(
                message.patent_id,
                normalized_family_id,
                normalized_assignees,
                normalized_inventors,
                normalized_dates,
                normalized_codes
            )

            # Publish event for indexing
            await self._publish_index_event(message.patent_id)

            logger.info("Patent normalization completed", 
                       patent_id=message.patent_id)

            return NormalizeResponse(
                patent_id=message.patent_id,
                status="success",
                message="Patent normalized successfully",
                normalized_data={
                    "family_id": normalized_family_id,
                    "assignees": normalized_assignees,
                    "inventors": normalized_inventors,
                    "dates": normalized_dates,
                    "codes": normalized_codes
                }
            )

        except Exception as e:
            logger.error("Patent normalization failed", 
                        error=str(e),
                        patent_id=message.patent_id)
            raise

    async def _normalize_family_id(self, metadata: PatentMetadata) -> Optional[str]:
        """Normalize family ID."""
        try:
            if not metadata.family_id:
                return None
            
            # Extract and standardize family ID
            family_id = self.normalizer.normalize_family_id(metadata.family_id)
            
            # Check if family exists, create if not
            await self._ensure_family_exists(family_id, metadata)
            
            return family_id
        except Exception as e:
            logger.error("Family ID normalization failed", error=str(e))
            return metadata.family_id

    async def _normalize_assignees(self, assignees: Optional[List[str]]) -> List[str]:
        """Normalize assignee names."""
        try:
            if not assignees:
                return []
            
            normalized = []
            for assignee in assignees:
                normalized_assignee = self.normalizer.normalize_assignee(assignee)
                if normalized_assignee:
                    normalized.append(normalized_assignee)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_assignees = []
            for assignee in normalized:
                if assignee not in seen:
                    seen.add(assignee)
                    unique_assignees.append(assignee)
            
            return unique_assignees
        except Exception as e:
            logger.error("Assignee normalization failed", error=str(e))
            return assignees or []

    async def _normalize_inventors(self, inventors: Optional[List[str]]) -> List[str]:
        """Normalize inventor names."""
        try:
            if not inventors:
                return []
            
            normalized = []
            for inventor in inventors:
                normalized_inventor = self.normalizer.normalize_inventor(inventor)
                if normalized_inventor:
                    normalized.append(normalized_inventor)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_inventors = []
            for inventor in normalized:
                if inventor not in seen:
                    seen.add(inventor)
                    unique_inventors.append(inventor)
            
            return unique_inventors
        except Exception as e:
            logger.error("Inventor normalization failed", error=str(e))
            return inventors or []

    async def _normalize_dates(self, metadata: PatentMetadata) -> Dict[str, Optional[datetime]]:
        """Normalize dates."""
        try:
            normalized_dates = {}
            
            # Normalize priority date
            if metadata.prio_date:
                normalized_dates['prio_date'] = self.normalizer.normalize_date(metadata.prio_date)
            
            # Add other dates if available
            # This could include filing date, publication date, etc.
            
            return normalized_dates
        except Exception as e:
            logger.error("Date normalization failed", error=str(e))
            return {}

    async def _normalize_codes(self, metadata: PatentMetadata) -> Dict[str, List[str]]:
        """Normalize CPC and IPC codes."""
        try:
            normalized_codes = {}
            
            # Normalize CPC codes
            if metadata.cpc_codes:
                normalized_cpc = []
                for code in metadata.cpc_codes:
                    normalized_code = self.normalizer.normalize_cpc_code(code)
                    if normalized_code:
                        normalized_cpc.append(normalized_code)
                normalized_codes['cpc_codes'] = normalized_cpc
            
            # Normalize IPC codes
            if metadata.ipc_codes:
                normalized_ipc = []
                for code in metadata.ipc_codes:
                    normalized_code = self.normalizer.normalize_ipc_code(code)
                    if normalized_code:
                        normalized_ipc.append(normalized_code)
                normalized_codes['ipc_codes'] = normalized_ipc
            
            # Add rollup codes
            rollup_codes = await self._get_rollup_codes(normalized_codes)
            normalized_codes.update(rollup_codes)
            
            return normalized_codes
        except Exception as e:
            logger.error("Code normalization failed", error=str(e))
            return {}

    async def _ensure_family_exists(self, family_id: str, metadata: PatentMetadata):
        """Ensure patent family exists in database."""
        try:
            # Check if family exists
            existing_family = await self.db_client.get_patent_family(family_id, metadata.workspace_id)
            
            if not existing_family:
                # Create family record
                await self.db_client.create_patent_family(family_id, metadata)
                logger.info("Created patent family", family_id=family_id)
        except Exception as e:
            logger.error("Failed to ensure family exists", error=str(e))

    async def _get_rollup_codes(self, normalized_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Get rollup codes for CPC/IPC codes."""
        try:
            rollup_codes = {}
            
            # Get CPC rollups
            if 'cpc_codes' in normalized_codes:
                cpc_rollups = []
                for code in normalized_codes['cpc_codes']:
                    rollup = self.normalizer.get_cpc_rollup(code)
                    if rollup:
                        cpc_rollups.append(rollup)
                rollup_codes['cpc_rollups'] = cpc_rollups
            
            # Get IPC rollups
            if 'ipc_codes' in normalized_codes:
                ipc_rollups = []
                for code in normalized_codes['ipc_codes']:
                    rollup = self.normalizer.get_ipc_rollup(code)
                    if rollup:
                        ipc_rollups.append(rollup)
                rollup_codes['ipc_rollups'] = ipc_rollups
            
            return rollup_codes
        except Exception as e:
            logger.error("Failed to get rollup codes", error=str(e))
            return {}

    async def _update_patent_metadata(self, patent_id: str, family_id: Optional[str], 
                                    assignees: List[str], inventors: List[str], 
                                    dates: Dict[str, Optional[datetime]], 
                                    codes: Dict[str, List[str]]):
        """Update patent metadata with normalized data."""
        try:
            await self.db_client.update_patent_metadata(
                patent_id=patent_id,
                family_id=family_id,
                assignees=assignees,
                inventors=inventors,
                dates=dates,
                codes=codes
            )
            
            logger.info("Updated patent metadata", patent_id=patent_id)
        except Exception as e:
            logger.error("Failed to update patent metadata", error=str(e))
            raise

    async def _publish_index_event(self, patent_id: str):
        """Publish event for indexing."""
        try:
            await self.nats_client.publish(
                "index.upsert",
                {
                    "patent_id": patent_id,
                    "action": "normalize"
                }
            )
        except Exception as e:
            logger.error("Failed to publish index event", error=str(e))

    async def start(self):
        """Start the normalize worker."""
        await super().start()
        await self.nats_client.subscribe("patent.normalize", self.process_message)
        logger.info("Normalize worker started")

    async def stop(self):
        """Stop the normalize worker."""
        await super().stop()
        logger.info("Normalize worker stopped")
