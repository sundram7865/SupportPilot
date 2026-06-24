from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "supportpilot_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.worker.tasks.health",
        "app.worker.tasks.sla",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    beat_schedule={
        "check-ticket-sla-every-minute": {
            "task": "tickets.check_sla",
            "schedule": 60.0,
        },
    },
)