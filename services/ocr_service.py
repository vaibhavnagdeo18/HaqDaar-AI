from typing import Dict, Any, List
from pydantic import BaseModel
import logging

# import cv2
# import pytesseract

logger = logging.getLogger(__name__)

class DocumentQuality(BaseModel):
    quality_score: float
    issues: List[str]
    is_processable: bool
    guidance: str

class OCRService:
    def __init__(self, gemini_service):
        self.gemini_service = gemini_service

    async def assess_document_quality(self, image: bytes, doc_type: str) -> DocumentQuality:
        """
        Stub method returning mock response.
        """
        logger.info(f"Assessing quality for {doc_type} (Stubbed)")
        return DocumentQuality(
            quality_score=0.9,
            issues=[],
            is_processable=True,
            guidance="Perfect."
        )

    async def extract_fields(self, image: bytes, doc_type: str) -> dict:
        """
        Stub method returning empty dict.
        """
        logger.info(f"Extracting fields for {doc_type} (Stubbed)")
        return {}

    async def guided_capture_instructions(self, doc_type: str, language: str) -> str:
        """
        Return step-by-step photo capture instructions in family's language.
        """
        if doc_type == "death_certificate" and language == "Telugu":
            return "మీ కెమెరా తెరవండి. సర్టిఫికేట్ను టేబుల్పై సమతలంగా ఉంచండి. నాలుగు మూలలు కనిపించేలా చూసుకోండి. ఫోటో పంపండి."
        return "Please open your camera and take a clear photo of the document."
