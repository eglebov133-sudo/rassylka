"""Seed new monitor tests into DB."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(encoding="utf-8")

async def main():
    from backend.database import init_db
    from backend.services.monitor_engine import seed_tests, DEFAULT_TESTS
    
    await init_db()
    print(f"Seeding {len(DEFAULT_TESTS)} test definitions...")
    await seed_tests()
    
    # Verify
    from backend.database import async_session
    from backend.models import MonitorTest
    from sqlalchemy import select, func
    async with async_session() as db:
        count = (await db.execute(select(func.count(MonitorTest.id)))).scalar()
        print(f"Total tests in DB: {count}")
        
        # Show by group
        for group in ["public", "buyer", "seller"]:
            gc = (await db.execute(
                select(func.count(MonitorTest.id)).where(MonitorTest.group == group)
            )).scalar()
            print(f"  {group}: {gc}")

asyncio.run(main())
