from fastapi import FastAPI
from .schemas import ScoreIn, DecisionOut
from .policy import decide
from .config import settings

app = FastAPI(title="decision-svc", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}

@app.post("/decide", response_model=DecisionOut)
def decide_endpoint(data: ScoreIn):
    action, reasons = decide(data.model_dump())
    return {
        "event_id": data.event_id,
        "risk": round(data.scores.get("calibrated", 0.0), 4),
        "action": action,
        "reasons": reasons,
        "policy": "v1",
    }
