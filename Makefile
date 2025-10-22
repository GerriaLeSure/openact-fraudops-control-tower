.PHONY: up down test logs clean build

# Docker Compose commands
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

# Testing
test:
	python test_services.py

# Clean up
clean:
	docker compose down -v
	docker system prune -f

# Build only
build:
	docker compose build

# Development helpers
dev-score:
	cd services/score-svc && uvicorn app.main:app --reload --port 8002

dev-decision:
	cd services/decision-svc && uvicorn app.main:app --reload --port 8003

dev-case:
	cd services/case-svc && uvicorn app.main:app --reload --port 8004

dev-gateway:
	cd services/gateway && uvicorn app.main:app --reload --port 8001

# Quick smoke test
smoke-test:
	@echo "🧪 Running smoke test..."
	@echo "1. Getting auth token..."
	@curl -s -X POST http://localhost:8001/auth/login -H "content-type: application/json" -d '{"username":"sup:gerria","password":"x"}' | jq -r .access_token > token.txt
	@echo "2. Testing score service..."
	@curl -s -X POST http://localhost:8001/score -H "authorization: bearer $$(cat token.txt)" -H "content-type: application/json" -d '{"event_id":"e1","entity_id":"acct_7","ts":"2025-10-21T21:10:11Z","amount":1200.0,"channel":"web","velocity_1h":9,"ip_risk":0.82,"geo_distance_km":500.0,"merchant_risk":0.25,"age_days":120,"device_fingerprint":"abc","features_version":"v1"}' | jq .
	@echo "✅ Smoke test completed!"
	@rm -f token.txt

# Windows PowerShell commands
setup-windows:
	powershell -ExecutionPolicy Bypass -File setup.ps1

smoke-test-windows:
	powershell -ExecutionPolicy Bypass -File smoke_test.ps1
