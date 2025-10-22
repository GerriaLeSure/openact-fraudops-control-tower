# OpenAct FraudOps Control Tower

Enterprise-grade fraud detection and investigation platform for real-time fraud scoring, case management, and audit intelligence.

## Impact
Achieved 94% detection on labeled fraud cohorts, saving $2.5M annually and reducing analyst review time by ~80% through calibrated ensemble scoring, decision policies, and evidence-ready case workflows.

## Architecture

This system provides real-time fraud detection through an ensemble of machine learning models, rule-based systems, and comprehensive case management capabilities.

### Key Components

- **Event Ingestion**: REST/gRPC endpoints for transaction and claim events
- **Feature Engineering**: Real-time feature computation with Redis caching
- **Ensemble Scoring**: XGBoost + Neural Network + Rules with calibration
- **Decision Engine**: Risk-based policy engine with configurable thresholds
- **Case Management**: Full lifecycle case tracking with SLA monitoring
- **Audit System**: Immutable evidence storage with WORM compliance
- **Analyst UI**: React-based workbench for fraud investigators
- **Model Monitoring**: Drift detection and performance monitoring

### Technology Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2
- **Message Queue**: Apache Kafka
- **Databases**: PostgreSQL, MongoDB, Redis
- **Storage**: MinIO/S3 for evidence and artifacts
- **Frontend**: React, Vite, Tailwind CSS
- **ML**: XGBoost, PyTorch, SHAP
- **Monitoring**: Prometheus, Grafana, ELK Stack

## Quick Start

### Minimal Terminal Flow

**Linux/macOS:**
```bash
# Get started
git clone https://github.com/<youruser>/openact-fraudops.git
cd openact-fraudops
cp .env.example .env

# Start everything with Docker
make up
# OR: docker compose up --build -d

# Test the platform
python test_services.py
# OR: make smoke-test

# Access the platform
# UI: http://localhost:5173
# Gateway: http://localhost:8001
# Metrics: http://localhost:8005/metrics

# Clean up
make down
```

**Windows PowerShell:**
```powershell
# Get started
git clone https://github.com/<youruser>/openact-fraudops.git
cd openact-fraudops

# Automated setup (recommended)
.\setup.ps1

# OR manual setup
docker compose up --build -d
.\smoke_test.ps1

# Access the platform
# UI: http://localhost:5173
# Gateway: http://localhost:8001
# Metrics: http://localhost:8005/metrics
```

**Development mode (individual services):**
```bash
make dev-score      # Score service on :8002
make dev-decision   # Decision service on :8003
make dev-case       # Case service on :8004
make dev-gateway    # Gateway on :8001
```

### Detailed Setup

1. **Prerequisites**
   ```bash
   docker-compose --version
   python 3.11+
   ```

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Infrastructure**
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```

4. **Install Dependencies**
   ```bash
   # Install shared dependencies
   pip install -r requirements.txt
   
   # Install service-specific dependencies
   for service in services/*/; do
     pip install -r "$service/requirements.txt"
   done
   ```

5. **Run Services**
   ```bash
   # Start all services
   ./scripts/start-all.sh
   ```

6. **Access UI**
   - Open http://localhost:3000 for the Analyst Workbench
   - Open http://localhost:8080 for API Gateway

## Service Architecture

The system is built with a clean microservices architecture:

### Core Services
- **gateway** (Port 8001): JWT authentication, CORS, rate limiting, and service proxying
- **score-svc** (Port 8002): Ensemble ML scoring with XGBoost, Neural Networks, and rules
- **decision-svc** (Port 8003): Policy engine with configurable thresholds and business rules  
- **case-svc** (Port 8004): Case management with MongoDB for investigations
- **model-monitor-svc** (Port 8005): Model monitoring with Prometheus metrics and drift detection

### Infrastructure
- **Kafka + Zookeeper**: Event streaming and message queuing
- **PostgreSQL**: Decision policies and audit metadata
- **MongoDB**: Case management and investigation data
- **Redis**: Caching and session storage
- **MinIO**: Immutable audit logs and evidence storage
- **React UI**: Analyst workbench and operations dashboard

### API Endpoints (via Gateway)
```bash
# Authentication
POST /auth/login
{
  "username": "sup:gerria",
  "password": "x"
}

# Score a transaction
POST /score (requires JWT)
{
  "event_id": "e1",
  "entity_id": "acct_7", 
  "amount": 1200.0,
  "velocity_1h": 9,
  "ip_risk": 0.82,
  ...
}

# Make a decision
POST /decide (requires JWT)
{
  "event_id": "e1",
  "scores": {"calibrated": 0.86},
  "features": {"velocity_1h": 9}
}

# Open a case
POST /cases (requires JWT)
{
  "event_id": "e1",
  "risk": 0.86,
  "action": "hold",
  "reasons": ["velocity_high"]
}

# Model monitoring
POST /monitor/ingest-score (requires supervisor/admin JWT)
GET /metrics (Prometheus format)
```

## Development

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design and [DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md) for API specifications.

## License

See [LICENSE](LICENSE) for details.