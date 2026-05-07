import logging
from typing import List
from models.family import Family
from models.claim import Claim

logger = logging.getLogger(__name__)

DOCUMENTS_BY_SCHEME = {
    "epf_form_20": [
        "death_certificate",      # Mandatory
        "aadhaar_claimant",       # Mandatory  
        "bank_passbook",          # Mandatory
        "epf_passbook",           # Mandatory
        "marriage_certificate",   # If spouse
        "birth_certificate",      # If child
    ],
    "pmjjby": [
        "death_certificate",
        "aadhaar_claimant",
        "bank_passbook",
        "pmjjby_policy_number",   # From bank
    ]
}

class DocumentCollectionWorkflow:
    def __init__(self, whatsapp_service, sarvam_service, ocr_service):
        self.whatsapp = whatsapp_service
        self.sarvam = sarvam_service
        self.ocr = ocr_service

    async def collect_documents(self, family: Family, claims: List[Claim]) -> None:
        """
        1. Deduplicate: death_certificate needed for 5 schemes → ask once
        2. Prioritize: ask for documents needed for most urgent deadline first
        3. For each document:
           a. Send guided capture instructions via Sarvam TTS
           b. Wait for upload
           c. Run quality assessment
        """
        logger.info(f"Starting document collection for family {family.id}")
