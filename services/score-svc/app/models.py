from pathlib import Path
import json
import math

# Stubs you can replace with real loaders (xgboost/pytorch)
class XGBModel:
    version = "xgb_2025_10_01"
    def predict_proba(self, feats: dict) -> float:
        # toy signal
        return min(1.0, 0.15 + 0.5*float(feats["ip_risk"]) + 0.01*feats["velocity_1h"])

class NNModel:
    version = "nn_2025_10_01"
    def predict_proba(self, feats: dict) -> float:
        return min(1.0, 0.1 + 0.35*float(feats["merchant_risk"]) + 0.001*feats["geo_distance_km"])

def rules_score(feats: dict) -> float:
    s = 0.0
    if feats["velocity_1h"] >= 8: s += 0.35
    if feats["ip_risk"] >= 0.8:  s += 0.35
    if feats["amount"] >= 2000: s += 0.2
    return min(1.0, s)

def shap_like(feats: dict):
    # dummy "explanations"
    return sorted(
        [("velocity_1h", feats["velocity_1h"]/10.0),
         ("ip_risk", feats["ip_risk"]*0.5),
         ("merchant_risk", feats["merchant_risk"]*0.4)],
        key=lambda x: -x[1]
    )[:5]

class Ensemble:
    def __init__(self, w_xgb=0.5, w_nn=0.4, w_rules=0.1):
        self.xgb = XGBModel()
        self.nn = NNModel()
        self.w = (w_xgb, w_nn, w_rules)

    @property
    def version(self) -> str:
        return f"{self.xgb.version}_{self.nn.version}"

    def score(self, feats: dict) -> dict:
        sx = self.xgb.predict_proba(feats)
        sn = self.nn.predict_proba(feats)
        sr = rules_score(feats)
        raw = self.w[0]*sx + self.w[1]*sn + self.w[2]*sr
        # simple Platt-like calibration stub
        calibrated = 1.0/(1.0 + math.exp(-5*(raw-0.5)))
        return {
            "xgb": round(sx, 4),
            "nn": round(sn, 4),
            "rules": round(sr, 4),
            "ensemble": round(raw, 4),
            "calibrated": round(calibrated, 4),
            "explain": shap_like(feats),
        }
