from .config import settings

def decide(payload: dict) -> tuple[str, list[str]]:
    s = payload["scores"].get("calibrated", 0.0)
    f = payload.get("features", {})
    reasons = []

    if f.get("velocity_1h", 0) >= 8:
        reasons.append("velocity_high")
    if float(f.get("ip_risk", 0)) >= 0.8:
        reasons.append("ip_proxy_match")
    if payload.get("channel") not in settings.TRUSTED_CHANNELS:
        reasons.append("untrusted_channel")

    # primary thresholds
    if s >= settings.BLOCK_THRESHOLD or ("ip_proxy_match" in reasons and s >= 0.80):
        return "block", reasons
    if s >= settings.HOLD_THRESHOLD or "velocity_high" in reasons:
        return "hold", reasons
    return "allow", reasons
