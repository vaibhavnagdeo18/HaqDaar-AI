import logging
from typing import List, Optional
from pydantic import BaseModel
from services.pdf_service import PDFService

logger = logging.getLogger(__name__)

class GeneratedForm(BaseModel):
    pdf_bytes: bytes
    missing_fields: List[str]
    is_ready: bool

class FormAgent:
    def __init__(self, pdf_service: PDFService):
        self.pdf_service = pdf_service
        self.REQUIRED_FIELDS = ["breadwinner_name", "date_of_death", "uan", "nominee_name", "relationship", "bank_account", "ifsc"]

    async def generate_epf_form(self, family_data: dict) -> GeneratedForm:
        """
        Gathers data and calls PDFService to generate a structured EPF Form 20.
        """
        logger.info(f"FormAgent: Generating EPF Form 20 for {family_data.get('breadwinner_name')}")
        
        missing = []
        for field in self.REQUIRED_FIELDS:
            if not family_data.get(field):
                missing.append(field)
        
        # Call PDFService with the data (including placeholders for missing fields)
        pdf_bytes = self.pdf_service.generate_epf_form_20(family_data)
        
        return GeneratedForm(
            pdf_bytes=pdf_bytes,
            missing_fields=missing,
            is_ready=(len(missing) == 0)
        )
