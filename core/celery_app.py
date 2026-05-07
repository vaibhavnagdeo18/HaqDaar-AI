from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "ghostwriter",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['services.notification_service']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=False, # Use local timezone
)

# Beat schedule
celery_app.conf.beat_schedule = {
    'daily-deadline-check-9am': {
        'task': 'services.notification_service.daily_deadline_check',
        'schedule': crontab(hour=9, minute=0), # Every day at 9 AM IST
    },
    'weekly-case-summary': {
        'task': 'services.notification_service.weekly_case_summary',
        'schedule': crontab(day_of_week=0, hour=10, minute=0), # Mondays at 10 AM
    },
    'stale-case-followup': {
        'task': 'services.notification_service.stale_case_followup',
        'schedule': crontab(hour='*/12', minute=0), # Every 12 hours
    }
}
