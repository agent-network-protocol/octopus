#!/usr/bin/env python3
"""
Test script to check OpenAI response format.
"""

import json
from octopus.master_agent import MasterAgent
from octopus.agents.text_processor_agent import TextProcessorAgent
from octopus.utils.log_base import setup_enhanced_logging

# Setup logging
logger = setup_enhanced_logging()

def main():
    """Test OpenAI response format."""
    try:
        # Initialize agents
        text_processor = TextProcessorAgent()
        text_processor.initialize()
        
        master_agent = MasterAgent()
        master_agent.initialize()
        
        # Get capabilities
        capabilities = master_agent._get_agent_capabilities()
        print("Available capabilities:")
        print(json.dumps(capabilities, indent=2, ensure_ascii=False))
        
        # Test a simple request
        print("\nTesting agent selection...")
        result = master_agent._select_agent_for_request(
            "分析情感", 
            capabilities
        )
        print(f"Selection result: {result}")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 