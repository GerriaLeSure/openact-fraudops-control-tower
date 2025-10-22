import httpx
from fastapi import FastAPI, Depends, Body, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .config import settings
from .auth import create_token, require_role

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="gateway", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"],
)

@app.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, username: str = Body(...), password: str = Body(...)):
    # simple demo auth: accept any user, role via prefix e.g., admin:alice
    role = "analyst"
    if username.startswith("admin:"): role = "admin"
    elif username.startswith("sup:"): role = "supervisor"
    token = create_token(username, role=role)
    return {"access_token": token, "token_type": "bearer", "role": role}

# --- proxies ---
async def forward_json(url: str, payload: dict | None = None, method: str = "POST"):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.request(method, url, json=payload)
        r.raise_for_status()
        return r.json()

@app.post("/score")
@limiter.limit("100/minute")
async def score_proxy(request: Request, payload: dict, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.SCORE_URL}/score", payload, "POST")

@app.post("/decide")
@limiter.limit("100/minute")
async def decide_proxy(request: Request, payload: dict, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.DECISION_URL}/decide", payload, "POST")

@app.post("/cases")
@limiter.limit("50/minute")
async def open_case(request: Request, payload: dict, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.CASE_URL}/cases", payload, "POST")

@app.get("/cases")
@limiter.limit("200/minute")
async def list_cases(request: Request, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.CASE_URL}/cases", None, "GET")

@app.get("/cases/{cid}")
@limiter.limit("200/minute")
async def get_case(request: Request, cid: str, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.CASE_URL}/cases/{cid}", None, "GET")

@app.post("/monitor/ingest-score")
@limiter.limit("1000/minute")
async def monitor_ingest(request: Request, payload: dict, _=Depends(require_role(["admin","supervisor"]))):
    return await forward_json(f"{settings.MONITOR_URL}/ingest/score", payload, "POST")

# Analytics endpoints
@app.get("/analytics")
@limiter.limit("60/minute")
async def get_analytics(request: Request, hours: int = 24, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.ANALYTICS_URL}/analytics?hours={hours}", None, "GET")

@app.get("/analytics/kpis")
@limiter.limit("60/minute")
async def get_kpis(request: Request, hours: int = 24, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.ANALYTICS_URL}/analytics/kpis?hours={hours}", None, "GET")

@app.get("/analytics/trends")
@limiter.limit("60/minute")
async def get_trends(request: Request, hours: int = 24, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.ANALYTICS_URL}/analytics/trends?hours={hours}", None, "GET")

@app.get("/analytics/distributions")
@limiter.limit("60/minute")
async def get_distributions(request: Request, hours: int = 24, _=Depends(require_role(["analyst","supervisor","admin"]))):
    return await forward_json(f"{settings.ANALYTICS_URL}/analytics/distributions?hours={hours}", None, "GET")

@app.get("/health")
def health():
    return {"status": "ok", "gateway": True}
