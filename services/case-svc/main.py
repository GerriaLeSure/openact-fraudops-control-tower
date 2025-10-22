"""Case management service for fraud investigation workflow."""

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Case Service",
    description="Service for case management and investigation workflow",
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

# MongoDB client
mongo_client = None
db = None


# Pydantic models
class CaseCreate(BaseModel):
    """Case creation model."""
    event_id: str = Field(..., description="Associated event identifier")
    risk_score: float = Field(..., ge=0, le=1, description="Risk score")
    decision_action: str = Field(..., description="Original decision action")
    priority: str = Field("medium", description="Case priority")
    assigned_to: Optional[str] = Field(None, description="Assigned analyst")


class CaseUpdate(BaseModel):
    """Case update model."""
    status: Optional[str] = Field(None, description="Case status")
    priority: Optional[str] = Field(None, description="Case priority")
    assigned_to: Optional[str] = Field(None, description="Assigned analyst")


class NoteCreate(BaseModel):
    """Note creation model."""
    content: str = Field(..., description="Note content")
    is_internal: bool = Field(False, description="Internal note flag")


class ActionCreate(BaseModel):
    """Action creation model."""
    action_type: str = Field(..., description="Action type")
    description: str = Field(..., description="Action description")
    outcome: Optional[str] = Field(None, description="Action outcome")


class Case(BaseModel):
    """Case model."""
    case_id: str
    event_id: str
    status: str
    priority: str
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    sla_deadline: datetime
    risk_score: float
    decision_action: str
    notes: List[Dict] = []
    actions: List[Dict] = []


def get_mongo_client():
    """Get MongoDB client."""
    global mongo_client, db
    if mongo_client is None:
        mongo_host = os.getenv("MONGODB_HOST", "localhost")
        mongo_port = int(os.getenv("MONGODB_PORT", 27017))
        mongo_db = os.getenv("MONGODB_DB", "fraudops_cases")
        
        mongo_client = AsyncIOMotorClient(f"mongodb://{mongo_host}:{mongo_port}")
        db = mongo_client[mongo_db]
        
        # Create indexes
        db.cases.create_index("case_id", unique=True)
        db.cases.create_index("event_id")
        db.cases.create_index("status")
        db.cases.create_index("assigned_to")
        db.cases.create_index("created_at")
        db.cases.create_index("sla_deadline")
        
        db.notes.create_index("case_id")
        db.notes.create_index("created_at")
        
        db.actions.create_index("case_id")
        db.actions.create_index("created_at")
    
    return mongo_client, db


def calculate_sla_deadline(priority: str) -> datetime:
    """Calculate SLA deadline based on priority."""
    now = datetime.utcnow()
    
    if priority == "critical":
        return now + timedelta(hours=2)
    elif priority == "high":
        return now + timedelta(hours=8)
    elif priority == "medium":
        return now + timedelta(hours=24)
    else:  # low
        return now + timedelta(days=3)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Case Service")
    get_mongo_client()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global mongo_client
    if mongo_client:
        mongo_client.close()
    logger.info("Shutting down Case Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "case-svc", "timestamp": datetime.utcnow().isoformat()}


@app.post("/cases", response_model=Case)
async def create_case(case_data: CaseCreate):
    """Create a new case."""
    try:
        _, db = get_mongo_client()
        
        # Generate case ID
        case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate SLA deadline
        sla_deadline = calculate_sla_deadline(case_data.priority)
        
        # Create case document
        case_doc = {
            "case_id": case_id,
            "event_id": case_data.event_id,
            "status": "open",
            "priority": case_data.priority,
            "assigned_to": case_data.assigned_to,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "sla_deadline": sla_deadline,
            "risk_score": case_data.risk_score,
            "decision_action": case_data.decision_action,
            "notes": [],
            "actions": []
        }
        
        # Insert case
        result = await db.cases.insert_one(case_doc)
        
        if result.inserted_id:
            logger.info(f"Case created: {case_id}")
            return Case(**case_doc)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create case"
            )
            
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating case"
        )


@app.get("/cases/{case_id}", response_model=Case)
async def get_case(case_id: str):
    """Get a case by ID."""
    try:
        _, db = get_mongo_client()
        
        case = await db.cases.find_one({"case_id": case_id})
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Get notes and actions
        notes = await db.notes.find({"case_id": case_id}).sort("created_at", -1).to_list(None)
        actions = await db.actions.find({"case_id": case_id}).sort("created_at", -1).to_list(None)
        
        case["notes"] = notes
        case["actions"] = actions
        
        return Case(**case)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting case"
        )


@app.patch("/cases/{case_id}/assign")
async def assign_case(case_id: str, assigned_to: str):
    """Assign a case to an analyst."""
    try:
        _, db = get_mongo_client()
        
        # Update case
        result = await db.cases.update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "assigned_to": assigned_to,
                    "status": "assigned",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Add assignment action
        action_doc = {
            "action_id": str(uuid.uuid4()),
            "case_id": case_id,
            "action_type": "assignment",
            "description": f"Case assigned to {assigned_to}",
            "performed_by": assigned_to,
            "created_at": datetime.utcnow()
        }
        
        await db.actions.insert_one(action_doc)
        
        logger.info(f"Case {case_id} assigned to {assigned_to}")
        return {"message": "Case assigned successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error assigning case"
        )


@app.post("/cases/{case_id}/note")
async def add_note(case_id: str, note_data: NoteCreate, author: str = "system"):
    """Add a note to a case."""
    try:
        _, db = get_mongo_client()
        
        # Check if case exists
        case = await db.cases.find_one({"case_id": case_id})
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Create note document
        note_doc = {
            "note_id": str(uuid.uuid4()),
            "case_id": case_id,
            "content": note_data.content,
            "author": author,
            "is_internal": note_data.is_internal,
            "created_at": datetime.utcnow()
        }
        
        # Insert note
        await db.notes.insert_one(note_doc)
        
        # Update case timestamp
        await db.cases.update_one(
            {"case_id": case_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        
        logger.info(f"Note added to case {case_id}")
        return {"message": "Note added successfully", "note_id": note_doc["note_id"]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding note: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding note"
        )


@app.post("/cases/{case_id}/action")
async def add_action(case_id: str, action_data: ActionCreate, performed_by: str = "system"):
    """Add an action to a case."""
    try:
        _, db = get_mongo_client()
        
        # Check if case exists
        case = await db.cases.find_one({"case_id": case_id})
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Create action document
        action_doc = {
            "action_id": str(uuid.uuid4()),
            "case_id": case_id,
            "action_type": action_data.action_type,
            "description": action_data.description,
            "outcome": action_data.outcome,
            "performed_by": performed_by,
            "created_at": datetime.utcnow()
        }
        
        # Insert action
        await db.actions.insert_one(action_doc)
        
        # Update case timestamp
        await db.cases.update_one(
            {"case_id": case_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        
        logger.info(f"Action added to case {case_id}")
        return {"message": "Action added successfully", "action_id": action_doc["action_id"]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding action"
        )


@app.patch("/cases/{case_id}/status")
async def update_case_status(case_id: str, status: str, updated_by: str = "system"):
    """Update case status."""
    try:
        _, db = get_mongo_client()
        
        # Validate status
        valid_statuses = ["open", "assigned", "investigating", "resolved", "closed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        # Update case
        result = await db.cases.update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Add status change action
        action_doc = {
            "action_id": str(uuid.uuid4()),
            "case_id": case_id,
            "action_type": "status_change",
            "description": f"Status changed to {status}",
            "performed_by": updated_by,
            "created_at": datetime.utcnow()
        }
        
        await db.actions.insert_one(action_doc)
        
        logger.info(f"Case {case_id} status updated to {status}")
        return {"message": "Case status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating case status"
        )


@app.get("/cases")
async def list_cases(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List cases with optional filters."""
    try:
        _, db = get_mongo_client()
        
        # Build filter
        filter_dict = {}
        if status:
            filter_dict["status"] = status
        if assigned_to:
            filter_dict["assigned_to"] = assigned_to
        if priority:
            filter_dict["priority"] = priority
        
        # Query cases
        cursor = db.cases.find(filter_dict).sort("created_at", -1).skip(offset).limit(limit)
        cases = await cursor.to_list(None)
        
        # Get total count
        total_count = await db.cases.count_documents(filter_dict)
        
        return {
            "cases": cases,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing cases"
        )


@app.get("/cases/{case_id}/sla")
async def get_case_sla(case_id: str):
    """Get SLA information for a case."""
    try:
        _, db = get_mongo_client()
        
        case = await db.cases.find_one({"case_id": case_id})
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        now = datetime.utcnow()
        sla_deadline = case["sla_deadline"]
        
        # Calculate SLA status
        if now > sla_deadline:
            sla_status = "breached"
            time_remaining = None
        else:
            sla_status = "active"
            time_remaining = (sla_deadline - now).total_seconds() / 3600  # hours
        
        return {
            "case_id": case_id,
            "sla_deadline": sla_deadline,
            "sla_status": sla_status,
            "time_remaining_hours": time_remaining,
            "priority": case["priority"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SLA info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting SLA info"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("CASE_SVC_PORT", 8005))
    uvicorn.run(app, host="0.0.0.0", port=port)
