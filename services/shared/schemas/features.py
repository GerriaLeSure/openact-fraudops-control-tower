"""Feature vector schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Geolocation(BaseModel):
    """Geolocation information."""
    
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FeatureMetadata(BaseModel):
    """Feature computation metadata."""
    
    computation_time_ms: Optional[float] = None
    cache_hit: Optional[bool] = None
    data_freshness_minutes: Optional[float] = None


class FeatureVector(BaseModel):
    """Feature vector schema."""
    
    event_id: UUID = Field(..., description="Original event identifier")
    entity_id: str = Field(..., description="Account or user identifier")
    timestamp: datetime = Field(..., description="Feature computation timestamp")
    amount: Optional[float] = Field(None, description="Transaction or claim amount")
    currency: Optional[str] = Field(None, description="Currency code")
    channel: Optional[str] = Field(None, description="Transaction channel")
    velocity_1h: int = Field(0, ge=0, description="Number of transactions in last hour")
    velocity_24h: int = Field(0, ge=0, description="Number of transactions in last 24 hours")
    velocity_7d: int = Field(0, ge=0, description="Number of transactions in last 7 days")
    ip_risk: float = Field(0.0, ge=0, le=1, description="IP address risk score")
    ip_geolocation: Optional[Geolocation] = Field(None, description="IP geolocation")
    geo_distance_km: float = Field(0.0, ge=0, description="Distance from usual location in kilometers")
    merchant_risk: float = Field(0.0, ge=0, le=1, description="Merchant risk score")
    merchant_category: Optional[str] = Field(None, description="Merchant category code")
    age_days: int = Field(0, ge=0, description="Account age in days")
    device_fingerprint: Optional[str] = Field(None, description="Device fingerprint hash")
    session_id: Optional[str] = Field(None, description="Session identifier")
    user_agent_hash: Optional[str] = Field(None, description="Hashed user agent")
    features_version: str = Field(..., description="Feature schema version")
    feature_metadata: Optional[FeatureMetadata] = Field(None, description="Feature computation metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
