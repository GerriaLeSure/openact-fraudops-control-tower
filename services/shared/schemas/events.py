"""Event schemas for transaction and claim events."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class TransactionEvent(BaseModel):
    """Transaction event schema."""
    
    event_id: UUID = Field(..., description="Unique identifier for the transaction event")
    entity_id: str = Field(..., description="Account or user identifier")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the transaction")
    amount: float = Field(..., ge=0, description="Transaction amount")
    currency: str = Field(..., regex=r"^[A-Z]{3}$", description="ISO 4217 currency code")
    channel: str = Field(..., description="Transaction channel")
    merchant_id: Optional[str] = Field(None, description="Merchant identifier")
    merchant_category: Optional[str] = Field(None, description="Merchant category code")
    ip_address: Optional[str] = Field(None, description="IP address of the transaction")
    device_fingerprint: Optional[str] = Field(None, description="Device fingerprint hash")
    user_agent: Optional[str] = Field(None, description="User agent string")
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional transaction metadata")

    @validator('channel')
    def validate_channel(cls, v):
        allowed_channels = ['web', 'mobile', 'atm', 'pos', 'phone', 'api']
        if v not in allowed_channels:
            raise ValueError(f'Channel must be one of {allowed_channels}')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ClaimEvent(BaseModel):
    """Claim event schema."""
    
    event_id: UUID = Field(..., description="Unique identifier for the claim event")
    entity_id: str = Field(..., description="Policy or customer identifier")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the claim")
    claim_amount: float = Field(..., ge=0, description="Claim amount")
    claim_type: str = Field(..., description="Type of insurance claim")
    policy_id: Optional[str] = Field(None, description="Insurance policy identifier")
    incident_date: Optional[str] = Field(None, description="Date of the incident")
    incident_location: Optional[Dict[str, Any]] = Field(None, description="Incident location details")
    claim_description: Optional[str] = Field(None, description="Description of the claim")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional claim metadata")

    @validator('claim_type')
    def validate_claim_type(cls, v):
        allowed_types = ['auto', 'home', 'health', 'life', 'travel', 'other']
        if v not in allowed_types:
            raise ValueError(f'Claim type must be one of {allowed_types}')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
