"""
Chat API Router for Octopus web interface.
Provides chat and status endpoints for the web frontend.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from octopus.master_agent import MasterAgent
from octopus.agents.message.message_agent import MessageAgent

logger = logging.getLogger(__name__)
router = APIRouter()

# Global agents instances (will be injected from main app)
master_agent: Optional[MasterAgent] = None
message_agent: Optional[MessageAgent] = None


# Pydantic models for API
class ChatRequest(BaseModel):
    message: str
    timestamp: str


class ChatResponse(BaseModel):
    success: bool
    response: str = None
    error: str = None
    request_id: str
    timestamp: str


class StatusResponse(BaseModel):
    status: str
    message: str = None


def set_agents(master: MasterAgent, message: MessageAgent):
    """Set the global agent instances."""
    global master_agent, message_agent
    master_agent = master
    message_agent = message
    logger.info("Agents injected into chat router")


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get system status for the frontend."""
    logger.debug("Status endpoint accessed")
    
    if master_agent is None or message_agent is None:
        return StatusResponse(
            status="error", 
            message="Agents not initialized"
        )
    
    return StatusResponse(
        status="healthy",
        message="All systems operational"
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message through the master agent."""
    logger.info(f"Chat request received: {request.message[:100]}...")
    
    request_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    try:
        # Check if agents are initialized
        if master_agent is None:
            raise HTTPException(
                status_code=503, 
                detail="Master agent not initialized"
            )
        
        # Process the message through master agent
        response_text = await master_agent.process_natural_language(
            request=request.message,
            request_id=request_id
        )
        
        logger.info(f"Chat response generated for request {request_id}")
        
        return ChatResponse(
            success=True,
            response=response_text,
            request_id=request_id,
            timestamp=timestamp
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request {request_id}: {str(e)}")
        
        return ChatResponse(
            success=False,
            error=str(e),
            request_id=request_id,
            timestamp=timestamp
        ) 