# 🚀 OpenAct FraudOps - Quick Start Guide

## Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Git

## 🏃‍♂️ Quick Start (5 minutes)

### 1. Clone and Setup

**Linux/macOS:**
```bash
git clone https://github.com/<youruser>/openact-fraudops.git
cd openact-fraudops
cp .env.example .env  # Edit if needed
```

**Windows:**
```powershell
git clone https://github.com/<youruser>/openact-fraudops.git
cd openact-fraudops
# .env will be created automatically by setup.ps1
```

### 2. Start Everything

**Linux/macOS:**
```bash
# Option 1: Using Makefile
make up

# Option 2: Direct Docker Compose
docker compose up --build -d
```

**Windows:**
```powershell
# Automated setup (recommended)
.\setup.ps1

# OR manual setup
docker compose up --build -d
```

### 3. Test the System

**Linux/macOS:**
```bash
# Run comprehensive tests
python test_services.py

# Or quick smoke test
make smoke-test
```

**Windows:**
```powershell
# Comprehensive test
python test_services.py

# Or quick smoke test
.\smoke_test.ps1
```

### 4. Access the Platform
- **Analyst UI**: http://localhost:5173
- **API Gateway**: http://localhost:8001
- **Prometheus Metrics**: http://localhost:8005/metrics

## 🔧 Development Commands

```bash
# Start/Stop
make up          # Start all services
make down        # Stop all services
make logs        # View logs
make clean       # Clean up volumes

# Individual services
make dev-score      # Score service on :8002
make dev-decision   # Decision service on :8003
make dev-case       # Case service on :8004
make dev-gateway    # Gateway on :8001

# Testing
make test        # Run test suite
make smoke-test  # Quick end-to-end test
```

## 🧪 Manual Testing

### 1. Get Authentication Token
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"sup:gerria","password":"x"}' \
  | jq -r .access_token
```

### 2. Score a Transaction
```bash
curl -X POST http://localhost:8001/score \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id":"e1",
    "entity_id":"acct_7",
    "amount":1200.0,
    "channel":"web",
    "velocity_1h":9,
    "ip_risk":0.82,
    "geo_distance_km":500.0,
    "merchant_risk":0.25,
    "age_days":120,
    "device_fingerprint":"abc"
  }'
```

### 3. Make a Decision
```bash
curl -X POST http://localhost:8001/decide \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id":"e1",
    "entity_id":"acct_7",
    "channel":"web",
    "scores":{"calibrated":0.86},
    "features":{"velocity_1h":9,"ip_risk":0.82}
  }'
```

## 🏗️ Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   React UI  │───▶│   Gateway   │───▶│   Services  │
│  (Port 5173)│    │ (Port 8001) │    │ (8002-8005) │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │  Databases  │
                   │ Kafka/Redis │
                   │ Postgres/Mongo │
                   └─────────────┘
```

## 🔐 Authentication Roles

- **analyst**: Basic access to score/decide/cases
- **supervisor**: All analyst + model monitoring
- **admin**: Full system access

Login with:
- `analyst:username` → analyst role
- `sup:username` → supervisor role  
- `admin:username` → admin role

## 📊 Monitoring

- **Prometheus Metrics**: http://localhost:8005/metrics
- **Model Drift**: PSI calculations for feature drift
- **Calibration**: Brier score tracking
- **Latency**: Request timing histograms

## 🐛 Troubleshooting

### Services Not Starting
```bash
# Check logs
make logs

# Restart specific service
docker compose restart score-svc
```

### Port Conflicts
```bash
# Check what's using ports
netstat -tulpn | grep :8001

# Stop conflicting services
docker compose down
```

### Database Issues
```bash
# Reset databases
make clean
make up
```

## 🚀 Next Steps

1. **Customize Models**: Update `services/score-svc/app/models.py`
2. **Adjust Policies**: Modify `services/decision-svc/app/policy.py`
3. **Add Features**: Extend the UI in `ui/web/src/`
4. **Deploy**: Use the Docker images in production

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Data Contracts](docs/DATA_CONTRACTS.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
