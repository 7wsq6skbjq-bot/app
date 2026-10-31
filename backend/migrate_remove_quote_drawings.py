"""One-time migration: remove the Adams Rite `drawing_pages` field from all
quotes. The drawings-on-quotes feature has been retired.
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).resolve().parent / ".env")


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    res = await db.erp_quotes.update_many({}, {"$unset": {"drawing_pages": ""}})
    print(f"drawing_pages retiré de {res.modified_count} soumission(s)")


if __name__ == "__main__":
    asyncio.run(main())
