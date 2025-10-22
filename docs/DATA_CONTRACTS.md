# Data Contracts

This document defines the data schemas and contracts used throughout the fraud operations system.

## Kafka Topic Schemas

### events.txns.v1 - Transaction Events

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "entity_id", "timestamp", "amount", "currency", "channel"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the transaction event"
    },
    "entity_id": {
      "type": "string",
      "description": "Account or user identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of the transaction"
    },
    "amount": {
      "type": "number",
      "minimum": 0,
      "description": "Transaction amount"
    },
    "currency": {
      "type": "string",
      "pattern": "^[A-Z]{3}$",
      "description": "ISO 4217 currency code"
    },
    "channel": {
      "type": "string",
      "enum": ["web", "mobile", "atm", "pos", "phone", "api"],
      "description": "Transaction channel"
    },
    "merchant_id": {
      "type": "string",
      "description": "Merchant identifier"
    },
    "merchant_category": {
      "type": "string",
      "description": "Merchant category code"
    },
    "ip_address": {
      "type": "string",
      "format": "ipv4",
      "description": "IP address of the transaction"
    },
    "device_fingerprint": {
      "type": "string",
      "description": "Device fingerprint hash"
    },
    "user_agent": {
      "type": "string",
      "description": "User agent string"
    },
    "session_id": {
      "type": "string",
      "description": "Session identifier"
    },
    "metadata": {
      "type": "object",
      "description": "Additional transaction metadata"
    }
  }
}
```

### events.claims.v1 - Claim Events

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "entity_id", "timestamp", "claim_amount", "claim_type"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the claim event"
    },
    "entity_id": {
      "type": "string",
      "description": "Policy or customer identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of the claim"
    },
    "claim_amount": {
      "type": "number",
      "minimum": 0,
      "description": "Claim amount"
    },
    "claim_type": {
      "type": "string",
      "enum": ["auto", "home", "health", "life", "travel", "other"],
      "description": "Type of insurance claim"
    },
    "policy_id": {
      "type": "string",
      "description": "Insurance policy identifier"
    },
    "incident_date": {
      "type": "string",
      "format": "date",
      "description": "Date of the incident"
    },
    "incident_location": {
      "type": "object",
      "properties": {
        "latitude": {"type": "number"},
        "longitude": {"type": "number"},
        "address": {"type": "string"},
        "city": {"type": "string"},
        "state": {"type": "string"},
        "country": {"type": "string"}
      }
    },
    "claim_description": {
      "type": "string",
      "description": "Description of the claim"
    },
    "metadata": {
      "type": "object",
      "description": "Additional claim metadata"
    }
  }
}
```

### features.online.v1 - Feature Vectors

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "entity_id", "timestamp", "features_version"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Original event identifier"
    },
    "entity_id": {
      "type": "string",
      "description": "Account or user identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Feature computation timestamp"
    },
    "amount": {
      "type": "number",
      "description": "Transaction or claim amount"
    },
    "currency": {
      "type": "string",
      "description": "Currency code"
    },
    "channel": {
      "type": "string",
      "description": "Transaction channel"
    },
    "velocity_1h": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of transactions in last hour"
    },
    "velocity_24h": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of transactions in last 24 hours"
    },
    "velocity_7d": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of transactions in last 7 days"
    },
    "ip_risk": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "IP address risk score"
    },
    "ip_geolocation": {
      "type": "object",
      "properties": {
        "country": {"type": "string"},
        "region": {"type": "string"},
        "city": {"type": "string"},
        "latitude": {"type": "number"},
        "longitude": {"type": "number"}
      }
    },
    "geo_distance_km": {
      "type": "number",
      "minimum": 0,
      "description": "Distance from usual location in kilometers"
    },
    "merchant_risk": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Merchant risk score"
    },
    "merchant_category": {
      "type": "string",
      "description": "Merchant category code"
    },
    "age_days": {
      "type": "integer",
      "minimum": 0,
      "description": "Account age in days"
    },
    "device_fingerprint": {
      "type": "string",
      "description": "Device fingerprint hash"
    },
    "session_id": {
      "type": "string",
      "description": "Session identifier"
    },
    "user_agent_hash": {
      "type": "string",
      "description": "Hashed user agent"
    },
    "features_version": {
      "type": "string",
      "description": "Feature schema version"
    },
    "feature_metadata": {
      "type": "object",
      "properties": {
        "computation_time_ms": {"type": "number"},
        "cache_hit": {"type": "boolean"},
        "data_freshness_minutes": {"type": "number"}
      }
    }
  }
}
```

### alerts.scores.v1 - Model Scores

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "scores", "model_version"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Original event identifier"
    },
    "scores": {
      "type": "object",
      "required": ["xgb", "nn", "rules", "ensemble", "calibrated"],
      "properties": {
        "xgb": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "XGBoost model score"
        },
        "nn": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Neural network model score"
        },
        "rules": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Rule-based score"
        },
        "ensemble": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Weighted ensemble score"
        },
        "calibrated": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Platt-calibrated final score"
        }
      }
    },
    "explain": {
      "type": "object",
      "properties": {
        "top_features": {
          "type": "array",
          "items": {
            "type": "array",
            "items": [
              {"type": "string"},
              {"type": "number"}
            ],
            "minItems": 2,
            "maxItems": 2
          },
          "description": "Top contributing features with SHAP values"
        },
        "feature_importance": {
          "type": "object",
          "description": "Feature importance scores"
        }
      }
    },
    "model_version": {
      "type": "string",
      "description": "Model version identifier"
    },
    "computation_time_ms": {
      "type": "number",
      "description": "Model computation time in milliseconds"
    }
  }
}
```

### alerts.decisions.v1 - Decisions

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "risk", "action", "policy", "reasons"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Original event identifier"
    },
    "risk": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Final risk score"
    },
    "action": {
      "type": "string",
      "enum": ["allow", "hold", "block", "escalate"],
      "description": "Decision action"
    },
    "policy": {
      "type": "string",
      "description": "Policy version used"
    },
    "reasons": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Array of reason codes"
    },
    "case_id": {
      "type": "string",
      "description": "Associated case identifier if created"
    },
    "watchlist_hits": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Watchlist matches"
    },
    "velocity_anomaly": {
      "type": "boolean",
      "description": "Velocity anomaly detected"
    },
    "graph_anomaly": {
      "type": "boolean",
      "description": "Graph-based anomaly detected"
    },
    "decision_time_ms": {
      "type": "number",
      "description": "Decision computation time"
    }
  }
}
```

## API Response Schemas

### Case Management

#### Case Object
```json
{
  "type": "object",
  "required": ["case_id", "event_id", "status", "priority", "created_at"],
  "properties": {
    "case_id": {
      "type": "string",
      "description": "Unique case identifier"
    },
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Associated event identifier"
    },
    "status": {
      "type": "string",
      "enum": ["open", "assigned", "investigating", "resolved", "closed"],
      "description": "Case status"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"],
      "description": "Case priority"
    },
    "assigned_to": {
      "type": "string",
      "description": "Assigned analyst username"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Case creation timestamp"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "Last update timestamp"
    },
    "sla_deadline": {
      "type": "string",
      "format": "date-time",
      "description": "SLA deadline"
    },
    "risk_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Associated risk score"
    },
    "decision_action": {
      "type": "string",
      "description": "Original decision action"
    }
  }
}
```

#### Note Object
```json
{
  "type": "object",
  "required": ["note_id", "case_id", "content", "author", "created_at"],
  "properties": {
    "note_id": {
      "type": "string",
      "description": "Unique note identifier"
    },
    "case_id": {
      "type": "string",
      "description": "Associated case identifier"
    },
    "content": {
      "type": "string",
      "description": "Note content"
    },
    "author": {
      "type": "string",
      "description": "Author username"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Note creation timestamp"
    },
    "is_internal": {
      "type": "boolean",
      "description": "Internal note flag"
    }
  }
}
```

## Error Response Schema

```json
{
  "type": "object",
  "required": ["error", "message", "timestamp"],
  "properties": {
    "error": {
      "type": "string",
      "description": "Error code"
    },
    "message": {
      "type": "string",
      "description": "Human-readable error message"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Error timestamp"
    },
    "details": {
      "type": "object",
      "description": "Additional error details"
    },
    "request_id": {
      "type": "string",
      "description": "Request identifier for tracing"
    }
  }
}
```

## Data Validation Rules

### Transaction Events
- `amount` must be non-negative
- `currency` must be valid ISO 4217 code
- `ip_address` must be valid IPv4 format
- `timestamp` must be valid ISO 8601 format

### Feature Vectors
- All velocity fields must be non-negative integers
- Risk scores must be between 0 and 1
- Geographic coordinates must be valid latitude/longitude
- `features_version` must match supported versions

### Model Scores
- All scores must be between 0 and 1
- `ensemble` score must be weighted average of component scores
- `calibrated` score must be Platt-calibrated version of ensemble
- SHAP values must sum to the model score

### Decisions
- `action` must be one of the defined enum values
- `reasons` array must not be empty
- `case_id` must be present for hold/block/escalate actions
- Risk score must match the calibrated score from scoring service

## Versioning Strategy

### Schema Versioning
- Major version changes require new Kafka topics
- Minor version changes are backward compatible
- Patch version changes are internal only

### Model Versioning
- Format: `YYYY_MM_DD_model_type_version`
- Example: `2025_01_15_xgb_17_nn_05`
- Version tracking in model metadata

### API Versioning
- URL-based versioning: `/api/v1/`, `/api/v2/`
- Header-based versioning for backward compatibility
- Deprecation notices in API documentation
