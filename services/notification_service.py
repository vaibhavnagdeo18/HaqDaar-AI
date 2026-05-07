import asyncio
import logging
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

async def run_daily_deadline_check():
    logger.info("Starting daily deadline check...")
    async with AsyncSessionLocal() as db:
        # Query cases that are filed or ready to submit
        result = await db.execute(
            select(Case)
            .options(selectinload(Case.family))
            .where(Case.status.in_([CaseStatus.filed, CaseStatus.ready_to_submit]))
        )
        cases = result.scalars().all()
        
        for case in cases:
            # For demo purposes, we check a mock 'days_remaining' from onboarding_data
            # In a real app, this would be calculated from Claim objects and their schemes
            days_remaining = case.onboarding_data.get("days_to_deadline", 7) # Default to 7 for demo
            
            phone = case.family.whatsapp_number
            lang = case.onboarding_data.get("preferred_language", "English")
            
            message = None
            if days_remaining == 7:
                message = "Reminder: You have 7 days left to complete your claim for ₹13,74,192. Please ensure all documents are ready."
            elif days_remaining == 3:
                message = "URGENT: Only 3 days left for your EPF claim! Please reply 'FILE NOW' to submit immediately."
            elif days_remaining == 1:
                message = "CRITICAL: Last 24 hours to file your claim. Failure to file today may result in loss of benefits."
            
            if message:
                try:
                    translated = await sarvam_service.translate(message, "English", lang)
                    await whatsapp_service.send_text(phone, translated)
                    logger.info(f"Sent deadline alert to {phone} ({days_remaining} days)")
                except Exception as e:
                    logger.error(f"Failed to send alert to {phone}: {e}")

@shared_task(name="services.notification_service.daily_deadline_check")
def daily_deadline_check():
    asyncio.run(run_daily_deadline_check())

@shared_task(name="services.notification_service.weekly_case_summary")
def weekly_case_summary():
    # Placeholder for weekly summary task
    pass

@shared_task(name="services.notification_service.stale_case_followup")
def stale_case_followup():
    # Placeholder for stale case follow-up
    pass
