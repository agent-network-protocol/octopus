"""
Example usage of the Octopus multi-agent system.
"""

import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from octopus.master_agent import MasterAgent
from octopus.agents.text_processor_agent import TextProcessorAgent
from octopus.router.agents_router import router


def demonstrate_system():
    """Demonstrate the Octopus multi-agent system."""
    
    print("=== Octopus Multi-Agent System Demo ===\n")
    
    # 1. Initialize agents
    print("1. Initializing agents...")
    
    # Text processor will be auto-registered via decorator
    text_agent = TextProcessorAgent()
    
    # Initialize master agent (requires OpenAI API key)
    try:
        master = MasterAgent()
        print("✓ Master agent initialized")
    except ValueError as e:
        print(f"✗ Error: {e}")
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    # 2. Show registered agents
    print("\n2. Registered agents:")
    agents = router.list_agents()
    for agent in agents:
        print(f"   - {agent['name']}: {agent['description']}")
        print(f"     Methods: {', '.join(agent['methods'])}")
    
    # 3. Direct agent usage example
    print("\n3. Direct agent usage example:")
    sample_text = """
    The Octopus multi-agent system is an amazing framework for building intelligent applications.
    It provides excellent capabilities for task decomposition and parallel execution.
    The system is designed to be flexible and extensible, making it perfect for various use cases.
    """
    
    # Use text processor directly
    print(f"\nAnalyzing text: '{sample_text[:50]}...'")
    
    word_count = router.execute_agent_method(
        agent_name="text_processor",
        method_name="count_words",
        parameters={"text": sample_text}
    )
    print(f"\nWord count: {word_count}")
    
    keywords = router.execute_agent_method(
        agent_name="text_processor",
        method_name="extract_keywords",
        parameters={"text": sample_text, "top_n": 5}
    )
    print(f"\nTop keywords: {keywords}")
    
    sentiment = router.execute_agent_method(
        agent_name="text_processor",
        method_name="analyze_sentiment",
        parameters={"text": sample_text}
    )
    print(f"\nSentiment: {sentiment}")
    
    # 4. Master agent orchestration example
    print("\n4. Master agent orchestration example:")
    
    # Complex task that requires multiple agents
    complex_task = """
    Analyze the following customer review and provide a comprehensive analysis:
    'I recently purchased this product and I'm extremely happy with it. 
    The quality is outstanding and it works perfectly. Highly recommend!'
    
    Please provide:
    1. Word statistics
    2. Key themes/keywords
    3. Sentiment analysis
    4. A brief summary
    """
    
    print(f"\nTask: {complex_task[:100]}...")
    
    # Process task through master agent
    result = master.process_task(complex_task)
    
    if result["status"] == "success":
        print("\n✓ Task completed successfully!")
        print(f"\nAnalysis objective: {result['analysis']['objective']}")
        print(f"\nExecution plan steps: {len(result['execution_plan'])}")
        for step in result['execution_plan']:
            print(f"   - {step['id']}: {step['description']} [{step['status']}]")
        
        print(f"\nFinal synthesis:")
        print(result['results']['synthesis'])
    else:
        print(f"\n✗ Task failed: {result.get('error', 'Unknown error')}")
    
    # 5. Show task history
    print("\n5. Task history:")
    history = master.get_task_history(limit=5)
    print(f"Total tasks processed: {len(history)}")
    for i, task in enumerate(history, 1):
        print(f"   {i}. {task['task'][:50]}... - {task['timestamp']}")


def demonstrate_direct_usage():
    """Demonstrate direct usage without master agent."""
    
    print("\n=== Direct Agent Usage (No Master) ===\n")
    
    # Initialize text processor
    text_agent = TextProcessorAgent()
    
    # Sample document
    document = """
    Artificial Intelligence is transforming the world. Machine learning algorithms 
    are becoming more sophisticated. Deep learning has revolutionized computer vision 
    and natural language processing. The future of AI is bright but also presents 
    challenges that need careful consideration.
    """
    
    # Analyze document
    print("Analyzing document...")
    
    # Get word statistics
    stats = text_agent.count_words(document)
    print(f"\nDocument statistics: {stats}")
    
    # Extract keywords
    keywords = text_agent.extract_keywords(document, top_n=5)
    print(f"\nTop keywords:")
    for kw in keywords:
        print(f"   - {kw['keyword']}: {kw['frequency']} occurrences")
    
    # Analyze sentiment
    sentiment = text_agent.analyze_sentiment(document)
    print(f"\nSentiment analysis: {sentiment}")
    
    # Generate summary
    summary = text_agent.summarize_text(document, num_sentences=2)
    print(f"\nSummary: {summary['summary']}")


if __name__ == "__main__":
    # Check if running with direct flag
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        demonstrate_direct_usage()
    else:
        demonstrate_system()
    
    print("\n=== Demo completed ===") 