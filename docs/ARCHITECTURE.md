# Architecture Documentation

## System Overview

The OpenAct FraudOps Control Tower is a comprehensive fraud detection and investigation platform built with a microservices architecture. The system provides real-time fraud scoring, decision making, case management, and analytics capabilities.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  React UI (Analyst Workbench)  │  External APIs  │  Mobile App │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  JWT Authentication  │  Rate Limiting  │  CORS  │  Load Balancer │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Microservices Layer                         │
├─────────────────────────────────────────────────────────────────┤
│ Score Service │ Decision Service │ Case Service │ Analytics Svc │
│ Model Monitor │ Audit Service    │ Summary Svc  │ Feature Svc   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                │
├─────────────────────────────────────────────────────────────────┤
│ Kafka/Redis │ PostgreSQL │ MongoDB │ MinIO/S3 │ Prometheus     │
└─────────────────────────────────────────────────────────────────┘
```

## Service Architecture

### Core Services

#### 1. Gateway Service (Port 8001)
- **Purpose**: API gateway with authentication, authorization, and rate limiting
- **Technology**: FastAPI, JWT, SlowAPI
- **Responsibilities**:
  - JWT token validation
  - Role-based access control (analyst, supervisor, admin)
  - Rate limiting and CORS
  - Request routing to backend services
  - Security middleware

#### 2. Score Service (Port 8002)
- **Purpose**: Ensemble ML model for fraud scoring
- **Technology**: FastAPI, XGBoost, PyTorch, SHAP
- **Responsibilities**:
  - Feature vector processing
  - Ensemble model scoring (XGBoost + Neural Network + Rules)
  - Probability calibration
  - SHAP explanations
  - Model versioning

#### 3. Decision Service (Port 8003)
- **Purpose**: Business rule engine for fraud decisions
- **Technology**: FastAPI, PostgreSQL
- **Responsibilities**:
  - Policy evaluation
  - Threshold management
  - Business rule execution
  - Decision reasoning
  - Policy versioning

#### 4. Case Service (Port 8004)
- **Purpose**: Fraud investigation case management
- **Technology**: FastAPI, MongoDB
- **Responsibilities**:
  - Case creation and management
  - Investigator assignment
  - Notes and actions tracking
  - Case status management
  - Evidence collection

#### 5. Model Monitor Service (Port 8005)
- **Purpose**: Model performance monitoring and drift detection
- **Technology**: FastAPI, Prometheus, MLflow
- **Responsibilities**:
  - Model performance metrics
  - Drift detection (PSI)
  - Calibration monitoring (Brier score)
  - Latency tracking
  - MLflow integration

#### 6. Analytics Service (Port 8006)
- **Purpose**: Business intelligence and reporting
- **Technology**: FastAPI, MongoDB
- **Responsibilities**:
  - KPI computation
  - Time series analytics
  - Distribution analysis
  - Executive reporting
  - Dashboard data

### Supporting Services

#### Feature Service
- **Purpose**: Feature engineering and enrichment
- **Technology**: FastAPI, Redis, scikit-learn
- **Responsibilities**:
  - Real-time feature computation
  - Redis lookups
  - Geographic calculations
  - Feature versioning

#### Audit Service
- **Purpose**: Immutable audit logging
- **Technology**: FastAPI, MinIO/S3, PostgreSQL
- **Responsibilities**:
  - Decision audit trails
  - Evidence storage
  - Compliance reporting
  - Data integrity

#### Summary Service
- **Purpose**: AI-powered case summarization
- **Technology**: FastAPI, OpenAI/Azure AI
- **Responsibilities**:
  - Case summarization
  - PII redaction
  - Multi-provider support
  - Content generation

## Data Flow

### 1. Transaction Processing Flow

```
Transaction → Ingest Service → Feature Service → Score Service → Decision Service → Case Service
     ↓              ↓              ↓              ↓              ↓              ↓
   Kafka        Feature        Ensemble        Business        Case          Audit
   Topic        Enrichment     Scoring         Rules          Creation      Logging
```

### 2. Investigation Flow

```
Case Creation → Assignment → Investigation → Action → Resolution → Audit
     ↓              ↓            ↓           ↓         ↓          ↓
   MongoDB      User Mgmt    Notes/Actions  Decision  Status    MinIO
```

### 3. Monitoring Flow

```
Model Output → Monitor Service → Prometheus → Grafana → Alerts
     ↓              ↓              ↓          ↓         ↓
   Metrics      Drift Detection   Storage   Dashboard  Notifications
```

## Data Architecture

### Databases

#### PostgreSQL
- **Purpose**: Relational data and policies
- **Tables**:
  - `decision_policy`: Business rules and thresholds
  - `users`: User management and roles
  - `audit_hashes`: Audit trail integrity

#### MongoDB
- **Purpose**: Document storage for cases and investigations
- **Collections**:
  - `cases`: Fraud investigation cases
  - `case_notes`: Investigator notes
  - `case_actions`: Case actions and decisions

#### Redis
- **Purpose**: Caching and session storage
- **Usage**:
  - Feature lookups
  - Session management
  - Rate limiting
  - Temporary data

#### MinIO/S3
- **Purpose**: Object storage for evidence and artifacts
- **Buckets**:
  - `fraudops-audit`: Immutable audit logs
  - `fraudops-evidence`: Case evidence files
  - `fraudops-models`: Model artifacts

### Message Queues

#### Kafka
- **Purpose**: Event streaming and decoupling
- **Topics**:
  - `events.txns.v1`: Raw transaction events
  - `events.claims.v1`: Raw claim events
  - `features.online.v1`: Enriched feature vectors
  - `alerts.scores.v1`: Model score outputs
  - `alerts.decisions.v1`: Decision outputs

## Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Stateless authentication
- **Role-Based Access**: analyst, supervisor, admin
- **Token Expiration**: Configurable (default: 2 hours)
- **Refresh Tokens**: For long-lived sessions

### Network Security
- **CORS**: Configurable origins
- **Rate Limiting**: Per-endpoint limits
- **Trusted Hosts**: Host validation
- **HTTPS**: TLS encryption in production

### Data Security
- **PII Redaction**: Automatic in summaries
- **Audit Trails**: Immutable logging
- **Data Encryption**: At rest and in transit
- **Access Logging**: All API calls logged

## Monitoring & Observability

### Metrics
- **Prometheus**: System and business metrics
- **Grafana**: Dashboards and visualization
- **Custom Metrics**: Model performance, drift, latency

### Logging
- **Structured Logging**: JSON format
- **Log Aggregation**: ELK/OpenSearch stack
- **Log Levels**: DEBUG, INFO, WARN, ERROR
- **Correlation IDs**: Request tracing

### Alerting
- **Model Drift**: PSI threshold alerts
- **Performance**: Latency and error rate alerts
- **Business**: Fraud rate and case volume alerts
- **Infrastructure**: Resource utilization alerts

## Deployment Architecture

### Container Orchestration
- **Docker**: Service containerization
- **Docker Compose**: Local development
- **Kubernetes**: Production orchestration
- **Helm**: Package management

### CI/CD Pipeline
- **GitHub Actions**: Automated testing and deployment
- **Multi-stage Builds**: Optimized container images
- **Security Scanning**: Vulnerability detection
- **Performance Testing**: Load and stress testing

### Infrastructure
- **Load Balancers**: Traffic distribution
- **Auto-scaling**: Dynamic resource allocation
- **Health Checks**: Service monitoring
- **Rolling Deployments**: Zero-downtime updates

## Scalability Considerations

### Horizontal Scaling
- **Stateless Services**: Easy horizontal scaling
- **Database Sharding**: Partition large datasets
- **Cache Distribution**: Redis clustering
- **Message Partitioning**: Kafka topic partitioning

### Performance Optimization
- **Connection Pooling**: Database connections
- **Caching Strategies**: Multi-level caching
- **Async Processing**: Non-blocking operations
- **CDN Integration**: Static asset delivery

### Resilience Patterns
- **Circuit Breakers**: Fault isolation
- **Retry Mechanisms**: Transient failure handling
- **Dead Letter Queues**: Failed message handling
- **Graceful Degradation**: Service fallbacks

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **Validation**: Pydantic
- **Database**: PostgreSQL, MongoDB
- **Cache**: Redis
- **Message Queue**: Kafka
- **Storage**: MinIO/S3

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context
- **HTTP Client**: Fetch API

### ML/AI
- **ML Framework**: XGBoost, PyTorch
- **Model Tracking**: MLflow
- **Experiment Tracking**: Weights & Biases
- **Explainability**: SHAP
- **Monitoring**: Custom drift detection

### DevOps
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana
- **Logging**: ELK Stack
- **Security**: Trivy, CodeQL

## Future Enhancements

### Planned Features
- **Graph Analytics**: Fraud ring detection
- **Real-time Streaming**: Apache Flink integration
- **Advanced ML**: Deep learning models
- **Multi-tenancy**: SaaS capabilities
- **API Versioning**: Backward compatibility

### Scalability Roadmap
- **Event Sourcing**: CQRS pattern
- **Microservice Mesh**: Service mesh integration
- **Global Distribution**: Multi-region deployment
- **Edge Computing**: Edge fraud detection
- **Quantum Security**: Post-quantum cryptography