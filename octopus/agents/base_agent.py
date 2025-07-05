"""
Base agent class for all agents in the Octopus system.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
import inspect
from dataclasses import dataclass, field


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Agent information structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str = None, description: str = None, **kwargs):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name
            description: Agent description
            **kwargs: Additional configuration parameters
        """
        # Generate unique agent ID
        self.agent_id = str(uuid.uuid4())
        
        # Set agent info
        self.info = AgentInfo(
            id=self.agent_id,
            name=name or self.__class__.__name__,
            description=description or self.__class__.__doc__ or "No description provided",
            version=kwargs.get("version", "1.0.0"),
            tags=kwargs.get("tags", []),
            dependencies=kwargs.get("dependencies", [])
        )
        
        # Initialize logger for this agent
        self.logger = logging.getLogger(f"{__name__}.{self.info.name}")
        
        # Agent state management
        self._state = {
            "initialized": False,
            "last_activity": None,
            "execution_count": 0,
            "error_count": 0,
            "total_execution_time": 0.0
        }
        
        # Resource management
        self._resources = {}
        
        # Configuration
        self.config = kwargs.get("config", {})
        
        # Initialize the agent
        self._initialize()
        
    def _initialize(self):
        """Initialize agent resources and state."""
        try:
            self.logger.info(f"Initializing agent: {self.info.name} (ID: {self.agent_id})")
            
            # Call custom initialization if implemented
            self.initialize()
            
            self._state["initialized"] = True
            self._state["last_activity"] = datetime.now()
            
            self.logger.info(f"Agent {self.info.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.info.name}: {str(e)}")
            raise
    
    def initialize(self):
        """
        Custom initialization method for derived classes.
        Override this method to perform agent-specific initialization.
        """
        pass
    
    def cleanup(self):
        """
        Cleanup agent resources.
        Override this method to perform agent-specific cleanup.
        """
        pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
    
    def update_state(self, key: str, value: Any):
        """Update agent state."""
        self._state[key] = value
        self._state["last_activity"] = datetime.now()
    
    def get_state(self, key: str = None) -> Any:
        """Get agent state."""
        if key:
            return self._state.get(key)
        return self._state.copy()
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "id": self.info.id,
            "name": self.info.name,
            "description": self.info.description,
            "version": self.info.version,
            "status": self.info.status,
            "tags": self.info.tags,
            "dependencies": self.info.dependencies,
            "created_at": self.info.created_at.isoformat(),
            "state": self.get_state(),
            "capabilities": self.info.capabilities
        }
    
    def set_status(self, status: str):
        """Set agent status."""
        valid_statuses = ["active", "inactive", "error", "maintenance"]
        if status in valid_statuses:
            self.info.status = status
            self.logger.info(f"Agent {self.info.name} status changed to: {status}")
        else:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
    
    def add_capability(self, name: str, metadata: Dict[str, Any]):
        """Add a capability to the agent."""
        self.info.capabilities[name] = metadata
        self.logger.debug(f"Added capability '{name}' to agent {self.info.name}")
    
    def execute_with_tracking(self, method_name: str, *args, **kwargs) -> Any:
        """Execute a method with performance tracking."""
        start_time = datetime.now()
        
        try:
            # Get the method
            method = getattr(self, method_name, None)
            if not method:
                raise AttributeError(f"Method '{method_name}' not found in agent {self.info.name}")
            
            # Execute the method
            self.logger.debug(f"Executing method '{method_name}' on agent {self.info.name}")
            result = method(*args, **kwargs)
            
            # Update statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._state["execution_count"] += 1
            self._state["total_execution_time"] += execution_time
            self._state["last_activity"] = datetime.now()
            
            self.logger.debug(f"Method '{method_name}' executed successfully in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            self._state["error_count"] += 1
            self.logger.error(f"Error executing method '{method_name}': {str(e)}")
            raise
    
    def validate_parameters(self, method_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate method parameters against method signature.
        
        Args:
            method_name: Name of the method to validate parameters for
            parameters: Parameters to validate
            
        Returns:
            Validated and processed parameters
        """
        method = getattr(self, method_name, None)
        if not method:
            raise AttributeError(f"Method '{method_name}' not found")
        
        # Get method signature
        sig = inspect.signature(method)
        
        # Validate parameters
        validated_params = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            if param_name in parameters:
                validated_params[param_name] = parameters[param_name]
            elif param.default != inspect.Parameter.empty:
                validated_params[param_name] = param.default
            else:
                raise ValueError(f"Required parameter '{param_name}' missing for method '{method_name}'")
        
        return validated_params
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"<{self.__class__.__name__}(id={self.agent_id}, name={self.info.name})>"
    