"""Summary service with provider abstraction for event and case summarization."""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudOps Summary Service",
    description="Service for event and case summarization with provider abstraction",
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


# Pydantic models
class SummaryRequest(BaseModel):
    """Summary request model."""
    event_data: Dict[str, Any]
    decision_data: Optional[Dict[str, Any]] = None
    case_data: Optional[Dict[str, Any]] = None


class SummaryResponse(BaseModel):
    """Summary response model."""
    summary: str
    provider: str
    word_count: int
    pii_redacted: bool


# Abstract base class for summary providers
class SummaryProvider(ABC):
    """Abstract base class for summary providers."""
    
    @abstractmethod
    def summarize(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                 case_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a summary of the event, decision, and case data."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass


class NoneProvider(SummaryProvider):
    """No-op provider that returns a basic summary."""
    
    def summarize(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                 case_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a basic summary without external services."""
        event_id = event_data.get('event_id', 'Unknown')
        amount = event_data.get('amount', event_data.get('claim_amount', 'Unknown'))
        action = decision_data.get('action', 'Unknown') if decision_data else 'Unknown'
        
        summary = f"Transaction {event_id} for amount {amount} was processed with decision {action}. "
        
        if case_data:
            case_id = case_data.get('case_id', 'Unknown')
            status = case_data.get('status', 'Unknown')
            summary += f"Case {case_id} was created with status {status}."
        
        return summary
    
    def get_provider_name(self) -> str:
        return "none"


class OpenAIProvider(SummaryProvider):
    """OpenAI-based summary provider."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI provider")
    
    def summarize(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                 case_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a summary using OpenAI."""
        try:
            # Prepare context
            context = self._prepare_context(event_data, decision_data, case_data)
            
            # Redact PII
            redacted_context = self._redact_pii(context)
            
            # Generate summary
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fraud analyst assistant. Generate a neutral, factual summary of fraud detection events in 120-180 words. Focus on key details like transaction amounts, risk scores, decisions made, and case status. Do not include any personal opinions or recommendations."
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize this fraud detection event:\n\n{redacted_context}"
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating OpenAI summary: {e}")
            # Fallback to basic summary
            return self._generate_fallback_summary(event_data, decision_data, case_data)
    
    def get_provider_name(self) -> str:
        return "openai"
    
    def _prepare_context(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                        case_data: Optional[Dict[str, Any]] = None) -> str:
        """Prepare context for summarization."""
        context_parts = []
        
        # Event data
        context_parts.append("Event Details:")
        context_parts.append(f"- Event ID: {event_data.get('event_id', 'Unknown')}")
        context_parts.append(f"- Amount: {event_data.get('amount', event_data.get('claim_amount', 'Unknown'))}")
        context_parts.append(f"- Channel: {event_data.get('channel', 'Unknown')}")
        context_parts.append(f"- Timestamp: {event_data.get('timestamp', 'Unknown')}")
        
        # Decision data
        if decision_data:
            context_parts.append("\nDecision Details:")
            context_parts.append(f"- Action: {decision_data.get('action', 'Unknown')}")
            context_parts.append(f"- Risk Score: {decision_data.get('risk', 'Unknown')}")
            context_parts.append(f"- Reasons: {', '.join(decision_data.get('reasons', []))}")
        
        # Case data
        if case_data:
            context_parts.append("\nCase Details:")
            context_parts.append(f"- Case ID: {case_data.get('case_id', 'Unknown')}")
            context_parts.append(f"- Status: {case_data.get('status', 'Unknown')}")
            context_parts.append(f"- Priority: {case_data.get('priority', 'Unknown')}")
            context_parts.append(f"- Assigned To: {case_data.get('assigned_to', 'Unassigned')}")
        
        return "\n".join(context_parts)
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII from text."""
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
        
        # Phone numbers (various formats)
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)
        text = re.sub(r'\(\d{3}\)\s*\d{3}[-.]?\d{4}', '[PHONE_REDACTED]', text)
        
        # Credit card numbers (basic pattern)
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]', text)
        
        # SSN (basic pattern)
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
        
        return text
    
    def _generate_fallback_summary(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                                  case_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a fallback summary when OpenAI fails."""
        event_id = event_data.get('event_id', 'Unknown')
        amount = event_data.get('amount', event_data.get('claim_amount', 'Unknown'))
        action = decision_data.get('action', 'Unknown') if decision_data else 'Unknown'
        
        summary = f"A transaction event {event_id} involving amount {amount} was processed through the fraud detection system. "
        summary += f"The system made a decision to {action} the transaction based on risk assessment. "
        
        if case_data:
            case_id = case_data.get('case_id', 'Unknown')
            status = case_data.get('status', 'Unknown')
            summary += f"A case {case_id} was created and is currently in {status} status for further investigation."
        
        return summary


class AzureAIProvider(SummaryProvider):
    """Azure OpenAI-based summary provider."""
    
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
        
        if not all([self.endpoint, self.api_key]):
            raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables are required")
        
        try:
            from azure.ai.openai import AzureOpenAI
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version
            )
        except ImportError:
            raise ImportError("azure-ai-openai package is required for Azure AI provider")
    
    def summarize(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                 case_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a summary using Azure OpenAI."""
        try:
            # Prepare context
            context = self._prepare_context(event_data, decision_data, case_data)
            
            # Redact PII
            redacted_context = self._redact_pii(context)
            
            # Generate summary
            response = self.client.chat.completions.create(
                model="gpt-35-turbo",  # Azure model name
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fraud analyst assistant. Generate a neutral, factual summary of fraud detection events in 120-180 words. Focus on key details like transaction amounts, risk scores, decisions made, and case status. Do not include any personal opinions or recommendations."
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize this fraud detection event:\n\n{redacted_context}"
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating Azure AI summary: {e}")
            # Fallback to basic summary
            return self._generate_fallback_summary(event_data, decision_data, case_data)
    
    def get_provider_name(self) -> str:
        return "azureai"
    
    def _prepare_context(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                        case_data: Optional[Dict[str, Any]] = None) -> str:
        """Prepare context for summarization."""
        context_parts = []
        
        # Event data
        context_parts.append("Event Details:")
        context_parts.append(f"- Event ID: {event_data.get('event_id', 'Unknown')}")
        context_parts.append(f"- Amount: {event_data.get('amount', event_data.get('claim_amount', 'Unknown'))}")
        context_parts.append(f"- Channel: {event_data.get('channel', 'Unknown')}")
        context_parts.append(f"- Timestamp: {event_data.get('timestamp', 'Unknown')}")
        
        # Decision data
        if decision_data:
            context_parts.append("\nDecision Details:")
            context_parts.append(f"- Action: {decision_data.get('action', 'Unknown')}")
            context_parts.append(f"- Risk Score: {decision_data.get('risk', 'Unknown')}")
            context_parts.append(f"- Reasons: {', '.join(decision_data.get('reasons', []))}")
        
        # Case data
        if case_data:
            context_parts.append("\nCase Details:")
            context_parts.append(f"- Case ID: {case_data.get('case_id', 'Unknown')}")
            context_parts.append(f"- Status: {case_data.get('status', 'Unknown')}")
            context_parts.append(f"- Priority: {case_data.get('priority', 'Unknown')}")
            context_parts.append(f"- Assigned To: {case_data.get('assigned_to', 'Unassigned')}")
        
        return "\n".join(context_parts)
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII from text."""
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
        
        # Phone numbers (various formats)
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)
        text = re.sub(r'\(\d{3}\)\s*\d{3}[-.]?\d{4}', '[PHONE_REDACTED]', text)
        
        # Credit card numbers (basic pattern)
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]', text)
        
        # SSN (basic pattern)
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
        
        return text
    
    def _generate_fallback_summary(self, event_data: Dict[str, Any], decision_data: Optional[Dict[str, Any]] = None, 
                                  case_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a fallback summary when Azure AI fails."""
        event_id = event_data.get('event_id', 'Unknown')
        amount = event_data.get('amount', event_data.get('claim_amount', 'Unknown'))
        action = decision_data.get('action', 'Unknown') if decision_data else 'Unknown'
        
        summary = f"A transaction event {event_id} involving amount {amount} was processed through the fraud detection system. "
        summary += f"The system made a decision to {action} the transaction based on risk assessment. "
        
        if case_data:
            case_id = case_data.get('case_id', 'Unknown')
            status = case_data.get('status', 'Unknown')
            summary += f"A case {case_id} was created and is currently in {status} status for further investigation."
        
        return summary


# Provider factory
def create_provider() -> SummaryProvider:
    """Create summary provider based on configuration."""
    provider_name = os.getenv("SUMMARY_PROVIDER", "none").lower()
    
    if provider_name == "none":
        return NoneProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "azureai":
        return AzureAIProvider()
    else:
        logger.warning(f"Unknown provider {provider_name}, falling back to none")
        return NoneProvider()


# Global provider instance
summary_provider = None


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    global summary_provider
    logger.info("Starting Summary Service")
    try:
        summary_provider = create_provider()
        logger.info(f"Summary provider initialized: {summary_provider.get_provider_name()}")
    except Exception as e:
        logger.error(f"Error initializing summary provider: {e}")
        summary_provider = NoneProvider()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Summary Service")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "summary-svc", 
        "provider": summary_provider.get_provider_name() if summary_provider else "none"
    }


@app.post("/summaries/{case_id}", response_model=SummaryResponse)
async def generate_summary(case_id: str, request: SummaryRequest):
    """Generate a summary for a case."""
    try:
        if not summary_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Summary provider not available"
            )
        
        # Generate summary
        summary = summary_provider.summarize(
            request.event_data,
            request.decision_data,
            request.case_data
        )
        
        # Count words
        word_count = len(summary.split())
        
        # Check if PII was redacted (basic check)
        pii_redacted = any(marker in summary for marker in [
            '[EMAIL_REDACTED]', '[PHONE_REDACTED]', '[CARD_REDACTED]', '[SSN_REDACTED]'
        ])
        
        return SummaryResponse(
            summary=summary,
            provider=summary_provider.get_provider_name(),
            word_count=word_count,
            pii_redacted=pii_redacted
        )
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating summary"
        )


@app.post("/summaries/event", response_model=SummaryResponse)
async def generate_event_summary(request: SummaryRequest):
    """Generate a summary for an event."""
    try:
        if not summary_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Summary provider not available"
            )
        
        # Generate summary
        summary = summary_provider.summarize(
            request.event_data,
            request.decision_data,
            request.case_data
        )
        
        # Count words
        word_count = len(summary.split())
        
        # Check if PII was redacted (basic check)
        pii_redacted = any(marker in summary for marker in [
            '[EMAIL_REDACTED]', '[PHONE_REDACTED]', '[CARD_REDACTED]', '[SSN_REDACTED]'
        ])
        
        return SummaryResponse(
            summary=summary,
            provider=summary_provider.get_provider_name(),
            word_count=word_count,
            pii_redacted=pii_redacted
        )
        
    except Exception as e:
        logger.error(f"Error generating event summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating event summary"
        )


@app.get("/providers")
async def get_available_providers():
    """Get available summary providers."""
    providers = ["none"]
    
    # Check if OpenAI is available
    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")
    
    # Check if Azure AI is available
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        providers.append("azureai")
    
    return {
        "available_providers": providers,
        "current_provider": summary_provider.get_provider_name() if summary_provider else "none"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SUMMARY_SVC_PORT", 8008))
    uvicorn.run(app, host="0.0.0.0", port=port)
