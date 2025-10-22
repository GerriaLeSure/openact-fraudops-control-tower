from fastapi import FastAPI, HTTPException
from bson import ObjectId
from .config import settings
from .schemas import CaseCreate, CaseOut, NoteCreate, ActionCreate
from . import models, crud

app = FastAPI(title="case-svc", version="0.1.0")

@app.on_event("startup")
async def startup():
    await models.ensure_indexes()

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}

@app.post("/cases", response_model=dict)
async def open_case(body: CaseCreate):
    cid = await crud.create_case(body.model_dump())
    return {"case_id": cid}

@app.get("/cases", response_model=list[CaseOut])
async def list_cases():
    data = await crud.list_cases()
    for d in data: d["_id"] = str(d["_id"])
    return data

@app.get("/cases/{cid}", response_model=CaseOut)
async def get_case(cid: str):
    data = await crud.get_case(cid)
    if not data: raise HTTPException(404, "case not found")
    data["_id"] = str(data["_id"])
    return data

@app.patch("/cases/{cid}/assign")
async def assign(cid: str, user: str):
    await crud.assign_case(cid, user)
    return {"ok": True}

@app.post("/cases/{cid}/notes")
async def add_note(cid: str, body: NoteCreate):
    await crud.add_note(cid, body.text)
    return {"ok": True}

@app.post("/cases/{cid}/actions")
async def add_action(cid: str, body: ActionCreate):
    await crud.add_action(cid, body.type, body.params)
    return {"ok": True}
