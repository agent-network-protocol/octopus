"""
Agent loader module for Octopus API.
Ensures all agents are properly registered and initialized.
"""

import logging
import importlib
from typing import List


logger = logging.getLogger(__name__)


def load_all_agents() -> List[str]:
    """
    Load and register all available agents.
    
    Returns:
        List of loaded agent names
    """
    loaded_agents = []
    
    # Import and register master agent
    try:
        from octopus.master_agent import MasterAgent
        logger.info("Loaded MasterAgent")
        loaded_agents.append("master_agent")
    except Exception as e:
        logger.error(f"Failed to load MasterAgent: {str(e)}")
    
    # Import and register sub-agents
    agent_modules = [
        ("octopus.agents.text_processor_agent", "TextProcessorAgent"),
        # Add more agent modules here as they are created
    ]
    
    for module_name, class_name in agent_modules:
        try:
            module = importlib.import_module(module_name)
            agent_class = getattr(module, class_name)
            logger.info(f"Loaded {class_name} from {module_name}")
            loaded_agents.append(class_name.lower().replace("agent", ""))
        except Exception as e:
            logger.error(f"Failed to load {class_name} from {module_name}: {str(e)}")
    
    logger.info(f"Successfully loaded {len(loaded_agents)} agents: {loaded_agents}")
    return loaded_agents


def initialize_agents():
    """Initialize all agents by loading their modules."""
    logger.info("Initializing agents...")
    loaded_agents = load_all_agents()
    
    # Import router to access registered agents
    from octopus.router.agents_router import router as agent_router
    
    # Get list of registered agents
    registered_agents = agent_router.list_agents()
    logger.info(f"Registered agents: {[agent['name'] for agent in registered_agents]}")
    
    return loaded_agents 