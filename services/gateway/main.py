"""API Gateway with JWT authentication and RBAC."""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import httpx
import psycopg2
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps API Gateway",
    description="API Gateway with authentication and authorization",
    version="1.0.0"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Service URLs
SERVICE_URLS = {
    "ingest": f"http://localhost:{os.getenv('INGEST_SVC_PORT', '8001')}",
    "feature": f"http://localhost:{os.getenv('FEATURE_SVC_PORT', '8002')}",
    "score": f"http://localhost:{os.getenv('SCORE_SVC_PORT', '8003')}",
    "decision": f"http://localhost:{os.getenv('DECISION_SVC_PORT', '8004')}",
    "case": f"http://localhost:{os.getenv('CASE_SVC_PORT', '8005')}",
    "audit": f"http://localhost:{os.getenv('AUDIT_SVC_PORT', '8006')}",
    "model-monitor": f"http://localhost:{os.getenv('MODEL_MONITOR_SVC_PORT', '8007')}",
    "summary": f"http://localhost:{os.getenv('SUMMARY_SVC_PORT', '8008')}",
}

# Global variables
postgres_conn = None


# Pydantic models
class UserLogin(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class ServiceRequest(BaseModel):
    service: str
    path: str
    method: str
    data: Optional[Dict[str, Any]] = None


def get_postgres_connection():
    """Get PostgreSQL connection."""
    global postgres_conn
    if postgres_conn is None or postgres_conn.closed:
        try:
            postgres_conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "fraudops"),
                user=os.getenv("POSTGRES_USER", "fraudops"),
                password=os.getenv("POSTGRES_PASSWORD", "fraudops_password")
            )
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            return None
    return postgres_conn


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[User]:
    """Get user by username."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, role, is_active
            FROM users 
            WHERE username = %s AND is_active = true
        """, (username,))
        
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return User(
                id=result[0],
                username=result[1],
                email=result[2],
                role=result[3],
                is_active=result[4]
            )
        return None
        
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, role, is_active, password_hash
            FROM users 
            WHERE username = %s AND is_active = true
        """, (username,))
        
        result = cursor.fetchone()
        cursor.close()
        
        if result and verify_password(password, result[5]):
            return User(
                id=result[0],
                username=result[1],
                email=result[2],
                role=result[3],
                is_active=result[4]
            )
        return None
        
    except Exception as e:
        logger.error(f"Error authenticating user: {e}")
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Verify JWT token and return user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(username)
    if user is None:
        raise credentials_exception
    
    return user


def require_role(allowed_roles: List[str]):
    """Decorator to require specific roles."""
    def role_checker(current_user: User = Depends(verify_token)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


def log_request(request: Request, user: Optional[User] = None, service: str = None):
    """Log API request for audit."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_events 
            (event_id, event_type, entity_id, user_id, action, details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            f"req_{int(time.time() * 1000)}",
            "api_request",
            None,
            user.id if user else None,
            f"{request.method} {request.url.path}",
            {
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "service": service,
                "user_agent": request.headers.get("user-agent"),
                "ip_address": request.client.host if request.client else None
            }
        ))
        conn.commit()
        cursor.close()
        
    except Exception as e:
        logger.error(f"Error logging request: {e}")


async def proxy_request(service: str, path: str, method: str, data: Dict[str, Any] = None, user: User = None):
    """Proxy request to backend service."""
    if service not in SERVICE_URLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service} not found"
        )
    
    service_url = SERVICE_URLS[service]
    url = f"{service_url}{path}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Content-Type": "application/json"}
            if user:
                # Forward user context to backend service
                headers["X-User-ID"] = str(user.id)
                headers["X-User-Role"] = user.role
            
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = await client.put(url, json=data, headers=headers)
            elif method.upper() == "PATCH":
                response = await client.patch(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                    detail=f"Method {method} not allowed"
                )
            
            return response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Service timeout"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )
    except Exception as e:
        logger.error(f"Error proxying request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting API Gateway")
    get_postgres_connection()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global postgres_conn
    if postgres_conn:
        postgres_conn.close()
    logger.info("Shutting down API Gateway")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "gateway", "timestamp": datetime.utcnow().isoformat()}


@app.post("/auth/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, user_credentials: UserLogin):
    """Authenticate user and return JWT token."""
    user = authenticate_user(user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Log login event
    log_request(request, user, "auth")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user
    )


@app.get("/auth/me", response_model=User)
async def get_current_user(current_user: User = Depends(verify_token)):
    """Get current user information."""
    return current_user


@app.post("/proxy/{service:path}")
@limiter.limit("100/minute")
async def proxy_to_service(
    request: Request,
    service: str,
    service_request: ServiceRequest,
    current_user: User = Depends(verify_token)
):
    """Proxy request to backend service."""
    # Log request
    log_request(request, current_user, service)
    
    # Check permissions based on service and user role
    if service in ["audit", "model-monitor"] and current_user.role not in ["supervisor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this service"
        )
    
    result = await proxy_request(
        service_request.service,
        service_request.path,
        service_request.method,
        service_request.data,
        current_user
    )
    
    return result


# Direct service endpoints
@app.get("/cases")
@limiter.limit("100/minute")
async def get_cases(
    request: Request,
    current_user: User = Depends(verify_token)
):
    """Get cases."""
    log_request(request, current_user, "case")
    return await proxy_request("case", "/cases", "GET", user=current_user)


@app.get("/cases/{case_id}")
@limiter.limit("100/minute")
async def get_case(
    request: Request,
    case_id: str,
    current_user: User = Depends(verify_token)
):
    """Get specific case."""
    log_request(request, current_user, "case")
    return await proxy_request("case", f"/cases/{case_id}", "GET", user=current_user)


@app.patch("/cases/{case_id}/assign")
@limiter.limit("50/minute")
async def assign_case(
    request: Request,
    case_id: str,
    assigned_to: str,
    current_user: User = Depends(verify_token)
):
    """Assign case."""
    log_request(request, current_user, "case")
    return await proxy_request("case", f"/cases/{case_id}/assign", "PATCH", {"assigned_to": assigned_to}, current_user)


@app.post("/cases/{case_id}/note")
@limiter.limit("50/minute")
async def add_note(
    request: Request,
    case_id: str,
    note_data: Dict[str, Any],
    current_user: User = Depends(verify_token)
):
    """Add note to case."""
    log_request(request, current_user, "case")
    return await proxy_request("case", f"/cases/{case_id}/note", "POST", note_data, current_user)


@app.post("/cases/{case_id}/action")
@limiter.limit("50/minute")
async def add_action(
    request: Request,
    case_id: str,
    action_data: Dict[str, Any],
    current_user: User = Depends(verify_token)
):
    """Add action to case."""
    log_request(request, current_user, "case")
    return await proxy_request("case", f"/cases/{case_id}/action", "POST", action_data, current_user)


@app.patch("/cases/{case_id}/status")
@limiter.limit("50/minute")
async def update_case_status(
    request: Request,
    case_id: str,
    status: str,
    current_user: User = Depends(verify_token)
):
    """Update case status."""
    log_request(request, current_user, "case")
    return await proxy_request("case", f"/cases/{case_id}/status", "PATCH", {"status": status}, current_user)


@app.get("/policy")
@limiter.limit("50/minute")
async def get_policy(
    request: Request,
    current_user: User = Depends(require_role(["supervisor", "admin"]))
):
    """Get decision policy."""
    log_request(request, current_user, "decision")
    return await proxy_request("decision", "/policy", "GET", user=current_user)


@app.get("/audit/{event_id}")
@limiter.limit("50/minute")
async def get_audit_event(
    request: Request,
    event_id: str,
    current_user: User = Depends(require_role(["supervisor", "admin"]))
):
    """Get audit event."""
    log_request(request, current_user, "audit")
    return await proxy_request("audit", f"/audit/{event_id}", "GET", user=current_user)


@app.get("/metrics")
@limiter.limit("50/minute")
async def get_metrics(
    request: Request,
    current_user: User = Depends(require_role(["supervisor", "admin"]))
):
    """Get system metrics."""
    log_request(request, current_user, "model-monitor")
    return await proxy_request("model-monitor", "/metrics", "GET", user=current_user)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("GATEWAY_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
