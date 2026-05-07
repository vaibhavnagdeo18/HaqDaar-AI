import uuid
import logging
from sqlalchemy.orm import Session
from models.family import Family
from models.claim import Claim
import datetime

logger = logging.getLogger(__name__)

DEADLINE_DEPENDENCIES = {
    "bank_nominee_transfer": ["epf_reference_number"],  # Needs EPF number first
    "edli_claim": ["epf_form_20"],  # Filed alongside EPF
    "state_pension": ["death_certificate_attested"],  # Needs attested copy
}

class TrackerAgent:
    def __init__(self, whatsapp_service, sarvam_service):
        self.whatsapp = whatsapp_service
        self.sarvam = sarvam_service

    async def check_and_alert(self, family_id: uuid.UUID, db_session: Session):
        """
        Run every 24 hours via Celery for all active cases.
        """
        # Note: Need actual DB query logic here
        logger.info(f"Checking deadlines for family {family_id}")
        
        # Mock logic to show structure
        # 1. Fetch claims
        # 2. Check dependencies
        # 3. Calculate days remaining
        days_remaining = 4
        if days_remaining < 7:
            alert_msg = "Your EPF claim deadline is in 4 days. You still need to submit the bank nominee form. Should I help you now? Reply YES to continue."
            # Translate
            # Send via whatsapp
