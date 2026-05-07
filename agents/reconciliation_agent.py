import logging
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

class ReconciliationResult(BaseModel):
    has_mismatch: bool
    mismatch_description: str
    affidavit_text: str

class ReconciliationAgent:
    def __init__(self, gemini_service, sarvam_service):
        self.gemini = gemini_service
        self.sarvam = sarvam_service

    async def analyze_identities(self, name1: str, name2: str, target_lang: str = "English") -> ReconciliationResult:
        logger.info(f"Analyzing identity mismatch: {name1} vs {name2}")
        
        prompt = f"""
        You are a legal identity reconciliation expert in India.
        Compare the following two names from different documents:
        Name A: "{name1}"
        Name B: "{name2}"
        
        If they are essentially the same person but with spelling variations, missing initials, or common Indian naming differences, set has_mismatch to true.
        
        If has_mismatch is true, draft a formal "One and the Same Person Affidavit" in English.
        Include placeholders for signatures, date, and place.
        
        Respond ONLY with a JSON object:
        {{
            "has_mismatch": boolean,
            "mismatch_description": "string",
            "affidavit_text": "string (The full affidavit text in English)"
        }}
        """
        
        try:
            response_text = await self.gemini.generate_response(prompt)
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_text)
            
            has_mismatch = data.get("has_mismatch", False)
            mismatch_desc = data.get("mismatch_description", "")
            affidavit_en = data.get("affidavit_text", "")
            
            final_affidavit = affidavit_en
            if has_mismatch and target_lang != "English" and affidavit_en:
                try:
                    final_affidavit = await self.sarvam.translate(affidavit_en, "English", target_lang)
                except Exception as te:
                    logger.error(f"Failed to translate affidavit: {te}")
            
            return ReconciliationResult(
                has_mismatch=has_mismatch,
                mismatch_description=mismatch_desc,
                affidavit_text=final_affidavit
            )
        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
            return ReconciliationResult(
                has_mismatch=False,
                mismatch_description="Error during analysis.",
                affidavit_text=""
            )
