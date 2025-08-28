"""Patent data models for the workers."""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class PatentClaim(BaseModel):
    """Model for a patent claim."""
    number: int
    text: str
    is_independent: bool = False
    dependencies: Optional[List[int]] = None


class PatentMetadata(BaseModel):
    """Model for patent metadata."""
    pub_number: str
    app_number: Optional[str] = None
    prio_date: Optional[date] = None
    family_id: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    assignees: Optional[List[str]] = None
    inventors: Optional[List[str]] = None
    cpc_codes: Optional[List[str]] = None
    ipc_codes: Optional[List[str]] = None
    lang: str = "en"
    source: str  # 'uspto', 'epo', 'wipo', etc.
    ocr_used: bool = False


class PatentDocument(BaseModel):
    """Model for a complete patent document."""
    metadata: PatentMetadata
    text: str
    claims: List[PatentClaim]
    original_file_path: Optional[str] = None
    extracted_at: Optional[str] = None
