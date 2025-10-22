"""Audit service for immutable evidence storage and audit trail."""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Audit Service",
    description="Service for immutable audit trail and evidence storage",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
postgres_conn = None
minio_client = None


class AuditEvent(BaseModel):
    """Audit event model."""
    event_id: str = Field(..., description="Event identifier")
    event_type: str = Field(..., description="Type of event")
    entity_id: Optional[str] = Field(None, description="Entity identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    action: str = Field(..., description="Action performed")
    details: Dict[str, Any] = Field(..., description="Event details")


class EvidenceBundle(BaseModel):
    """Evidence bundle model."""
    bundle_id: str
    event_id: str
    evidence_type: str
    data: Dict[str, Any]
    created_at: datetime
    hash: str
    size_bytes: int


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


def get_minio_client():
    """Get MinIO client."""
    global minio_client
    if minio_client is None:
        try:
            minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
            minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
            
            minio_client = Minio(
                minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=minio_secure
            )
            
            # Ensure bucket exists
            bucket_name = os.getenv("MINIO_BUCKET", "fraudops-evidence")
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Error connecting to MinIO: {e}")
            return None
    return minio_client


def calculate_hash(data: str) -> str:
    """Calculate SHA-256 hash of data."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def store_evidence_bundle(data: Dict[str, Any], evidence_type: str) -> EvidenceBundle:
    """Store evidence bundle in MinIO and return bundle info."""
    try:
        minio_client = get_minio_client()
        if minio_client is None:
            raise Exception("MinIO client not available")
        
        # Generate bundle ID
        bundle_id = str(uuid.uuid4())
        event_id = data.get("event_id", "unknown")
        
        # Create evidence data
        evidence_data = {
            "bundle_id": bundle_id,
            "event_id": event_id,
            "evidence_type": evidence_type,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "service": "audit-svc",
                "version": "1.0.0"
            }
        }
        
        # Convert to JSON
        json_data = json.dumps(evidence_data, indent=2)
        data_bytes = json_data.encode('utf-8')
        
        # Calculate hash
        data_hash = calculate_hash(json_data)
        
        # Create object key (date-based path for organization)
        date_path = datetime.utcnow().strftime("%Y/%m/%d")
        object_key = f"{date_path}/{bundle_id}.json"
        
        # Store in MinIO
        bucket_name = os.getenv("MINIO_BUCKET", "fraudops-evidence")
        minio_client.put_object(
            bucket_name,
            object_key,
            data=json_data,
            length=len(data_bytes),
            content_type="application/json"
        )
        
        # Create evidence bundle
        bundle = EvidenceBundle(
            bundle_id=bundle_id,
            event_id=event_id,
            evidence_type=evidence_type,
            data=evidence_data,
            created_at=datetime.utcnow(),
            hash=data_hash,
            size_bytes=len(data_bytes)
        )
        
        logger.info(f"Evidence bundle stored: {bundle_id}")
        return bundle
        
    except Exception as e:
        logger.error(f"Error storing evidence bundle: {e}")
        raise


def log_audit_event(audit_event: AuditEvent, evidence_bundle: Optional[EvidenceBundle] = None):
    """Log audit event to PostgreSQL."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            logger.error("PostgreSQL connection not available")
            return
        
        cursor = conn.cursor()
        
        # Insert audit event
        cursor.execute("""
            INSERT INTO audit_events 
            (event_id, event_type, entity_id, user_id, action, details, evidence_hash, evidence_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            audit_event.event_id,
            audit_event.event_type,
            audit_event.entity_id,
            audit_event.user_id,
            audit_event.action,
            json.dumps(audit_event.details),
            evidence_bundle.hash if evidence_bundle else None,
            f"{datetime.utcnow().strftime('%Y/%m/%d')}/{evidence_bundle.bundle_id}.json" if evidence_bundle else None
        ))
        
        conn.commit()
        cursor.close()
        
        logger.info(f"Audit event logged: {audit_event.event_id}")
        
    except Exception as e:
        logger.error(f"Error logging audit event: {e}")
        if conn:
            conn.rollback()


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Audit Service")
    get_postgres_connection()
    get_minio_client()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global postgres_conn
    if postgres_conn:
        postgres_conn.close()
    logger.info("Shutting down Audit Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "audit-svc", "timestamp": datetime.utcnow().isoformat()}


@app.post("/audit/event")
async def log_event(audit_event: AuditEvent):
    """Log an audit event."""
    try:
        # Store evidence bundle
        evidence_bundle = store_evidence_bundle(
            audit_event.dict(),
            "audit_event"
        )
        
        # Log to PostgreSQL
        log_audit_event(audit_event, evidence_bundle)
        
        return {
            "message": "Audit event logged successfully",
            "event_id": audit_event.event_id,
            "bundle_id": evidence_bundle.bundle_id,
            "hash": evidence_bundle.hash
        }
        
    except Exception as e:
        logger.error(f"Error logging audit event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging audit event"
        )


@app.post("/audit/decision")
async def log_decision(decision_data: Dict[str, Any]):
    """Log a decision event."""
    try:
        event_id = decision_data.get("event_id", str(uuid.uuid4()))
        
        # Create audit event
        audit_event = AuditEvent(
            event_id=event_id,
            event_type="decision",
            entity_id=decision_data.get("entity_id"),
            user_id=decision_data.get("user_id"),
            action=decision_data.get("action", "decision_made"),
            details=decision_data
        )
        
        # Store evidence bundle
        evidence_bundle = store_evidence_bundle(
            decision_data,
            "decision"
        )
        
        # Log to PostgreSQL
        log_audit_event(audit_event, evidence_bundle)
        
        return {
            "message": "Decision logged successfully",
            "event_id": event_id,
            "bundle_id": evidence_bundle.bundle_id,
            "hash": evidence_bundle.hash
        }
        
    except Exception as e:
        logger.error(f"Error logging decision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging decision"
        )


@app.post("/audit/case")
async def log_case_event(case_data: Dict[str, Any]):
    """Log a case event."""
    try:
        event_id = case_data.get("event_id", str(uuid.uuid4()))
        
        # Create audit event
        audit_event = AuditEvent(
            event_id=event_id,
            event_type="case",
            entity_id=case_data.get("case_id"),
            user_id=case_data.get("user_id"),
            action=case_data.get("action", "case_event"),
            details=case_data
        )
        
        # Store evidence bundle
        evidence_bundle = store_evidence_bundle(
            case_data,
            "case_event"
        )
        
        # Log to PostgreSQL
        log_audit_event(audit_event, evidence_bundle)
        
        return {
            "message": "Case event logged successfully",
            "event_id": event_id,
            "bundle_id": evidence_bundle.bundle_id,
            "hash": evidence_bundle.hash
        }
        
    except Exception as e:
        logger.error(f"Error logging case event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging case event"
        )


@app.get("/audit/{event_id}")
async def get_audit_bundle(event_id: str):
    """Get audit bundle by event ID."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection not available"
            )
        
        cursor = conn.cursor()
        
        # Get audit event
        cursor.execute("""
            SELECT event_id, event_type, entity_id, user_id, action, details, 
                   evidence_hash, evidence_path, created_at
            FROM audit_events 
            WHERE event_id = %s
        """, (event_id,))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit event not found"
            )
        
        event_id, event_type, entity_id, user_id, action, details, evidence_hash, evidence_path, created_at = result
        
        # Get evidence bundle from MinIO
        evidence_data = None
        if evidence_path:
            try:
                minio_client = get_minio_client()
                bucket_name = os.getenv("MINIO_BUCKET", "fraudops-evidence")
                
                response = minio_client.get_object(bucket_name, evidence_path)
                evidence_data = json.loads(response.read().decode('utf-8'))
                response.close()
                response.release_conn()
                
            except Exception as e:
                logger.error(f"Error retrieving evidence bundle: {e}")
        
        cursor.close()
        
        return {
            "event_id": event_id,
            "event_type": event_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "action": action,
            "details": details,
            "evidence_hash": evidence_hash,
            "evidence_path": evidence_path,
            "created_at": created_at,
            "evidence_data": evidence_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit bundle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting audit bundle"
        )


@app.get("/audit/events")
async def list_audit_events(
    event_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List audit events with optional filters."""
    try:
        conn = get_postgres_connection()
        if conn is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection not available"
            )
        
        cursor = conn.cursor()
        
        # Build filter
        where_conditions = []
        params = []
        
        if event_type:
            where_conditions.append("event_type = %s")
            params.append(event_type)
        
        if entity_id:
            where_conditions.append("entity_id = %s")
            params.append(entity_id)
        
        if user_id:
            where_conditions.append("user_id = %s")
            params.append(user_id)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Query events
        query = f"""
            SELECT event_id, event_type, entity_id, user_id, action, details, 
                   evidence_hash, evidence_path, created_at
            FROM audit_events 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            event_id, event_type, entity_id, user_id, action, details, evidence_hash, evidence_path, created_at = row
            events.append({
                "event_id": event_id,
                "event_type": event_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "action": action,
                "details": details,
                "evidence_hash": evidence_hash,
                "evidence_path": evidence_path,
                "created_at": created_at
            })
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM audit_events WHERE {where_clause}"
        cursor.execute(count_query, params[:-2])  # Remove limit and offset
        total_count = cursor.fetchone()[0]
        
        cursor.close()
        
        return {
            "events": events,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing audit events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing audit events"
        )


@app.get("/audit/verify/{event_id}")
async def verify_audit_integrity(event_id: str):
    """Verify audit event integrity."""
    try:
        # Get audit event
        audit_data = await get_audit_bundle(event_id)
        
        if not audit_data.get("evidence_data"):
            return {
                "event_id": event_id,
                "integrity_status": "no_evidence",
                "message": "No evidence data found"
            }
        
        # Calculate hash of evidence data
        evidence_data = audit_data["evidence_data"]
        evidence_json = json.dumps(evidence_data, sort_keys=True, indent=2)
        calculated_hash = calculate_hash(evidence_json)
        stored_hash = audit_data["evidence_hash"]
        
        # Verify integrity
        integrity_ok = calculated_hash == stored_hash
        
        return {
            "event_id": event_id,
            "integrity_status": "verified" if integrity_ok else "compromised",
            "calculated_hash": calculated_hash,
            "stored_hash": stored_hash,
            "message": "Integrity verified" if integrity_ok else "Hash mismatch detected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying audit integrity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying audit integrity"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AUDIT_SVC_PORT", 8006))
    uvicorn.run(app, host="0.0.0.0", port=port)
