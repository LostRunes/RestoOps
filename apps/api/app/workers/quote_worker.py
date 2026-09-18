import asyncio
from app.db.session import AsyncSessionLocal
from app.jobs.celery_app import celery_app
from app.services.quote_service import QuoteService


async def _async_check_quote_expirations():
    async with AsyncSessionLocal() as db:
        service = QuoteService(db)
        expired = await service.check_expirations()
        await db.commit()
        return len(expired)


@celery_app.task(name="app.workers.quote_worker.check_quote_expirations")
def check_quote_expirations():
    return asyncio.run(_async_check_quote_expirations())
