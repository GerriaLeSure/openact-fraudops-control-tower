"""Decision schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DecisionOutput(BaseModel):
    """Decision engine output."""
    
    event_id: UUID = Field(..., description="Original event identifier")
    risk: float = Field(..., ge=0, le=1, description="Final risk score")
    action: str = Field(..., description="Decision action")
    policy: str = Field(..., description="Policy version used")
    reasons: List[str] = Field(..., description="Array of reason codes")
    case_id: Optional[str] = Field(None, description="Associated case identifier if created")
    watchlist_hits: Optional[List[str]] = Field(None, description="Watchlist matches")
    velocity_anomaly: Optional[bool] = Field(None, description="Velocity anomaly detected")
    graph_anomaly: Optional[bool] = Field(None, description="Graph-based anomaly detected")
    decision_time_ms: Optional[float] = Field(None, description="Decision computation time")

    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }
