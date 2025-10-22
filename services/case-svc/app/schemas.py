from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class CaseCreate(BaseModel):
    event_id: str
    entity_id: str
    risk: float
    action: str
    reasons: List[str] = []

class CaseOut(BaseModel):
    id: str = Field(alias="_id")
    event_id: str
    entity_id: str
    status: str
    risk: float
    action: str
    reasons: List[str]
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class NoteCreate(BaseModel):
    text: str

class ActionCreate(BaseModel):
    type: str
    params: Dict[str, str] = {}
