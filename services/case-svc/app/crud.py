from datetime import datetime
from bson import ObjectId
from .models import cases, notes, actions

async def create_case(data: dict) -> str:
    now = datetime.utcnow()
    payload = {
        "event_id": data["event_id"],
        "entity_id": data["entity_id"],
        "risk": data["risk"],
        "action": data["action"],
        "reasons": data.get("reasons", []),
        "status": "open",
        "assignee": None,
        "created_at": now,
        "updated_at": now,
    }
    res = await cases.insert_one(payload)
    return str(res.inserted_id)

async def get_case(cid: str) -> dict | None:
    return await cases.find_one({"_id": ObjectId(cid)})

async def list_cases(limit=50) -> list[dict]:
    cursor = cases.find({}).sort("updated_at", -1).limit(limit)
    return [c async for c in cursor]

async def assign_case(cid: str, user: str):
    await cases.update_one({"_id": ObjectId(cid)}, {"$set": {"assignee": user, "updated_at": datetime.utcnow()}})

async def add_note(cid: str, text: str):
    await notes.insert_one({"case_id": ObjectId(cid), "text": text, "ts": datetime.utcnow()})

async def add_action(cid: str, type: str, params: dict):
    await actions.insert_one({"case_id": ObjectId(cid), "type": type, "params": params, "ts": datetime.utcnow()})
