"""Unit tests for schema validation."""

import pytest
from datetime import datetime
from uuid import uuid4

from services.shared.schemas.events import TransactionEvent, ClaimEvent
from services.shared.schemas.features import FeatureVector, Geolocation
from services.shared.schemas.scores import ScoreOutput, ModelScores
from services.shared.schemas.decisions import DecisionOutput


class TestTransactionEvent:
    """Test transaction event schema validation."""
    
    def test_valid_transaction_event(self):
        """Test valid transaction event."""
        event_data = {
            "event_id": str(uuid4()),
            "entity_id": "user_123",
            "timestamp": datetime.utcnow(),
            "amount": 100.50,
            "currency": "USD",
            "channel": "web",
            "merchant_id": "merchant_456",
            "ip_address": "192.168.1.1"
        }
        
        event = TransactionEvent(**event_data)
        assert event.entity_id == "user_123"
        assert event.amount == 100.50
        assert event.currency == "USD"
        assert event.channel == "web"
    
    def test_invalid_currency(self):
        """Test invalid currency code."""
        event_data = {
            "event_id": str(uuid4()),
            "entity_id": "user_123",
            "timestamp": datetime.utcnow(),
            "amount": 100.50,
            "currency": "INVALID",
            "channel": "web"
        }
        
        with pytest.raises(ValueError):
            TransactionEvent(**event_data)
    
    def test_invalid_channel(self):
        """Test invalid channel."""
        event_data = {
            "event_id": str(uuid4()),
            "entity_id": "user_123",
            "timestamp": datetime.utcnow(),
            "amount": 100.50,
            "currency": "USD",
            "channel": "invalid_channel"
        }
        
        with pytest.raises(ValueError):
            TransactionEvent(**event_data)
    
    def test_negative_amount(self):
        """Test negative amount validation."""
        event_data = {
            "event_id": str(uuid4()),
            "entity_id": "user_123",
            "timestamp": datetime.utcnow(),
            "amount": -100.50,
            "currency": "USD",
            "channel": "web"
        }
        
        with pytest.raises(ValueError):
            TransactionEvent(**event_data)


class TestClaimEvent:
    """Test claim event schema validation."""
    
    def test_valid_claim_event(self):
        """Test valid claim event."""
        event_data = {
            "event_id": str(uuid4()),
            "entity_id": "policy_123",
            "timestamp": datetime.utcnow(),
            "claim_amount": 5000.00,
            "claim_type": "auto",
            "policy_id": "policy_456"
        }
        
        event = ClaimEvent(**event_data)
        assert event.entity_id == "policy_123"
        assert event.claim_amount == 5000.00
        assert event.claim_type == "auto"
    
    def test_invalid_claim_type(self):
        """Test invalid claim type."""
        event_data = {
            "event_id": str(uuid4()),
            "entity_id": "policy_123",
            "timestamp": datetime.utcnow(),
            "claim_amount": 5000.00,
            "claim_type": "invalid_type"
        }
        
        with pytest.raises(ValueError):
            ClaimEvent(**event_data)


class TestFeatureVector:
    """Test feature vector schema validation."""
    
    def test_valid_feature_vector(self):
        """Test valid feature vector."""
        feature_data = {
            "event_id": str(uuid4()),
            "entity_id": "user_123",
            "timestamp": datetime.utcnow(),
            "amount": 100.50,
            "currency": "USD",
            "velocity_1h": 5,
            "velocity_24h": 20,
            "velocity_7d": 100,
            "ip_risk": 0.3,
            "geo_distance_km": 50.5,
            "merchant_risk": 0.1,
            "age_days": 365,
            "features_version": "v1"
        }
        
        feature_vector = FeatureVector(**feature_data)
        assert feature_vector.velocity_1h == 5
        assert feature_vector.ip_risk == 0.3
        assert feature_vector.geo_distance_km == 50.5
    
    def test_risk_score_bounds(self):
        """Test risk score bounds validation."""
        feature_data = {
            "event_id": str(uuid4()),
            "entity_id": "user_123",
            "timestamp": datetime.utcnow(),
            "features_version": "v1",
            "ip_risk": 1.5  # Invalid: > 1
        }
        
        with pytest.raises(ValueError):
            FeatureVector(**feature_data)


class TestModelScores:
    """Test model scores schema validation."""
    
    def test_valid_model_scores(self):
        """Test valid model scores."""
        scores_data = {
            "xgb": 0.8,
            "nn": 0.7,
            "rules": 0.3,
            "ensemble": 0.75,
            "calibrated": 0.78
        }
        
        scores = ModelScores(**scores_data)
        assert scores.xgb == 0.8
        assert scores.calibrated == 0.78
    
    def test_score_bounds(self):
        """Test score bounds validation."""
        scores_data = {
            "xgb": 1.5,  # Invalid: > 1
            "nn": 0.7,
            "rules": 0.3,
            "ensemble": 0.75,
            "calibrated": 0.78
        }
        
        with pytest.raises(ValueError):
            ModelScores(**scores_data)


class TestDecisionOutput:
    """Test decision output schema validation."""
    
    def test_valid_decision_output(self):
        """Test valid decision output."""
        decision_data = {
            "event_id": str(uuid4()),
            "risk": 0.8,
            "action": "block",
            "policy": "v1.0",
            "reasons": ["high_risk_score", "velocity_anomaly"]
        }
        
        decision = DecisionOutput(**decision_data)
        assert decision.risk == 0.8
        assert decision.action == "block"
        assert len(decision.reasons) == 2
    
    def test_invalid_action(self):
        """Test invalid action."""
        decision_data = {
            "event_id": str(uuid4()),
            "risk": 0.8,
            "action": "invalid_action",
            "policy": "v1.0",
            "reasons": ["high_risk_score"]
        }
        
        with pytest.raises(ValueError):
            DecisionOutput(**decision_data)
