"""Ingest service for transaction and claim events."""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer
from pydantic import ValidationError

from shared.schemas.events import TransactionEvent, ClaimEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Ingest Service",
    description="Service for ingesting transaction and claim events",
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

# Kafka producer
kafka_producer = None


def get_kafka_producer() -> KafkaProducer:
    """Get or create Kafka producer."""
    global kafka_producer
    if kafka_producer is None:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        kafka_producer = KafkaProducer(
            bootstrap_servers=[bootstrap_servers],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=3,
            acks='all'
        )
    return kafka_producer


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Ingest Service")
    # Initialize Kafka producer
    get_kafka_producer()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global kafka_producer
    if kafka_producer:
        kafka_producer.close()
    logger.info("Shutting down Ingest Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ingest-svc", "timestamp": datetime.utcnow().isoformat()}


@app.post("/txn")
async def ingest_transaction(event_data: Dict[str, Any]):
    """Ingest a transaction event."""
    try:
        # Add event_id if not present
        if "event_id" not in event_data:
            event_data["event_id"] = str(uuid.uuid4())
        
        # Validate the event
        transaction_event = TransactionEvent(**event_data)
        
        # Convert to dict for Kafka
        event_dict = transaction_event.dict()
        event_dict["timestamp"] = event_dict["timestamp"].isoformat()
        
        # Produce to Kafka
        producer = get_kafka_producer()
        producer.send(
            "events.txns.v1",
            key=event_dict["entity_id"],
            value=event_dict
        )
        
        logger.info(f"Transaction event ingested: {event_dict['event_id']}")
        
        return {
            "status": "success",
            "event_id": event_dict["event_id"],
            "message": "Transaction event ingested successfully"
        }
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e}"
        )
    except Exception as e:
        logger.error(f"Error ingesting transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/claim")
async def ingest_claim(event_data: Dict[str, Any]):
    """Ingest a claim event."""
    try:
        # Add event_id if not present
        if "event_id" not in event_data:
            event_data["event_id"] = str(uuid.uuid4())
        
        # Validate the event
        claim_event = ClaimEvent(**event_data)
        
        # Convert to dict for Kafka
        event_dict = claim_event.dict()
        event_dict["timestamp"] = event_dict["timestamp"].isoformat()
        
        # Produce to Kafka
        producer = get_kafka_producer()
        producer.send(
            "events.claims.v1",
            key=event_dict["entity_id"],
            value=event_dict
        )
        
        logger.info(f"Claim event ingested: {event_dict['event_id']}")
        
        return {
            "status": "success",
            "event_id": event_dict["event_id"],
            "message": "Claim event ingested successfully"
        }
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e}"
        )
    except Exception as e:
        logger.error(f"Error ingesting claim: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("INGEST_SVC_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
