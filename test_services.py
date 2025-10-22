#!/usr/bin/env python3
"""
Comprehensive test script for the OpenAct FraudOps platform
"""
import requests
import json
import time
import sys

def test_gateway_auth():
    """Test JWT authentication"""
    print("🔐 Testing gateway authentication...")
    
    # Test login
    login_data = {"username": "sup:gerria", "password": "x"}
    try:
        response = requests.post("http://localhost:8001/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data["access_token"]
            role = token_data["role"]
            print(f"✅ Login successful: role={role}")
            return token
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Gateway not running on port 8001")
        return None

def test_score_service(token):
    """Test the score service through gateway"""
    print("\n🎯 Testing score service...")
    
    test_data = {
        "event_id": "e1",
        "entity_id": "acct_7", 
        "ts": "2025-10-21T21:10:11Z",
        "amount": 1200.0,
        "channel": "web",
        "velocity_1h": 9,
        "ip_risk": 0.82,
        "geo_distance_km": 500.0,
        "merchant_risk": 0.25,
        "age_days": 120,
        "device_fingerprint": "abc",
        "features_version": "v1"
    }
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        response = requests.post("http://localhost:8001/score", json=test_data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Score service working: {result}")
            return result
        else:
            print(f"❌ Score service error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Score service not accessible through gateway")
        return None

def test_decision_service(token, score_result):
    """Test the decision service through gateway"""
    print("\n⚖️ Testing decision service...")
    
    if not score_result:
        print("❌ No score result available")
        return None
    
    test_data = {
        "event_id": "e1",
        "entity_id": "acct_7",
        "channel": "web",
        "scores": {"calibrated": score_result["scores"]["calibrated"]},
        "features": {"velocity_1h": 9, "ip_risk": 0.82}
    }
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        response = requests.post("http://localhost:8001/decide", json=test_data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Decision service working: {result}")
            return result
        else:
            print(f"❌ Decision service error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Decision service not accessible through gateway")
        return None

def test_case_service(token, decision_result):
    """Test the case service through gateway"""
    print("\n📋 Testing case service...")
    
    if not decision_result:
        print("❌ No decision result available")
        return None
    
    # Only create case if action is hold or block
    if decision_result["action"] in ["hold", "block"]:
        test_data = {
            "event_id": "e1",
            "entity_id": "acct_7",
            "risk": decision_result["risk"],
            "action": decision_result["action"],
            "reasons": decision_result["reasons"]
        }
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        try:
            response = requests.post("http://localhost:8001/cases", json=test_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Case service working: {result}")
                return result
            else:
                print(f"❌ Case service error: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.ConnectionError:
            print("❌ Case service not accessible through gateway")
            return None
    else:
        print(f"ℹ️ No case needed for action: {decision_result['action']}")
        return {"action": decision_result["action"], "case_created": False}

def test_model_monitor(token, score_result):
    """Test the model monitor service"""
    print("\n📊 Testing model monitor service...")
    
    if not score_result:
        print("❌ No score result available")
        return None
    
    # Send score data to monitor
    monitor_data = {
        "calibrated": score_result["scores"]["calibrated"],
        "features": {"velocity_1h": 9, "ip_risk": 0.82, "merchant_risk": 0.25}
    }
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        response = requests.post("http://localhost:8001/monitor/ingest-score", json=monitor_data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Model monitor working: {result}")
            return result
        else:
            print(f"❌ Model monitor error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Model monitor not accessible through gateway")
        return None

def test_prometheus_metrics():
    """Test Prometheus metrics endpoint"""
    print("\n📈 Testing Prometheus metrics...")
    
    try:
        response = requests.get("http://localhost:8005/metrics")
        if response.status_code == 200:
            metrics = response.text
            if "monitor_requests_total" in metrics:
                print("✅ Prometheus metrics working")
                return True
            else:
                print("⚠️ Prometheus metrics endpoint accessible but no expected metrics found")
                return False
        else:
            print(f"❌ Prometheus metrics error: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Model monitor not running on port 8005")
        return False

def main():
    print("🧪 Testing OpenAct FraudOps Platform")
    print("=" * 60)
    
    # Test authentication
    token = test_gateway_auth()
    if not token:
        print("\n❌ Authentication failed. Make sure the gateway is running.")
        sys.exit(1)
    
    # Test end-to-end flow
    score_result = test_score_service(token)
    decision_result = test_decision_service(token, score_result)
    case_result = test_case_service(token, decision_result)
    monitor_result = test_model_monitor(token, score_result)
    
    # Test monitoring
    prometheus_ok = test_prometheus_metrics()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"Authentication: {'✅ Working' if token else '❌ Failed'}")
    print(f"Score Service: {'✅ Working' if score_result else '❌ Failed'}")
    print(f"Decision Service: {'✅ Working' if decision_result else '❌ Failed'}")
    print(f"Case Service: {'✅ Working' if case_result else '❌ Failed'}")
    print(f"Model Monitor: {'✅ Working' if monitor_result else '❌ Failed'}")
    print(f"Prometheus Metrics: {'✅ Working' if prometheus_ok else '❌ Failed'}")
    
    if all([token, score_result, decision_result, case_result, monitor_result, prometheus_ok]):
        print("\n🎉 All services are working correctly!")
        print("\n🌐 Access Points:")
        print("  Gateway: http://localhost:8001")
        print("  UI: http://localhost:5173")
        print("  Prometheus: http://localhost:8005/metrics")
        print("\n📋 Example Flow:")
        print("  1. Score transaction → Get ensemble risk score")
        print("  2. Make decision → Apply business rules")
        print("  3. Open case → Create investigation if needed")
        print("  4. Monitor metrics → Track model performance")
    else:
        print("\n⚠️ Some services need attention.")
        print("Run: docker compose up --build -d")
        print("Then: python test_services.py")

if __name__ == "__main__":
    main()