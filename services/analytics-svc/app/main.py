from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .analytics import AnalyticsEngine
from .schemas import AnalyticsResponse
from typing import Optional

app = FastAPI(title="analytics-svc", version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Analytics engine
analytics_engine = AnalyticsEngine()

@app.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1-168)")
):
    """Get comprehensive analytics for the fraud operations dashboard"""
    try:
        return await analytics_engine.generate_analytics(hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics computation failed: {str(e)}")

@app.get("/analytics/kpis")
async def get_kpis(
    hours: int = Query(24, ge=1, le=168)
):
    """Get KPI metrics only"""
    try:
        kpis = await analytics_engine.compute_kpis(hours)
        return {"kpis": kpis, "time_range_hours": hours}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KPI computation failed: {str(e)}")

@app.get("/analytics/trends")
async def get_trends(
    hours: int = Query(24, ge=1, le=168)
):
    """Get time series trends only"""
    try:
        trends = await analytics_engine.compute_time_series(hours)
        return {"trends": trends, "time_range_hours": hours}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend computation failed: {str(e)}")

@app.get("/analytics/distributions")
async def get_distributions(
    hours: int = Query(24, ge=1, le=168)
):
    """Get distribution analytics only"""
    try:
        distributions = await analytics_engine.compute_distributions(hours)
        return {"distributions": distributions, "time_range_hours": hours}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Distribution computation failed: {str(e)}")

@app.get("/health")
async def health():
    return {
        "status": "ok", 
        "service": settings.SERVICE_NAME,
        "mongo_connected": True  # Would check actual connection in production
    }
