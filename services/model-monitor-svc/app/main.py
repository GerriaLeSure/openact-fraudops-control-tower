from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from .store import SCORES, FEATURES, push_feature
from .mlflow_client import mlflow_client
from .config import settings
import time

app = FastAPI(title="model-monitor-svc", version="0.1.0")

REQS = Counter("monitor_requests_total", "Requests total", ["route"])
LAT = Histogram("monitor_latency_seconds", "Latency", ["route"])
RISK_G = Gauge("monitor_risk_last", "Last calibrated score")
PSI_G = Gauge("monitor_psi_feature", "PSI per feature", ["feature"])
BRIER_G = Gauge("monitor_brier_score", "Brier score for calibration")
ALERT_G = Gauge("monitor_alerts_total", "Total alerts", ["alert_type"])

@app.post("/ingest/score")
def ingest_score(payload: dict):
    start_time = time.time()
    with LAT.labels("/ingest/score").time():
        s = float(payload.get("calibrated", 0.0))
        SCORES.append(s)
        RISK_G.set(s)
        
        # track a couple of example features if present
        feats = payload.get("features", {})
        for k in ("velocity_1h","ip_risk","merchant_risk"):
            if k in feats:
                push_feature(k, float(feats[k]))
        
        # Log to MLflow if configured
        if settings.MLFLOW_TRACKING_URI:
            latency_ms = (time.time() - start_time) * 1000
            mlflow_client.log_model_metrics(
                model_name="ensemble_fraud_detector",
                metrics={"calibrated_score": s, "latency_ms": latency_ms},
                tags={"event_type": "score_ingestion"}
            )
        
        return {"ok": True, "n": len(SCORES)}

@app.get("/metrics")
def prom_metrics():
    # compute PSI for tracked features using first half as ref, last half as cur
    for name, dq in FEATURES.items():
        data = list(dq)
        if len(data) >= 200:
            mid = len(data)//2
            from .metrics import psi, brier_score
            psi_val = psi(data[:mid], data[mid:])
            PSI_G.labels(name).set(psi_val)
            
            # Log drift alerts
            if psi_val > settings.PSI_THRESHOLD:
                ALERT_G.labels("drift").inc()
                if settings.MLFLOW_TRACKING_URI:
                    mlflow_client.log_drift_metrics(name, psi_val, 0.0, len(data))
    
    # Compute Brier score if we have labels
    if len(SCORES) >= 100:
        # Mock labels for demo (in production, get from ground truth)
        mock_labels = [1 if s > 0.5 else 0 for s in list(SCORES)[-100:]]
        mock_scores = list(SCORES)[-100:]
        from .metrics import brier_score
        brier_val = brier_score(mock_labels, mock_scores)
        BRIER_G.set(brier_val)
        
        if brier_val > settings.BRIER_THRESHOLD:
            ALERT_G.labels("calibration").inc()
    
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health():
    return {"status": "ok", "scores_buffer": len(SCORES), "features": list(FEATURES.keys())}
