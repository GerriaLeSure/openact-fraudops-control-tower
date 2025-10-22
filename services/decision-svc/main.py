"""Decision service for risk-based decision engine."""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import psycopg2
import redis
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError

from shared.schemas.scores import ScoreOutput
from shared.schemas.decisions import DecisionOutput

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Decision Service",
    description="Service for risk-based decision engine",
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

# Global variables
postgres_conn = None
redis_client = None
kafka_consumer = None
kafka_producer = None
current_policy = None


def get_postgres_connection():
    """Get PostgreSQL connection."""
    global postgres_conn
    if postgres_conn is None or postgres_conn.closed:
        try:
            postgres_conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "fraudops"),
                user=os.getenv("POSTGRES_USER", "fraudops"),
                password=os.getenv("POSTGRES_PASSWORD", "fraudops_password")
            )
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            return None
    return postgres_conn


def get_redis_client() -> redis.Redis:
    """Get Redis client."""
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
            "alerts.scores.v1",
            bootstrap_servers=[bootstrap_servers],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id="decision-svc",
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


def load_decision_policy():
    """Load the current decision policy from PostgreSQL."""
    global current_policy
    
    try:
        conn = get_postgres_connection()
        if conn is None:
            logger.error("Cannot connect to PostgreSQL")
            return
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT policy_config, version 
            FROM decision_policy 
            WHERE is_active = true 
            ORDER BY effective_date DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if result:
            policy_config, version = result
            current_policy = {
                'version': version,
                'config': policy_config
            }
            logger.info(f"Loaded decision policy version: {version}")
        else:
            # Use default policy
            current_policy = {
                'version': 'v1.0',
                'config': {
                    'rules': {
                        'block': {
                            'conditions': [
                                {'calibrated_score': {'gte': 0.90}},
                                {'calibrated_score': {'gte': 0.80}, 'watchlist_hit': True}
                            ],
                            'action': 'block',
                            'reason_codes': ['high_risk_score', 'watchlist_match']
                        },
                        'hold': {
                            'conditions': [
                                {'calibrated_score': {'gte': 0.70, 'lt': 0.90}},
                                {'conflicting_signals': True}
                            ],
                            'action': 'hold',
                            'reason_codes': ['medium_risk', 'conflicting_signals']
                        },
                        'allow': {
                            'conditions': [
                                {'calibrated_score': {'lt': 0.70}},
                                {'velocity_normal': True}
                            ],
                            'action': 'allow',
                            'reason_codes': ['low_risk', 'normal_velocity']
                        }
                    }
                }
            }
            logger.info("Using default decision policy")
        
        cursor.close()
        
    except Exception as e:
        logger.error(f"Error loading decision policy: {e}")
        # Use default policy as fallback
        current_policy = {
            'version': 'v1.0',
            'config': {
                'rules': {
                    'allow': {
                        'conditions': [{'calibrated_score': {'lt': 1.0}}],
                        'action': 'allow',
                        'reason_codes': ['default_allow']
                    }
                }
            }
        }


def check_velocity_anomaly(entity_id: str, velocity_1h: int, velocity_24h: int) -> bool:
    """Check for velocity anomalies."""
    try:
        redis_client = get_redis_client()
        
        # Get historical velocity patterns
        historical_1h = redis_client.get(f"velocity_pattern_1h:{entity_id}")
        historical_24h = redis_client.get(f"velocity_pattern_24h:{entity_id}")
        
        # Simple anomaly detection
        if historical_1h:
            avg_1h = float(historical_1h)
            if velocity_1h > avg_1h * 3:  # 3x normal velocity
                return True
        
        if historical_24h:
            avg_24h = float(historical_24h)
            if velocity_24h > avg_24h * 2:  # 2x normal velocity
                return True
        
        # Update patterns
        if not historical_1h:
            redis_client.setex(f"velocity_pattern_1h:{entity_id}", 86400, velocity_1h)
        else:
            # Exponential moving average
            alpha = 0.1
            new_avg = alpha * velocity_1h + (1 - alpha) * float(historical_1h)
            redis_client.setex(f"velocity_pattern_1h:{entity_id}", 86400, new_avg)
        
        if not historical_24h:
            redis_client.setex(f"velocity_pattern_24h:{entity_id}", 86400, velocity_24h)
        else:
            alpha = 0.1
            new_avg = alpha * velocity_24h + (1 - alpha) * float(historical_24h)
            redis_client.setex(f"velocity_pattern_24h:{entity_id}", 86400, new_avg)
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking velocity anomaly: {e}")
        return False


def check_watchlist(entity_id: str, ip_address: str = None, device_fingerprint: str = None) -> List[str]:
    """Check against watchlists."""
    watchlist_hits = []
    
    try:
        redis_client = get_redis_client()
        
        # Check entity watchlist
        if redis_client.sismember("watchlist:entities", entity_id):
            watchlist_hits.append("entity_watchlist")
        
        # Check IP watchlist
        if ip_address and redis_client.sismember("watchlist:ips", ip_address):
            watchlist_hits.append("ip_watchlist")
        
        # Check device watchlist
        if device_fingerprint and redis_client.sismember("watchlist:devices", device_fingerprint):
            watchlist_hits.append("device_watchlist")
        
    except Exception as e:
        logger.error(f"Error checking watchlist: {e}")
    
    return watchlist_hits


def check_graph_anomaly(entity_id: str, device_fingerprint: str = None) -> bool:
    """Check for graph-based anomalies."""
    try:
        redis_client = get_redis_client()
        
        if not device_fingerprint:
            return False
        
        # Count device-account links
        device_accounts_key = f"device_accounts:{device_fingerprint}"
        account_count = redis_client.scard(device_accounts_key)
        
        # Add current account to device
        redis_client.sadd(device_accounts_key, entity_id)
        redis_client.expire(device_accounts_key, 86400 * 30)  # 30 days
        
        # Check for anomaly (more than 5 accounts per device)
        if account_count > 5:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking graph anomaly: {e}")
        return False


def evaluate_conditions(conditions: List[Dict], score_data: Dict, entity_id: str) -> bool:
    """Evaluate policy conditions."""
    for condition in conditions:
        if 'calibrated_score' in condition:
            score_condition = condition['calibrated_score']
            calibrated_score = score_data.get('calibrated', 0)
            
            if 'gte' in score_condition and calibrated_score < score_condition['gte']:
                continue
            if 'lt' in score_condition and calibrated_score >= score_condition['lt']:
                continue
        
        if 'watchlist_hit' in condition:
            # This would be determined by watchlist checks
            continue
        
        if 'conflicting_signals' in condition:
            # Check for conflicting signals
            xgb_score = score_data.get('xgb', 0)
            nn_score = score_data.get('nn', 0)
            rules_score = score_data.get('rules', 0)
            
            # Check if scores are conflicting (high variance)
            scores = [xgb_score, nn_score, rules_score]
            score_variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            if score_variance < 0.1:  # Low variance, not conflicting
                continue
        
        if 'velocity_normal' in condition:
            # This would be determined by velocity checks
            continue
        
        # If we get here, condition is met
        return True
    
    return False


def make_decision(score_output: ScoreOutput, entity_id: str, ip_address: str = None, 
                 device_fingerprint: str = None) -> DecisionOutput:
    """Make a decision based on scores and policy."""
    start_time = time.time()
    
    if current_policy is None:
        load_decision_policy()
    
    # Extract score data
    score_data = {
        'calibrated': score_output.scores.calibrated,
        'xgb': score_output.scores.xgb,
        'nn': score_output.scores.nn,
        'rules': score_output.scores.rules,
        'ensemble': score_output.scores.ensemble
    }
    
    # Check for anomalies
    velocity_anomaly = False  # Would need velocity data from feature vector
    graph_anomaly = check_graph_anomaly(entity_id, device_fingerprint)
    watchlist_hits = check_watchlist(entity_id, ip_address, device_fingerprint)
    
    # Evaluate policy rules
    decision_action = "allow"  # Default
    reasons = []
    case_id = None
    
    rules = current_policy['config']['rules']
    
    # Check rules in order of severity
    for rule_name, rule_config in [('block', rules.get('block')), 
                                  ('hold', rules.get('hold')), 
                                  ('allow', rules.get('allow'))]:
        if rule_config and evaluate_conditions(rule_config['conditions'], score_data, entity_id):
            decision_action = rule_config['action']
            reasons = rule_config.get('reason_codes', [])
            break
    
    # Override with watchlist hits
    if watchlist_hits:
        if score_data['calibrated'] >= 0.8:
            decision_action = "block"
            reasons.extend(watchlist_hits)
        else:
            decision_action = "hold"
            reasons.extend(watchlist_hits)
    
    # Override with velocity anomaly
    if velocity_anomaly:
        if decision_action == "allow":
            decision_action = "hold"
        reasons.append("velocity_anomaly")
    
    # Override with graph anomaly
    if graph_anomaly:
        if decision_action == "allow":
            decision_action = "hold"
        reasons.append("graph_anomaly")
    
    # Generate case ID for hold/block/escalate actions
    if decision_action in ["hold", "block", "escalate"]:
        case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"
    
    # Compute decision time
    decision_time = (time.time() - start_time) * 1000
    
    # Create decision output
    decision = DecisionOutput(
        event_id=score_output.event_id,
        risk=score_data['calibrated'],
        action=decision_action,
        policy=current_policy['version'],
        reasons=reasons,
        case_id=case_id,
        watchlist_hits=watchlist_hits,
        velocity_anomaly=velocity_anomaly,
        graph_anomaly=graph_anomaly,
        decision_time_ms=decision_time
    )
    
    return decision


def process_score_output(score_data: Dict[str, Any]):
    """Process a score output and make a decision."""
    try:
        # Parse score output
        score_output = ScoreOutput(**score_data)
        
        # Extract entity information (would come from original event)
        entity_id = "unknown"  # Would extract from original event
        ip_address = None
        device_fingerprint = None
        
        # Make decision
        decision = make_decision(score_output, entity_id, ip_address, device_fingerprint)
        
        # Convert to dict for Kafka
        decision_dict = decision.dict()
        decision_dict["event_id"] = str(decision_dict["event_id"])
        
        # Publish to Kafka
        producer = get_kafka_producer()
        producer.send(
            "alerts.decisions.v1",
            key=entity_id,
            value=decision_dict
        )
        
        logger.info(f"Decision made for event: {score_output.event_id} - {decision.action}")
        
    except Exception as e:
        logger.error(f"Error processing score output: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Decision Service")
    load_decision_policy()
    get_postgres_connection()
    get_redis_client()
    get_kafka_consumer()
    get_kafka_producer()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global kafka_consumer, kafka_producer, postgres_conn
    if kafka_consumer:
        kafka_consumer.close()
    if kafka_producer:
        kafka_producer.close()
    if postgres_conn:
        postgres_conn.close()
    logger.info("Shutting down Decision Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "decision-svc", 
        "timestamp": datetime.utcnow().isoformat(),
        "policy_loaded": current_policy is not None
    }


@app.post("/decide")
async def decide_sync(score_data: Dict[str, Any], entity_id: str = "test_entity"):
    """Make a decision synchronously for testing."""
    try:
        # Parse score output
        score_output = ScoreOutput(**score_data)
        
        # Make decision
        decision = make_decision(score_output, entity_id)
        
        # Convert to dict for response
        decision_dict = decision.dict()
        decision_dict["event_id"] = str(decision_dict["event_id"])
        
        return decision_dict
        
    except Exception as e:
        logger.error(f"Error making decision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error making decision"
        )


@app.get("/policy")
async def get_current_policy():
    """Get the current decision policy."""
    if current_policy is None:
        load_decision_policy()
    
    return current_policy


@app.post("/policy/reload")
async def reload_policy():
    """Reload the decision policy from database."""
    load_decision_policy()
    return {"message": "Policy reloaded", "version": current_policy['version']}


def consume_scores():
    """Consume score outputs from Kafka and make decisions."""
    consumer = get_kafka_consumer()
    logger.info("Starting to consume score outputs...")
    
    for message in consumer:
        try:
            score_data = message.value
            process_score_output(score_data)
        except Exception as e:
            logger.error(f"Error consuming message: {e}")


if __name__ == "__main__":
    import uvicorn
    import threading
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=consume_scores, daemon=True)
    consumer_thread.start()
    
    # Start FastAPI server
    port = int(os.getenv("DECISION_SVC_PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)
