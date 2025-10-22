from fastapi import FastAPI
from .schemas import FeatureVector, ScoreResponse
from .config import settings
from .models import Ensemble

weights = [float(x) for x in settings.ENSEMBLE_WEIGHTS.split(",")]
model = Ensemble(*weights)

app = FastAPI(title="score-svc", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME, "model_version": model.version}

@app.post("/score", response_model=ScoreResponse)
def score(fv: FeatureVector):
    feats = fv.model_dump()
    out = model.score(feats)
    return {
        "event_id": fv.event_id,
        "scores": {k: out[k] for k in ["xgb","nn","rules","ensemble","calibrated"]},
        "explain": {"top_features": out["explain"]},
        "model_version": model.version,
    }
