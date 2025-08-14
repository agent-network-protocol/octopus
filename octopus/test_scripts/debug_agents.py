#!/usr/bin/env python3
"""
Debug script to check agent registration and router state.
"""

from octopus.agents.text_processor_agent import TextProcessorAgent
from octopus.master_agent import MasterAgent
from octopus.router.agents_router import router
from octopus.utils.log_base import setup_enhanced_logging

# Setup logging
logger = setup_enhanced_logging()


def main():
    """Debug agent registration."""
    try:
        # Initialize agents
        text_processor = TextProcessorAgent()
        text_processor.initialize()

        master_agent = MasterAgent()
        master_agent.initialize()

        # Check router state
        logger.info("=== Router State ===")
        agents = router.list_agents()
        logger.info(f"Total agents: {len(agents)}")

        for agent in agents:
            logger.info(f"Agent: {agent['name']}")
            logger.info(f"  Description: {agent['description']}")
            logger.info(f"  Methods: {agent['methods']}")
            logger.info(f"  Status: {agent['status']}")

            # Check registration details
            registration = router.get_agent(agent["name"])
            if registration:
                logger.info(
                    f"  Registration methods: {list(registration.methods.keys())}"
                )
                for method_name, method_info in registration.methods.items():
                    logger.info(f"    {method_name}: {method_info.description}")
            else:
                logger.info("  No registration found")

            logger.info("-" * 30)

        # Test MasterAgent capabilities
        logger.info("\n=== MasterAgent Capabilities ===")
        capabilities = master_agent._get_agent_capabilities()
        logger.info(f"Capabilities found: {len(capabilities)}")

        for cap in capabilities:
            logger.info(f"Agent: {cap['name']}")
            logger.info(f"  Description: {cap['description']}")
            logger.info(f"  Methods: {list(cap['methods'].keys())}")
            logger.info("-" * 30)

    except Exception as e:
        logger.error(f"Error in debug: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
