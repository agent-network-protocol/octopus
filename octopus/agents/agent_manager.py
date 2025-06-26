"""
Agent manager for handling multiple agents in the Octopus system.
"""

import logging
from typing import Dict, List, Optional, Any
from octopus.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentManager:
    """Manager for handling multiple agents."""
    
    def __init__(self, max_agents: int = 100):
        """Initialize the agent manager."""
        self.max_agents = max_agents
        self.agents: Dict[str, BaseAgent] = {}
        logger.info(f"Initialized AgentManager with max_agents={max_agents}")
    
    async def register_agent(self, agent: BaseAgent) -> bool:
        """Register a new agent."""
        if len(self.agents) >= self.max_agents:
            logger.warning(f"Cannot register agent {agent.name}: max agents limit reached")
            return False
        
        if agent.agent_id in self.agents:
            logger.warning(f"Agent with ID {agent.agent_id} already exists")
            return False
        
        self.agents[agent.agent_id] = agent
        await agent.initialize()
        logger.info(f"Registered agent {agent.name} with ID: {agent.agent_id}")
        return True
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id not in self.agents:
            logger.warning(f"Agent with ID {agent_id} not found")
            return False
        
        agent = self.agents[agent_id]
        await agent.shutdown()
        del self.agents[agent_id]
        logger.info(f"Unregistered agent {agent.name}")
        return True
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [agent.get_info() for agent in self.agents.values()]
    
    async def execute_task(self, agent_id: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a task with a specific agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent with ID {agent_id} not found")
            return None
        
        try:
            result = await agent.execute(task)
            logger.info(f"Task executed successfully by agent {agent.name}")
            return result
        except Exception as e:
            logger.error(f"Error executing task with agent {agent.name}: {e}")
            return None
    
    async def shutdown_all(self) -> None:
        """Shutdown all agents."""
        logger.info("Shutting down all agents")
        for agent in self.agents.values():
            await agent.shutdown()
        self.agents.clear()
        logger.info("All agents shut down") 