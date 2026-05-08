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
import asyncio
from pydantic import BaseModel
from typing import List, Optional

from sqlalchemy.orm.attributes import flag_modified

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
from agents.support_agent import SupportAgent
from services.pdf_service import PDFService
from services.esign_service import ESignService

from models import Family, Case, CaseStatus
from api.v1.b2b import router as b2b_router

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

app.include_router(b2b_router)

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
support_agent = SupportAgent(gemini_service)
esign_service = ESignService()

_processed_wamids: set[str] = set()

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
        "field": "claimant_name",
        "text": "What is your full name? (You — the person making this claim)"
    },
    {
        "field": "relationship",
        "text": "What is your relationship to the deceased?\nReply 1 for Wife / Husband\nReply 2 for Son / Daughter\nReply 3 for Mother / Father\nReply 4 for Other"
    },
    {
        "field": "claimant_dob",
        "text": "What is your date of birth? (e.g. 01/01/1985)"
    },
    {
        "field": "claimant_address",
        "text": "What is your full address including PIN code? (e.g. H.No 5-10, Ameerpet, Hyderabad 500016)"
    },
    {
        "field": "pf_account_no",
        "text": "Do you know the EPF/UAN account number of the deceased?\nType the number, or reply 'skip' if not sure"
    },
    {
        "field": "bank_account",
        "text": "What is your bank account number? (where you want to receive the claim amount)"
    },
    {
        "field": "bank_ifsc",
        "text": "What is your bank IFSC code? (e.g. SBIN0001234)"
    },
    {
        "field": "death_certificate",
        "text": "Almost done! Please upload a clear photo of the Death Certificate."
    },
    {
        "field": "state",
        "text": "Which state are you in?\nReply 1 for Telangana\nReply 2 for Andhra Pradesh\nReply 3 for Maharashtra\nReply 4 for Karnataka\nReply 5 for Other"
    },
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

def _detect_script_language(text: str) -> str:
    """Detect language from Unicode script ranges in the transcript — reliable regardless of STT language_code."""
    for ch in text:
        cp = ord(ch)
        if 0x0C00 <= cp <= 0x0C7F:
            return "Telugu"
        if 0x0900 <= cp <= 0x097F:
            return "Hindi"
        if 0x0B80 <= cp <= 0x0BFF:
            return "Tamil"
        if 0x0C80 <= cp <= 0x0CFF:
            return "Kannada"
    return "English"

_CHOICE_FIELD_OPTIONS = {
    "preferred_language": {"Telugu": "Telugu", "తెలుగు": "Telugu", "hindi": "Hindi", "हिंदी": "Hindi", "english": "English"},
    "employment_type": {
        "government": "Government", "govt": "Government", "ప్రభుత్వం": "Government", "सरकारी": "Government",
        "private": "Private", "ప్రైవేట్": "Private", "प्राइवेट": "Private",
        "business": "Business", "own": "Business", "వ్యాపారం": "Business", "व्यापार": "Business",
        "daily": "Daily Wage", "wage": "Daily Wage", "రోజువారీ": "Daily Wage", "दिहाड़ी": "Daily Wage",
    },
    "had_epf": {
        "yes": "Yes", "అవును": "Yes", "हां": "Yes", "ha": "Yes", "haan": "Yes",
        "no": "No", "లేదు": "No", "नहीं": "No",
        "not sure": "Not sure", "don't know": "Not sure", "తెలియదు": "Not sure", "पता नहीं": "Not sure",
    },
    "relationship": {
        "wife": "Wife/Husband", "husband": "Wife/Husband", "భర్త": "Wife/Husband", "భార్య": "Wife/Husband", "पति": "Wife/Husband", "पत्नी": "Wife/Husband",
        "son": "Son/Daughter", "daughter": "Son/Daughter", "కొడుకు": "Son/Daughter", "కూతురు": "Son/Daughter", "बेटा": "Son/Daughter", "बेटी": "Son/Daughter",
        "mother": "Mother/Father", "father": "Mother/Father", "అమ్మ": "Mother/Father", "నాన్న": "Mother/Father", "माँ": "Mother/Father", "पिता": "Mother/Father",
    },
    "state": {
        "telangana": "Telangana", "తెలంగాణ": "Telangana",
        "andhra": "Andhra Pradesh", "ఆంధ్ర": "Andhra Pradesh",
        "maharashtra": "Maharashtra", "karnataka": "Karnataka",
    },
}

_CHOICE_FIELD_NUM_MAP = {
    "preferred_language": {"1": "Telugu", "2": "Hindi", "3": "English"},
    "employment_type": {"1": "Government", "2": "Private", "3": "Business", "4": "Daily Wage"},
    "had_epf": {"1": "Yes", "2": "Not sure", "3": "No"},
    "relationship": {"1": "Wife/Husband", "2": "Son/Daughter", "3": "Mother/Father", "4": "Other"},
    "state": {"1": "Telangana", "2": "Andhra Pradesh", "3": "Maharashtra", "4": "Karnataka", "5": "Other"},
}

async def _resolve_choice_field(field: str, raw_input: str) -> str:
    """Resolve a natural-language or numbered answer to a canonical field value."""
    num_map = _CHOICE_FIELD_NUM_MAP.get(field, {})
    clean = raw_input.strip().lower()
    if clean in num_map:
        return num_map[clean]
    keyword_map = _CHOICE_FIELD_OPTIONS.get(field, {})
    for kw, val in keyword_map.items():
        if kw in clean:
            return val
    # Language selection must be explicit — no Gemini fallback (avoids "hi" → "Hindi")
    if field == "preferred_language":
        return ""  # empty → caller will re-ask the question
    # Gemini fallback for other choice fields with natural-language speech
    options_str = " | ".join(num_map.values()) if num_map else field
    prompt = (
        f"The user was asked to choose for field '{field}'. Options: {options_str}.\n"
        f"User said: \"{raw_input}\"\n"
        f"Reply with ONLY the matching option name from the list, nothing else. "
        f"If unclear, reply with the closest match."
    )
    try:
        result = await gemini_service.model.generate_content_async(prompt)
        answer = result.text.strip().strip('"').strip("'")
        for val in num_map.values():
            if val.lower() in answer.lower() or answer.lower() in val.lower():
                return val
        return answer or raw_input
    except Exception:
        return raw_input

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

_GREETINGS = {"hi", "hello", "hey", "namaste", "నమస్కారం", "నమస్కార్", "నమస్తే", "नमस्ते", "నమస్కారం", "start", "begin", "ok", "okay", "hii", "helo"}

async def process_user_message(sender_phone: str, message_text: str, session: AsyncSession):
    msg_clean = message_text.lower().strip()
    case = await get_or_create_case(sender_phone, session)

    # If language not yet chosen and user sent a greeting, just (re)ask the language question
    if case.onboarding_step == 0 and msg_clean in _GREETINGS:
        lang_q = ONBOARDING_QUESTIONS[0]["text"]
        await whatsapp_service.send_text(sender_phone, lang_q)
        return

    # SupportAgent — runs first, before any claims logic
    support_result = await support_agent.assess_message(
        message_text,
        preferred_language=case.onboarding_data.get("preferred_language", "English")
    )
    if support_result.is_grief_message:
        support_msg = support_agent.build_whatsapp_message(support_result)
        await whatsapp_service.send_text(sender_phone, support_msg)
        if support_result.intercept:
            return  # Pause claims flow for this turn; resume on next message

    STATUS_TRIGGERS = {"status", "where is my claim", "my claim", "claim status", "update", "what happened", "kya hua", "claim"}
    if any(t in msg_clean for t in STATUS_TRIGGERS):
        data = case.onboarding_data
        name = data.get("breadwinner_name", "your family member")
        step = case.onboarding_step
        total = len(ONBOARDING_QUESTIONS)
        lines = [f"Claim status for {name.title()}"]
        lines.append("─" * 30)
        if case.status.value == "filed":
            lines.append("Form Status : Filed")
            if data.get("form5if_path"):
                lines.append("Form 5(IF)  : Generated")
            esign_status = data.get("esign_status", "")
            if esign_status == "signed":
                lines.append(f"eSign       : Signed (ID: {data.get('esign_transaction_id','')})")
            elif esign_status == "pending":
                url = f"{settings.APP_BASE_URL}/esign/{data.get('esign_token','')}"
                lines.append(f"eSign       : Pending — sign here:\n{url}")
        elif case.status.value == "onboarding":
            lines.append(f"Progress    : {step}/{total} steps complete")
            if step < total:
                lines.append(f"Next step   : {ONBOARDING_QUESTIONS[step]['text'].split(chr(10))[0]}")
        elif case.status.value == "audit_failed":
            lines.append("Status      : Documents need review")
        if case.entitlement_total and float(case.entitlement_total) > 0:
            lines.append(f"Entitlement : ₹{float(case.entitlement_total):,.0f}")
        await send_translated_message_and_voice(sender_phone, "\n".join(lines), case)
        return

    if "generate letter" in msg_clean or "download" in msg_clean or "file claim" in msg_clean:
        await send_translated_message_and_voice(sender_phone, "Generating your formal EPF Form 20... please wait.", case)
        result = await form_agent.generate_epf_form(case.onboarding_data)
        case.onboarding_data["esign_transaction_id"] = result.esign_transaction_id
        caption = f"EPF Form 20 ready. eSign ID: {result.esign_transaction_id}"
        await whatsapp_service.send_document(sender_phone, result.pdf_bytes, "EPF_Form_20.pdf", caption=caption)
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
    CHOICE_FIELDS = {"preferred_language", "employment_type", "had_epf", "relationship", "state"}
    if field in CHOICE_FIELDS:
        resolved = await _resolve_choice_field(field, message_text)
        if not resolved and field == "preferred_language":
            # Unrecognised input — re-ask language question without advancing
            await whatsapp_service.send_text(sender_phone, ONBOARDING_QUESTIONS[0]["text"])
            return
        case.onboarding_data[field] = resolved
    elif field == "bank_ifsc":
        case.onboarding_data[field] = message_text.strip().upper()
    elif field == "pf_account_no":
        case.onboarding_data[field] = "" if msg_clean in ("skip", "తెలియదు", "पता नहीं", "don't know") else message_text.strip()
    elif field == "death_certificate":
        # For document uploads, msg_clean will be a local file path saved by the webhook handler.
        # Run quality pre-flight before accepting the step.
        if os.path.exists(msg_clean):
            quality_result = await quality_agent.assess_document(msg_clean, expected_doc_type="death_certificate")
            case.onboarding_data["death_certificate_quality_score"] = quality_result.quality_score
            case.onboarding_data["death_certificate_issues"] = quality_result.issues
            case.onboarding_data["death_certificate_type_match"] = not quality_result.type_mismatch
            if not quality_result.is_valid:
                feedback = quality_agent.build_whatsapp_feedback(quality_result)
                await send_translated_message_and_voice(sender_phone, feedback, case)
                flag_modified(case, "onboarding_data")
                await session.commit()
                return  # Hold at this step until a valid upload is received
            case.onboarding_data[field] = msg_clean
        else:
            case.onboarding_data[field] = msg_clean
    else:
        case.onboarding_data[field] = msg_clean

    flag_modified(case, "onboarding_data")
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

        if audit.compliance_grade == 100:
            await send_translated_message_and_voice(
                sender_phone,
                "Score is 100/100! Filling in the official Form 5(IF) with your details now...",
                case
            )
            try:
                # Use the official Form5IF template overlay
                case_id_str = str(case.id)
                form5if = await form_agent.generate_form5if(
                    case.onboarding_data,
                    case_id=case_id_str,
                    save_to_disk=True,
                    storage_path=settings.STORAGE_PATH,
                )
                case.onboarding_data["form5if_path"] = form5if.file_path

                caption_text = (
                    "Your official EPFO Form 5(IF) is pre-filled with your details. "
                    "Print it, sign it, and submit at your nearest EPFO office or MeeSeva centre."
                )
                target_lang = case.onboarding_data.get("preferred_language", "English")
                translated_caption = await sarvam_service.translate(caption_text, "English", target_lang)

                await whatsapp_service.send_document(
                    sender_phone,
                    form5if.pdf_bytes,
                    f"filled_Form5IF_{case_id_str[:8]}.pdf",
                    caption=translated_caption,
                )
                case.status = CaseStatus.filed
                logger.info(f"Form5IF sent to {sender_phone}, saved at {form5if.file_path}")

                # Create eSign request and send signing link
                esign_req = esign_service.create_request(
                    str(case.id), settings.SECRET_KEY, settings.APP_BASE_URL
                )
                case.onboarding_data["esign_token"] = esign_req["token"]
                case.onboarding_data["esign_transaction_id"] = esign_req["transaction_id"]
                case.onboarding_data["esign_status"] = "pending"
                sign_msg = (
                    f"To make this form legally valid, please sign it using Aadhaar eSign:\n\n"
                    f"{esign_req['signing_url']}\n\n"
                    f"Tap the link, enter your Aadhaar OTP, and your signed form will be sent back here."
                )
                await whatsapp_service.send_text(sender_phone, sign_msg)
            except Exception as e:
                logger.error(f"Form5IF overlay failed, falling back to generated form: {e}")
                generated = await form_agent.generate_epf_form(case.onboarding_data)
                case.onboarding_data["esign_transaction_id"] = generated.esign_transaction_id
                caption_text = (
                    f"Your EPF Form 20 is ready (eSign ID: {generated.esign_transaction_id}). "
                    "Please sign it and submit at your nearest EPFO office."
                )
                target_lang = case.onboarding_data.get("preferred_language", "English")
                translated_caption = await sarvam_service.translate(caption_text, "English", target_lang)
                await whatsapp_service.send_document(
                    sender_phone, generated.pdf_bytes, "EPF_Form_20.pdf", caption=translated_caption
                )
                case.status = CaseStatus.filed
        flag_modified(case, "onboarding_data")
        await session.commit()
        return

    if next_step < len(ONBOARDING_QUESTIONS):
        await send_translated_message_and_voice(sender_phone, ONBOARDING_QUESTIONS[next_step]["text"], case)
    else:
        if case.status == CaseStatus.onboarding: case.status = CaseStatus.verification_pending
        await send_translated_message_and_voice(sender_phone, "Onboarding complete.", case)
    await session.commit()

ESIGN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Haqdaar — Aadhaar eSign</title>
<style>
  body{{font-family:sans-serif;background:#f5f7fa;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
  .card{{background:#fff;border-radius:12px;padding:32px;max-width:420px;width:90%;box-shadow:0 4px 24px rgba(0,0,0,.08)}}
  h2{{color:#1a56db;margin-top:0}}
  .field{{margin:8px 0 16px}}
  label{{font-size:13px;color:#555;display:block;margin-bottom:4px}}
  input{{width:100%;padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:15px;box-sizing:border-box}}
  button{{width:100%;padding:12px;background:#1a56db;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;margin-top:8px}}
  button:hover{{background:#1447b3}}
  .info{{background:#eff6ff;border-left:4px solid #1a56db;padding:12px;border-radius:4px;font-size:13px;color:#1e40af;margin-bottom:20px}}
  .txn{{font-size:12px;color:#9ca3af;text-align:center;margin-top:16px}}
  {extra_style}
</style></head>
<body><div class="card">
  <h2>Aadhaar eSign</h2>
  <div class="info">You are signing your official EPFO Form 5(IF) for <strong>{name}</strong>. This makes the form legally valid for submission.</div>
  <form method="post">
    <div class="field"><label>Your Aadhaar-linked mobile OTP</label>
    <input name="otp" type="text" maxlength="6" placeholder="Enter 6-digit OTP" required autofocus></div>
    <button type="submit">Sign with Aadhaar eSign</button>
  </form>
  <div class="txn">Transaction ID: {txn_id}</div>
</div></body></html>"""

ESIGN_SUCCESS = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signed — Haqdaar</title>
<style>body{{font-family:sans-serif;background:#f5f7fa;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#fff;border-radius:12px;padding:32px;max-width:420px;width:90%;box-shadow:0 4px 24px rgba(0,0,0,.08);text-align:center}}
.check{{font-size:64px}} h2{{color:#059669}} p{{color:#374151;font-size:15px}}</style></head>
<body><div class="card"><div class="check">✅</div>
<h2>Document Signed!</h2>
<p>Your signed Form 5(IF) has been sent to your WhatsApp. Present it at your nearest EPFO office or MeeSeva centre.</p>
</div></body></html>"""

@app.get("/esign/{token}", response_class=HTMLResponse)
async def esign_page(token: str):
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Case).join(Family).where(
                Case.onboarding_data.op('->>')('esign_token') == token
            )
        )
        case = result.scalars().first()
        if not case:
            return HTMLResponse("<h3>Invalid or expired signing link.</h3>", status_code=404)
        name = case.onboarding_data.get("breadwinner_name", "Deceased")
        txn = case.onboarding_data.get("esign_transaction_id", "")
        html = ESIGN_PAGE.format(name=name.title(), txn_id=txn, extra_style="")
        return HTMLResponse(html)

@app.post("/esign/{token}", response_class=HTMLResponse)
async def esign_confirm(token: str, request: Request):
    form = await request.form()
    otp = form.get("otp", "").strip()
    if len(otp) != 6 or not otp.isdigit():
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(Case).join(Family).where(Case.onboarding_data.op('->>')('esign_token') == token)
            )
            case = result.scalars().first()
            name = case.onboarding_data.get("breadwinner_name", "Deceased") if case else ""
            txn = case.onboarding_data.get("esign_transaction_id", "") if case else ""
        html = ESIGN_PAGE.format(name=name.title(), txn_id=txn,
                                  extra_style=".error{color:#dc2626;font-size:13px;margin-top:8px}")
        return HTMLResponse(html.replace("</form>", '<p class="error">Please enter a valid 6-digit OTP.</p></form>'))

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Case).options(selectinload(Case.family)).join(Family).where(
                Case.onboarding_data.op('->>')('esign_token') == token
            )
        )
        case = result.scalars().first()
        if not case or case.onboarding_data.get("esign_status") == "signed":
            return HTMLResponse("<h3>This link has already been used or is invalid.</h3>", status_code=400)

        file_path = case.onboarding_data.get("form5if_path")
        if not file_path or not os.path.exists(file_path):
            return HTMLResponse("<h3>Form not found. Please contact support.</h3>", status_code=404)

        with open(file_path, "rb") as f:
            pdf_bytes = f.read()

        signer_name = case.onboarding_data.get("claimant_name") or case.onboarding_data.get("breadwinner_name", "Claimant")
        txn_id = case.onboarding_data.get("esign_transaction_id", "")
        signed_pdf = esign_service.apply_signature(pdf_bytes, signer_name, txn_id)

        signed_path = file_path.replace(".pdf", "_signed.pdf")
        with open(signed_path, "wb") as f:
            f.write(signed_pdf)

        case.onboarding_data["esign_status"] = "signed"
        case.onboarding_data["esign_signed_path"] = signed_path
        flag_modified(case, "onboarding_data")
        await session.commit()

        phone = case.family.whatsapp_number
        caption = (
            "Your Form 5(IF) has been digitally signed via Aadhaar eSign. "
            f"Transaction ID: {txn_id}. "
            "Present this at your nearest EPFO office or MeeSeva centre."
        )
        target_lang = case.onboarding_data.get("preferred_language", "English")
        translated_caption = await sarvam_service.translate(caption, "English", target_lang)
        await whatsapp_service.send_document(phone, signed_pdf, f"SIGNED_Form5IF_{str(case.id)[:8]}.pdf", caption=translated_caption)
        logger.info(f"Signed Form5IF delivered to {phone}, txn {txn_id}")

    return HTMLResponse(ESIGN_SUCCESS)

@app.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return int(challenge)
    logger.warning(f"Webhook verification failed: mode={mode}, token_match={token == settings.WHATSAPP_VERIFY_TOKEN}")
    return JSONResponse(status_code=403, content={"error": "Forbidden"})

async def _handle_payload(payload: dict):
    async with AsyncSession(engine) as session:
        try:
            if payload.get("object") == "whatsapp_business_account":
                for entry in payload.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        if "messages" in value:
                            for message in value["messages"]:
                                wamid = message.get("id", "")
                                if wamid and wamid in _processed_wamids:
                                    logger.info(f"Skipping duplicate WAMID {wamid}")
                                    continue
                                if wamid:
                                    _processed_wamids.add(wamid)
                                    if len(_processed_wamids) > 10000:
                                        _processed_wamids.clear()
                                sender_phone = message.get("from")
                                msg_type = message.get("type")
                                if msg_type == "text":
                                    await process_user_message(sender_phone, message.get("text", {}).get("body", ""), session)
                                elif msg_type in ("image", "document"):
                                    media_id = message.get(msg_type, {}).get("id")
                                    if media_id:
                                        media_bytes = await whatsapp_service.download_media(media_id)
                                        ext = "jpg" if msg_type == "image" else "pdf"
                                        local_path = f"/tmp/wa_upload_{sender_phone}_{media_id}.{ext}"
                                        with open(local_path, "wb") as f:
                                            f.write(media_bytes)
                                        await process_user_message(sender_phone, local_path, session)
                                elif msg_type == "audio":
                                    media_id = message.get("audio", {}).get("id")
                                    if media_id:
                                        import io
                                        from pydub import AudioSegment
                                        audio_bytes = await whatsapp_service.download_media(media_id)
                                        try:
                                            ogg_audio = AudioSegment.from_ogg(io.BytesIO(audio_bytes))
                                            wav_io = io.BytesIO()
                                            ogg_audio.export(wav_io, format="wav")
                                            wav_bytes = wav_io.getvalue()
                                        except Exception as conv_err:
                                            logger.error(f"Voice conversion error: {conv_err}")
                                            await whatsapp_service.send_text(sender_phone, "Sorry, I couldn't process the voice message. Please type your response.")
                                            continue
                                        case_for_lang = await get_or_create_case(sender_phone, session)
                                        lang_name_to_code = {"Telugu": "te-IN", "Hindi": "hi-IN", "Tamil": "ta-IN", "Kannada": "kn-IN", "English": "en-IN"}
                                        current_lang = case_for_lang.onboarding_data.get("preferred_language", "")
                                        # Default hint to te-IN (primary user base); override if language already set
                                        lang_hint = lang_name_to_code.get(current_lang, "te-IN")
                                        transcript, _ = await sarvam_service.transcribe_voice(wav_bytes, lang_hint)
                                        if not transcript.strip():
                                            await whatsapp_service.send_text(sender_phone, "Sorry, I couldn't understand. Please type your answer or try speaking again clearly.")
                                            continue
                                        logger.info(f"STT transcript [{lang_hint}]: {transcript}")
                                        # Detect language reliably from Unicode script of transcript
                                        if not current_lang:
                                            detected_lang = _detect_script_language(transcript)
                                            case_for_lang.onboarding_data["preferred_language"] = detected_lang
                                            flag_modified(case_for_lang, "onboarding_data")
                                            if case_for_lang.onboarding_step == 0:
                                                # Skip the language-selection question — we already know the language.
                                                # Ask the first real question in the detected language instead of
                                                # mis-processing this voice message as a field answer.
                                                case_for_lang.onboarding_step = 1
                                                await session.commit()
                                                await session.refresh(case_for_lang)
                                                logger.info(f"Script-detected language: {detected_lang}")
                                                next_q = ONBOARDING_QUESTIONS[1]["text"]
                                                await send_translated_message_and_voice(sender_phone, next_q, case_for_lang)
                                                continue
                                            await session.commit()
                                            await session.refresh(case_for_lang)
                                            logger.info(f"Script-detected language mid-flow: {detected_lang}")
                                        await process_user_message(sender_phone, transcript.strip(), session)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            await session.rollback()

@app.post("/webhook/whatsapp")
async def handle_whatsapp_webhook(request: Request):
    payload = await request.json()
    asyncio.create_task(_handle_payload(payload))
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
