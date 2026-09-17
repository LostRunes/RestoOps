from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "restoops_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
)


@celery_app.task(name="app.jobs.celery_app.health_check_task")
def health_check_task():
    return {"status": "ok", "message": "Celery worker is operational"}
