import asyncio
from app.db.session import AsyncSessionLocal
from app.jobs.celery_app import celery_app
from app.services.email_ingestion import EmailIngestionService


async def _async_ingest_emails():
    async with AsyncSessionLocal() as db:
        service = EmailIngestionService(db)
        return await service.ingest_new_messages()


@celery_app.task(name="app.workers.email_ingestion_worker.ingest_emails")
def ingest_emails():
    return asyncio.run(_async_ingest_emails())
