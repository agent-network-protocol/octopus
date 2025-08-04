"""
RPC Services for Octopus Agent System

This module contains specialized classes for handling RPC operations:
- OpenRPCGenerator: Generates OpenRPC specifications
- JSONRPCHandler: Handles JSON-RPC requests and responses

These classes are used by AgentRouter to provide RPC functionality
while maintaining clear separation of concerns.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class OpenRPCGenerator:
    """
    Specialized class for generating OpenRPC specifications from agent definitions.
    
    This class is responsible for:
    - Converting agent methods to OpenRPC format
    - Applying access level filtering
    - Generating complete OpenRPC specifications
    """
    
    def __init__(self, agent_router):
        """
        Initialize the OpenRPC generator.
        
        Args:
            agent_router: Reference to AgentRouter instance
        """
        self.agent_router = agent_router
    
    def generate_interface(self, base_url: str, app_version: str = "1.0.0") -> Dict[str, Any]:
        """
        Generate complete OpenRPC interface specification.
        
        Args:
            base_url: Base URL for the API server
            app_version: Application version
            
        Returns:
            OpenRPC specification dictionary
        """
        methods = []
        components_schemas = {}
        
        agents_list = self.agent_router.list_agents()
        
        for agent in agents_list:
            agent_name = agent["name"]
            agent_registration = self.agent_router.get_agent(agent_name)
            
            if not agent_registration or not agent_registration.methods:
                continue
            
            for method_name, method_info in agent_registration.methods.items():
                # Only include methods that are external or both (not internal-only)
                access_level = getattr(method_info, 'access_level', 'internal')
                if access_level not in ['external', 'both']:
                    logger.debug(f"Skipping internal method {agent_name}.{method_name}")
                    continue
                
                # Create OpenRPC method definition
                openrpc_method = {
                    "name": f"{agent_name}.{method_name}",
                    "summary": method_info.description or f"{method_name} method",
                    "description": method_info.docstring or method_info.description,
                    "params": self._convert_params_to_openrpc(method_info.parameters),
                    "result": {
                        "name": f"{method_name}Result",
                        "description": f"Result of {method_name} operation",
                        "schema": self._convert_return_type_to_schema(method_info.returns)
                    }
                }
                methods.append(openrpc_method)
        
        return {
            "openrpc": "1.3.2",
            "info": {
                "title": "Octopus Multi-Agent System API",
                "version": app_version,
                "description": "OpenRPC API for Octopus multi-agent system"
            },
            "servers": [
                {
                    "name": "Production Server",
                    "url": f"{base_url}/agents/jsonrpc",
                    "description": "Production server for Octopus API"
                }
            ],
            "methods": methods,
            "components": {
                "schemas": components_schemas
            }
        }
    
    def _convert_params_to_openrpc(self, parameters: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert agent method parameters to OpenRPC format."""
        params = []
        
        for param_name, param_info in parameters.items():
            param_type = param_info.get("type", "string")
            param_schema = {
                "type": self._python_type_to_json_type(param_type)
            }
            
            # Add format for specific types
            if param_type in ["datetime", "date"]:
                param_schema["format"] = "date-time" if param_type == "datetime" else "date"
            
            openrpc_param = {
                "name": param_name,
                "description": param_info.get("description", f"Parameter {param_name}"),
                "required": param_info.get("required", True),
                "schema": param_schema
            }
            params.append(openrpc_param)
        
        return params
    
    def _convert_return_type_to_schema(self, return_type: str) -> Dict[str, Any]:
        """Convert return type to JSON schema."""
        if return_type in ["dict", "Dict", "Dict[str, Any]"]:
            return {"type": "object"}
        elif return_type in ["list", "List", "List[Any]"]:
            return {"type": "array"}
        else:
            return {"type": self._python_type_to_json_type(return_type)}
    
    def _python_type_to_json_type(self, python_type: str) -> str:
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
            "Any": "string",
            "None": "null",
            "datetime": "string",
            "date": "string"
        }
        
        # Handle complex types
        if "[" in python_type:
            base_type = python_type.split("[")[0].strip()
            return type_mapping.get(base_type, "string")
        
        return type_mapping.get(python_type, "string")


class JSONRPCHandler:
    """
    Specialized class for handling JSON-RPC requests and responses.
    
    This class is responsible for:
    - Parsing JSON-RPC requests
    - Enforcing access level controls
    - Executing agent methods
    - Formatting JSON-RPC responses
    """
    
    def __init__(self, agent_router):
        """
        Initialize the JSON-RPC handler.
        
        Args:
            agent_router: Reference to AgentRouter instance
        """
        self.agent_router = agent_router
    
    def handle_call(self, method: str, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle a JSON-RPC method call with access level enforcement.
        
        Args:
            method: Method name in format "agent_name.method_name"
            params: Method parameters
            request_id: JSON-RPC request ID
            
        Returns:
            JSON-RPC response dictionary
        """
        try:
            logger.info(f"Handling JSON-RPC call: {method}")
            
            # Parse method name (format: agent_name.method_name)
            if "." not in method:
                return self._create_error_response(
                    request_id, -32601, "Method not found",
                    f"Invalid method format. Expected 'agent_name.method_name', got '{method}'"
                )
            
            agent_name, method_name = method.split(".", 1)
            
            # Check if method is allowed for external access
            if not self._is_method_accessible(agent_name, method_name):
                logger.warning(f"Access denied: Method {agent_name}.{method_name} is internal only")
                return self._create_error_response(
                    request_id, -32601, "Method not found",
                    f"Method '{method}' is not available for external access"
                )
            
            # Execute agent method
            try:
                result = self.agent_router.execute_agent_method(agent_name, method_name, params)
                return self._create_success_response(request_id, result)
                
            except ValueError as e:
                return self._create_error_response(
                    request_id, -32601, "Method not found", str(e)
                )
            except Exception as e:
                logger.error(f"Error executing {method}: {str(e)}")
                return self._create_error_response(
                    request_id, -32603, "Internal error", str(e)
                )
                
        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {str(e)}")
            return self._create_error_response(
                request_id, -32700, "Parse error", str(e)
            )
    
    def _is_method_accessible(self, agent_name: str, method_name: str) -> bool:
        """
        Check if a method is accessible for external calls.
        
        Args:
            agent_name: Name of the agent
            method_name: Name of the method
            
        Returns:
            True if method is accessible externally, False otherwise
        """
        agent_registration = self.agent_router.get_agent(agent_name)
        if not agent_registration or method_name not in agent_registration.methods:
            return False
        
        method_info = agent_registration.methods[method_name]
        access_level = getattr(method_info, 'access_level', 'internal')
        
        return access_level in ['external', 'both']
    
    def _create_success_response(self, request_id: str, result: Any) -> Dict[str, Any]:
        """Create a successful JSON-RPC response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    def _create_error_response(self, request_id: str, code: int, message: str, data: str = None) -> Dict[str, Any]:
        """Create an error JSON-RPC response."""
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        
        if data:
            error_response["error"]["data"] = data
        
        return error_response


