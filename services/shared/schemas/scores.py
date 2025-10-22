"""Model scoring schemas."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelScores(BaseModel):
    """Individual model scores."""
    
    xgb: float = Field(..., ge=0, le=1, description="XGBoost model score")
    nn: float = Field(..., ge=0, le=1, description="Neural network model score")
    rules: float = Field(..., ge=0, le=1, description="Rule-based score")
    ensemble: float = Field(..., ge=0, le=1, description="Weighted ensemble score")
    calibrated: float = Field(..., ge=0, le=1, description="Platt-calibrated final score")


class FeatureExplanation(BaseModel):
    """Feature explanation with SHAP values."""
    
    top_features: List[List] = Field(..., description="Top contributing features with SHAP values")
    feature_importance: Optional[Dict[str, float]] = Field(None, description="Feature importance scores")


class ScoreOutput(BaseModel):
    """Model scoring output."""
    
    event_id: UUID = Field(..., description="Original event identifier")
    scores: ModelScores = Field(..., description="Model scores")
    explain: Optional[FeatureExplanation] = Field(None, description="Feature explanations")
    model_version: str = Field(..., description="Model version identifier")
    computation_time_ms: Optional[float] = Field(None, description="Model computation time in milliseconds")

    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }
