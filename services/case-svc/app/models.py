from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.DB_NAME]

cases = db.get_collection("cases")
notes = db.get_collection("case_notes")
actions = db.get_collection("case_actions")

async def ensure_indexes():
    await cases.create_index("event_id", unique=True)
    await cases.create_index([("status", 1), ("updated_at", -1)])
