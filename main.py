from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import logging
import os
import json
from pydantic import BaseModel
from typing import List, Optional

from core.config import settings
from core.database import engine, Base, AsyncSessionLocal
from services.whatsapp_service import WhatsAppService
from services.sarvam_service import SarvamService
from services.gemini_service import GeminiService
from agents.entitlement_agent import EntitlementAgent
from agents.dispute_agent import DisputeAgent
from agents.quality_agent import QualityAgent
from agents.reconciliation_agent import ReconciliationAgent
from agents.compliance_agent import ComplianceAgent
from agents.form_agent import FormAgent
from services.pdf_service import PDFService

from models import Family, Case, CaseStatus

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GhostWriter AI",
    description="WhatsApp-first agentic system for post-death claims",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

whatsapp_service = WhatsAppService()
sarvam_service = SarvamService()
gemini_service = GeminiService()
pdf_service = PDFService()
entitlement_agent = EntitlementAgent(gemini_service, sarvam_service)
dispute_agent = DisputeAgent(gemini_service, sarvam_service)
quality_agent = QualityAgent(gemini_service)
reconciliation_agent = ReconciliationAgent(gemini_service, sarvam_service)
compliance_agent = ComplianceAgent(gemini_service)
form_agent = FormAgent(pdf_service)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

ONBOARDING_QUESTIONS = [
    {
        "field": "preferred_language",
        "text": "Namaste! Welcome to Haqdaar. What language do you prefer?\nReply 1 for Telugu\nReply 2 for Hindi\nReply 3 for English"
    },
    {
        "field": "breadwinner_name",
        "text": "I'm so sorry for your loss. What was the name of the person who passed away?"
    },
    {
        "field": "date_of_death",
        "text": "When did they pass away? (e.g. 15/08/2023)"
    },
    {
        "field": "employment_type",
        "text": "What kind of work did they do?\nReply 1 for Government job\nReply 2 for Private company\nReply 3 for Own business\nReply 4 for Daily wage work"
    },
    {
        "field": "had_epf",
        "text": "Did they have an EPF (Provident Fund) account through their employer?\nReply 1 for Yes\nReply 2 for Not sure\nReply 3 for No"
    },
    {
        "field": "state",
        "text": "Which state are you in?\nReply 1 for Telangana\nReply 2 for Andhra Pradesh\nReply 3 for Maharashtra\nReply 4 for Karnataka\nReply 5 for Other"
    },
    {
        "field": "death_certificate",
        "text": "To begin your claims, I need to verify your documents. Please upload a clear photo of the Death Certificate."
    }
]

async def get_or_create_case(phone: str, session: AsyncSession) -> Case:
    result = await session.execute(select(Family).where(Family.whatsapp_number == phone))
    family = result.scalars().first()
    if not family:
        family = Family(whatsapp_number=phone)
        session.add(family)
        await session.commit()
        await session.refresh(family)
    
    result = await session.execute(
        select(Case).where(Case.family_id == family.id).where(Case.status != CaseStatus.filed).order_by(Case.created_at.desc())
    )
    case = result.scalars().first()
    if not case:
        case = Case(family_id=family.id, status=CaseStatus.onboarding, onboarding_step=0, onboarding_data={})
        session.add(case)
        await session.commit()
        await session.refresh(case)
    return case

async def send_translated_message_and_voice(phone: str, text: str, case: Case):
    target_lang = case.onboarding_data.get("preferred_language", "English")
    translated_text = await sarvam_service.translate(text, "English", target_lang)
    await whatsapp_service.send_text(phone, translated_text)
    
    lang_code_map = {"Telugu": "te-IN", "Hindi": "hi-IN", "Tamil": "ta-IN", "Kannada": "kn-IN", "English": "en-IN"}
    voice_bytes = await sarvam_service.text_to_speech(translated_text, lang_code_map.get(target_lang, "en-IN"))
    if voice_bytes:
        import asyncio
        await asyncio.sleep(1) 
        await whatsapp_service.send_voice(phone, voice_bytes)

async def process_user_message(sender_phone: str, message_text: str, session: AsyncSession):
    msg_clean = message_text.lower().strip()
    case = await get_or_create_case(sender_phone, session)
    
    if "generate letter" in msg_clean or "download" in msg_clean or "file claim" in msg_clean:
        await send_translated_message_and_voice(sender_phone, "Generating your formal EPF Form 20... please wait.", case)
        result = await form_agent.generate_epf_form(case.onboarding_data)
        await whatsapp_service.send_document(sender_phone, result.pdf_bytes, "EPF_Form_20.pdf")
        case.status = CaseStatus.filed
        await session.commit()
        return

    if msg_clean.startswith("reconcile:") or ("aadhaar name" in msg_clean and "death certificate name" in msg_clean):
        try:
            if msg_clean.startswith("reconcile:"):
                parts = msg_clean.split(":")
                names = parts[1].split("vs")
                name1, name2 = names[0].strip(), names[1].strip()
            else:
                import re
                name1_match = re.search(r"aadhaar name (?:is )?([^ and\.]+)", msg_clean)
                name2_match = re.search(r"death certificate name (?:is )?([^ and\.]+)", msg_clean)
                name1 = name1_match.group(1) if name1_match else "Name A"
                name2 = name2_match.group(1) if name2_match else "Name B"
            
            await send_translated_message_and_voice(sender_phone, f"Analyzing identities for {name1} and {name2}...", case)
            response = await reconciliation_agent.analyze_identities(name1, name2, target_lang=case.onboarding_data.get("preferred_language", "English"))
            if response.has_mismatch:
                await send_translated_message_and_voice(sender_phone, f"Mismatch: {response.mismatch_description}. Sending affidavit...", case)
                await whatsapp_service.send_text(sender_phone, response.affidavit_text[:4000])
                case.onboarding_data["identity_mismatch"] = True
            else:
                await send_translated_message_and_voice(sender_phone, "Success! The names match correctly.", case)
            case.onboarding_data["name_reconciliation"] = response.dict()
            await session.commit()
        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
        return

    step_idx = case.onboarding_step
    if step_idx >= len(ONBOARDING_QUESTIONS):
        await send_translated_message_and_voice(sender_phone, "Processing your claims...", case)
        return

    field = ONBOARDING_QUESTIONS[step_idx]["field"]
    if field == "preferred_language":
        lang_map = {"1": "Telugu", "2": "Hindi", "3": "English"}
        case.onboarding_data[field] = lang_map.get(msg_clean, "English")
    elif field == "employment_type":
        emp_map = {"1": "Government", "2": "Private", "3": "Business", "4": "Daily Wage"}
        case.onboarding_data[field] = emp_map.get(msg_clean, msg_clean)
    elif field == "had_epf":
        epf_map = {"1": "Yes", "2": "Not sure", "3": "No"}
        case.onboarding_data[field] = epf_map.get(msg_clean, msg_clean)
    elif field == "state":
        state_map = {"1": "Telangana", "2": "Andhra Pradesh", "3": "Maharashtra", "4": "Karnataka", "5": "Other"}
        case.onboarding_data[field] = state_map.get(msg_clean, msg_clean)
    else:
        case.onboarding_data[field] = msg_clean

    case.onboarding_step += 1
    next_step = case.onboarding_step

    if field == "state":
        audit = await compliance_agent.audit_family_data(case.onboarding_data)
        case.onboarding_data["compliance_grade"] = audit.compliance_grade
        await send_translated_message_and_voice(sender_phone, audit.message, case)
        case.status = CaseStatus.ready_to_submit if audit.is_ready_to_file else CaseStatus.audit_failed
        
        report = await entitlement_agent.discover_entitlements(case.onboarding_data)
        case.entitlement_total = report.total_entitlement
        scheme_details = "".join([f"{idx+1}. {s.name}: ₹{s.amount:,.0f}\n" for idx, s in enumerate(report.schemes)])
        msg = f"Entitled to ₹{report.total_entitlement:,.0f} across {len(report.schemes)} schemes.\n\n{scheme_details}"
        await send_translated_message_and_voice(sender_phone, msg, case)

        # Task 4: Deadline dependencies message
        deadline_msg = "EPF Form 20 must be filed before bank nominee transfer. EPF deadline: 30 days. File EPF this week to stay on track."
        await send_translated_message_and_voice(sender_phone, deadline_msg, case)

        # Task 1: Auto-generate PDF if 100/100
        if audit.compliance_grade == 100:
            await send_translated_message_and_voice(sender_phone, "Score is 100/100! Automatically sending your EPF Form 20...", case)
            template_path = "data/form_templates/epf_form_20_official.pdf"
            if os.path.exists(template_path):
                with open(template_path, "rb") as f:
                    pdf_bytes = f.read()
                
                caption_text = "Your EPF Form 20 is ready. Please fill in your personal details, get it signed, and submit at your nearest EPFO office or MeeSeva centre."
                target_lang = case.onboarding_data.get("preferred_language", "English")
                translated_caption = await sarvam_service.translate(caption_text, "English", target_lang)
                
                await whatsapp_service.send_document(
                    sender_phone, 
                    pdf_bytes, 
                    "EPF_Form_20.pdf", 
                    caption=translated_caption
                )
                case.status = CaseStatus.filed
            else:
                logger.error(f"Official template not found at {template_path}")

    if next_step < len(ONBOARDING_QUESTIONS):
        await send_translated_message_and_voice(sender_phone, ONBOARDING_QUESTIONS[next_step]["text"], case)
    else:
        if case.status == CaseStatus.onboarding: case.status = CaseStatus.verification_pending
        await send_translated_message_and_voice(sender_phone, "Onboarding complete.", case)
    await session.commit()

@app.post("/webhook/whatsapp")
async def handle_whatsapp_webhook(request: Request):
    payload = await request.json()
    async with AsyncSession(engine) as session:
        try:
            if payload.get("object") == "whatsapp_business_account":
                for entry in payload.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        if "messages" in value:
                            for message in value["messages"]:
                                sender_phone = message.get("from")
                                msg_type = message.get("type")
                                if msg_type == "text":
                                    await process_user_message(sender_phone, message.get("text", {}).get("body", ""), session)
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            await session.rollback()
    return {"status": "received"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Case).options(selectinload(Case.family)).join(Family).order_by(Case.created_at.desc())
        )
        cases = result.scalars().all()
        case_list = []
        for c in cases:
            case_list.append({
                "phone": c.family.whatsapp_number,
                "state": c.onboarding_data.get("state", "N/A"),
                "compliance_score": c.onboarding_data.get("compliance_grade", 0),
                "total_entitlement": float(c.entitlement_total),
                "status": c.status.value
            })
        return templates.TemplateResponse("dashboard.html", {"request": request, "cases": case_list})

@app.get("/api/cases/{phone}")
async def get_case_detail(phone: str):
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Case).options(selectinload(Case.family)).join(Family).where(Family.whatsapp_number == phone)
        )
        case = result.scalars().first()
        if not case: return JSONResponse(status_code=404, content={"error": "Not found"})
        return {
            "status": case.status,
            "compliance_grade": case.onboarding_data.get("compliance_grade", 0),
            "family_data": case.onboarding_data,
            "entitlement_total": float(case.entitlement_total),
            "onboarding_step": case.onboarding_step
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
