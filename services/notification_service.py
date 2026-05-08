import asyncio
import logging
from datetime import datetime, timezone, timedelta
from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from core.database import AsyncSessionLocal
from models import Case, CaseStatus, Family
from services.whatsapp_service import WhatsAppService
from services.sarvam_service import SarvamService

logger = logging.getLogger(__name__)
whatsapp_service = WhatsAppService()
sarvam_service = SarvamService()

# WhatsApp only allows free-form messages within 24 hours of the last user message.
# Outside that window, messages MUST be sent as pre-approved Message Templates via
# send_template(). Register templates in Meta Business Manager before enabling proactive alerts.
# Template name to register: "haqdaar_deadline_reminder" with params {{1}}=days, {{2}}=amount
_SESSION_WINDOW_HOURS = 23  # send free-form only if user messaged within this window


def _within_session_window(case: Case) -> bool:
    last_active = case.family.last_active
    if not last_active:
        return False
    if last_active.tzinfo is None:
        last_active = last_active.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_active) < timedelta(hours=_SESSION_WINDOW_HOURS)


async def run_daily_deadline_check():
    logger.info("Starting daily deadline check...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Case)
            .options(selectinload(Case.family))
            .where(Case.status.in_([CaseStatus.filed, CaseStatus.ready_to_submit]))
        )
        cases = result.scalars().all()

        for case in cases:
            days_remaining = case.onboarding_data.get("days_to_deadline", 7)
            phone = case.family.whatsapp_number
            lang = case.onboarding_data.get("preferred_language", "English")
            entitlement = float(case.entitlement_total or 0)
            amount_str = f"Rs. {entitlement:,.0f}" if entitlement > 0 else "your EPF benefits"

            if days_remaining == 7:
                message = f"Reminder: You have 7 days left to complete your claim for {amount_str}. Please ensure all documents are ready."
            elif days_remaining == 3:
                message = f"Urgent: Only 3 days left for your EPF claim of {amount_str}. Please complete your filing as soon as possible."
            elif days_remaining == 1:
                message = f"Critical: Last 24 hours to file your claim for {amount_str}. Failure to file today may result in loss of benefits."
            else:
                continue

            try:
                if _within_session_window(case):
                    translated = await sarvam_service.translate(message, "English", lang)
                    await whatsapp_service.send_text(phone, translated)
                    logger.info(f"Sent deadline alert to {phone} ({days_remaining} days, {amount_str})")
                else:
                    # Outside 24-hour window — must use a pre-approved template.
                    # Uncomment once "haqdaar_deadline_reminder" is approved in Meta Business Manager:
                    # lang_code = {"Telugu": "te", "Hindi": "hi"}.get(lang, "en")
                    # await whatsapp_service.send_template(phone, "haqdaar_deadline_reminder", lang_code,
                    #     components=[{"type":"body","parameters":[
                    #         {"type":"text","text":str(days_remaining)},
                    #         {"type":"text","text":amount_str}
                    #     ]}])
                    logger.info(f"Skipped alert to {phone} — outside 24h session window. Needs approved template.")
            except Exception as e:
                logger.error(f"Failed to send alert to {phone}: {e}")


async def run_stale_case_followup():
    """Nudge users who started onboarding but haven't completed it in 48 hours."""
    logger.info("Starting stale case followup...")
    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        result = await db.execute(
            select(Case)
            .options(selectinload(Case.family))
            .where(Case.status == CaseStatus.onboarding)
            .where(Case.created_at < cutoff)
        )
        cases = result.scalars().all()

        for case in cases:
            if not _within_session_window(case):
                logger.info(f"Skipping stale nudge for {case.family.whatsapp_number} — outside session window.")
                continue
            phone = case.family.whatsapp_number
            lang = case.onboarding_data.get("preferred_language", "English")
            step = case.onboarding_step
            total = 14
            name = case.onboarding_data.get("breadwinner_name", "your family member")
            message = (
                f"You have completed {step} out of {total} steps for the claim of {name}. "
                "Reply here to continue — we will guide you through the remaining steps."
            )
            try:
                translated = await sarvam_service.translate(message, "English", lang)
                await whatsapp_service.send_text(phone, translated)
                logger.info(f"Sent stale nudge to {phone} (step {step}/{total})")
            except Exception as e:
                logger.error(f"Failed to send stale nudge to {phone}: {e}")


@shared_task(name="services.notification_service.daily_deadline_check")
def daily_deadline_check():
    asyncio.run(run_daily_deadline_check())


@shared_task(name="services.notification_service.weekly_case_summary")
def weekly_case_summary():
    pass


@shared_task(name="services.notification_service.stale_case_followup")
def stale_case_followup():
    asyncio.run(run_stale_case_followup())
