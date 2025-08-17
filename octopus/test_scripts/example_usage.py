#!/usr/bin/env python3
"""
Example usage of the MasterAgent with natural language interface.
"""

from octopus.agents.text_processor_agent import TextProcessorAgent
from octopus.master_agent import MasterAgent
from octopus.utils.log_base import get_logger

# Get logger - logging is automatically initialized
logger = get_logger(__name__)


def main():
    """Example usage of the MasterAgent."""
    try:
        # Initialize the TextProcessorAgent first (to have something to delegate to)
        text_processor = TextProcessorAgent()
        text_processor.initialize()

        # Initialize the MasterAgent
        master_agent = MasterAgent()
        master_agent.initialize()

        # Example natural language requests
        test_requests = [
            {
                "request": "请帮我分析一下这段文本的情感：我今天很开心，因为完成了一个重要的项目。",
                "request_id": "req_001",
            },
            {
                "request": "统计这段文本的词频：Python is a powerful programming language. Python is easy to learn.",
                "request_id": "req_002",
            },
            {
                "request": "从这段文本中提取关键词：人工智能是当今科技发展的重要方向，机器学习和深度学习技术正在改变我们的生活。",
                "request_id": "req_003",
            },
        ]

        # Process each request
        for i, test_request in enumerate(test_requests, 1):
            logger.info(f"\n=== Test {i}: {test_request['request_id']} ===")
            logger.info(f"Request: {test_request['request']}")

            # Use the natural language interface
            response = master_agent.process_natural_language(
                request=test_request["request"], request_id=test_request["request_id"]
            )

            logger.info(f"Response: {response}")
            print(f"\nTest {i} Response:")
            print(response)
            print("-" * 50)

        # Test status endpoint
        logger.info("\n=== Testing Status Endpoint ===")
        status = master_agent.get_status()
        logger.info(f"Master Agent Status: {status}")
        print("\nMaster Agent Status:")
        print(status)

    except Exception as e:
        logger.error(f"Error in example usage: {str(e)}")
        print(f"Error: {str(e)}")

    finally:
        # Cleanup
        if "master_agent" in locals():
            master_agent.cleanup()
        if "text_processor" in locals():
            text_processor.cleanup()


if __name__ == "__main__":
    main()
