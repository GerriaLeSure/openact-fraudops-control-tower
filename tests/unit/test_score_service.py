"""
Unit tests for the score service
"""
import pytest
from unittest.mock import Mock, patch
from services.score_svc.app.models import XGBModel, NNModel, Ensemble, rules_score, shap_like
from services.score_svc.app.schemas import FeatureVector, ScoreResponse

class TestXGBModel:
    def test_predict_proba(self):
        model = XGBModel()
        feats = {"ip_risk": 0.8, "velocity_1h": 5}
        result = model.predict_proba(feats)
        assert 0 <= result <= 1
        assert result > 0.1  # Should be above baseline

    def test_version(self):
        model = XGBModel()
        assert model.version == "xgb_2025_10_01"

class TestNNModel:
    def test_predict_proba(self):
        model = NNModel()
        feats = {"merchant_risk": 0.3, "geo_distance_km": 100}
        result = model.predict_proba(feats)
        assert 0 <= result <= 1
        assert result > 0.05  # Should be above baseline

    def test_version(self):
        model = NNModel()
        assert model.version == "nn_2025_10_01"

class TestRulesScore:
    def test_velocity_high(self):
        feats = {"velocity_1h": 10, "ip_risk": 0.5, "amount": 1000}
        result = rules_score(feats)
        assert result >= 0.35  # Should trigger velocity rule

    def test_ip_risk_high(self):
        feats = {"velocity_1h": 3, "ip_risk": 0.9, "amount": 1000}
        result = rules_score(feats)
        assert result >= 0.35  # Should trigger IP risk rule

    def test_amount_high(self):
        feats = {"velocity_1h": 3, "ip_risk": 0.5, "amount": 3000}
        result = rules_score(feats)
        assert result >= 0.2  # Should trigger amount rule

    def test_no_triggers(self):
        feats = {"velocity_1h": 3, "ip_risk": 0.5, "amount": 1000}
        result = rules_score(feats)
        assert result == 0.0  # No rules should trigger

class TestEnsemble:
    def test_ensemble_creation(self):
        ensemble = Ensemble(0.5, 0.3, 0.2)
        assert ensemble.w == (0.5, 0.3, 0.2)
        assert ensemble.xgb is not None
        assert ensemble.nn is not None

    def test_version_property(self):
        ensemble = Ensemble()
        version = ensemble.version
        assert "xgb_2025_10_01" in version
        assert "nn_2025_10_01" in version

    def test_score_method(self):
        ensemble = Ensemble(0.5, 0.3, 0.2)
        feats = {
            "velocity_1h": 5,
            "ip_risk": 0.6,
            "merchant_risk": 0.3,
            "geo_distance_km": 200,
            "amount": 1500
        }
        result = ensemble.score(feats)
        
        # Check all expected keys are present
        expected_keys = ["xgb", "nn", "rules", "ensemble", "calibrated", "explain"]
        for key in expected_keys:
            assert key in result
        
        # Check all scores are between 0 and 1
        for key in ["xgb", "nn", "rules", "ensemble", "calibrated"]:
            assert 0 <= result[key] <= 1
        
        # Check explain is a list of tuples
        assert isinstance(result["explain"], list)
        assert len(result["explain"]) <= 5
        for item in result["explain"]:
            assert isinstance(item, tuple)
            assert len(item) == 2

class TestShapLike:
    def test_shap_like_output(self):
        feats = {
            "velocity_1h": 8,
            "ip_risk": 0.7,
            "merchant_risk": 0.4
        }
        result = shap_like(feats)
        
        assert isinstance(result, list)
        assert len(result) <= 5
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], str)  # feature name
            assert isinstance(item[1], float)  # importance

class TestFeatureVector:
    def test_feature_vector_validation(self):
        # Valid feature vector
        fv = FeatureVector(
            event_id="test_123",
            entity_id="acct_456",
            ts="2025-10-21T21:10:11Z",
            amount=1200.0,
            channel="web",
            velocity_1h=5,
            ip_risk=0.6,
            geo_distance_km=150.0,
            merchant_risk=0.3,
            age_days=90,
            device_fingerprint="abc123"
        )
        assert fv.event_id == "test_123"
        assert fv.amount == 1200.0
        assert fv.features_version == "v1"  # default value

    def test_feature_vector_invalid_data(self):
        with pytest.raises(ValueError):
            FeatureVector(
                event_id="test_123",
                entity_id="acct_456",
                ts="invalid_timestamp",
                amount="not_a_number",  # Should be float
                channel="web",
                velocity_1h=5,
                ip_risk=0.6,
                geo_distance_km=150.0,
                merchant_risk=0.3,
                age_days=90,
                device_fingerprint="abc123"
            )

class TestScoreResponse:
    def test_score_response_validation(self):
        response = ScoreResponse(
            event_id="test_123",
            scores={
                "xgb": 0.7,
                "nn": 0.6,
                "rules": 0.5,
                "ensemble": 0.6,
                "calibrated": 0.8
            },
            explain=[("velocity_1h", 0.8), ("ip_risk", 0.6)],
            model_version="xgb_2025_10_01_nn_2025_10_01"
        )
        assert response.event_id == "test_123"
        assert len(response.scores) == 5
        assert len(response.explain) == 2
        assert response.model_version is not None
