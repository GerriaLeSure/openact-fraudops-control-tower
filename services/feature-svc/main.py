"""Feature service for real-time feature engineering."""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import redis
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from geopy.distance import geodesic
from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError

from shared.schemas.events import TransactionEvent, ClaimEvent
from shared.schemas.features import FeatureVector, Geolocation, FeatureMetadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Feature Service",
    description="Service for real-time feature engineering",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
redis_client = None
kafka_consumer = None
kafka_producer = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global redis_client
    if redis_client is None:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
    return redis_client


def get_kafka_consumer() -> KafkaConsumer:
    """Get or create Kafka consumer."""
    global kafka_consumer
    if kafka_consumer is None:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        kafka_consumer = KafkaConsumer(
            "events.txns.v1",
            "events.claims.v1",
            bootstrap_servers=[bootstrap_servers],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id="feature-svc",
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
    return kafka_consumer


def get_kafka_producer() -> KafkaProducer:
    """Get or create Kafka producer."""
    global kafka_producer
    if kafka_producer is None:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        kafka_producer = KafkaProducer(
            bootstrap_servers=[bootstrap_servers],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=3,
            acks='all'
        )
    return kafka_producer


def get_ip_risk_score(ip_address: str) -> float:
    """Get IP risk score from cache or compute default."""
    if not ip_address:
        return 0.0
    
    redis_client = get_redis_client()
    cache_key = f"ip_risk:{ip_address}"
    
    # Try to get from cache
    cached_score = redis_client.get(cache_key)
    if cached_score:
        return float(cached_score)
    
    # Default risk scoring logic (simplified)
    # In production, this would call an external IP risk service
    risk_score = 0.1  # Default low risk
    
    # Cache the result for 1 hour
    redis_client.setex(cache_key, 3600, risk_score)
    return risk_score


def get_merchant_risk_score(merchant_id: str) -> float:
    """Get merchant risk score from cache or compute default."""
    if not merchant_id:
        return 0.0
    
    redis_client = get_redis_client()
    cache_key = f"merchant_risk:{merchant_id}"
    
    # Try to get from cache
    cached_score = redis_client.get(cache_key)
    if cached_score:
        return float(cached_score)
    
    # Default risk scoring logic (simplified)
    risk_score = 0.05  # Default low risk
    
    # Cache the result for 24 hours
    redis_client.setex(cache_key, 86400, risk_score)
    return risk_score


def get_velocity_counts(entity_id: str, time_windows: list) -> Dict[str, int]:
    """Get velocity counts for different time windows."""
    redis_client = get_redis_client()
    velocity_counts = {}
    
    for window in time_windows:
        cache_key = f"velocity:{entity_id}:{window}"
        count = redis_client.get(cache_key)
        velocity_counts[f"velocity_{window}"] = int(count) if count else 0
    
    return velocity_counts


def update_velocity_counts(entity_id: str, time_windows: list):
    """Update velocity counts for different time windows."""
    redis_client = get_redis_client()
    current_time = datetime.utcnow()
    
    for window in time_windows:
        cache_key = f"velocity:{entity_id}:{window}"
        
        # Increment counter
        redis_client.incr(cache_key)
        
        # Set expiration based on window
        if window == "1h":
            redis_client.expire(cache_key, 3600)
        elif window == "24h":
            redis_client.expire(cache_key, 86400)
        elif window == "7d":
            redis_client.expire(cache_key, 604800)


def get_geolocation(ip_address: str) -> Optional[Geolocation]:
    """Get geolocation for IP address."""
    if not ip_address:
        return None
    
    redis_client = get_redis_client()
    cache_key = f"geo:{ip_address}"
    
    # Try to get from cache
    cached_geo = redis_client.get(cache_key)
    if cached_geo:
        geo_data = json.loads(cached_geo)
        return Geolocation(**geo_data)
    
    # Default geolocation (simplified)
    # In production, this would call a geolocation service
    geo_data = {
        "country": "US",
        "region": "CA",
        "city": "San Francisco",
        "latitude": 37.7749,
        "longitude": -122.4194
    }
    
    # Cache the result for 24 hours
    redis_client.setex(cache_key, 86400, json.dumps(geo_data))
    return Geolocation(**geo_data)


def calculate_geo_distance(entity_id: str, current_lat: float, current_lon: float) -> float:
    """Calculate distance from usual location."""
    if not current_lat or not current_lon:
        return 0.0
    
    redis_client = get_redis_client()
    cache_key = f"usual_location:{entity_id}"
    
    # Get usual location from cache
    usual_location = redis_client.get(cache_key)
    if not usual_location:
        # Set default location and return 0 distance
        default_location = {"lat": current_lat, "lon": current_lon}
        redis_client.setex(cache_key, 86400 * 30, json.dumps(default_location))
        return 0.0
    
    usual_data = json.loads(usual_location)
    usual_lat = usual_data["lat"]
    usual_lon = usual_data["lon"]
    
    # Calculate distance in kilometers
    distance = geodesic((usual_lat, usual_lon), (current_lat, current_lon)).kilometers
    return distance


def get_account_age(entity_id: str) -> int:
    """Get account age in days."""
    redis_client = get_redis_client()
    cache_key = f"account_age:{entity_id}"
    
    # Try to get from cache
    cached_age = redis_client.get(cache_key)
    if cached_age:
        return int(cached_age)
    
    # Default age (simplified)
    age_days = 365  # Default 1 year
    
    # Cache the result for 24 hours
    redis_client.setex(cache_key, 86400, age_days)
    return age_days


def process_event(event_data: Dict[str, Any], topic: str):
    """Process an event and generate features."""
    start_time = time.time()
    
    try:
        # Parse event based on topic
        if topic == "events.txns.v1":
            event = TransactionEvent(**event_data)
            amount = event.amount
            currency = event.currency
        else:  # events.claims.v1
            event = ClaimEvent(**event_data)
            amount = event.claim_amount
            currency = "USD"  # Default for claims
        
        entity_id = event.entity_id
        
        # Get velocity counts
        time_windows = ["1h", "24h", "7d"]
        velocity_counts = get_velocity_counts(entity_id, time_windows)
        
        # Update velocity counts
        update_velocity_counts(entity_id, time_windows)
        
        # Get risk scores
        ip_risk = get_ip_risk_score(getattr(event, 'ip_address', None))
        merchant_risk = get_merchant_risk_score(getattr(event, 'merchant_id', None))
        
        # Get geolocation
        ip_geolocation = get_geolocation(getattr(event, 'ip_address', None))
        
        # Calculate geo distance
        geo_distance = 0.0
        if ip_geolocation and ip_geolocation.latitude and ip_geolocation.longitude:
            geo_distance = calculate_geo_distance(
                entity_id, 
                ip_geolocation.latitude, 
                ip_geolocation.longitude
            )
        
        # Get account age
        age_days = get_account_age(entity_id)
        
        # Create feature vector
        feature_vector = FeatureVector(
            event_id=event.event_id,
            entity_id=entity_id,
            timestamp=datetime.utcnow(),
            amount=amount,
            currency=currency,
            channel=getattr(event, 'channel', None),
            velocity_1h=velocity_counts.get("velocity_1h", 0),
            velocity_24h=velocity_counts.get("velocity_24h", 0),
            velocity_7d=velocity_counts.get("velocity_7d", 0),
            ip_risk=ip_risk,
            ip_geolocation=ip_geolocation,
            geo_distance_km=geo_distance,
            merchant_risk=merchant_risk,
            merchant_category=getattr(event, 'merchant_category', None),
            age_days=age_days,
            device_fingerprint=getattr(event, 'device_fingerprint', None),
            session_id=getattr(event, 'session_id', None),
            user_agent_hash=hash(getattr(event, 'user_agent', '')) if getattr(event, 'user_agent', None) else None,
            features_version="v1",
            feature_metadata=FeatureMetadata(
                computation_time_ms=(time.time() - start_time) * 1000,
                cache_hit=True,  # Simplified
                data_freshness_minutes=0.0
            )
        )
        
        # Convert to dict for Kafka
        feature_dict = feature_vector.dict()
        feature_dict["timestamp"] = feature_dict["timestamp"].isoformat()
        
        # Publish to Kafka
        producer = get_kafka_producer()
        producer.send(
            "features.online.v1",
            key=entity_id,
            value=feature_dict
        )
        
        logger.info(f"Features generated for event: {event.event_id}")
        
    except Exception as e:
        logger.error(f"Error processing event: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Feature Service")
    # Initialize clients
    get_redis_client()
    get_kafka_consumer()
    get_kafka_producer()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global kafka_consumer, kafka_producer, redis_client
    if kafka_consumer:
        kafka_consumer.close()
    if kafka_producer:
        kafka_producer.close()
    if redis_client:
        redis_client.close()
    logger.info("Shutting down Feature Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "feature-svc", "timestamp": datetime.utcnow().isoformat()}


@app.post("/process")
async def process_event_sync(event_data: Dict[str, Any], topic: str = "events.txns.v1"):
    """Process an event synchronously for testing."""
    try:
        process_event(event_data, topic)
        return {"status": "success", "message": "Event processed successfully"}
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing event"
        )


def consume_events():
    """Consume events from Kafka and process them."""
    consumer = get_kafka_consumer()
    logger.info("Starting to consume events...")
    
    for message in consumer:
        try:
            topic = message.topic
            event_data = message.value
            process_event(event_data, topic)
        except Exception as e:
            logger.error(f"Error consuming message: {e}")


if __name__ == "__main__":
    import uvicorn
    import threading
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=consume_events, daemon=True)
    consumer_thread.start()
    
    # Start FastAPI server
    port = int(os.getenv("FEATURE_SVC_PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
