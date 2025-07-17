"""
Test script for Octopus Agent API endpoints.
"""

import asyncio
import json
import logging
from typing import Dict, Any

import httpx

from octopus.config.settings import get_settings
from octopus.utils.log_base import setup_enhanced_logging


# Initialize logging
setup_enhanced_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# API base URL
BASE_URL = f"http://{settings.host}:{settings.port}"


async def test_agent_description():
    """Test the agent description endpoint."""
    logger.info("Testing agent description endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/agents/ad.json")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Agent description endpoint working")
                logger.info(f"Found agent: {data.get('name')}")
                logger.info(f"Number of interfaces: {len(data.get('ad:interfaces', []))}")
                logger.info(f"Number of resources: {len(data.get('ad:resources', []))}")
                
                # Print some interface examples
                interfaces = data.get('ad:interfaces', [])
                if interfaces:
                    logger.info("Sample interfaces:")
                    for i, interface in enumerate(interfaces[:3]):  # Show first 3
                        method = interface.get('schema', {}).get('method', 'Unknown')
                        description = interface.get('schema', {}).get('description', 'No description')
                        logger.info(f"  {i+1}. {method}: {description}")
                
                return True
            else:
                logger.error(f"❌ Agent description endpoint failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing agent description: {str(e)}")
            return False


async def test_agents_list():
    """Test the agents list endpoint."""
    logger.info("Testing agents list endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/agents")
            
            if response.status_code == 200:
                data = response.json()
                agents = data.get('agents', [])
                logger.info(f"✅ Agents list endpoint working - Found {len(agents)} agents")
                
                for agent in agents:
                    logger.info(f"  - {agent['name']}: {agent['description']}")
                
                return True
            else:
                logger.error(f"❌ Agents list endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing agents list: {str(e)}")
            return False


async def test_jsonrpc_call():
    """Test JSON-RPC call to an agent method."""
    logger.info("Testing JSON-RPC call...")
    
    # Test call to text processor
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": "text_processor.count_words",
        "params": {
            "text": "Hello world, this is a test message for counting words."
        },
        "id": "test-1"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/agents/jsonrpc",
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("error"):
                    logger.warning(f"⚠️ JSON-RPC call returned error: {data['error']}")
                    return False
                else:
                    logger.info("✅ JSON-RPC call successful")
                    logger.info(f"Result: {json.dumps(data.get('result'), indent=2)}")
                    return True
            else:
                logger.error(f"❌ JSON-RPC call failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing JSON-RPC call: {str(e)}")
            return False


async def test_master_agent_call():
    """Test JSON-RPC call to master agent."""
    logger.info("Testing master agent JSON-RPC call...")
    
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": "master_agent.get_status",
        "params": {},
        "id": "test-master-1"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/agents/jsonrpc",
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("error"):
                    logger.warning(f"⚠️ Master agent call returned error: {data['error']}")
                    return False
                else:
                    logger.info("✅ Master agent call successful")
                    logger.info(f"Result: {json.dumps(data.get('result'), indent=2)}")
                    return True
            else:
                logger.error(f"❌ Master agent call failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing master agent call: {str(e)}")
            return False


async def test_agent_info():
    """Test individual agent info endpoint."""
    logger.info("Testing agent info endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test text processor agent info
            response = await client.get(f"{BASE_URL}/api/agents/text_processor/info")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Agent info endpoint working")
                logger.info(f"Agent: {data.get('name')} v{data.get('version')}")
                logger.info(f"Methods: {list(data.get('methods', {}).keys())}")
                return True
            else:
                logger.error(f"❌ Agent info endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing agent info: {str(e)}")
            return False


async def run_all_tests():
    """Run all API tests."""
    logger.info(f"Starting API tests for {BASE_URL}")
    logger.info("=" * 50)
    
    tests = [
        ("Agent Description", test_agent_description),
        ("Agents List", test_agents_list),
        ("Agent Info", test_agent_info),
        ("JSON-RPC Text Processor", test_jsonrpc_call),
        ("JSON-RPC Master Agent", test_master_agent_call),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running test: {test_name}")
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"❌ Test {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
    else:
        logger.warning(f"⚠️ {total - passed} tests failed")
    
    return passed == total


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1) 