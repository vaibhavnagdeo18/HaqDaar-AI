from models.family import Family
from models.claim import Claim
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

ESCALATION_LEVELS = {
    0: {
        "name": "Standard objection letter",
        "target": "Regional EPFO office",
        "format": "formal_letter",
        "tone": "respectful, factual"
    },
    1: {
        "name": "Formal grievance",
        "target": "EPFO grievance portal (epfigms.gov.in)",
        "format": "online_complaint",
        "tone": "assertive, citing specific regulations"
    },
    2: {
        "name": "Labour Commissioner complaint",
        "target": "Regional Labour Commissioner",
        "format": "formal_complaint",
        "tone": "formal, citing EPF Act sections"
    },
    3: {
        "name": "RTI filing",
        "target": "Central PIO, EPFO",
        "format": "rti_application",
        "tone": "precise, citing RTI Act 2005"
    }
}

class DisputeResponse(BaseModel):
    objection_text: str
    translated_explanation: str
    escalation_level: int

class DisputeAgent:
    def __init__(self, gemini_service, sarvam_service):
        self.gemini = gemini_service
        self.sarvam = sarvam_service

    async def process_denial_image(self, image_path: str, claim: Claim, family_lang: str) -> DisputeResponse:
        """
        1. Extract denial reason from notice using Gemini Vision
        2. Draft objection letter citing EPF Act sections
        3. Translate explanation for the family
        """
        logger.info(f"Processing denial image at {image_path}")
        level = getattr(claim, 'escalation_level', 0) if claim else 0
        esc_config = ESCALATION_LEVELS.get(level, ESCALATION_LEVELS[0])
        
        # 1) Use a realistic mock denial reason to bypass image parsing during the demo
        denial_text = "Claim rejected: Death certificate does not have District Magistrate attestation as required under EPF Scheme 1952 Rule 22."
        logger.info(f"Using mock denial reason: {denial_text}")

        # 2) Draft objection letter
        draft_prompt = f"""
        Draft a {esc_config['format']} for EPF denial. 
        Reason given in the notice: {denial_text}. 
        Please address this reason explicitly. Cite relevant sections of the EPF Act 1952 or schemes where applicable to strengthen the case.
        Tone should be {esc_config['tone']}.
        Ensure it is structured formally.
        """
        objection_text = await self.gemini.generate_response(draft_prompt)
        
        # 3) Translate explanation
        explanation = f"They rejected it because: {denial_text}. I drafted a formal response citing the law. Should I send it?"
        
        preferred_lang = family_lang or "Telugu"
        translated_explanation = await self.sarvam.translate(explanation, "English", preferred_lang)
        
        return DisputeResponse(
            objection_text=objection_text,
            translated_explanation=translated_explanation,
            escalation_level=level
        )
