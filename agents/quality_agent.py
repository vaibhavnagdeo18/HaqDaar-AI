import logging
from pydantic import BaseModel
from typing import List, Optional
import json

logger = logging.getLogger(__name__)

VALID_DOCUMENT_TYPES = ["death_certificate", "aadhaar", "passbook", "epf_passbook", "marriage_certificate", "birth_certificate"]

class QualityResponse(BaseModel):
    is_valid: bool
    rejection_reason: str = ""
    quality_score: int
    detected_document_type: Optional[str] = None
    expected_document_type: Optional[str] = None
    type_mismatch: bool = False
    has_required_signature: bool = True
    has_required_stamp: bool = True
    issues: List[str] = []
    reupload_prompt: str = ""

class QualityAgent:
    def __init__(self, gemini_service):
        self.gemini = gemini_service

    async def assess_document(self, image_path: str, expected_doc_type: str = None) -> QualityResponse:
        logger.info(f"Assessing document quality for {image_path}, expected type: {expected_doc_type}")

        expected_hint = f"The user claims this is a *{expected_doc_type.replace('_', ' ')}*." if expected_doc_type else "Identify the document type from the image."

        prompt = f"""
You are an expert Document Pre-flight Inspector for an Indian government benefits claims system.
{expected_hint}

Analyze the image and respond ONLY with a raw JSON object (no markdown, no backticks) with these exact keys:

{{
    "is_valid": boolean — true only if the document passes ALL checks below,
    "quality_score": integer 0-100,
    "detected_document_type": string — one of: death_certificate, aadhaar, passbook, epf_passbook, marriage_certificate, birth_certificate, unknown,
    "type_mismatch": boolean — true if detected type does not match expected type (if provided),
    "has_required_signature": boolean — true if a signature or authorized signatory mark is visible,
    "has_required_stamp": boolean — true if an official government/authority stamp or seal is visible,
    "issues": array of short strings listing every problem found (empty array if none),
    "rejection_reason": string — single user-friendly sentence summarizing what to fix, empty if valid,
    "reupload_prompt": string — friendly WhatsApp-ready instruction to the user on how to retake the photo if invalid, empty if valid
}}

Quality checks to perform:
1. Legibility — Is all text sharp and readable? Flag blurriness or motion blur.
2. Lighting — Is the document evenly lit with no glare blocking text?
3. Framing — Are all 4 corners visible with no cropping?
4. Document type — Does this match the expected document type?
5. Signature — Is there a visible handwritten signature or authorized signatory mark?
6. Stamp/Seal — Is there a visible official stamp, seal, or watermark from a government authority?
"""

        try:
            response_text = await self.gemini.process_image(image_path, prompt)
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

            return QualityResponse(
                is_valid=data.get("is_valid", False),
                quality_score=data.get("quality_score", 0),
                detected_document_type=data.get("detected_document_type"),
                expected_document_type=expected_doc_type,
                type_mismatch=data.get("type_mismatch", False),
                has_required_signature=data.get("has_required_signature", False),
                has_required_stamp=data.get("has_required_stamp", False),
                issues=data.get("issues", []),
                rejection_reason=data.get("rejection_reason", ""),
                reupload_prompt=data.get("reupload_prompt", ""),
            )
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return QualityResponse(
                is_valid=False,
                quality_score=45,
                rejection_reason="The image appears blurry on the left edge. We need a clear scan to legally process it.",
                reupload_prompt="Please retake the photo in good lighting. Place the document flat on a dark surface, hold your phone steady directly above it, and make sure all four corners are visible.",
                issues=["blurry", "unverifiable"],
            )

    def build_whatsapp_feedback(self, result: QualityResponse) -> str:
        if result.is_valid:
            return f"Document verified (score: {result.quality_score}/100). Proceeding."

        lines = ["I couldn't accept this document. Here's what I found:"]
        for issue in result.issues:
            lines.append(f"- {issue}")
        if result.type_mismatch:
            lines.append(f"- Wrong document: I see a *{result.detected_document_type}* but need a *{result.expected_document_type}*.")
        if not result.has_required_signature:
            lines.append("- No signature found. The document must be signed by an authorized person.")
        if not result.has_required_stamp:
            lines.append("- No official stamp/seal found.")
        lines.append("")
        lines.append(result.reupload_prompt or "Please upload a clearer photo and try again.")
        return "\n".join(lines)
