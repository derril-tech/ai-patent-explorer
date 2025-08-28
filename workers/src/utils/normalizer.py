"""Patent normalizer for standardizing various patent data fields."""

import re
from typing import Optional, List
from datetime import datetime, date
import unicodedata

import structlog

logger = structlog.get_logger(__name__)


class PatentNormalizer:
    """Normalizer for patent data fields."""

    def __init__(self):
        # Common company name variations
        self.company_variations = {
            'international business machines': 'IBM',
            'ibm corp': 'IBM',
            'ibm corporation': 'IBM',
            'microsoft corp': 'Microsoft',
            'microsoft corporation': 'Microsoft',
            'apple inc': 'Apple',
            'apple computer': 'Apple',
            'google llc': 'Google',
            'google inc': 'Google',
            'alphabet inc': 'Alphabet',
            'amazon com': 'Amazon',
            'amazon.com': 'Amazon',
            'amazon.com inc': 'Amazon',
            'facebook inc': 'Meta',
            'meta platforms': 'Meta',
            'tesla inc': 'Tesla',
            'tesla motors': 'Tesla',
        }

        # CPC classification hierarchy
        self.cpc_hierarchy = {
            'A': 'Human Necessities',
            'B': 'Performing Operations; Transporting',
            'C': 'Chemistry; Metallurgy',
            'D': 'Textiles; Paper',
            'E': 'Fixed Constructions',
            'F': 'Mechanical Engineering; Lighting; Heating; Weapons; Blasting',
            'G': 'Physics',
            'H': 'Electricity',
            'Y': 'General Tagging of New Technological Developments',
        }

        # IPC classification hierarchy
        self.ipc_hierarchy = {
            'A': 'Human Necessities',
            'B': 'Performing Operations; Transporting',
            'C': 'Chemistry; Metallurgy',
            'D': 'Textiles; Paper',
            'E': 'Fixed Constructions',
            'F': 'Mechanical Engineering; Lighting; Heating; Weapons; Blasting',
            'G': 'Physics',
            'H': 'Electricity',
        }

    def normalize_family_id(self, family_id: str) -> str:
        """Normalize patent family ID."""
        try:
            if not family_id:
                return ""
            
            # Remove common prefixes and suffixes
            normalized = family_id.strip().upper()
            
            # Remove common prefixes
            prefixes_to_remove = ['FAMILY:', 'FAM:', 'ID:', 'PATENT FAMILY:']
            for prefix in prefixes_to_remove:
                if normalized.startswith(prefix):
                    normalized = normalized[len(prefix):].strip()
            
            # Remove common suffixes
            suffixes_to_remove = ['(FAMILY)', '(PATENT FAMILY)']
            for suffix in suffixes_to_remove:
                if normalized.endswith(suffix):
                    normalized = normalized[:-len(suffix)].strip()
            
            # Ensure it's a valid format (alphanumeric with possible hyphens)
            if re.match(r'^[A-Z0-9\-]+$', normalized):
                return normalized
            else:
                # Try to extract a valid family ID
                match = re.search(r'([A-Z0-9\-]{5,})', normalized)
                if match:
                    return match.group(1)
                else:
                    return normalized
            
        except Exception as e:
            logger.error("Family ID normalization failed", error=str(e), family_id=family_id)
            return family_id

    def normalize_assignee(self, assignee: str) -> Optional[str]:
        """Normalize assignee name."""
        try:
            if not assignee:
                return None
            
            # Normalize unicode characters
            normalized = unicodedata.normalize('NFKC', assignee.strip())
            
            # Remove common legal suffixes
            legal_suffixes = [
                r'\s+inc\.?$', r'\s+corp\.?$', r'\s+llc$', r'\s+ltd\.?$',
                r'\s+limited$', r'\s+company$', r'\s+co\.?$', r'\s+corporation$'
            ]
            
            for suffix in legal_suffixes:
                normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)
            
            # Check for known variations
            lower_assignee = normalized.lower()
            for variation, standard in self.company_variations.items():
                if variation in lower_assignee:
                    return standard
            
            # Remove extra whitespace and normalize
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            
            return normalized if normalized else None
            
        except Exception as e:
            logger.error("Assignee normalization failed", error=str(e), assignee=assignee)
            return assignee

    def normalize_inventor(self, inventor: str) -> Optional[str]:
        """Normalize inventor name."""
        try:
            if not inventor:
                return None
            
            # Normalize unicode characters
            normalized = unicodedata.normalize('NFKC', inventor.strip())
            
            # Remove common suffixes
            suffixes_to_remove = [
                r'\s+ph\.?d\.?$', r'\s+md$', r'\s+esq\.?$', r'\s+jr\.?$',
                r'\s+sr\.?$', r'\s+iii$', r'\s+iv$', r'\s+v$'
            ]
            
            for suffix in suffixes_to_remove:
                normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)
            
            # Standardize name format (Last, First Middle)
            # This is a simple approach - more sophisticated name parsing could be added
            parts = re.split(r'[,\s]+', normalized)
            if len(parts) >= 2:
                # Assume last name is first part, rest are first/middle names
                last_name = parts[0]
                first_names = ' '.join(parts[1:])
                normalized = f"{last_name}, {first_names}"
            
            # Remove extra whitespace
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            
            return normalized if normalized else None
            
        except Exception as e:
            logger.error("Inventor normalization failed", error=str(e), inventor=inventor)
            return inventor

    def normalize_date(self, date_obj) -> Optional[datetime]:
        """Normalize date object."""
        try:
            if not date_obj:
                return None
            
            # If it's already a datetime object, return it
            if isinstance(date_obj, datetime):
                return date_obj
            
            # If it's a date object, convert to datetime
            if isinstance(date_obj, date):
                return datetime.combine(date_obj, datetime.min.time())
            
            # If it's a string, try to parse it
            if isinstance(date_obj, str):
                # Try common date formats
                date_formats = [
                    '%Y-%m-%d',
                    '%Y/%m/%d',
                    '%m/%d/%Y',
                    '%d/%m/%Y',
                    '%Y%m%d',
                    '%B %d, %Y',
                    '%b %d, %Y',
                    '%d %B %Y',
                    '%d %b %Y'
                ]
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_obj, fmt)
                        return parsed_date
                    except ValueError:
                        continue
                
                # If no format matches, try to extract date using regex
                date_match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_obj)
                if date_match:
                    year, month, day = date_match.groups()
                    return datetime(int(year), int(month), int(day))
            
            return None
            
        except Exception as e:
            logger.error("Date normalization failed", error=str(e), date_obj=date_obj)
            return None

    def normalize_cpc_code(self, code: str) -> Optional[str]:
        """Normalize CPC classification code."""
        try:
            if not code:
                return None
            
            # Remove whitespace and convert to uppercase
            normalized = code.strip().upper()
            
            # CPC format: A01B 1/00 or A01B1/00
            # Remove spaces and ensure proper format
            normalized = re.sub(r'\s+', '', normalized)
            
            # Validate CPC format
            if re.match(r'^[A-HY]\d{2}[A-Z]\d{1,3}/\d{1,3}$', normalized):
                return normalized
            
            # Try to fix common format issues
            # Add missing slash
            if re.match(r'^[A-HY]\d{2}[A-Z]\d{1,3}\d{1,3}$', normalized):
                # Insert slash before last group of digits
                match = re.match(r'^([A-HY]\d{2}[A-Z]\d{1,3})(\d{1,3})$', normalized)
                if match:
                    return f"{match.group(1)}/{match.group(2)}"
            
            return normalized if normalized else None
            
        except Exception as e:
            logger.error("CPC code normalization failed", error=str(e), code=code)
            return code

    def normalize_ipc_code(self, code: str) -> Optional[str]:
        """Normalize IPC classification code."""
        try:
            if not code:
                return None
            
            # Remove whitespace and convert to uppercase
            normalized = code.strip().upper()
            
            # IPC format: A01B 1/00 or A01B1/00
            # Remove spaces and ensure proper format
            normalized = re.sub(r'\s+', '', normalized)
            
            # Validate IPC format
            if re.match(r'^[A-H]\d{2}[A-Z]\d{1,3}/\d{1,3}$', normalized):
                return normalized
            
            # Try to fix common format issues
            # Add missing slash
            if re.match(r'^[A-H]\d{2}[A-Z]\d{1,3}\d{1,3}$', normalized):
                # Insert slash before last group of digits
                match = re.match(r'^([A-H]\d{2}[A-Z]\d{1,3})(\d{1,3})$', normalized)
                if match:
                    return f"{match.group(1)}/{match.group(2)}"
            
            return normalized if normalized else None
            
        except Exception as e:
            logger.error("IPC code normalization failed", error=str(e), code=code)
            return code

    def get_cpc_rollup(self, code: str) -> Optional[str]:
        """Get CPC rollup code (section level)."""
        try:
            if not code:
                return None
            
            # Extract section (first character)
            section = code[0] if len(code) > 0 else None
            
            if section and section in self.cpc_hierarchy:
                return f"{section} - {self.cpc_hierarchy[section]}"
            
            return None
            
        except Exception as e:
            logger.error("CPC rollup failed", error=str(e), code=code)
            return None

    def get_ipc_rollup(self, code: str) -> Optional[str]:
        """Get IPC rollup code (section level)."""
        try:
            if not code:
                return None
            
            # Extract section (first character)
            section = code[0] if len(code) > 0 else None
            
            if section and section in self.ipc_hierarchy:
                return f"{section} - {self.ipc_hierarchy[section]}"
            
            return None
            
        except Exception as e:
            logger.error("IPC rollup failed", error=str(e), code=code)
            return None

    def normalize_publication_number(self, pub_number: str) -> str:
        """Normalize publication number."""
        try:
            if not pub_number:
                return ""
            
            # Remove whitespace and convert to uppercase
            normalized = pub_number.strip().upper()
            
            # Remove common prefixes
            prefixes_to_remove = ['PUB:', 'PUBLICATION:', 'PATENT:', 'PAT:']
            for prefix in prefixes_to_remove:
                if normalized.startswith(prefix):
                    normalized = normalized[len(prefix):].strip()
            
            # Standardize format for US patents
            if re.match(r'^US\d+$', normalized):
                # Add proper formatting for US patents
                match = re.match(r'^US(\d+)$', normalized)
                if match:
                    number = match.group(1)
                    if len(number) <= 7:
                        return f"US{number.zfill(7)}"
                    else:
                        return f"US{number}"
            
            return normalized
            
        except Exception as e:
            logger.error("Publication number normalization failed", error=str(e), pub_number=pub_number)
            return pub_number
