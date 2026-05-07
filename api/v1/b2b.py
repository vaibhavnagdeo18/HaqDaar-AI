import hashlib
import secrets
import base64
import tempfile
import os
import logging
import uuid as uuid_lib
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from core.database import get_db
from core.auth import get_partner
from models.partner import Partner
from models.family import Family
from models.case import Case, CaseStatus
from models.document import Document
from agents.compliance_agent import ComplianceAgent
from agents.entitlement_agent import EntitlementAgent
from agents.quality_agent import QualityAgent
from agents.form_agent import FormAgent
from services.gemini_service import GeminiService
from services.sarvam_service import SarvamService
from services.pdf_service import PDFService

from api.v1.schemas import (
    CreatePartnerRequest, CreatePartnerResponse,
    InitializeCaseRequest, InitializeCaseResponse, AgentResult,
    UploadDocRequest, UploadDocResponse,
    CaseStatusResponse, DocumentSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/b2b", tags=["B2B Claims-as-a-Service"])

# Shared agent instances
_gemini = GeminiService()
_sarvam = SarvamService()
_pdf = PDFService()
_compliance_agent = ComplianceAgent(_gemini)
_entitlement_agent = EntitlementAgent(_gemini, _sarvam)
_quality_agent = QualityAgent(_gemini)
_form_agent = FormAgent(_pdf)


# ── Partner registration (no auth — call once, store key securely) ────────────

@router.post("/partners", response_model=CreatePartnerResponse, status_code=201)
async def create_partner(
    body: CreatePartnerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new B2B partner. Returns the raw API key exactly once.
    Hash it with SHA-256 to verify future requests.
    """
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    existing = await db.execute(
        select(Partner).where(Partner.partner_name == body.partner_name)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Partner name already registered.")

    partner = Partner(
        partner_name=body.partner_name,
        api_key_hash=key_hash,
        webhook_url=body.webhook_url,
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)

    return CreatePartnerResponse(
        partner_id=partner.id,
        partner_name=partner.partner_name,
        api_key=raw_key,
    )


# ── Initialize a case ─────────────────────────────────────────────────────────

@router.post("/initialize", response_model=InitializeCaseResponse, status_code=201)
async def initialize_case(
    body: InitializeCaseRequest,
    partner: Partner = Depends(get_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new case for a policyholder, run Compliance + Entitlement agents immediately,
    and auto-generate the EPF Form 20 PDF if compliance is 100%.
    """
    # Idempotency: return existing case for the same partner + external_ref_id
    existing = await db.execute(
        select(Case).where(
            Case.partner_id == partner.id,
            Case.external_ref_id == body.external_ref_id,
        )
    )
    if (existing_case := existing.scalars().first()):
        raise HTTPException(
            status_code=409,
            detail=f"Case already exists for ref {body.external_ref_id}. Use GET /status/{existing_case.id}",
        )

    # Create a synthetic phone number as the Family key for B2B cases
    synthetic_phone = f"b2b_{partner.id.hex[:8]}_{body.external_ref_id}"
    result = await db.execute(select(Family).where(Family.whatsapp_number == synthetic_phone))
    family = result.scalars().first()
    if not family:
        family = Family(whatsapp_number=synthetic_phone)
        db.add(family)
        await db.flush()

    family_data = {
        "breadwinner_name": body.breadwinner_name,
        "date_of_death": body.date_of_death,
        "employment_type": body.employment_type,
        "state": body.state,
        "had_epf": body.had_epf,
        "claimant_name": body.claimant_name,
        "claimant_relationship": body.claimant_relationship,
        "claimant_aadhaar": body.claimant_aadhaar,
        "claimant_bank_account": body.claimant_bank_account,
        "claimant_bank_ifsc": body.claimant_bank_ifsc,
        "preferred_language": body.preferred_language,
        "partner_name": partner.partner_name,
    }

    case = Case(
        family_id=family.id,
        partner_id=partner.id,
        external_ref_id=body.external_ref_id,
        status=CaseStatus.onboarding,
        onboarding_step=0,
        onboarding_data=family_data,
    )
    db.add(case)
    await db.flush()

    agents_run: List[AgentResult] = []

    # Work on a mutable copy — reassign at the end to trigger SQLAlchemy change detection
    onboarding_data = dict(case.onboarding_data)

    # Run Compliance Agent
    try:
        audit = await _compliance_agent.audit_family_data(family_data)
        onboarding_data["compliance_grade"] = audit.compliance_grade
        agents_run.append(AgentResult(
            agent="ComplianceAgent",
            status="success",
            summary=audit.message,
        ))
        case.status = CaseStatus.ready_to_submit if audit.is_ready_to_file else CaseStatus.audit_failed
    except Exception as e:
        logger.error(f"ComplianceAgent failed: {e}")
        audit = None
        agents_run.append(AgentResult(agent="ComplianceAgent", status="error", summary=str(e)))

    # Run Entitlement Agent
    try:
        report = await _entitlement_agent.discover_entitlements(family_data)
        case.entitlement_total = report.total_entitlement
        onboarding_data["entitlement_schemes"] = [s.dict() for s in report.schemes]
        agents_run.append(AgentResult(
            agent="EntitlementAgent",
            status="success",
            summary=f"Found {len(report.schemes)} schemes totalling INR {report.total_entitlement:,.0f}",
        ))
    except Exception as e:
        logger.error(f"EntitlementAgent failed: {e}")
        report = None
        agents_run.append(AgentResult(agent="EntitlementAgent", status="error", summary=str(e)))

    # Auto-generate PDF + trigger webhook if compliance is 100%
    esign_id = None
    pdf_dispatched = False

    if audit and audit.compliance_grade == 100:
        try:
            generated = await _form_agent.generate_epf_form(
                family_data, partner_name=partner.partner_name
            )
            esign_id = generated.esign_transaction_id
            onboarding_data["esign_transaction_id"] = esign_id
            case.status = CaseStatus.filed
            agents_run.append(AgentResult(
                agent="FormAgent",
                status="success",
                summary=f"EPF Form 20 generated. eSign ID: {esign_id}",
            ))

            # Fire outbound webhook to partner
            if partner.webhook_url:
                pdf_dispatched = await _fire_webhook(
                    partner=partner,
                    case=case,
                    pdf_bytes=generated.pdf_bytes,
                    esign_id=esign_id,
                )
        except Exception as e:
            logger.error(f"FormAgent failed: {e}")
            agents_run.append(AgentResult(agent="FormAgent", status="error", summary=str(e)))

    # Reassign dict so SQLAlchemy detects the JSON mutation
    case.onboarding_data = onboarding_data
    flag_modified(case, "onboarding_data")

    await db.commit()
    await db.refresh(case)

    return InitializeCaseResponse(
        case_id=case.id,
        external_ref_id=body.external_ref_id,
        partner_id=partner.id,
        compliance_grade=onboarding_data.get("compliance_grade", 0),
        entitlement_total=float(case.entitlement_total or 0),
        schemes_found=len(onboarding_data.get("entitlement_schemes", [])),
        agents_run=agents_run,
        esign_transaction_id=esign_id,
        pdf_dispatched=pdf_dispatched,
    )


# ── Document upload ───────────────────────────────────────────────────────────

@router.post("/upload-doc/{case_id}", response_model=UploadDocResponse, status_code=200)
async def upload_document(
    case_id: str,
    body: UploadDocRequest,
    partner: Partner = Depends(get_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document (via URL or base64) for Quality Agent pre-flight assessment.
    Saves the result to the Document table linked to the family.
    """
    case = await _get_case_for_partner(case_id, partner, db)

    # Resolve document bytes
    doc_bytes = await _resolve_document_bytes(body)

    # Save to a temp file for Gemini Vision
    suffix = ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(doc_bytes)
        tmp_path = tmp.name

    try:
        quality = await _quality_agent.assess_document(tmp_path, expected_doc_type=body.document_type)
    finally:
        os.unlink(tmp_path)

    # Persist document record
    storage_path = f"documents/b2b_{case.id}_{body.document_type}{suffix}"
    os.makedirs("documents", exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(doc_bytes)

    doc = Document(
        family_id=case.family_id,
        document_type=body.document_type,
        file_path=storage_path,
        quality_score=quality.quality_score / 100.0,
        issues=quality.issues,
        is_valid=quality.is_valid,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return UploadDocResponse(
        document_id=doc.id,
        document_type=body.document_type,
        is_valid=quality.is_valid,
        quality_score=quality.quality_score,
        issues=quality.issues,
        rejection_reason=quality.rejection_reason,
        reupload_required=not quality.is_valid,
    )


# ── Case status ───────────────────────────────────────────────────────────────

@router.get("/status/{case_id}", response_model=CaseStatusResponse)
async def get_case_status(
    case_id: str,
    partner: Partner = Depends(get_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the current state of all agents for a B2B case.
    """
    case = await _get_case_for_partner(case_id, partner, db)

    result = await db.execute(
        select(Document).where(Document.family_id == case.family_id)
    )
    documents = result.scalars().all()

    doc_summaries = [
        DocumentSummary(
            document_type=d.document_type,
            is_valid=d.is_valid or False,
            quality_score=int((d.quality_score or 0) * 100),
        )
        for d in documents
    ]

    data = case.onboarding_data or {}
    compliance_grade = data.get("compliance_grade", 0)
    schemes = data.get("entitlement_schemes", [])

    agents_run = [
        AgentResult(
            agent="ComplianceAgent",
            status="success" if compliance_grade else "pending",
            summary=f"Score: {compliance_grade}/100",
        ),
        AgentResult(
            agent="EntitlementAgent",
            status="success" if schemes else "pending",
            summary=f"{len(schemes)} scheme(s) identified",
        ),
    ]
    if data.get("esign_transaction_id"):
        agents_run.append(AgentResult(
            agent="FormAgent",
            status="success",
            summary=f"PDF generated. eSign ID: {data['esign_transaction_id']}",
        ))

    return CaseStatusResponse(
        case_id=case.id,
        external_ref_id=case.external_ref_id,
        partner_id=case.partner_id,
        status=case.status.value,
        compliance_grade=compliance_grade,
        entitlement_total=float(case.entitlement_total or 0),
        onboarding_step=case.onboarding_step or 0,
        esign_transaction_id=data.get("esign_transaction_id"),
        documents=doc_summaries,
        agents_run=agents_run,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_case_for_partner(case_id: str, partner: Partner, db: AsyncSession) -> Case:
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.partner_id == partner.id)
    )
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found for this partner.")
    return case


async def _resolve_document_bytes(body: UploadDocRequest) -> bytes:
    if body.document_url:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(body.document_url)
            response.raise_for_status()
            return response.content
    elif body.document_base64:
        try:
            return base64.b64decode(body.document_base64)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid base64 string.")
    else:
        raise HTTPException(status_code=422, detail="Provide either document_url or document_base64.")


async def _fire_webhook(partner: Partner, case: Case, pdf_bytes: bytes, esign_id: str) -> bool:
    """POST case result + base64 PDF to the partner's webhook URL."""
    payload = {
        "event": "pdf_generated",
        "case_id": str(case.id),
        "external_ref_id": case.external_ref_id,
        "esign_transaction_id": esign_id,
        "status": case.status.value,
        "compliance_grade": case.onboarding_data.get("compliance_grade", 0),
        "entitlement_total": float(case.entitlement_total or 0),
        "pdf_base64": base64.b64encode(pdf_bytes).decode(),
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(partner.webhook_url, json=payload)
            resp.raise_for_status()
            logger.info(f"Webhook delivered to {partner.webhook_url}: HTTP {resp.status_code}")
            return True
    except Exception as e:
        logger.error(f"Webhook delivery failed for partner {partner.partner_name}: {e}")
        return False
