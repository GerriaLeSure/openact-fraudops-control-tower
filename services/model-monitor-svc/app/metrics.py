from math import sqrt
from .store import SCORES, FEATURES

def brier_score(y_true: list[int], y_prob: list[float]) -> float:
    if not y_true or not y_prob or len(y_true) != len(y_prob): return -1.0
    return sum((p - y)**2 for y,p in zip(y_true,y_prob)) / len(y_true)

def psi(ref: list[float], cur: list[float], bins: int = 10) -> float:
    if len(ref) < bins or len(cur) < bins: return 0.0
    mn, mx = min(min(ref), min(cur)), max(max(ref), max(cur))
    if mx == mn: return 0.0
    w = (mx - mn)/bins
    s = 0.0
    for i in range(bins):
        lo, hi = mn + i*w, mn + (i+1)*w
        rp = max(1e-6, sum(1 for v in ref if lo <= v < hi)/len(ref))
        cp = max(1e-6, sum(1 for v in cur if lo <= v < hi)/len(cur))
        s += (rp - cp) * (0.0 if cp==0 else __import__("math").log(rp/cp))
    return s
