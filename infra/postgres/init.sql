-- Initialize PostgreSQL database for fraud operations

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'analyst',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create decision policy table
CREATE TABLE IF NOT EXISTS decision_policy (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL,
    effective_date TIMESTAMP NOT NULL,
    policy_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

-- Create audit events table
CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100),
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    evidence_hash VARCHAR(64),
    evidence_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create model metrics table
CREATE TABLE IF NOT EXISTS model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10,6) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create feature drift table
CREATE TABLE IF NOT EXISTS feature_drift (
    id SERIAL PRIMARY KEY,
    feature_name VARCHAR(100) NOT NULL,
    psi_value DECIMAL(10,6) NOT NULL,
    reference_period_start TIMESTAMP NOT NULL,
    reference_period_end TIMESTAMP NOT NULL,
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default users
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@fraudops.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8.5.2', 'admin'),
('supervisor', 'supervisor@fraudops.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8.5.2', 'supervisor'),
('analyst1', 'analyst1@fraudops.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8.5.2', 'analyst')
ON CONFLICT (username) DO NOTHING;

-- Insert default decision policy
INSERT INTO decision_policy (version, effective_date, policy_config, created_by) VALUES
('v1.0', CURRENT_TIMESTAMP, '{
    "rules": {
        "block": {
            "conditions": [
                {"calibrated_score": {"gte": 0.90}},
                {"calibrated_score": {"gte": 0.80}, "watchlist_hit": true}
            ],
            "action": "block",
            "reason_codes": ["high_risk_score", "watchlist_match"]
        },
        "hold": {
            "conditions": [
                {"calibrated_score": {"gte": 0.70, "lt": 0.90}},
                {"conflicting_signals": true}
            ],
            "action": "hold",
            "reason_codes": ["medium_risk", "conflicting_signals"]
        },
        "allow": {
            "conditions": [
                {"calibrated_score": {"lt": 0.70}},
                {"velocity_normal": true}
            ],
            "action": "allow",
            "reason_codes": ["low_risk", "normal_velocity"]
        }
    }
}', 1)
ON CONFLICT DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_events_event_id ON audit_events(event_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity_id ON audit_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at);
CREATE INDEX IF NOT EXISTS idx_model_metrics_model_name ON model_metrics(model_name);
CREATE INDEX IF NOT EXISTS idx_model_metrics_timestamp ON model_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_feature_drift_feature_name ON feature_drift(feature_name);
CREATE INDEX IF NOT EXISTS idx_feature_drift_created_at ON feature_drift(created_at);
