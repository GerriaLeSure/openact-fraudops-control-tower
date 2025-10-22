from collections import deque
from statistics import mean
from typing import Deque

# In-memory ring buffers (swap to DB later)
SCORES: Deque[float] = deque(maxlen=10000)
LABELS: Deque[int] = deque(maxlen=10000)  # optional ground-truth later
FEATURES: dict[str, Deque[float]] = {}    # per-feature stream for PSI
def push_feature(name: str, value: float):
    if name not in FEATURES:
        FEATURES[name] = deque(maxlen=10000)
    FEATURES[name].append(float(value))
