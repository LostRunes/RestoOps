import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT tablename FROM pg_tables WHERE tablename IN ('ai_runs','ai_actions','audit_logs') ORDER BY tablename"
        ))
        tables = [row[0] for row in r.all()]
        print("Tables found:", tables)

asyncio.run(check())
