import logging
from typing import List, Optional
from pydantic import BaseModel
from services.pdf_service import PDFService
from services.form_overlay_service import FormOverlayService

logger = logging.getLogger(__name__)


class GeneratedForm(BaseModel):
    pdf_bytes: bytes
    missing_fields: List[str]
    is_ready: bool
    esign_transaction_id: Optional[str] = None
    form_type: str = "generated"   # "generated" | "form5if_overlay"
    file_path: Optional[str] = None


class FormAgent:
    def __init__(self, pdf_service: PDFService):
        self.pdf_service = pdf_service
        self.overlay_service = FormOverlayService()

        self.REQUIRED_FIELDS_EPF20 = [
            "breadwinner_name", "date_of_death", "uan",
            "nominee_name", "relationship", "bank_account", "ifsc",
        ]
        self.REQUIRED_FIELDS_FORM5IF = [
            "breadwinner_name", "date_of_death",
        ]

    async def generate_epf_form(
        self,
        family_data: dict,
        partner_name: Optional[str] = None,
    ) -> GeneratedForm:
        """Generate EPF Form 20 (ReportLab, with digital signature block)."""
        logger.info(f"FormAgent: Generating EPF Form 20 for {family_data.get('breadwinner_name')}")

        missing = [f for f in self.REQUIRED_FIELDS_EPF20 if not family_data.get(f)]
        resolved_partner = partner_name or family_data.get("partner_name")

        pdf_bytes, transaction_id = self.pdf_service.generate_epf_form_20(
            family_data,
            partner_name=resolved_partner,
        )

        return GeneratedForm(
            pdf_bytes=pdf_bytes,
            missing_fields=missing,
            is_ready=(len(missing) == 0),
            esign_transaction_id=transaction_id,
            form_type="generated",
        )

    async def generate_form5if(
        self,
        family_data: dict,
        case_id: str,
        save_to_disk: bool = True,
        storage_path: str = "./documents",
    ) -> GeneratedForm:
        """
        Overlay user data onto the official Form5IF.pdf (EDLI Insurance Claim).
        Triggered when ComplianceAgent marks a case as Ready for Filing.
        """
        logger.info(f"FormAgent: Filling Form5IF for case {case_id}, deceased: {family_data.get('breadwinner_name')}")

        missing = [f for f in self.REQUIRED_FIELDS_FORM5IF if not family_data.get(f)]

        pdf_bytes = self.overlay_service.generate_form5if(family_data, case_id)

        file_path = None
        if save_to_disk:
            file_path = self.overlay_service.save_to_disk(pdf_bytes, case_id, storage_path)

        return GeneratedForm(
            pdf_bytes=pdf_bytes,
            missing_fields=missing,
            is_ready=True,
            form_type="form5if_overlay",
            file_path=file_path,
        )
