from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
from datetime import date
from uuid import UUID


# ── Partner management ────────────────────────────────────────────────────────

class CreatePartnerRequest(BaseModel):
    partner_name: str
    webhook_url: Optional[str] = None


class CreatePartnerResponse(BaseModel):
    partner_id: UUID
    partner_name: str
    api_key: str  # raw key returned exactly once — store it securely


# ── Case initialization ───────────────────────────────────────────────────────

class InitializeCaseRequest(BaseModel):
    # Partner's own reference (policy number, claim ID, etc.)
    external_ref_id: str

    # Deceased / policyholder
    breadwinner_name: str
    date_of_death: str           # DD/MM/YYYY
    employment_type: str         # Government | Private | Business | Daily Wage
    state: str
    had_epf: Optional[str] = "Not sure"

    # Claimant
    claimant_name: str
    claimant_relationship: Optional[str] = None
    claimant_aadhaar: Optional[str] = None
    claimant_bank_account: Optional[str] = None
    claimant_bank_ifsc: Optional[str] = None

    preferred_language: Optional[str] = "English"


class AgentResult(BaseModel):
    agent: str
    status: str
    summary: str


class InitializeCaseResponse(BaseModel):
    case_id: UUID
    external_ref_id: str
    partner_id: UUID
    compliance_grade: int
    entitlement_total: float
    schemes_found: int
    agents_run: List[AgentResult]
    esign_transaction_id: Optional[str] = None
    pdf_dispatched: bool = False


# ── Document upload ───────────────────────────────────────────────────────────

class UploadDocRequest(BaseModel):
    document_type: str           # death_certificate | aadhaar | passbook | epf_passbook
    document_url: Optional[str] = None
    document_base64: Optional[str] = None

    @field_validator("document_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        allowed = {"death_certificate", "aadhaar", "passbook", "epf_passbook",
                   "marriage_certificate", "birth_certificate"}
        if v not in allowed:
            raise ValueError(f"document_type must be one of: {', '.join(sorted(allowed))}")
        return v


class UploadDocResponse(BaseModel):
    document_id: UUID
    document_type: str
    is_valid: bool
    quality_score: int
    issues: List[str]
    rejection_reason: str
    reupload_required: bool


# ── Case status ───────────────────────────────────────────────────────────────

class DocumentSummary(BaseModel):
    document_type: str
    is_valid: bool
    quality_score: int


class CaseStatusResponse(BaseModel):
    case_id: UUID
    external_ref_id: Optional[str]
    partner_id: Optional[UUID]
    status: str
    compliance_grade: int
    entitlement_total: float
    onboarding_step: int
    esign_transaction_id: Optional[str]
    documents: List[DocumentSummary]
    agents_run: List[AgentResult]
