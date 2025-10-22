# API Reference

## Overview

The OpenAct FraudOps platform provides a comprehensive REST API for fraud detection, case management, and analytics. All API endpoints are secured with JWT authentication and rate limiting.

## Base URL

- **Development**: `http://localhost:8001`
- **Production**: `https://api.openact-fraudops.com`

## Authentication

All API endpoints (except `/auth/login`) require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

### Login

**POST** `/auth/login`

Authenticate and receive a JWT token.

**Request Body:**
```json
{
  "username": "sup:gerria",
  "password": "x"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "role": "supervisor"
}
```

**Username Formats:**
- `analyst:username` → analyst role
- `sup:username` → supervisor role  
- `admin:username` → admin role

## Core Services

### Score Service

**POST** `/score`

Score a transaction using the ensemble ML model.

**Request Body:**
```json
{
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
```

**Response:**
```json
{
  "event_id": "e1",
  "scores": {
    "xgb": 0.7234,
    "nn": 0.6891,
    "rules": 0.7000,
    "ensemble": 0.7042,
    "calibrated": 0.8600
  },
  "explain": {
    "top_features": [
      ["velocity_1h", 0.9],
      ["ip_risk", 0.41],
      ["merchant_risk", 0.1]
    ]
  },
  "model_version": "xgb_2025_10_01_nn_2025_10_01"
}
```

### Decision Service

**POST** `/decide`

Make a fraud decision based on scores and business rules.

**Request Body:**
```json
{
  "event_id": "e1",
  "entity_id": "acct_7",
  "channel": "web",
  "scores": {
    "calibrated": 0.86
  },
  "features": {
    "velocity_1h": 9,
    "ip_risk": 0.82
  }
}
```

**Response:**
```json
{
  "event_id": "e1",
  "risk": 0.86,
  "action": "hold",
  "reasons": ["velocity_high", "ip_proxy_match"],
  "policy": "v1"
}
```

**Actions:**
- `allow` - Transaction approved
- `hold` - Transaction held for review
- `block` - Transaction blocked
- `escalate` - Escalated to supervisor

### Case Management

#### Create Case

**POST** `/cases`

Create a new fraud investigation case.

**Request Body:**
```json
{
  "event_id": "e1",
  "entity_id": "acct_7",
  "risk": 0.86,
  "action": "hold",
  "reasons": ["velocity_high", "ip_proxy_match"]
}
```

**Response:**
```json
{
  "case_id": "64f8a1b2c3d4e5f6a7b8c9d0"
}
```

#### List Cases

**GET** `/cases`

Retrieve a list of cases.

**Response:**
```json
[
  {
    "id": "64f8a1b2c3d4e5f6a7b8c9d0",
    "event_id": "e1",
    "entity_id": "acct_7",
    "status": "open",
    "risk": 0.86,
    "action": "hold",
    "reasons": ["velocity_high", "ip_proxy_match"],
    "assignee": null,
    "created_at": "2025-10-21T21:10:11Z",
    "updated_at": "2025-10-21T21:10:11Z"
  }
]
```

#### Get Case

**GET** `/cases/{case_id}`

Retrieve a specific case by ID.

**Response:**
```json
{
  "id": "64f8a1b2c3d4e5f6a7b8c9d0",
  "event_id": "e1",
  "entity_id": "acct_7",
  "status": "open",
  "risk": 0.86,
  "action": "hold",
  "reasons": ["velocity_high", "ip_proxy_match"],
  "assignee": "analyst1",
  "created_at": "2025-10-21T21:10:11Z",
  "updated_at": "2025-10-21T21:15:30Z"
}
```

#### Assign Case

**PATCH** `/cases/{case_id}/assign?user={username}`

Assign a case to a specific user.

**Response:**
```json
{
  "ok": true
}
```

#### Add Note

**POST** `/cases/{case_id}/notes`

Add a note to a case.

**Request Body:**
```json
{
  "text": "Investigation note here"
}
```

**Response:**
```json
{
  "ok": true
}
```

### Model Monitoring

**POST** `/monitor/ingest-score`

Ingest model performance data for monitoring.

**Request Body:**
```json
{
  "calibrated": 0.86,
  "features": {
    "velocity_1h": 9,
    "ip_risk": 0.82,
    "merchant_risk": 0.25
  }
}
```

**Response:**
```json
{
  "ok": true,
  "n": 1247
}
```

**GET** `/metrics`

Retrieve Prometheus metrics.

**Response:**
```
# HELP monitor_requests_total Requests total
# TYPE monitor_requests_total counter
monitor_requests_total{route="/ingest/score"} 1247

# HELP monitor_risk_last Last calibrated score
# TYPE monitor_risk_last gauge
monitor_risk_last 0.86

# HELP monitor_psi_feature PSI per feature
# TYPE monitor_psi_feature gauge
monitor_psi_feature{feature="velocity_1h"} 0.15
```

### Analytics

#### Get Analytics

**GET** `/analytics?hours=24`

Retrieve comprehensive analytics data.

**Query Parameters:**
- `hours` (optional): Time range in hours (1-168, default: 24)

**Response:**
```json
{
  "time_range_hours": 24,
  "generated_at": "2025-10-21T21:30:00Z",
  "kpis": [
    {
      "name": "Total Cases",
      "value": 150,
      "change_percent": 12.5,
      "trend": "up"
    },
    {
      "name": "Fraud Rate",
      "value": 3.2,
      "change_percent": -0.5,
      "trend": "down"
    }
  ],
  "decisions_per_minute": [
    {
      "timestamp": "2025-10-21T21:00:00Z",
      "value": 5.2
    }
  ],
  "action_distribution": [
    {
      "action": "allow",
      "count": 1200,
      "percentage": 80.0
    },
    {
      "action": "hold",
      "count": 200,
      "percentage": 13.3
    }
  ],
  "total_transactions": 1500,
  "total_fraud_detected": 48,
  "avg_response_time_ms": 150.0,
  "model_accuracy": 94.2
}
```

#### Get KPIs

**GET** `/analytics/kpis?hours=24`

Retrieve KPI metrics only.

#### Get Trends

**GET** `/analytics/trends?hours=24`

Retrieve time series trends only.

#### Get Distributions

**GET** `/analytics/distributions?hours=24`

Retrieve distribution analytics only.

## Rate Limits

- **Login**: 5 requests per minute
- **Score/Decide**: 100 requests per minute
- **Cases**: 50 requests per minute (create), 200 requests per minute (read)
- **Monitor**: 1000 requests per minute
- **Analytics**: 60 requests per minute

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "invalid_token"
}
```

### 403 Forbidden
```json
{
  "detail": "insufficient_role"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## SDK Examples

### Python
```python
import requests

# Login
response = requests.post("http://localhost:8001/auth/login", json={
    "username": "sup:gerria",
    "password": "x"
})
token = response.json()["access_token"]

# Score transaction
headers = {"Authorization": f"Bearer {token}"}
score_response = requests.post("http://localhost:8001/score", 
    json=transaction_data, headers=headers)
```

### JavaScript
```javascript
// Login
const loginResponse = await fetch("http://localhost:8001/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username: "sup:gerria", password: "x"})
});
const {access_token} = await loginResponse.json();

// Score transaction
const scoreResponse = await fetch("http://localhost:8001/score", {
    method: "POST",
    headers: {
        "Authorization": `Bearer ${access_token}`,
        "Content-Type": "application/json"
    },
    body: JSON.stringify(transactionData)
});
```

### cURL
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"sup:gerria","password":"x"}' | jq -r .access_token)

# Score transaction
curl -X POST http://localhost:8001/score \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_id":"e1","entity_id":"acct_7",...}'
```
