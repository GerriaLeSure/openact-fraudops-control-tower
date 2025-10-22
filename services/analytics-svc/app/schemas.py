from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float

class KPIMetric(BaseModel):
    name: str
    value: float
    change_percent: Optional[float] = None
    trend: Optional[str] = None  # "up", "down", "stable"

class ChannelAnalytics(BaseModel):
    channel: str
    total_transactions: int
    fraud_rate: float
    avg_amount: float
    total_volume: float

class RegionAnalytics(BaseModel):
    region: str
    total_transactions: int
    fraud_rate: float
    avg_amount: float

class ActionDistribution(BaseModel):
    action: str
    count: int
    percentage: float

class AnalyticsResponse(BaseModel):
    time_range_hours: int
    generated_at: datetime
    
    # KPI metrics
    kpis: List[KPIMetric]
    
    # Time series data
    decisions_per_minute: List[TimeSeriesPoint]
    fraud_rate_trend: List[TimeSeriesPoint]
    avg_latency_trend: List[TimeSeriesPoint]
    
    # Distribution data
    action_distribution: List[ActionDistribution]
    channel_analytics: List[ChannelAnalytics]
    region_analytics: List[RegionAnalytics]
    
    # Summary stats
    total_transactions: int
    total_fraud_detected: int
    avg_response_time_ms: float
    model_accuracy: Optional[float] = None
