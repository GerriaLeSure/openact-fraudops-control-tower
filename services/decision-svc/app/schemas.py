from pydantic import BaseModel
from typing import List, Dict

class ScoreIn(BaseModel):
    event_id: str
    entity_id: str
    channel: str
    scores: Dict[str, float]  # expects "calibrated"
    features: Dict[str, float|int|str] = {}

class DecisionOut(BaseModel):
    event_id: str
    risk: float
    action: str           # allow | hold | block | escalate
    reasons: List[str]
    policy: str = "v1"
