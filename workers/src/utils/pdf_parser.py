"""PDF patent parser with text extraction capabilities."""

import asyncio
from pathlib import Path
from typing import List, Optional
import re

import pdfplumber
import structlog

from ..models.patent import PatentDocument, PatentMetadata, PatentClaim

logger = structlog.get_logger(__name__)


class PDFPatentParser:
    """Parser for PDF patent documents."""

    def __init__(self):
        self.claim_patterns = [
            r'(\d+)\.\s*(.*?)(?=\d+\.|$)',
            r'Claim\s+(\d+)[:\.]\s*(.*?)(?=Claim\s+\d+[:\.]|$)',
        ]

    async def parse(self, file_path: Path) -> PatentDocument:
        """Parse a PDF patent document."""
        try:
            # Extract text from PDF
            text = await self._extract_text(file_path)
            
            # Extract metadata
            metadata = await self._extract_metadata(text)
            
            # Extract claims
            claims = await self._extract_claims(text)
            
            return PatentDocument(
                metadata=metadata,
                text=text,
                claims=claims,
                original_file_path=str(file_path)
            )

        except Exception as e:
            logger.error("PDF parsing failed", error=str(e), file_path=str(file_path))
            raise

    async def _extract_text(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            text_parts = []
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return " ".join(text_parts)
        except Exception as e:
            logger.error("Text extraction failed", error=str(e))
            raise

    async def _extract_metadata(self, text: str) -> PatentMetadata:
        """Extract metadata from PDF text."""
        try:
            # Extract publication number
            pub_number = self._extract_pub_number(text)
            
            # Extract title
            title = self._extract_title(text)
            
            # Extract abstract
            abstract = self._extract_abstract(text)
            
            return PatentMetadata(
                pub_number=pub_number,
                title=title,
                abstract=abstract,
                source="pdf"
            )
        except Exception as e:
            logger.error("Metadata extraction failed", error=str(e))
            raise

    async def _extract_claims(self, text: str) -> List[PatentClaim]:
        """Extract claims from PDF text."""
        try:
            claims = []
            
            # Try different claim patterns
            for pattern in self.claim_patterns:
                matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
                
                for match in matches:
                    claim_num = int(match.group(1))
                    claim_text = match.group(2).strip()
                    
                    if claim_text and len(claim_text) > 10:
                        # Determine if independent (simple heuristic)
                        is_independent = not any(
                            dep_word in claim_text.lower() 
                            for dep_word in ['according to claim', 'as claimed in', 'wherein']
                        )
                        
                        claims.append(PatentClaim(
                            number=claim_num,
                            text=claim_text,
                            is_independent=is_independent
                        ))
                
                if claims:
                    break
            
            return claims
        except Exception as e:
            logger.error("Claims extraction failed", error=str(e))
            return []

    def _extract_pub_number(self, text: str) -> str:
        """Extract publication number from text."""
        # Common patterns for publication numbers
        patterns = [
            r'US\s*(\d{1,3}(?:,\d{3})*(?:,\d{3})*)',
            r'Publication\s+Number[:\s]*([A-Z]{2}\s*\d+)',
            r'Pub\.?\s*No\.?[:\s]*([A-Z]{2}\s*\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).replace(' ', '')
        
        return ""

    def _extract_title(self, text: str) -> str:
        """Extract title from text."""
        # Look for title patterns
        patterns = [
            r'Title[:\s]*(.*?)(?=\n|Abstract|Claims|Description)',
            r'Invention\s+Title[:\s]*(.*?)(?=\n|Abstract|Claims|Description)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                if title and len(title) > 5:
                    return title
        
        return "Untitled Patent"

    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from text."""
        # Look for abstract patterns
        patterns = [
            r'Abstract[:\s]*(.*?)(?=\n\n|Claims|Description|Background)',
            r'Summary[:\s]*(.*?)(?=\n\n|Claims|Description|Background)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                if abstract and len(abstract) > 20:
                    return abstract
        
        return None
