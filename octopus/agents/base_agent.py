"""
Base agent class for all agents in the Octopus system.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: Optional[str] = None, name: Optional[str] = None):
        """Initialize the base agent."""
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name or f"Agent_{self.agent_id[:8]}"
        self.created_at = datetime.utcnow()
        self.status = "initialized"
        self.metadata: Dict[str, Any] = {}
        
        logger.info(f"Initialized agent {self.name} with ID: {self.agent_id}")
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task with the agent."""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent for operation."""
        pass
    
    async def shutdown(self) -> bool:
        """Shutdown the agent gracefully."""
        logger.info(f"Shutting down agent {self.name}")
        self.status = "shutdown"
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        } 