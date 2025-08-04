"""
Agent Description Router for Octopus API.
Provides agent description information and JSON-RPC interfaces.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from octopus.router.agents_router import router as agent_router
from octopus.config.settings import get_settings


logger = logging.getLogger(__name__)
router = APIRouter()

# Get settings
settings = get_settings()

# Default domain for agent descriptions
AGENT_DESCRIPTION_JSON_DOMAIN = f"{settings.host}:{settings.port}"
DID_DOMAIN = "didhost.cc"
DID_PATH = "test:public"

class JSONRPCRequest(BaseModel):
    """JSON-RPC request model."""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: str


class JSONRPCResponse(BaseModel):
    """JSON-RPC response model."""
    jsonrpc: str = "2.0"
    result: Any = None
    error: Dict[str, Any] = None
    id: str


@router.get("/ad.json")
async def get_agents_description():
    """
    Provide agent description information in ANP format with OpenRPC interfaces.
    
    Returns:
        Agent description in ANP format with embedded OpenRPC interface
    """
    try:
        logger.info("Generating agent description (ad.json)")
        
        # Get all registered agents
        agents_list = agent_router.list_agents()
        logger.info(f"Found {len(agents_list)} registered agents")
        
        if not agents_list:
            raise HTTPException(status_code=500, detail="No agents registered")
        
        # Generate OpenRPC interface for all agents
        openrpc_interface = agent_router.generate_openrpc_interface(
            base_url=f"http://{AGENT_DESCRIPTION_JSON_DOMAIN}",
            app_version=settings.app_version
        )
        
        # Create agent description in ANP format
        agent_description = {
            "protocolType": "ANP",
            "protocolVersion": "1.0.0",
            "type": "AgentDescription",
            "url": f"http://{AGENT_DESCRIPTION_JSON_DOMAIN}/ad.json",
            "name": "Octopus Multi-Agent System",
            "did": f"did:wba:{DID_DOMAIN}:{DID_PATH}",
            "owner": {
                "type": "Organization",
                "name": "Octopus AI",
                "url": f"http://{AGENT_DESCRIPTION_JSON_DOMAIN}"
            },
            "description": "A multi-agent system providing intelligent task delegation and natural language processing. The master agent coordinates with specialized sub-agents to handle various tasks including text processing, data analysis, and more.",
            "created": datetime.now().isoformat() + "Z",
            "securityDefinitions": {
                "didwba_sc": {
                    "scheme": "didwba",
                    "in": "header",
                    "name": "Authorization"
                }
            },
            "security": "didwba_sc",
            "interfaces": [
                {
                    "type": "StructuredInterface",
                    "protocol": "openrpc",
                    "description": "OpenRPC interface for accessing Octopus multi-agent services.",
                    "content": openrpc_interface
                }
            ]
        }
        
        logger.info(f"Generated agent description with {len(openrpc_interface['methods'])} OpenRPC methods")
        
        return JSONResponse(
            content=agent_description,
            media_type="application/json; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error generating agent description: {str(e)}")
        error_response = {
            "error": "Error generating agent description",
            "details": str(e),
        }
        return JSONResponse(
            status_code=500,
            content=error_response,
            media_type="application/json; charset=utf-8",
        )


@router.post("/agents/jsonrpc")
async def handle_jsonrpc_call(request: JSONRPCRequest):
    """
    Handle JSON-RPC calls to agent methods.
    
    Args:
        request: JSON-RPC request
        
    Returns:
        JSON-RPC response
    """
    try:
        # Delegate to agent router for handling
        response_dict = agent_router.handle_jsonrpc_call(
            method=request.method,
            params=request.params,
            request_id=request.id
        )
        
        # Convert response dict to JSONRPCResponse
        if "error" in response_dict:
            return JSONRPCResponse(
                id=response_dict["id"],
                error=response_dict["error"]
            )
        else:
            return JSONRPCResponse(
                id=response_dict["id"],
                result=response_dict["result"]
            )
            
    except Exception as e:
        logger.error(f"Error handling JSON-RPC request: {str(e)}")
        return JSONRPCResponse(
            id=getattr(request, 'id', 'unknown'),
            error={
                "code": -32700,
                "message": "Parse error",
                "data": str(e)
            }
        )


@router.get("/agents/{agent_name}/info")
async def get_agent_info(agent_name: str):
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Agent information including capabilities and methods
    """
    try:
        agent_registration = agent_router.get_agent(agent_name)
        if not agent_registration:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        # Build agent info
        agent_info = {
            "name": agent_registration.name,
            "description": agent_registration.description,
            "version": agent_registration.version,
            "tags": agent_registration.tags,
            "dependencies": agent_registration.dependencies,
            "status": "active" if agent_registration.instance else "not_instantiated",
            "methods": {}
        }
        
        # Add method information
        for method_name, method_info in agent_registration.methods.items():
            agent_info["methods"][method_name] = {
                "description": method_info.description,
                "parameters": method_info.parameters,
                "returns": method_info.returns,
                "deprecated": method_info.deprecated,
                "docstring": method_info.docstring
            }
        
        return JSONResponse(content=agent_info, media_type="application/json; charset=utf-8")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent info for '{agent_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/agents")
async def list_agents():
    """
    List all registered agents.
    
    Returns:
        List of registered agents with basic information
    """
    try:
        agents = agent_router.list_agents()
        return JSONResponse(content={"agents": agents}, media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 