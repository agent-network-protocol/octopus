"""
Agent router for managing and discovering agents with decorator-based registration.
"""

import inspect
import logging
import re
from typing import Any, Dict, List, Optional, Union, Callable, get_type_hints, Type
from functools import wraps
import json
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class MethodInfo:
    """Method information structure."""
    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    returns: str
    docstring: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class AgentRegistration:
    """Agent registration information."""
    name: str
    description: str
    version: str
    class_reference: Type
    module: str
    methods: Dict[str, MethodInfo]
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    instance: Optional[Any] = None


class AgentRouter:
    """Central router for agent registration and discovery."""
    
    _instance = None
    _agents: Dict[str, AgentRegistration] = {}
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(AgentRouter, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the router."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("AgentRouter initialized")
    
    def register(self, agent_info: Dict[str, Any]):
        """Register an agent with the router."""
        name = agent_info.get("name")
        if not name:
            raise ValueError("Agent name is required for registration")
        
        if name in self._agents:
            logger.warning(f"Agent '{name}' is already registered. Overwriting...")
        
        registration = AgentRegistration(
            name=name,
            description=agent_info.get("description", ""),
            version=agent_info.get("version", "1.0.0"),
            class_reference=agent_info.get("class_reference"),
            module=agent_info.get("module", ""),
            methods=agent_info.get("methods", {}),
            tags=agent_info.get("tags", []),
            dependencies=agent_info.get("dependencies", [])
        )
        
        self._agents[name] = registration
        logger.info(f"Registered agent: {name} (version: {registration.version})")
    
    def get_agent(self, name: str) -> Optional[AgentRegistration]:
        """Get an agent registration by name."""
        return self._agents.get(name)
    
    def get_agent_instance(self, name: str) -> Optional[Any]:
        """Get or create an agent instance."""
        registration = self._agents.get(name)
        if not registration:
            return None
        
        # Create instance if not exists
        if not registration.instance:
            try:
                registration.instance = registration.class_reference()
                logger.info(f"Created instance of agent: {name}")
            except Exception as e:
                logger.error(f"Failed to create instance of agent '{name}': {str(e)}")
                return None
        
        return registration.instance
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "name": reg.name,
                "description": reg.description,
                "version": reg.version,
                "tags": reg.tags,
                "methods": list(reg.methods.keys()),
                "status": "active" if reg.instance else "not_instantiated"
            }
            for reg in self._agents.values()
        ]
    
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability/method."""
        agents = []
        for name, registration in self._agents.items():
            if capability in registration.methods:
                agents.append(name)
        return agents
    
    def find_agents_by_tag(self, tag: str) -> List[str]:
        """Find agents by tag."""
        agents = []
        for name, registration in self._agents.items():
            if tag in registration.tags:
                agents.append(name)
        return agents
    
    def execute_agent_method(self, agent_name: str, method_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a method on an agent."""
        # Get agent instance
        agent = self.get_agent_instance(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found or could not be instantiated")
        
        # Get method info
        registration = self._agents[agent_name]
        if method_name not in registration.methods:
            raise ValueError(f"Method '{method_name}' not found in agent '{agent_name}'")
        
        # Validate parameters
        validated_params = agent.validate_parameters(method_name, parameters)
        
        # Execute method
        return agent.execute_with_tracking(method_name, **validated_params)
    
    def get_agent_schema(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the schema of an agent for LLM function calling."""
        registration = self._agents.get(agent_name)
        if not registration:
            return None
        
        functions = []
        for method_name, method_info in registration.methods.items():
            function_schema = {
                "type": "function",
                "function": {
                    "name": f"{agent_name}.{method_name}",
                    "description": method_info.description or method_info.docstring,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Build parameters schema
            for param_name, param_info in method_info.parameters.items():
                param_type = param_info.get("type", "string")
                param_schema = {"type": self._python_type_to_json_type(param_type)}
                
                if "description" in param_info:
                    param_schema["description"] = param_info["description"]
                
                function_schema["function"]["parameters"]["properties"][param_name] = param_schema
                
                if param_info.get("required", True):
                    function_schema["function"]["parameters"]["required"].append(param_name)
            
            functions.append(function_schema)
        
        return {
            "agent": agent_name,
            "description": registration.description,
            "functions": functions
        }
    
    def _python_type_to_json_type(self, python_type: str) -> str:
        """Convert Python type to JSON schema type."""
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "List": "array",
            "Dict": "object",
            "Any": "string"
        }
        
        # Extract base type from complex types
        base_type = python_type.split("[")[0].strip("<>").split(".")[-1]
        return type_mapping.get(base_type, "string")


# Global router instance
router = AgentRouter()


def register_agent(name: str, description: str = "", version: str = "1.0.0", 
                  tags: List[str] = None, dependencies: List[str] = None):
    """
    Decorator for registering an agent class.
    
    Args:
        name: Unique agent identifier
        description: Agent description
        version: Agent version
        tags: Agent tags for categorization
        dependencies: Required dependencies
    """
    def decorator(cls):
        # Prepare agent metadata
        agent_metadata = {
            "name": name,
            "description": description or cls.__doc__ or "",
            "version": version,
            "class_reference": cls,
            "module": cls.__module__,
            "tags": tags or [],
            "dependencies": dependencies or [],
            "methods": {}
        }
        
        # Discover methods with reflection
        for method_name, method_obj in inspect.getmembers(cls, predicate=inspect.ismethod):
            # Skip special methods
            if method_name.startswith("_"):
                continue
            
            # Check if method has agent_method decorator
            if hasattr(method_obj, '_agent_method_meta'):
                method_meta = method_obj._agent_method_meta
                
                # Parse method signature
                try:
                    signature = inspect.signature(method_obj)
                    parameters = {}
                    
                    # Extract parameters
                    for param_name, param in signature.parameters.items():
                        if param_name == 'self':
                            continue
                        
                        param_info = {
                            "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                            "required": param.default == inspect.Parameter.empty,
                        }
                        
                        if param.default != inspect.Parameter.empty:
                            param_info["default"] = param.default
                        
                        # Get description from decorator metadata
                        if param_name in method_meta.get("parameters", {}):
                            param_meta = method_meta["parameters"][param_name]
                            if isinstance(param_meta, dict):
                                param_info.update(param_meta)
                            else:
                                param_info["type"] = param_meta
                        
                        parameters[param_name] = param_info
                    
                    # Create method info
                    method_info = MethodInfo(
                        name=method_name,
                        description=method_meta.get("description", ""),
                        parameters=parameters,
                        returns=method_meta.get("returns", str(signature.return_annotation)),
                        docstring=inspect.getdoc(method_obj) or "",
                        examples=method_meta.get("examples", []),
                        deprecated=method_meta.get("deprecated", False)
                    )
                    
                    agent_metadata["methods"][method_name] = method_info
                    
                except Exception as e:
                    logger.error(f"Failed to parse method '{method_name}' in agent '{name}': {str(e)}")
        
        # Register agent
        router.register(agent_metadata)
        
        # Return the class unchanged
        return cls
    
    return decorator


def agent_method(description: str = "", parameters: Dict[str, Any] = None,
                returns: str = "Any", examples: List[Dict[str, Any]] = None,
                deprecated: bool = False):
    """
    Decorator for marking and documenting agent methods.
    
    Args:
        description: Method description
        parameters: Parameter descriptions
        returns: Return type description
        examples: Usage examples
        deprecated: Whether the method is deprecated
    """
    def decorator(func):
        # Attach metadata to function
        func._agent_method_meta = {
            "description": description,
            "parameters": parameters or {},
            "returns": returns,
            "examples": examples or [],
            "deprecated": deprecated
        }
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class ParameterExtractor:
    """Extract parameters from functions without decorators."""
    
    @staticmethod
    def extract_function_schema(func: Callable) -> Dict[str, Any]:
        """Extract function schema including parameters from signature and docstring."""
        func_name = func.__name__
        func_doc = inspect.getdoc(func) or ""
        
        # Parse docstring for parameter descriptions
        param_descriptions = ParameterExtractor._parse_docstring_params(func_doc)
        
        # Get function signature and type hints
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Extract parameters
        properties = {}
        required = []
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            
            # Get type hint
            param_type = type_hints.get(param_name, param.annotation)
            json_type = ParameterExtractor._python_type_to_json_schema(param_type)
            
            # Build parameter info
            param_info = {
                "type": json_type["type"],
                "description": param_descriptions.get(param_name, f"Parameter {param_name}")
            }
            
            if "items" in json_type:
                param_info["items"] = json_type["items"]
            
            properties[param_name] = param_info
            
            # Check if required
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                param_info["default"] = param.default
        
        # Extract function description
        func_description = func_doc.split('\n')[0] if func_doc else f"Function {func_name}"
        
        return {
            "type": "function",
            "function": {
                "name": func_name,
                "description": func_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        }
    
    @staticmethod
    def _parse_docstring_params(docstring: str) -> Dict[str, str]:
        """Parse parameter descriptions from docstring."""
        param_descriptions = {}
        
        if not docstring:
            return param_descriptions
        
        # Match Google-style docstring
        args_pattern = r'Args:\s*\n((?:\s+\w+[^:]*:.*\n?)*)'
        args_match = re.search(args_pattern, docstring, re.MULTILINE)
        
        if args_match:
            args_section = args_match.group(1)
            param_pattern = r'\s+(\w+)[^:]*:\s*(.+?)(?=\n\s+\w+|\n\s*$|\Z)'
            param_matches = re.findall(param_pattern, args_section, re.MULTILINE | re.DOTALL)
            
            for param_name, description in param_matches:
                param_descriptions[param_name] = description.strip()
        
        return param_descriptions
    
    @staticmethod
    def _python_type_to_json_schema(python_type) -> Dict[str, Any]:
        """Convert Python type to JSON Schema type."""
        if python_type is str:
            return {"type": "string"}
        elif python_type is int:
            return {"type": "integer"}
        elif python_type is float:
            return {"type": "number"}
        elif python_type is bool:
            return {"type": "boolean"}
        elif python_type is dict or python_type is Dict:
            return {"type": "object"}
        elif python_type is list or python_type is List:
            return {"type": "array"}
        
        # Handle generic types
        if hasattr(python_type, '__origin__'):
            origin = python_type.__origin__
            args = python_type.__args__ if hasattr(python_type, '__args__') else []
            
            if origin is list or origin is List:
                if args:
                    item_type = ParameterExtractor._python_type_to_json_schema(args[0])
                    return {"type": "array", "items": item_type}
                return {"type": "array"}
            
            elif origin is dict or origin is Dict:
                return {"type": "object"}
            
            elif origin is Union:
                # Handle Optional types
                if len(args) == 2 and type(None) in args:
                    non_none_type = args[0] if args[1] is type(None) else args[1]
                    return ParameterExtractor._python_type_to_json_schema(non_none_type)
                return {"type": "string"}
        
        return {"type": "string"}
