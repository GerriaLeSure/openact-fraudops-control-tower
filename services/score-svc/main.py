"""Score service for ensemble fraud scoring."""

import json
import logging
import os
import pickle
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import shap
import torch
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer, KafkaProducer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from shared.schemas.features import FeatureVector
from shared.schemas.scores import ScoreOutput, ModelScores, FeatureExplanation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Score Service",
    description="Service for ensemble fraud scoring",
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

# Global variables for models
xgb_model = None
nn_model = None
nn_scaler = None
feature_names = None
model_version = None
kafka_consumer = None
kafka_producer = None


class FraudNN(torch.nn.Module):
    """Neural network for fraud detection."""
    
    def __init__(self, input_size: int, hidden_sizes: List[int] = [64, 32, 16]):
        super(FraudNN, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                torch.nn.Linear(prev_size, hidden_size),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.2)
            ])
            prev_size = hidden_size
        
        # Output layer
        layers.append(torch.nn.Linear(prev_size, 1))
        layers.append(torch.nn.Sigmoid())
        
        self.network = torch.nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


def load_models():
    """Load trained models."""
    global xgb_model, nn_model, nn_scaler, feature_names, model_version
    
    try:
        # Load XGBoost model
        xgb_path = "models/fraud_xgb/"
        if os.path.exists(xgb_path):
            # Find latest model file
            model_files = [f for f in os.listdir(xgb_path) if f.endswith('.pkl')]
            if model_files:
                latest_model = sorted(model_files)[-1]
                with open(os.path.join(xgb_path, latest_model), 'rb') as f:
                    xgb_model = pickle.load(f)
                logger.info(f"Loaded XGBoost model: {latest_model}")
        
        # Load Neural Network model
        nn_path = "models/fraud_nn/"
        if os.path.exists(nn_path):
            # Find latest model file
            model_files = [f for f in os.listdir(nn_path) if f.endswith('.pth')]
            scaler_files = [f for f in os.listdir(nn_path) if f.endswith('_scaler.pkl')]
            
            if model_files and scaler_files:
                latest_model = sorted(model_files)[-1]
                latest_scaler = sorted(scaler_files)[-1]
                
                # Load scaler
                with open(os.path.join(nn_path, latest_scaler), 'rb') as f:
                    nn_scaler = pickle.load(f)
                
                # Load model
                input_size = len(feature_names) if feature_names else 8
                nn_model = FraudNN(input_size)
                nn_model.load_state_dict(torch.load(os.path.join(nn_path, latest_model)))
                nn_model.eval()
                
                logger.info(f"Loaded Neural Network model: {latest_model}")
        
        # Load feature names
        features_file = os.path.join(xgb_path, "feature_names.json")
        if os.path.exists(features_file):
            with open(features_file, 'r') as f:
                feature_names = json.load(f)
        
        # Set model version
        model_version = f"2025_01_15_xgb_01_nn_01"
        
        logger.info("Models loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        # Create dummy models for testing
        create_dummy_models()


def create_dummy_models():
    """Create dummy models for testing when real models are not available."""
    global xgb_model, nn_model, nn_scaler, feature_names, model_version
    
    logger.info("Creating dummy models for testing...")
    
    # Dummy feature names
    feature_names = [
        'amount', 'velocity_1h', 'velocity_24h', 'velocity_7d',
        'ip_risk', 'geo_distance_km', 'merchant_risk', 'age_days'
    ]
    
    # Dummy XGBoost model
    xgb_model = XGBClassifier(n_estimators=10, random_state=42)
    dummy_X = np.random.random((100, len(feature_names)))
    dummy_y = np.random.randint(0, 2, 100)
    xgb_model.fit(dummy_X, dummy_y)
    
    # Dummy Neural Network model
    nn_model = FraudNN(len(feature_names))
    nn_scaler = StandardScaler()
    nn_scaler.fit(dummy_X)
    
    model_version = "dummy_models_v1"
    logger.info("Dummy models created")


def get_kafka_consumer() -> KafkaConsumer:
    """Get or create Kafka consumer."""
    global kafka_consumer
    if kafka_consumer is None:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        kafka_consumer = KafkaConsumer(
            "features.online.v1",
            bootstrap_servers=[bootstrap_servers],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id="score-svc",
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


def extract_features(feature_vector: FeatureVector) -> np.ndarray:
    """Extract features from feature vector."""
    features = [
        feature_vector.amount or 0,
        feature_vector.velocity_1h,
        feature_vector.velocity_24h,
        feature_vector.velocity_7d,
        feature_vector.ip_risk,
        feature_vector.geo_distance_km,
        feature_vector.merchant_risk,
        feature_vector.age_days
    ]
    return np.array(features).reshape(1, -1)


def compute_rule_score(feature_vector: FeatureVector) -> float:
    """Compute rule-based score."""
    score = 0.0
    
    # High amount rule
    if feature_vector.amount and feature_vector.amount > 10000:
        score += 0.3
    
    # High velocity rules
    if feature_vector.velocity_1h > 10:
        score += 0.4
    elif feature_vector.velocity_1h > 5:
        score += 0.2
    
    # IP risk rule
    if feature_vector.ip_risk > 0.8:
        score += 0.3
    elif feature_vector.ip_risk > 0.5:
        score += 0.1
    
    # Geo distance rule
    if feature_vector.geo_distance_km > 1000:
        score += 0.2
    elif feature_vector.geo_distance_km > 500:
        score += 0.1
    
    # Merchant risk rule
    if feature_vector.merchant_risk > 0.7:
        score += 0.2
    
    return min(score, 1.0)


def compute_xgb_score(features: np.ndarray) -> float:
    """Compute XGBoost score."""
    if xgb_model is None:
        return 0.1  # Default score
    
    try:
        proba = xgb_model.predict_proba(features)[0, 1]
        return float(proba)
    except Exception as e:
        logger.error(f"Error computing XGBoost score: {e}")
        return 0.1


def compute_nn_score(features: np.ndarray) -> float:
    """Compute Neural Network score."""
    if nn_model is None or nn_scaler is None:
        return 0.1  # Default score
    
    try:
        # Scale features
        features_scaled = nn_scaler.transform(features)
        
        # Convert to tensor
        features_tensor = torch.FloatTensor(features_scaled)
        
        # Predict
        with torch.no_grad():
            proba = nn_model(features_tensor).numpy()[0, 0]
        
        return float(proba)
    except Exception as e:
        logger.error(f"Error computing Neural Network score: {e}")
        return 0.1


def compute_shap_explanation(features: np.ndarray) -> List[List]:
    """Compute SHAP explanation for top features."""
    try:
        if xgb_model is None:
            return [["amount", 0.1], ["velocity_1h", 0.1]]
        
        # Create SHAP explainer
        explainer = shap.TreeExplainer(xgb_model)
        shap_values = explainer.shap_values(features)
        
        # Get top features
        feature_importance = np.abs(shap_values[0])
        top_indices = np.argsort(feature_importance)[-5:][::-1]
        
        top_features = []
        for idx in top_indices:
            if idx < len(feature_names):
                feature_name = feature_names[idx]
                importance = float(feature_importance[idx])
                top_features.append([feature_name, importance])
        
        return top_features
    except Exception as e:
        logger.error(f"Error computing SHAP explanation: {e}")
        return [["amount", 0.1], ["velocity_1h", 0.1]]


def compute_ensemble_score(xgb_score: float, nn_score: float, rules_score: float) -> float:
    """Compute weighted ensemble score."""
    # Learned weights (in production, these would be optimized)
    weights = {
        'xgb': 0.5,
        'nn': 0.3,
        'rules': 0.2
    }
    
    ensemble_score = (
        weights['xgb'] * xgb_score +
        weights['nn'] * nn_score +
        weights['rules'] * rules_score
    )
    
    return ensemble_score


def calibrate_score(ensemble_score: float) -> float:
    """Apply Platt calibration to ensemble score."""
    # Simplified calibration (in production, use proper calibration)
    # Sigmoid function for calibration
    calibrated = 1 / (1 + np.exp(-5 * (ensemble_score - 0.5)))
    return calibrated


def score_feature_vector(feature_vector: FeatureVector) -> ScoreOutput:
    """Score a feature vector using ensemble models."""
    start_time = time.time()
    
    # Extract features
    features = extract_features(feature_vector)
    
    # Compute individual scores
    xgb_score = compute_xgb_score(features)
    nn_score = compute_nn_score(features)
    rules_score = compute_rule_score(feature_vector)
    
    # Compute ensemble score
    ensemble_score = compute_ensemble_score(xgb_score, nn_score, rules_score)
    
    # Calibrate score
    calibrated_score = calibrate_score(ensemble_score)
    
    # Compute explanation
    top_features = compute_shap_explanation(features)
    
    # Create scores object
    scores = ModelScores(
        xgb=xgb_score,
        nn=nn_score,
        rules=rules_score,
        ensemble=ensemble_score,
        calibrated=calibrated_score
    )
    
    # Create explanation object
    explain = FeatureExplanation(
        top_features=top_features,
        feature_importance={}
    )
    
    # Compute processing time
    computation_time = (time.time() - start_time) * 1000
    
    # Create score output
    score_output = ScoreOutput(
        event_id=feature_vector.event_id,
        scores=scores,
        explain=explain,
        model_version=model_version,
        computation_time_ms=computation_time
    )
    
    return score_output


def process_feature_vector(feature_data: Dict[str, Any]):
    """Process a feature vector and publish scores."""
    try:
        # Parse feature vector
        feature_vector = FeatureVector(**feature_data)
        
        # Score the feature vector
        score_output = score_feature_vector(feature_vector)
        
        # Convert to dict for Kafka
        score_dict = score_output.dict()
        score_dict["event_id"] = str(score_dict["event_id"])
        
        # Publish to Kafka
        producer = get_kafka_producer()
        producer.send(
            "alerts.scores.v1",
            key=feature_vector.entity_id,
            value=score_dict
        )
        
        logger.info(f"Scores generated for event: {feature_vector.event_id}")
        
    except Exception as e:
        logger.error(f"Error processing feature vector: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Score Service")
    load_models()
    get_kafka_consumer()
    get_kafka_producer()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global kafka_consumer, kafka_producer
    if kafka_consumer:
        kafka_consumer.close()
    if kafka_producer:
        kafka_producer.close()
    logger.info("Shutting down Score Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "score-svc", 
        "timestamp": datetime.utcnow().isoformat(),
        "models_loaded": xgb_model is not None and nn_model is not None
    }


@app.post("/score")
async def score_sync(feature_data: Dict[str, Any]):
    """Score a feature vector synchronously for testing."""
    try:
        # Parse feature vector
        feature_vector = FeatureVector(**feature_data)
        
        # Score the feature vector
        score_output = score_feature_vector(feature_vector)
        
        # Convert to dict for response
        score_dict = score_output.dict()
        score_dict["event_id"] = str(score_dict["event_id"])
        
        return score_dict
        
    except Exception as e:
        logger.error(f"Error scoring feature vector: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error scoring feature vector"
        )


def consume_features():
    """Consume feature vectors from Kafka and score them."""
    consumer = get_kafka_consumer()
    logger.info("Starting to consume feature vectors...")
    
    for message in consumer:
        try:
            feature_data = message.value
            process_feature_vector(feature_data)
        except Exception as e:
            logger.error(f"Error consuming message: {e}")


if __name__ == "__main__":
    import uvicorn
    import threading
    
    # Start consumer in background thread
    consumer_thread = threading.Thread(target=consume_features, daemon=True)
    consumer_thread.start()
    
    # Start FastAPI server
    port = int(os.getenv("SCORE_SVC_PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
