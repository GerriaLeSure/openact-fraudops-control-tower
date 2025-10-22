"""Model monitoring service for drift detection and performance monitoring."""

import json
import logging
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import psycopg2
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from sklearn.metrics import brier_score_loss
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Model Monitor Service",
    description="Service for model monitoring and drift detection",
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

# Prometheus metrics
decision_counter = Counter('fraud_decisions_total', 'Total fraud decisions', ['action'])
decision_latency = Histogram('fraud_decision_latency_seconds', 'Decision latency in seconds')
model_score_histogram = Histogram('fraud_model_scores', 'Model scores distribution', ['model_name'])
drift_psi_gauge = Gauge('fraud_feature_drift_psi', 'Feature drift PSI values', ['feature_name'])
calibration_brier_gauge = Gauge('fraud_model_calibration_brier', 'Model calibration Brier score', ['model_name'])
throughput_gauge = Gauge('fraud_throughput_per_second', 'Decisions per second')

# Global variables
postgres_conn = None
kafka_consumer = None
recent_scores = defaultdict(lambda: deque(maxlen=1000))
recent_features = defaultdict(lambda: deque(maxlen=1000))
reference_features = {}
throughput_window = deque(maxlen=60)  # 60 seconds window


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


def get_kafka_consumer() -> KafkaConsumer:
    """Get or create Kafka consumer."""
    global kafka_consumer
    if kafka_consumer is None:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        kafka_consumer = KafkaConsumer(
            "alerts.scores.v1",
            "alerts.decisions.v1",
            bootstrap_servers=[bootstrap_servers],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id="model-monitor-svc",
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
    return kafka_consumer


def calculate_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Calculate Population Stability Index (PSI)."""
    try:
        # Create bins based on expected distribution
        breakpoints = np.percentile(expected, np.linspace(0, 100, bins + 1))
        breakpoints[0] = -np.inf
        breakpoints[-1] = np.inf
        
        # Calculate expected and actual distributions
        expected_hist, _ = np.histogram(expected, bins=breakpoints)
        actual_hist, _ = np.histogram(actual, bins=breakpoints)
        
        # Normalize to probabilities
        expected_prob = expected_hist / len(expected)
        actual_prob = actual_hist / len(actual)
        
        # Avoid division by zero
        expected_prob = np.where(expected_prob == 0, 1e-6, expected_prob)
        actual_prob = np.where(actual_prob == 0, 1e-6, actual_prob)
        
        # Calculate PSI
        psi = np.sum((actual_prob - expected_prob) * np.log(actual_prob / expected_prob))
        
        return float(psi)
    except Exception as e:
        logger.error(f"Error calculating PSI: {e}")
        return 0.0


def calculate_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Calculate Brier score for calibration."""
    try:
        return float(brier_score_loss(y_true, y_prob))
    except Exception as e:
        logger.error(f"Error calculating Brier score: {e}")
        return 0.0


def update_reference_features(features: Dict[str, Any]):
    """Update reference feature distributions."""
    global reference_features
    
    for feature_name, value in features.items():
        if isinstance(value, (int, float)) and not np.isnan(value):
            if feature_name not in reference_features:
                reference_features[feature_name] = deque(maxlen=10000)
            reference_features[feature_name].append(value)


def detect_feature_drift(feature_name: str, current_values: List[float]) -> float:
    """Detect feature drift using PSI."""
    if feature_name not in reference_features or len(reference_features[feature_name]) < 100:
        return 0.0
    
    if len(current_values) < 50:
        return 0.0
    
    try:
        expected = np.array(list(reference_features[feature_name]))
        actual = np.array(current_values)
        
        psi = calculate_psi(expected, actual)
        return psi
    except Exception as e:
        logger.error(f"Error detecting drift for {feature_name}: {e}")
        return 0.0


def store_metric(metric_type: str, metric_value: float, metadata: Dict[str, Any] = None):
    """Store metric in PostgreSQL."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO model_metrics (model_name, metric_type, metric_value, metadata)
            VALUES (%s, %s, %s, %s)
        """, (
            metadata.get('model_name', 'ensemble') if metadata else 'ensemble',
            metric_type,
            metric_value,
            json.dumps(metadata) if metadata else None
        ))
        conn.commit()
        cursor.close()
        
    except Exception as e:
        logger.error(f"Error storing metric: {e}")


def store_feature_drift(feature_name: str, psi_value: float, reference_period: tuple, current_period: tuple):
    """Store feature drift information."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feature_drift 
            (feature_name, psi_value, reference_period_start, reference_period_end, 
             current_period_start, current_period_end)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            feature_name,
            psi_value,
            reference_period[0],
            reference_period[1],
            current_period[0],
            current_period[1]
        ))
        conn.commit()
        cursor.close()
        
    except Exception as e:
        logger.error(f"Error storing feature drift: {e}")


def process_score_message(score_data: Dict[str, Any]):
    """Process score message for monitoring."""
    try:
        scores = score_data.get('scores', {})
        computation_time = score_data.get('computation_time_ms', 0)
        
        # Update Prometheus metrics
        for model_name, score in scores.items():
            if isinstance(score, (int, float)):
                model_score_histogram.labels(model_name=model_name).observe(score)
                recent_scores[model_name].append(score)
        
        # Store latency metric
        if computation_time > 0:
            decision_latency.observe(computation_time / 1000.0)  # Convert to seconds
        
        # Store metrics in database
        store_metric('latency_ms', computation_time, {
            'model_name': 'ensemble',
            'event_id': score_data.get('event_id')
        })
        
        # Update throughput
        current_time = time.time()
        throughput_window.append(current_time)
        
        # Calculate throughput (decisions per second)
        if len(throughput_window) > 1:
            time_span = throughput_window[-1] - throughput_window[0]
            if time_span > 0:
                throughput = len(throughput_window) / time_span
                throughput_gauge.set(throughput)
        
    except Exception as e:
        logger.error(f"Error processing score message: {e}")


def process_decision_message(decision_data: Dict[str, Any]):
    """Process decision message for monitoring."""
    try:
        action = decision_data.get('action', 'unknown')
        decision_time = decision_data.get('decision_time_ms', 0)
        
        # Update Prometheus metrics
        decision_counter.labels(action=action).inc()
        
        if decision_time > 0:
            decision_latency.observe(decision_time / 1000.0)
        
        # Store metrics
        store_metric('decision_latency_ms', decision_time, {
            'action': action,
            'event_id': decision_data.get('event_id')
        })
        
    except Exception as e:
        logger.error(f"Error processing decision message: {e}")


def process_feature_message(feature_data: Dict[str, Any]):
    """Process feature message for drift detection."""
    try:
        # Extract numeric features
        numeric_features = {}
        for key, value in feature_data.items():
            if isinstance(value, (int, float)) and not np.isnan(value):
                numeric_features[key] = value
        
        # Update reference features
        update_reference_features(numeric_features)
        
        # Check for drift in key features
        key_features = ['amount', 'velocity_1h', 'velocity_24h', 'ip_risk', 'geo_distance_km', 'merchant_risk']
        
        for feature_name in key_features:
            if feature_name in numeric_features:
                recent_features[feature_name].append(numeric_features[feature_name])
                
                # Check drift every 100 samples
                if len(recent_features[feature_name]) >= 100:
                    psi_value = detect_feature_drift(feature_name, list(recent_features[feature_name]))
                    
                    if psi_value > 0:
                        drift_psi_gauge.labels(feature_name=feature_name).set(psi_value)
                        
                        # Store drift information if significant
                        if psi_value > 0.2:  # PSI threshold
                            now = datetime.utcnow()
                            reference_period = (now - timedelta(hours=24), now - timedelta(hours=1))
                            current_period = (now - timedelta(hours=1), now)
                            
                            store_feature_drift(feature_name, psi_value, reference_period, current_period)
                            
                            logger.warning(f"Feature drift detected: {feature_name} PSI={psi_value:.3f}")
                    
                    # Clear recent features after drift check
                    recent_features[feature_name].clear()
        
    except Exception as e:
        logger.error(f"Error processing feature message: {e}")


def calculate_calibration_metrics():
    """Calculate calibration metrics for models."""
    try:
        # This would typically use labeled data
        # For demonstration, we'll use synthetic data
        for model_name in ['xgb', 'nn', 'ensemble']:
            if len(recent_scores[model_name]) > 100:
                scores = np.array(list(recent_scores[model_name]))
                
                # Simulate true labels (in practice, these would come from actual outcomes)
                # Higher scores more likely to be fraud
                true_labels = (scores > 0.5).astype(int)
                
                brier_score = calculate_brier_score(true_labels, scores)
                calibration_brier_gauge.labels(model_name=model_name).set(brier_score)
                
                # Store calibration metric
                store_metric('calibration_brier', brier_score, {
                    'model_name': model_name,
                    'sample_size': len(scores)
                })
        
    except Exception as e:
        logger.error(f"Error calculating calibration metrics: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Model Monitor Service")
    get_postgres_connection()
    get_kafka_consumer()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global kafka_consumer, postgres_conn
    if kafka_consumer:
        kafka_consumer.close()
    if postgres_conn:
        postgres_conn.close()
    logger.info("Shutting down Model Monitor Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "model-monitor-svc", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics/calibration")
async def get_calibration_metrics():
    """Get calibration metrics."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT model_name, metric_value, created_at
            FROM model_metrics 
            WHERE metric_type = 'calibration_brier'
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        results = cursor.fetchall()
        cursor.close()
        
        metrics = []
        for row in results:
            metrics.append({
                'model_name': row[0],
                'brier_score': float(row[1]),
                'timestamp': row[2].isoformat()
            })
        
        return {
            'calibration_metrics': metrics,
            'summary': {
                'total_models': len(set(m['model_name'] for m in metrics)),
                'latest_brier_scores': {
                    m['model_name']: m['brier_score'] 
                    for m in metrics[:3]  # Latest 3 entries
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting calibration metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving calibration metrics")


@app.get("/metrics/drift")
async def get_drift_metrics():
    """Get feature drift metrics."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT feature_name, psi_value, created_at
            FROM feature_drift 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        results = cursor.fetchall()
        cursor.close()
        
        drift_metrics = []
        for row in results:
            drift_metrics.append({
                'feature_name': row[0],
                'psi_value': float(row[1]),
                'timestamp': row[2].isoformat(),
                'drift_level': 'high' if row[1] > 0.2 else 'medium' if row[1] > 0.1 else 'low'
            })
        
        return {
            'drift_metrics': drift_metrics,
            'summary': {
                'total_features_monitored': len(set(m['feature_name'] for m in drift_metrics)),
                'high_drift_features': [m['feature_name'] for m in drift_metrics if m['drift_level'] == 'high'],
                'latest_psi_values': {
                    m['feature_name']: m['psi_value'] 
                    for m in drift_metrics[:5]  # Latest 5 entries
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting drift metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving drift metrics")


@app.get("/metrics/latency")
async def get_latency_metrics():
    """Get latency metrics."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT metric_value, created_at
            FROM model_metrics 
            WHERE metric_type IN ('latency_ms', 'decision_latency_ms')
            AND created_at >= NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 1000
        """)
        
        results = cursor.fetchall()
        cursor.close()
        
        latencies = [float(row[0]) for row in results]
        
        if latencies:
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)
            
            p50 = latencies_sorted[int(n * 0.5)]
            p95 = latencies_sorted[int(n * 0.95)]
            p99 = latencies_sorted[int(n * 0.99)]
            
            return {
                'latency_metrics': {
                    'p50_ms': p50,
                    'p95_ms': p95,
                    'p99_ms': p99,
                    'mean_ms': np.mean(latencies),
                    'max_ms': max(latencies),
                    'min_ms': min(latencies),
                    'sample_count': len(latencies)
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            return {
                'latency_metrics': {
                    'p50_ms': 0,
                    'p95_ms': 0,
                    'p99_ms': 0,
                    'mean_ms': 0,
                    'max_ms': 0,
                    'min_ms': 0,
                    'sample_count': 0
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error getting latency metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving latency metrics")


@app.get("/metrics")
async def get_prometheus_metrics():
    """Get Prometheus metrics."""
    return generate_latest()


def consume_messages():
    """Consume messages from Kafka for monitoring."""
    consumer = get_kafka_consumer()
    logger.info("Starting to consume messages for monitoring...")
    
    last_calibration_check = time.time()
    
    for message in consumer:
        try:
            topic = message.topic
            data = message.value
            
            if topic == "alerts.scores.v1":
                process_score_message(data)
            elif topic == "alerts.decisions.v1":
                process_decision_message(data)
            elif topic == "features.online.v1":
                process_feature_message(data)
            
            # Calculate calibration metrics every 5 minutes
            if time.time() - last_calibration_check > 300:
                calculate_calibration_metrics()
                last_calibration_check = time.time()
                
        except Exception as e:
            logger.error(f"Error consuming message: {e}")


if __name__ == "__main__":
    import uvicorn
    import threading
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=consume_messages, daemon=True)
    consumer_thread.start()
    
    # Start FastAPI server
    port = int(os.getenv("MODEL_MONITOR_SVC_PORT", 8007))
    uvicorn.run(app, host="0.0.0.0", port=port)
