"""
Agent Description Router for Octopus API.
Provides agent description information and JSON-RPC interfaces.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request
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
DID_DOMAIN = "octopus.ai"
DID_PATH = "agents"

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


class AgentSchemaGenerator:
    """Generate JSON-RPC schema for agents."""
    
    @staticmethod
    def generate_agent_interfaces(agent_name: str, agent_registration) -> List[Dict[str, Any]]:
        """Generate JSON-RPC interfaces for an agent."""
        interfaces = []
        
        if not agent_registration or not agent_registration.methods:
            return interfaces
        
        for method_name, method_info in agent_registration.methods.items():
            # Create JSON-RPC interface definition
            interface = {
                "@type": "ad:StructuredInterface",
                "protocol": {
                    "name": "JSON-RPC",
                    "version": "2.0",
                    "transport": "HTTP",
                    "HTTP Method": "POST"
                },
                "schema": {
                    "method": f"{agent_name}.{method_name}",
                    "description": method_info.description or method_info.docstring,
                    "params": AgentSchemaGenerator._convert_params_to_jsonrpc_schema(method_info.parameters),
                    "returns": method_info.returns,
                    "annotations": {
                        "agent": agent_name,
                        "method": method_name,
                        "deprecated": method_info.deprecated
                    }
                },
                "url": f"http://{AGENT_DESCRIPTION_JSON_DOMAIN}/api/agents/jsonrpc"
            }
            interfaces.append(interface)
        
        return interfaces
    
    @staticmethod
    def _convert_params_to_jsonrpc_schema(parameters: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert agent method parameters to JSON-RPC schema."""
        if not parameters:
            return {"type": "object", "properties": {}, "required": []}
        
        properties = {}
        required = []
        
        for param_name, param_info in parameters.items():
            # Extract parameter type
            param_type = param_info.get("type", "string")
            param_schema = {
                "type": AgentSchemaGenerator._python_type_to_json_type(param_type),
                "description": param_info.get("description", f"Parameter {param_name}")
            }
            
            properties[param_name] = param_schema
            
            # Check if parameter is required
            if param_info.get("required", True):
                required.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False
        }
    
    @staticmethod
    def _python_type_to_json_type(python_type: str) -> str:
        """Convert Python type to JSON schema type."""
        type_mapping = {
            "str": "string",
            "int": "integer", 
            "float": "number",
            "bool": "boolean",
            "dict": "object",
            "list": "array",
            "Dict": "object",
            "List": "array",
            "Any": "string"
        }
        
        # Handle complex types
        if "[" in python_type:
            base_type = python_type.split("[")[0].strip()
            return type_mapping.get(base_type, "string")
        
        return type_mapping.get(python_type, "string")


@router.get("/agents/ad.json")
async def get_agents_description():
    """
    Provide comprehensive agent description information with JSON-RPC interfaces.
    
    Returns:
        Agent description in JSON-LD format with JSON-RPC integration
    """
    try:
        logger.info("Generating agent description (ad.json)")
        
        # Get all registered agents
        agents_list = agent_router.list_agents()
        logger.info(f"Found {len(agents_list)} registered agents")
        
        # Find master agent
        master_agent = None
        sub_agents = []
        
        for agent in agents_list:
            if agent["name"] == "master_agent":
                master_agent = agent
            else:
                sub_agents.append(agent)
        
        if not master_agent:
            logger.warning("Master agent not found, using first agent as primary")
            master_agent = agents_list[0] if agents_list else None
        
        if not master_agent:
            raise HTTPException(status_code=500, detail="No agents registered")
        
        # Create main agent description based on master agent
        agent_description = {
            "@context": {
                "@vocab": "https://schema.org/",
                "did": "https://w3id.org/did#", 
                "ad": "https://agent-network-protocol.com/ad#",
            },
            "@type": "ad:AgentDescription",
            "@id": f"http://{AGENT_DESCRIPTION_JSON_DOMAIN}/api/agents/ad.json",
            "name": "Octopus Multi-Agent System",
            "did": f"did:wba:{DID_DOMAIN}:{DID_PATH}",
            "description": "A multi-agent system providing intelligent task delegation and natural language processing. The master agent coordinates with specialized sub-agents to handle various tasks including text processing, data analysis, and more.",
            "version": settings.app_version,
            "owner": {
                "@type": "Organization",
                "name": f"{AGENT_DESCRIPTION_JSON_DOMAIN}",
                "@id": f"https://{AGENT_DESCRIPTION_JSON_DOMAIN}",
            },
            "ad:securityDefinitions": {
                "didwba_sc": {
                    "scheme": "didwba",
                    "in": "header", 
                    "name": "Authorization",
                }
            },
            "ad:security": "didwba_sc",
            "ad:interfaces": [],
            "ad:resources": [],
            "ad:agents": {
                "master": master_agent,
                "sub_agents": sub_agents
            }
        }
        
        # Generate interfaces for master agent
        master_registration = agent_router.get_agent("master_agent")
        if master_registration:
            master_interfaces = AgentSchemaGenerator.generate_agent_interfaces("master_agent", master_registration)
            agent_description["ad:interfaces"].extend(master_interfaces)
            logger.info(f"Added {len(master_interfaces)} interfaces for master agent")
        
        # Generate interfaces for sub-agents
        for sub_agent in sub_agents:
            agent_name = sub_agent["name"]
            agent_registration = agent_router.get_agent(agent_name)
            if agent_registration:
                agent_interfaces = AgentSchemaGenerator.generate_agent_interfaces(agent_name, agent_registration)
                agent_description["ad:interfaces"].extend(agent_interfaces)
                logger.info(f"Added {len(agent_interfaces)} interfaces for agent {agent_name}")
        
        # Add resources (agent capabilities)
        for agent in agents_list:
            resource_item = {
                "@type": "ad:Resource",
                "uri": f"urn:agent:{agent['name']}",
                "name": f"{agent['name']} capabilities",
                "description": agent['description'],
                "mimeType": "application/json",
                "url": f"http://{AGENT_DESCRIPTION_JSON_DOMAIN}/api/agents/{agent['name']}/info"
            }
            agent_description["ad:resources"].append(resource_item)
        
        logger.info(f"Generated agent description with {len(agent_description['ad:interfaces'])} interfaces and {len(agent_description['ad:resources'])} resources")
        
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
        logger.info(f"Handling JSON-RPC call: {request.method}")
        
        # Parse method name (format: agent_name.method_name)
        if "." not in request.method:
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": "Method not found",
                    "data": f"Invalid method format. Expected 'agent_name.method_name', got '{request.method}'"
                }
            )
        
        agent_name, method_name = request.method.split(".", 1)
        
        # Execute agent method
        try:
            result = agent_router.execute_agent_method(agent_name, method_name, request.params)
            return JSONRPCResponse(id=request.id, result=result)
            
        except ValueError as e:
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": "Method not found",
                    "data": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Error executing {request.method}: {str(e)}")
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
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