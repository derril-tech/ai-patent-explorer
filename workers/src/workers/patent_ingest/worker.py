"""Patent ingest worker for processing XML and PDF patent documents."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

import nats
from pydantic import BaseModel
import structlog

from ..base import BaseWorker
from ...models.patent import PatentDocument, PatentMetadata
from ...utils.xml_parser import XMLPatentParser
from ...utils.pdf_parser import PDFPatentParser
from ...utils.ocr import OCRProcessor
from ...utils.storage import StorageClient
from ...utils.database import DatabaseClient

logger = structlog.get_logger(__name__)


class IngestRequest(BaseModel):
    """Request model for patent ingestion."""
    workspace_id: str
    file_path: str
    file_type: str  # 'xml' or 'pdf'
    source: str  # 'uspto', 'epo', 'wipo', etc.
    metadata: Optional[Dict[str, Any]] = None


class IngestResponse(BaseModel):
    """Response model for patent ingestion."""
    patent_id: str
    status: str
    message: str
    metadata: PatentMetadata


class PatentIngestWorker(BaseWorker):
    """Worker for ingesting patent documents from XML and PDF sources."""

    def __init__(self):
        super().__init__()
        self.xml_parser = XMLPatentParser()
        self.pdf_parser = PDFPatentParser()
        self.ocr_processor = OCRProcessor()
        self.storage_client = StorageClient()
        self.db_client = DatabaseClient()

    async def process_message(self, message: IngestRequest) -> IngestResponse:
        """Process a patent ingestion request."""
        try:
            logger.info("Starting patent ingestion", 
                       workspace_id=message.workspace_id,
                       file_path=message.file_path,
                       file_type=message.file_type)

            # Download file from storage
            local_path = await self.storage_client.download_file(message.file_path)
            
            # Parse document based on type
            if message.file_type.lower() == 'xml':
                patent_doc = await self._parse_xml(local_path)
            elif message.file_type.lower() == 'pdf':
                patent_doc = await self._parse_pdf(local_path)
            else:
                raise ValueError(f"Unsupported file type: {message.file_type}")

            # Check for duplicates
            duplicate_id = await self._check_duplicate(patent_doc, message.workspace_id)
            if duplicate_id:
                logger.info("Duplicate patent found", 
                           patent_id=duplicate_id,
                           pub_number=patent_doc.metadata.pub_number)
                return IngestResponse(
                    patent_id=duplicate_id,
                    status="duplicate",
                    message="Patent already exists",
                    metadata=patent_doc.metadata
                )

            # Store document in database
            patent_id = await self._store_patent(patent_doc, message.workspace_id)

            # Upload processed files to storage
            await self._upload_processed_files(patent_doc, patent_id)

            # Publish events for downstream processing
            await self._publish_events(patent_id, patent_doc)

            logger.info("Patent ingestion completed", 
                       patent_id=patent_id,
                       pub_number=patent_doc.metadata.pub_number)

            return IngestResponse(
                patent_id=patent_id,
                status="success",
                message="Patent ingested successfully",
                metadata=patent_doc.metadata
            )

        except Exception as e:
            logger.error("Patent ingestion failed", 
                        error=str(e),
                        workspace_id=message.workspace_id,
                        file_path=message.file_path)
            raise

    async def _parse_xml(self, file_path: Path) -> PatentDocument:
        """Parse XML patent document."""
        try:
            return await self.xml_parser.parse(file_path)
        except Exception as e:
            logger.error("XML parsing failed", error=str(e), file_path=str(file_path))
            raise

    async def _parse_pdf(self, file_path: Path) -> PatentDocument:
        """Parse PDF patent document with OCR fallback."""
        try:
            # Try to extract text directly
            patent_doc = await self.pdf_parser.parse(file_path)
            
            # If text extraction fails or is poor quality, use OCR
            if not patent_doc.text or len(patent_doc.text.strip()) < 100:
                logger.info("Using OCR for PDF text extraction", file_path=str(file_path))
                ocr_text = await self.ocr_processor.extract_text(file_path)
                patent_doc.text = ocr_text
                patent_doc.metadata.ocr_used = True

            return patent_doc
        except Exception as e:
            logger.error("PDF parsing failed", error=str(e), file_path=str(file_path))
            raise

    async def _check_duplicate(self, patent_doc: PatentDocument, workspace_id: str) -> Optional[str]:
        """Check if patent already exists in workspace."""
        try:
            # Check by publication number
            existing = await self.db_client.get_patent_by_pub_number(
                workspace_id, patent_doc.metadata.pub_number
            )
            if existing:
                return existing.id

            # Check by content hash
            content_hash = self._calculate_content_hash(patent_doc)
            existing = await self.db_client.get_patent_by_content_hash(
                workspace_id, content_hash
            )
            if existing:
                return existing.id

            return None
        except Exception as e:
            logger.error("Duplicate check failed", error=str(e))
            return None

    async def _store_patent(self, patent_doc: PatentDocument, workspace_id: str) -> str:
        """Store patent document in database."""
        try:
            # Create patent record
            patent_id = await self.db_client.create_patent(
                workspace_id=workspace_id,
                metadata=patent_doc.metadata,
                text=patent_doc.text,
                claims=patent_doc.claims
            )

            # Store claims
            for claim in patent_doc.claims:
                await self.db_client.create_claim(
                    patent_id=patent_id,
                    claim_number=claim.number,
                    text=claim.text,
                    is_independent=claim.is_independent
                )

            return patent_id
        except Exception as e:
            logger.error("Failed to store patent", error=str(e))
            raise

    async def _upload_processed_files(self, patent_doc: PatentDocument, patent_id: str):
        """Upload processed files to storage."""
        try:
            # Upload original file
            if patent_doc.original_file_path:
                await self.storage_client.upload_file(
                    patent_doc.original_file_path,
                    f"patents/{patent_id}/original"
                )

            # Upload extracted text
            text_path = f"patents/{patent_id}/extracted_text.txt"
            await self.storage_client.upload_text(
                patent_doc.text,
                text_path
            )

            # Upload claims
            claims_path = f"patents/{patent_id}/claims.json"
            claims_data = [claim.dict() for claim in patent_doc.claims]
            await self.storage_client.upload_json(
                claims_data,
                claims_path
            )

        except Exception as e:
            logger.error("Failed to upload processed files", error=str(e))
            raise

    async def _publish_events(self, patent_id: str, patent_doc: PatentDocument):
        """Publish events for downstream processing."""
        try:
            # Publish patent.normalize event
            await self.nats_client.publish(
                "patent.normalize",
                {
                    "patent_id": patent_id,
                    "metadata": patent_doc.metadata.dict()
                }
            )

            # Publish index.upsert event
            await self.nats_client.publish(
                "index.upsert",
                {
                    "patent_id": patent_id,
                    "text": patent_doc.text,
                    "claims": [claim.dict() for claim in patent_doc.claims]
                }
            )

        except Exception as e:
            logger.error("Failed to publish events", error=str(e))
            raise

    def _calculate_content_hash(self, patent_doc: PatentDocument) -> str:
        """Calculate content hash for duplicate detection."""
        content = f"{patent_doc.metadata.pub_number}{patent_doc.text}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def start(self):
        """Start the patent ingest worker."""
        await super().start()
        await self.nats_client.subscribe("patent.ingest", self.process_message)
        logger.info("Patent ingest worker started")

    async def stop(self):
        """Stop the patent ingest worker."""
        await super().stop()
        logger.info("Patent ingest worker stopped")
