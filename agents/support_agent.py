import logging
from pydantic import BaseModel
from typing import Optional
import json

logger = logging.getLogger(__name__)

# Keywords that signal grief or emotional distress — checked before any LLM call
# to keep latency low on the hot path.
GRIEF_KEYWORDS = [
    "miss him", "miss her", "miss them", "crying", "can't stop crying",
    "can't eat", "can't sleep", "so lost", "feel lost", "heartbroken",
    "devastated", "broken", "alone", "lonely", "don't know what to do",
    "why did this happen", "so painful", "in pain", "grief", "grieving",
    "depressed", "depression", "suicid", "end my life", "no point",
    "please help me", "i need help", "overwhelmed", "too much",
]

class SupportResponse(BaseModel):
    is_grief_message: bool
    empathy_message: str = ""
    healing_steps: list[str] = []
    claims_nudge: str = ""
    intercept: bool = False  # True = skip claims logic for this turn


class SupportAgent:
    def __init__(self, gemini_service):
        self.gemini = gemini_service

    def _quick_screen(self, text: str) -> bool:
        """Fast keyword pre-screen before calling Gemini."""
        lowered = text.lower()
        return any(kw in lowered for kw in GRIEF_KEYWORDS)

    async def assess_message(self, message: str, preferred_language: str = "English") -> SupportResponse:
        """
        Determines whether a message carries significant emotional/grief content.
        If yes, returns an empathetic response + healing steps.
        Never blocks the claims flow permanently — sets intercept=True for one turn only.
        """
        if not self._quick_screen(message):
            return SupportResponse(is_grief_message=False)

        logger.info("SupportAgent: grief signal detected, running full assessment")

        prompt = f"""
You are a compassionate support companion embedded in Haqdaar, an AI system that helps Indian families
file post-death government claims. A family member has just sent this message:

"{message}"

Your job is to assess the emotional content and craft a warm, human response.

Respond ONLY with a raw JSON object (no markdown, no backticks):
{{
    "is_grief_message": boolean — true if the message expresses grief, distress, or emotional overwhelm,
    "empathy_message": string — a warm, short (2-3 sentence) empathetic response in {preferred_language}.
        Do NOT give legal or claims advice here. Acknowledge their pain first,
    "healing_steps": array of 2-3 short strings — gentle, practical "Next Steps for Healing"
        (e.g., "Talk to a trusted family member or friend today", "Contact iCall helpline: 9152987821"),
    "claims_nudge": string — one gentle sentence reminding them that their claims work can wait,
        and Haqdaar will be here when they are ready. In {preferred_language},
    "intercept": boolean — true if this message is primarily emotional and should NOT trigger
        claims data-collection this turn. Set false if grief is mild and they are still asking about claims.
}}
"""

        try:
            response_text = await self.gemini.generate_response(prompt)
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

            return SupportResponse(
                is_grief_message=data.get("is_grief_message", True),
                empathy_message=data.get("empathy_message", ""),
                healing_steps=data.get("healing_steps", []),
                claims_nudge=data.get("claims_nudge", ""),
                intercept=data.get("intercept", True),
            )
        except Exception as e:
            logger.error(f"SupportAgent assessment failed: {e}")
            return SupportResponse(
                is_grief_message=True,
                empathy_message=(
                    "We are so sorry for your loss. Please take all the time you need. "
                    "Haqdaar will be right here whenever you are ready to continue."
                ),
                healing_steps=[
                    "Reach out to a trusted family member or friend today.",
                    "iCall Mental Health Helpline: 9152987821 (free, confidential).",
                    "It is okay to take a break. Grief has no timeline.",
                ],
                claims_nudge="Your claims are safe with us. We will continue whenever you feel ready.",
                intercept=True,
            )

    def build_whatsapp_message(self, response: SupportResponse) -> str:
        """Formats a SupportResponse into a WhatsApp-ready message."""
        parts = [response.empathy_message]

        if response.healing_steps:
            parts.append("\n*Next Steps for Healing:*")
            for step in response.healing_steps:
                parts.append(f"- {step}")

        if response.claims_nudge:
            parts.append(f"\n_{response.claims_nudge}_")

        return "\n".join(parts)
