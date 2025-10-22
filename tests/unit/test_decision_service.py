"""
Unit tests for the decision service
"""
import pytest
from services.decision_svc.app.policy import decide
from services.decision_svc.app.schemas import ScoreIn, DecisionOut
from services.decision_svc.app.config import settings

class TestDecisionPolicy:
    def test_allow_decision(self):
        payload = {
            "scores": {"calibrated": 0.3},
            "features": {"velocity_1h": 3, "ip_risk": 0.4},
            "channel": "mobile"
        }
        action, reasons = decide(payload)
        assert action == "allow"
        assert len(reasons) == 0

    def test_hold_decision_high_velocity(self):
        payload = {
            "scores": {"calibrated": 0.5},
            "features": {"velocity_1h": 10, "ip_risk": 0.4},
            "channel": "web"
        }
        action, reasons = decide(payload)
        assert action == "hold"
        assert "velocity_high" in reasons

    def test_hold_decision_threshold(self):
        payload = {
            "scores": {"calibrated": 0.75},
            "features": {"velocity_1h": 3, "ip_risk": 0.4},
            "channel": "web"
        }
        action, reasons = decide(payload)
        assert action == "hold"
        assert "untrusted_channel" in reasons

    def test_block_decision_threshold(self):
        payload = {
            "scores": {"calibrated": 0.95},
            "features": {"velocity_1h": 3, "ip_risk": 0.4},
            "channel": "web"
        }
        action, reasons = decide(payload)
        assert action == "block"
        assert "untrusted_channel" in reasons

    def test_block_decision_ip_proxy(self):
        payload = {
            "scores": {"calibrated": 0.85},
            "features": {"velocity_1h": 3, "ip_risk": 0.9},
            "channel": "web"
        }
        action, reasons = decide(payload)
        assert action == "block"
        assert "ip_proxy_match" in reasons

    def test_trusted_channel(self):
        payload = {
            "scores": {"calibrated": 0.5},
            "features": {"velocity_1h": 3, "ip_risk": 0.4},
            "channel": "mobile"
        }
        action, reasons = decide(payload)
        assert action == "allow"
        assert "untrusted_channel" not in reasons

class TestScoreInSchema:
    def test_valid_score_input(self):
        score_input = ScoreIn(
            event_id="test_123",
            entity_id="acct_456",
            channel="web",
            scores={"calibrated": 0.7},
            features={"velocity_1h": 5, "ip_risk": 0.6}
        )
        assert score_input.event_id == "test_123"
        assert score_input.scores["calibrated"] == 0.7
        assert score_input.features["velocity_1h"] == 5

    def test_score_input_defaults(self):
        score_input = ScoreIn(
            event_id="test_123",
            entity_id="acct_456",
            channel="web",
            scores={"calibrated": 0.7}
        )
        assert score_input.features == {}

class TestDecisionOutSchema:
    def test_valid_decision_output(self):
        decision_output = DecisionOut(
            event_id="test_123",
            risk=0.7,
            action="hold",
            reasons=["velocity_high", "untrusted_channel"],
            policy="v1"
        )
        assert decision_output.event_id == "test_123"
        assert decision_output.risk == 0.7
        assert decision_output.action == "hold"
        assert len(decision_output.reasons) == 2
        assert decision_output.policy == "v1"

    def test_decision_output_defaults(self):
        decision_output = DecisionOut(
            event_id="test_123",
            risk=0.5,
            action="allow",
            reasons=[]
        )
        assert decision_output.policy == "v1"

class TestDecisionConfig:
    def test_config_values(self):
        assert settings.BLOCK_THRESHOLD == 0.90
        assert settings.HOLD_THRESHOLD == 0.70
        assert settings.WATCHLIST_ENABLED is True
        assert "mobile" in settings.TRUSTED_CHANNELS

class TestDecisionIntegration:
    def test_end_to_end_decision_flow(self):
        # Test a complete decision flow
        test_cases = [
            {
                "input": {
                    "scores": {"calibrated": 0.2},
                    "features": {"velocity_1h": 2, "ip_risk": 0.3},
                    "channel": "mobile"
                },
                "expected_action": "allow",
                "expected_reasons": []
            },
            {
                "input": {
                    "scores": {"calibrated": 0.6},
                    "features": {"velocity_1h": 9, "ip_risk": 0.5},
                    "channel": "web"
                },
                "expected_action": "hold",
                "expected_reasons": ["velocity_high", "untrusted_channel"]
            },
            {
                "input": {
                    "scores": {"calibrated": 0.95},
                    "features": {"velocity_1h": 2, "ip_risk": 0.3},
                    "channel": "web"
                },
                "expected_action": "block",
                "expected_reasons": ["untrusted_channel"]
            }
        ]
        
        for case in test_cases:
            action, reasons = decide(case["input"])
            assert action == case["expected_action"]
            assert set(reasons) == set(case["expected_reasons"])
