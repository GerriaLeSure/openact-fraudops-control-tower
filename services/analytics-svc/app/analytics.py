"""
Analytics computation engine for fraud operations dashboard
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import statistics
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings
from .schemas import (
    KPIMetric, TimeSeriesPoint, ChannelAnalytics, 
    RegionAnalytics, ActionDistribution, AnalyticsResponse
)

class AnalyticsEngine:
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.mongo_client[settings.DB_NAME]
        self.cases = self.db.get_collection("cases")
        self.actions = self.db.get_collection("case_actions")

    async def compute_kpis(self, hours: int = 24) -> List[KPIMetric]:
        """Compute key performance indicators"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get case statistics
        total_cases = await self.cases.count_documents({
            "created_at": {"$gte": since}
        })
        
        # Get previous period for comparison
        prev_since = since - timedelta(hours=hours)
        prev_total = await self.cases.count_documents({
            "created_at": {"$gte": prev_since, "$lt": since}
        })
        
        # Calculate fraud rate
        fraud_cases = await self.cases.count_documents({
            "created_at": {"$gte": since},
            "action": {"$in": ["block", "hold"]}
        })
        
        fraud_rate = (fraud_cases / total_cases * 100) if total_cases > 0 else 0
        
        # Calculate average case resolution time
        resolved_cases = await self.cases.find({
            "created_at": {"$gte": since},
            "status": "closed"
        }).to_list(1000)
        
        avg_resolution_hours = 0
        if resolved_cases:
            resolution_times = [
                (case["updated_at"] - case["created_at"]).total_seconds() / 3600
                for case in resolved_cases
            ]
            avg_resolution_hours = statistics.mean(resolution_times)
        
        # Calculate change percentages
        case_change = ((total_cases - prev_total) / prev_total * 100) if prev_total > 0 else 0
        
        return [
            KPIMetric(
                name="Total Cases",
                value=float(total_cases),
                change_percent=case_change,
                trend="up" if case_change > 5 else "down" if case_change < -5 else "stable"
            ),
            KPIMetric(
                name="Fraud Rate",
                value=fraud_rate,
                change_percent=0,  # Would need historical data
                trend="stable"
            ),
            KPIMetric(
                name="Avg Resolution Time",
                value=avg_resolution_hours,
                change_percent=0,
                trend="stable"
            ),
            KPIMetric(
                name="Cases per Hour",
                value=total_cases / hours,
                change_percent=0,
                trend="stable"
            )
        ]

    async def compute_time_series(self, hours: int = 24) -> Dict[str, List[TimeSeriesPoint]]:
        """Compute time series data for charts"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Decisions per minute
        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                    "day": {"$dayOfMonth": "$created_at"},
                    "hour": {"$hour": "$created_at"},
                    "minute": {"$minute": "$created_at"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        decisions_data = await self.cases.aggregate(pipeline).to_list(1000)
        decisions_per_minute = [
            TimeSeriesPoint(
                timestamp=datetime(
                    doc["_id"]["year"], doc["_id"]["month"], doc["_id"]["day"],
                    doc["_id"]["hour"], doc["_id"]["minute"]
                ),
                value=float(doc["count"])
            )
            for doc in decisions_data
        ]
        
        # Fraud rate trend (mock data for demo)
        fraud_rate_trend = [
            TimeSeriesPoint(
                timestamp=since + timedelta(minutes=i*30),
                value=5.0 + (i % 10) * 0.5  # Mock trend
            )
            for i in range(hours * 2)
        ]
        
        # Average latency trend (mock data)
        avg_latency_trend = [
            TimeSeriesPoint(
                timestamp=since + timedelta(minutes=i*30),
                value=150.0 + (i % 20) * 10  # Mock trend
            )
            for i in range(hours * 2)
        ]
        
        return {
            "decisions_per_minute": decisions_per_minute,
            "fraud_rate_trend": fraud_rate_trend,
            "avg_latency_trend": avg_latency_trend
        }

    async def compute_distributions(self, hours: int = 24) -> Dict[str, List]:
        """Compute distribution analytics"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Action distribution
        action_pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {"_id": "$action", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        action_data = await self.cases.aggregate(action_pipeline).to_list(100)
        total_actions = sum(doc["count"] for doc in action_data)
        
        action_distribution = [
            ActionDistribution(
                action=doc["_id"],
                count=doc["count"],
                percentage=(doc["count"] / total_actions * 100) if total_actions > 0 else 0
            )
            for doc in action_data
        ]
        
        # Channel analytics (mock data)
        channel_analytics = [
            ChannelAnalytics(
                channel="web",
                total_transactions=1500,
                fraud_rate=3.2,
                avg_amount=250.0,
                total_volume=375000.0
            ),
            ChannelAnalytics(
                channel="mobile",
                total_transactions=2000,
                fraud_rate=2.1,
                avg_amount=180.0,
                total_volume=360000.0
            ),
            ChannelAnalytics(
                channel="api",
                total_transactions=800,
                fraud_rate=4.5,
                avg_amount=500.0,
                total_volume=400000.0
            )
        ]
        
        # Region analytics (mock data)
        region_analytics = [
            RegionAnalytics(
                region="US",
                total_transactions=2000,
                fraud_rate=2.8,
                avg_amount=300.0
            ),
            RegionAnalytics(
                region="EU",
                total_transactions=1500,
                fraud_rate=3.5,
                avg_amount=280.0
            ),
            RegionAnalytics(
                region="APAC",
                total_transactions=800,
                fraud_rate=4.2,
                avg_amount=250.0
            )
        ]
        
        return {
            "action_distribution": action_distribution,
            "channel_analytics": channel_analytics,
            "region_analytics": region_analytics
        }

    async def generate_analytics(self, hours: int = 24) -> AnalyticsResponse:
        """Generate comprehensive analytics report"""
        kpis = await self.compute_kpis(hours)
        time_series = await self.compute_time_series(hours)
        distributions = await self.compute_distributions(hours)
        
        # Calculate summary stats
        total_transactions = sum(kpi.value for kpi in kpis if kpi.name == "Total Cases")
        total_fraud = sum(
            kpi.value * total_transactions / 100 
            for kpi in kpis if kpi.name == "Fraud Rate"
        )
        
        return AnalyticsResponse(
            time_range_hours=hours,
            generated_at=datetime.utcnow(),
            kpis=kpis,
            decisions_per_minute=time_series["decisions_per_minute"],
            fraud_rate_trend=time_series["fraud_rate_trend"],
            avg_latency_trend=time_series["avg_latency_trend"],
            action_distribution=distributions["action_distribution"],
            channel_analytics=distributions["channel_analytics"],
            region_analytics=distributions["region_analytics"],
            total_transactions=int(total_transactions),
            total_fraud_detected=int(total_fraud),
            avg_response_time_ms=150.0,  # Mock data
            model_accuracy=94.2  # Mock data
        )
