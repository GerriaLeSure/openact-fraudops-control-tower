from pydantic import BaseModel, Field
from typing import Dict, List, Tuple, Optional

class FeatureVector(BaseModel):
    event_id: str
    entity_id: str
    ts: str
    amount: float
    channel: str
    velocity_1h: int
    ip_risk: float
    geo_distance_km: float
    merchant_risk: float
    age_days: int
    device_fingerprint: str
    features_version: str = "v1"

class ScoreResponse(BaseModel):
    event_id: str
    scores: Dict[str, float]
    explain: Dict[str, List[Tuple[str, float]]]
    model_version: str
