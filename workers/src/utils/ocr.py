"""OCR processor for extracting text from PDF images."""

import asyncio
from pathlib import Path
from typing import Optional
import tempfile

import pytesseract
from PIL import Image
import pdf2image
import structlog

logger = structlog.get_logger(__name__)


class OCRProcessor:
    """OCR processor for extracting text from PDF images."""

    def __init__(self):
        # Configure tesseract path if needed
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass

    async def extract_text(self, file_path: Path) -> str:
        """Extract text from PDF using OCR."""
        try:
            # Convert PDF to images
            images = await self._pdf_to_images(file_path)
            
            # Extract text from each image
            text_parts = []
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1} with OCR")
                page_text = await self._extract_text_from_image(image)
                text_parts.append(page_text)
            
            return " ".join(text_parts)
        except Exception as e:
            logger.error("OCR text extraction failed", error=str(e))
            raise

    async def _pdf_to_images(self, file_path: Path) -> list:
        """Convert PDF to list of PIL Images."""
        try:
            # Convert PDF pages to images
            images = pdf2image.convert_from_path(
                file_path,
                dpi=300,  # High DPI for better OCR accuracy
                fmt='PNG'
            )
            return images
        except Exception as e:
            logger.error("PDF to image conversion failed", error=str(e))
            raise

    async def _extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from a single image using OCR."""
        try:
            # Configure OCR settings for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:!?()[]{}"\'-_/\\ '
            
            # Extract text
            text = pytesseract.image_to_string(
                image,
                config=custom_config,
                lang='eng'
            )
            
            return text.strip()
        except Exception as e:
            logger.error("OCR extraction from image failed", error=str(e))
            return ""

    async def extract_text_with_confidence(self, file_path: Path) -> tuple[str, float]:
        """Extract text with confidence score."""
        try:
            # Convert PDF to images
            images = await self._pdf_to_images(file_path)
            
            # Extract text with confidence from each image
            text_parts = []
            total_confidence = 0.0
            page_count = 0
            
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1} with OCR confidence")
                page_text, page_confidence = await self._extract_text_with_confidence_from_image(image)
                text_parts.append(page_text)
                total_confidence += page_confidence
                page_count += 1
            
            avg_confidence = total_confidence / page_count if page_count > 0 else 0.0
            return " ".join(text_parts), avg_confidence
        except Exception as e:
            logger.error("OCR text extraction with confidence failed", error=str(e))
            raise

    async def _extract_text_with_confidence_from_image(self, image: Image.Image) -> tuple[str, float]:
        """Extract text with confidence from a single image."""
        try:
            # Get OCR data with confidence scores
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config='--oem 3 --psm 6',
                lang='eng'
            )
            
            # Extract text and calculate average confidence
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(data['conf']):
                if conf > 0:  # Filter out low confidence results
                    text_parts.append(data['text'][i])
                    confidences.append(conf)
            
            text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return text.strip(), avg_confidence
        except Exception as e:
            logger.error("OCR extraction with confidence from image failed", error=str(e))
            return "", 0.0

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)
            
            return image
        except Exception as e:
            logger.error("Image preprocessing failed", error=str(e))
            return image
