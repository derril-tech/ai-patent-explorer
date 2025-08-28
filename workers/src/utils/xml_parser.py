"""XML patent parser for USPTO, EPO, and WIPO patent documents."""

import asyncio
from pathlib import Path
from typing import List, Optional
import xml.etree.ElementTree as ET
from datetime import datetime

import structlog
from lxml import etree

from ..models.patent import PatentDocument, PatentMetadata, PatentClaim

logger = structlog.get_logger(__name__)


class XMLPatentParser:
    """Parser for XML patent documents from various sources."""

    def __init__(self):
        self.namespaces = {
            'uspto': 'http://www.wipo.int/standards/XMLSchema/ST96/Patent',
            'epo': 'http://www.epo.org/fulltext',
            'wipo': 'http://www.wipo.int/standards/XMLSchema/ST96/Patent'
        }

    async def parse(self, file_path: Path) -> PatentDocument:
        """Parse an XML patent document."""
        try:
            # Parse XML file
            tree = etree.parse(str(file_path))
            root = tree.getroot()

            # Detect source and parse accordingly
            if self._is_uspto_xml(root):
                return await self._parse_uspto_xml(root, file_path)
            elif self._is_epo_xml(root):
                return await self._parse_epo_xml(root, file_path)
            elif self._is_wipo_xml(root):
                return await self._parse_wipo_xml(root, file_path)
            else:
                raise ValueError("Unknown XML format")

        except Exception as e:
            logger.error("XML parsing failed", error=str(e), file_path=str(file_path))
            raise

    def _is_uspto_xml(self, root) -> bool:
        """Check if XML is from USPTO."""
        return 'us-patent-application' in root.tag or 'us-patent-grant' in root.tag

    def _is_epo_xml(self, root) -> bool:
        """Check if XML is from EPO."""
        return 'ep-patent-document' in root.tag

    def _is_wipo_xml(self, root) -> bool:
        """Check if XML is from WIPO."""
        return 'patent-document' in root.tag

    async def _parse_uspto_xml(self, root, file_path: Path) -> PatentDocument:
        """Parse USPTO XML patent document."""
        try:
            # Extract metadata
            metadata = PatentMetadata(
                pub_number=self._extract_uspto_pub_number(root),
                app_number=self._extract_uspto_app_number(root),
                prio_date=self._extract_uspto_prio_date(root),
                title=self._extract_uspto_title(root),
                abstract=self._extract_uspto_abstract(root),
                assignees=self._extract_uspto_assignees(root),
                inventors=self._extract_uspto_inventors(root),
                source="uspto"
            )

            # Extract text
            text = self._extract_uspto_text(root)

            # Extract claims
            claims = self._extract_uspto_claims(root)

            return PatentDocument(
                metadata=metadata,
                text=text,
                claims=claims,
                original_file_path=str(file_path),
                extracted_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error("USPTO XML parsing failed", error=str(e))
            raise

    async def _parse_epo_xml(self, root, file_path: Path) -> PatentDocument:
        """Parse EPO XML patent document."""
        try:
            # Extract metadata
            metadata = PatentMetadata(
                pub_number=self._extract_epo_pub_number(root),
                app_number=self._extract_epo_app_number(root),
                prio_date=self._extract_epo_prio_date(root),
                title=self._extract_epo_title(root),
                abstract=self._extract_epo_abstract(root),
                assignees=self._extract_epo_assignees(root),
                inventors=self._extract_epo_inventors(root),
                source="epo"
            )

            # Extract text
            text = self._extract_epo_text(root)

            # Extract claims
            claims = self._extract_epo_claims(root)

            return PatentDocument(
                metadata=metadata,
                text=text,
                claims=claims,
                original_file_path=str(file_path),
                extracted_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error("EPO XML parsing failed", error=str(e))
            raise

    async def _parse_wipo_xml(self, root, file_path: Path) -> PatentDocument:
        """Parse WIPO XML patent document."""
        try:
            # Extract metadata
            metadata = PatentMetadata(
                pub_number=self._extract_wipo_pub_number(root),
                app_number=self._extract_wipo_app_number(root),
                prio_date=self._extract_wipo_prio_date(root),
                title=self._extract_wipo_title(root),
                abstract=self._extract_wipo_abstract(root),
                assignees=self._extract_wipo_assignees(root),
                inventors=self._extract_wipo_inventors(root),
                source="wipo"
            )

            # Extract text
            text = self._extract_wipo_text(root)

            # Extract claims
            claims = self._extract_wipo_claims(root)

            return PatentDocument(
                metadata=metadata,
                text=text,
                claims=claims,
                original_file_path=str(file_path),
                extracted_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error("WIPO XML parsing failed", error=str(e))
            raise

    # USPTO extraction methods
    def _extract_uspto_pub_number(self, root) -> str:
        """Extract publication number from USPTO XML."""
        pub_ref = root.find('.//publication-reference')
        if pub_ref is not None:
            doc_number = pub_ref.find('.//doc-number')
            if doc_number is not None:
                return doc_number.text
        return ""

    def _extract_uspto_app_number(self, root) -> Optional[str]:
        """Extract application number from USPTO XML."""
        app_ref = root.find('.//application-reference')
        if app_ref is not None:
            doc_number = app_ref.find('.//doc-number')
            if doc_number is not None:
                return doc_number.text
        return None

    def _extract_uspto_prio_date(self, root) -> Optional[datetime]:
        """Extract priority date from USPTO XML."""
        prio_claims = root.findall('.//priority-claim')
        if prio_claims:
            date_elem = prio_claims[0].find('.//date')
            if date_elem is not None:
                return datetime.strptime(date_elem.text, '%Y%m%d').date()
        return None

    def _extract_uspto_title(self, root) -> str:
        """Extract title from USPTO XML."""
        title_elem = root.find('.//invention-title')
        if title_elem is not None:
            return title_elem.text or ""
        return ""

    def _extract_uspto_abstract(self, root) -> Optional[str]:
        """Extract abstract from USPTO XML."""
        abstract_elem = root.find('.//abstract')
        if abstract_elem is not None:
            return abstract_elem.text or ""
        return None

    def _extract_uspto_assignees(self, root) -> List[str]:
        """Extract assignees from USPTO XML."""
        assignees = []
        assignee_elems = root.findall('.//assignee')
        for assignee in assignee_elems:
            org_name = assignee.find('.//orgname')
            if org_name is not None and org_name.text:
                assignees.append(org_name.text)
        return assignees

    def _extract_uspto_inventors(self, root) -> List[str]:
        """Extract inventors from USPTO XML."""
        inventors = []
        inventor_elems = root.findall('.//inventor')
        for inventor in inventor_elems:
            first_name = inventor.find('.//first-name')
            last_name = inventor.find('.//last-name')
            if first_name is not None and last_name is not None:
                name = f"{first_name.text} {last_name.text}".strip()
                if name:
                    inventors.append(name)
        return inventors

    def _extract_uspto_text(self, root) -> str:
        """Extract full text from USPTO XML."""
        text_parts = []
        
        # Extract description
        description = root.find('.//description')
        if description is not None:
            for elem in description.iter():
                if elem.text and elem.text.strip():
                    text_parts.append(elem.text.strip())
        
        # Extract claims
        claims = root.find('.//claims')
        if claims is not None:
            for elem in claims.iter():
                if elem.text and elem.text.strip():
                    text_parts.append(elem.text.strip())
        
        return " ".join(text_parts)

    def _extract_uspto_claims(self, root) -> List[PatentClaim]:
        """Extract claims from USPTO XML."""
        claims = []
        claim_elems = root.findall('.//claim')
        
        for i, claim_elem in enumerate(claim_elems, 1):
            claim_text = ""
            for elem in claim_elem.iter():
                if elem.text and elem.text.strip():
                    claim_text += elem.text.strip() + " "
            
            # Determine if independent
            is_independent = "dependent" not in claim_elem.get('claim-type', '').lower()
            
            claims.append(PatentClaim(
                number=i,
                text=claim_text.strip(),
                is_independent=is_independent
            ))
        
        return claims

    # EPO extraction methods (stubs)
    def _extract_epo_pub_number(self, root) -> str:
        """Extract publication number from EPO XML."""
        # Implementation for EPO
        return ""

    def _extract_epo_app_number(self, root) -> Optional[str]:
        """Extract application number from EPO XML."""
        return None

    def _extract_epo_prio_date(self, root) -> Optional[datetime]:
        """Extract priority date from EPO XML."""
        return None

    def _extract_epo_title(self, root) -> str:
        """Extract title from EPO XML."""
        return ""

    def _extract_epo_abstract(self, root) -> Optional[str]:
        """Extract abstract from EPO XML."""
        return None

    def _extract_epo_assignees(self, root) -> List[str]:
        """Extract assignees from EPO XML."""
        return []

    def _extract_epo_inventors(self, root) -> List[str]:
        """Extract inventors from EPO XML."""
        return []

    def _extract_epo_text(self, root) -> str:
        """Extract full text from EPO XML."""
        return ""

    def _extract_epo_claims(self, root) -> List[PatentClaim]:
        """Extract claims from EPO XML."""
        return []

    # WIPO extraction methods (stubs)
    def _extract_wipo_pub_number(self, root) -> str:
        """Extract publication number from WIPO XML."""
        return ""

    def _extract_wipo_app_number(self, root) -> Optional[str]:
        """Extract application number from WIPO XML."""
        return None

    def _extract_wipo_prio_date(self, root) -> Optional[datetime]:
        """Extract priority date from WIPO XML."""
        return None

    def _extract_wipo_title(self, root) -> str:
        """Extract title from WIPO XML."""
        return ""

    def _extract_wipo_abstract(self, root) -> Optional[str]:
        """Extract abstract from WIPO XML."""
        return None

    def _extract_wipo_assignees(self, root) -> List[str]:
        """Extract assignees from WIPO XML."""
        return []

    def _extract_wipo_inventors(self, root) -> List[str]:
        """Extract inventors from WIPO XML."""
        return []

    def _extract_wipo_text(self, root) -> str:
        """Extract full text from WIPO XML."""
        return ""

    def _extract_wipo_claims(self, root) -> List[PatentClaim]:
        """Extract claims from WIPO XML."""
        return []
