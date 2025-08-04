#!/usr/bin/env python3
"""
Test script for verifying the new ANP format ad.json and OpenRPC interface.
"""

import json
import requests
from typing import Dict, Any

# Test server configuration
BASE_URL = "http://localhost:8000"

def test_ad_json():
    """Test the /ad.json endpoint to verify ANP format."""
    print("=" * 80)
    print("Testing /ad.json endpoint")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/ad.json")
        response.raise_for_status()
        
        ad_data = response.json()
        
        # Verify ANP format structure
        print("\n1. Verifying ANP format structure:")
        assert ad_data.get("protocolType") == "ANP", "Missing or incorrect protocolType"
        assert ad_data.get("protocolVersion") == "1.0.0", "Missing or incorrect protocolVersion"
        assert ad_data.get("type") == "AgentDescription", "Missing or incorrect type"
        print("✓ Basic ANP structure verified")
        
        # Verify interfaces
        print("\n2. Checking interfaces:")
        interfaces = ad_data.get("interfaces", [])
        assert len(interfaces) > 0, "No interfaces found"
        
        for interface in interfaces:
            assert interface.get("type") == "StructuredInterface", "Invalid interface type"
            assert interface.get("protocol") == "openrpc", "Invalid protocol"
            assert "content" in interface, "Missing interface content"
            
            # Verify OpenRPC content
            openrpc_content = interface["content"]
            assert openrpc_content.get("openrpc") == "1.3.2", "Invalid OpenRPC version"
            assert "methods" in openrpc_content, "Missing methods in OpenRPC"
            
            print(f"✓ Found {len(openrpc_content['methods'])} OpenRPC methods")
            
            # Display methods with access levels
            print("\n3. Available methods:")
            for method in openrpc_content["methods"]:
                print(f"   - {method['name']}: {method.get('summary', 'No summary')}")
        
        # Pretty print the full response
        print("\n4. Full ad.json response:")
        print(json.dumps(ad_data, indent=2))
        
    except requests.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
    except AssertionError as e:
        print(f"❌ Validation Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


def test_jsonrpc_call(method: str, params: Dict[str, Any] = None):
    """Test JSON-RPC call to an agent method."""
    print("\n" + "=" * 80)
    print(f"Testing JSON-RPC call: {method}")
    print("=" * 80)
    
    request_data = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": "test-1"
    }
    
    print(f"\nRequest: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/agents/jsonrpc",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"\nResponse: {json.dumps(result, indent=2)}")
        
        if "error" in result:
            print(f"❌ Error: {result['error']['message']}")
        else:
            print("✓ Success")
            
    except requests.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


def main():
    """Run all tests."""
    print("ANP ad.json and OpenRPC Test Suite")
    print("==================================")
    
    # Test 1: Verify ad.json format
    test_ad_json()
    
    # Test 2: Test external method (should work)
    test_jsonrpc_call(
        "message.send_message",
        {
            "message_content": "Hello from JSON-RPC test",
            "recipient_did": "did:example:recipient123"
        }
    )
    
    # Test 3: Test internal method (should fail)
    test_jsonrpc_call(
        "message.receive_message",
        {
            "message_content": "This should fail",
            "sender_did": "did:example:sender123"
        }
    )
    
    # Test 4: Test external-only method
    test_jsonrpc_call(
        "message.get_message_history",
        {
            "other_did": "did:example:other123",
            "limit": 10
        }
    )
    
    # Test 5: Test method with no parameters
    test_jsonrpc_call("message.get_statistics")
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()