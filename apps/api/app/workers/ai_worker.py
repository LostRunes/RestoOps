"""
Celery worker for AI conversation processing.
Triggered after a new inbound message is received.
"""
import asyncio
from celery.utils.log import get_task_logger
from app.db.session import AsyncSessionLocal
from app.jobs.celery_app import celery_app

logger = get_task_logger(__name__)


async def _async_analyze_conversation(conversation_id: str, org_id: str):
    from app.services.ai_service import AIService
    async with AsyncSessionLocal() as db:
        service = AIService(db)
        return await service.analyze_conversation(conversation_id, org_id)


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.workers.ai_worker.process_conversation_ai",
    default_retry_delay=30,
)
def process_conversation_ai(self, conversation_id: str, org_id: str):
    """
    Analyze a conversation with the AI agent after an inbound message arrives.

    Retry strategy:
    - ConnectionError (Ollama not running): retry after 30s
    - TimeoutError: retry after 60s
    - Any other error: log and store without retry
    """
    try:
        result = asyncio.run(_async_analyze_conversation(conversation_id, org_id))
        logger.info(
            f"AI analysis complete for conversation {conversation_id}: "
            f"{result.get('actions_proposed', 0)} actions proposed"
        )
        return result
    except ConnectionError as exc:
        logger.warning(f"Ollama not reachable, retrying in 30s: {exc}")
        raise self.retry(exc=exc, countdown=30)
    except TimeoutError as exc:
        logger.warning(f"Ollama timed out, retrying in 60s: {exc}")
        raise self.retry(exc=exc, countdown=60)
    except Exception as exc:
        logger.error(f"AI worker failed for conversation {conversation_id}: {exc}")
        # Don't retry on unknown errors — log and move on
        return {"status": "FAILED", "error": str(exc)}
