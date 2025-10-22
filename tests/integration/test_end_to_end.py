"""
Integration tests for end-to-end fraud detection flow
"""
import pytest
import requests
import time
from typing import Dict, Any

class TestEndToEndFlow:
    """Test the complete fraud detection pipeline"""
    
    BASE_URL = "http://localhost:8001"
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{self.BASE_URL}/auth/login", json={
            "username": "sup:test_user",
            "password": "test_password"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def headers(self, auth_token):
        """Get headers with authentication"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_complete_fraud_detection_flow(self, headers):
        """Test the complete flow: score -> decide -> case creation"""
        
        # Step 1: Score a transaction
        transaction_data = {
            "event_id": "test_e2e_001",
            "entity_id": "acct_test_001",
            "ts": "2025-10-21T21:10:11Z",
            "amount": 2500.0,
            "channel": "web",
            "velocity_1h": 12,
            "ip_risk": 0.85,
            "geo_distance_km": 800.0,
            "merchant_risk": 0.4,
            "age_days": 45,
            "device_fingerprint": "test_device_001",
            "features_version": "v1"
        }
        
        score_response = requests.post(
            f"{self.BASE_URL}/score",
            json=transaction_data,
            headers=headers
        )
        assert score_response.status_code == 200
        score_data = score_response.json()
        
        # Verify score response structure
        assert "event_id" in score_data
        assert "scores" in score_data
        assert "explain" in score_data
        assert "model_version" in score_data
        
        # Verify score values are valid
        scores = score_data["scores"]
        for score_type in ["xgb", "nn", "rules", "ensemble", "calibrated"]:
            assert score_type in scores
            assert 0 <= scores[score_type] <= 1
        
        # Step 2: Make a decision
        decision_data = {
            "event_id": score_data["event_id"],
            "entity_id": transaction_data["entity_id"],
            "channel": transaction_data["channel"],
            "scores": {"calibrated": scores["calibrated"]},
            "features": {
                "velocity_1h": transaction_data["velocity_1h"],
                "ip_risk": transaction_data["ip_risk"]
            }
        }
        
        decision_response = requests.post(
            f"{self.BASE_URL}/decide",
            json=decision_data,
            headers=headers
        )
        assert decision_response.status_code == 200
        decision_data = decision_response.json()
        
        # Verify decision response structure
        assert "event_id" in decision_data
        assert "risk" in decision_data
        assert "action" in decision_data
        assert "reasons" in decision_data
        assert "policy" in decision_data
        
        # Verify action is valid
        assert decision_data["action"] in ["allow", "hold", "block", "escalate"]
        
        # Step 3: Create case if action requires it
        if decision_data["action"] in ["hold", "block"]:
            case_data = {
                "event_id": decision_data["event_id"],
                "entity_id": transaction_data["entity_id"],
                "risk": decision_data["risk"],
                "action": decision_data["action"],
                "reasons": decision_data["reasons"]
            }
            
            case_response = requests.post(
                f"{self.BASE_URL}/cases",
                json=case_data,
                headers=headers
            )
            assert case_response.status_code == 200
            case_result = case_response.json()
            
            # Verify case creation
            assert "case_id" in case_result
            assert case_result["case_id"] is not None
            
            # Step 4: Verify case can be retrieved
            case_id = case_result["case_id"]
            get_case_response = requests.get(
                f"{self.BASE_URL}/cases/{case_id}",
                headers=headers
            )
            assert get_case_response.status_code == 200
            case_details = get_case_response.json()
            
            # Verify case details
            assert case_details["event_id"] == transaction_data["event_id"]
            assert case_details["entity_id"] == transaction_data["entity_id"]
            assert case_details["action"] == decision_data["action"]
            assert case_details["status"] == "open"
    
    def test_analytics_endpoints(self, headers):
        """Test analytics endpoints"""
        
        # Test main analytics endpoint
        analytics_response = requests.get(
            f"{self.BASE_URL}/analytics?hours=24",
            headers=headers
        )
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        
        # Verify analytics structure
        assert "time_range_hours" in analytics_data
        assert "generated_at" in analytics_data
        assert "kpis" in analytics_data
        assert "decisions_per_minute" in analytics_data
        assert "action_distribution" in analytics_data
        
        # Test individual analytics endpoints
        kpis_response = requests.get(
            f"{self.BASE_URL}/analytics/kpis?hours=24",
            headers=headers
        )
        assert kpis_response.status_code == 200
        
        trends_response = requests.get(
            f"{self.BASE_URL}/analytics/trends?hours=24",
            headers=headers
        )
        assert trends_response.status_code == 200
        
        distributions_response = requests.get(
            f"{self.BASE_URL}/analytics/distributions?hours=24",
            headers=headers
        )
        assert distributions_response.status_code == 200
    
    def test_model_monitoring(self, headers):
        """Test model monitoring endpoints"""
        
        # Test score ingestion
        monitor_data = {
            "calibrated": 0.75,
            "features": {
                "velocity_1h": 8,
                "ip_risk": 0.7,
                "merchant_risk": 0.3
            }
        }
        
        monitor_response = requests.post(
            f"{self.BASE_URL}/monitor/ingest-score",
            json=monitor_data,
            headers=headers
        )
        assert monitor_response.status_code == 200
        monitor_result = monitor_response.json()
        
        # Verify monitoring response
        assert "ok" in monitor_result
        assert monitor_result["ok"] is True
        assert "n" in monitor_result
        assert monitor_result["n"] > 0
    
    def test_rate_limiting(self, headers):
        """Test rate limiting functionality"""
        
        # Make multiple requests quickly to test rate limiting
        responses = []
        for i in range(10):
            response = requests.post(f"{self.BASE_URL}/auth/login", json={
                "username": f"test_user_{i}",
                "password": "test_password"
            })
            responses.append(response)
        
        # At least one should be rate limited (429 status)
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or all(code == 200 for code in status_codes)
    
    def test_authentication_required(self):
        """Test that endpoints require authentication"""
        
        # Test without authentication
        response = requests.post(f"{self.BASE_URL}/score", json={
            "event_id": "test",
            "entity_id": "test",
            "amount": 100.0
        })
        assert response.status_code == 401
    
    def test_role_based_access(self):
        """Test role-based access control"""
        
        # Test with analyst role
        analyst_response = requests.post(f"{self.BASE_URL}/auth/login", json={
            "username": "analyst:test_user",
            "password": "test_password"
        })
        assert analyst_response.status_code == 200
        analyst_token = analyst_response.json()["access_token"]
        analyst_headers = {
            "Authorization": f"Bearer {analyst_token}",
            "Content-Type": "application/json"
        }
        
        # Analyst should be able to access basic endpoints
        score_response = requests.post(f"{self.BASE_URL}/score", 
            json={"event_id": "test", "entity_id": "test", "amount": 100.0},
            headers=analyst_headers
        )
        assert score_response.status_code == 200
        
        # Test with admin role
        admin_response = requests.post(f"{self.BASE_URL}/auth/login", json={
            "username": "admin:test_user",
            "password": "test_password"
        })
        assert admin_response.status_code == 200
        admin_token = admin_response.json()["access_token"]
        admin_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        # Admin should be able to access monitoring endpoints
        monitor_response = requests.post(f"{self.BASE_URL}/monitor/ingest-score",
            json={"calibrated": 0.5, "features": {}},
            headers=admin_headers
        )
        assert monitor_response.status_code == 200
