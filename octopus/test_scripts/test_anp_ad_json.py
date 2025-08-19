#!/usr/bin/env python3
"""
Test script for verifying the new ANP format ad.json and OpenRPC interface.
"""

import asyncio
import json
import os
import sys
import traceback
from typing import Any

import httpx

# Disable proxy for local testing
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)

# Test server configuration
from octopus.config.settings import get_settings

settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"

# Test configuration
TIMEOUT_SECONDS = 10

# HTTP client configuration
HTTP_CLIENT_CONFIG = {"timeout": TIMEOUT_SECONDS}


async def test_ad_json():
    """Test the /ad.json endpoint to verify ANP format."""
    print("=" * 80)
    print("Testing /ad.json endpoint")
    print("=" * 80)

    async with httpx.AsyncClient(**HTTP_CLIENT_CONFIG) as client:
        try:
            response = await client.get(f"{BASE_URL}/ad.json")
            response.raise_for_status()

            ad_data = response.json()

            # Verify ANP format structure
            print("\n1. Verifying ANP format structure:")
            assert (
                ad_data.get("protocolType") == "ANP"
            ), f"Expected protocolType 'ANP', got {ad_data.get('protocolType')}"
            assert (
                ad_data.get("protocolVersion") == "1.0.0"
            ), f"Expected protocolVersion '1.0.0', got {ad_data.get('protocolVersion')}"
            assert (
                ad_data.get("type") == "AgentDescription"
            ), f"Expected type 'AgentDescription', got {ad_data.get('type')}"
            print("✓ Basic ANP structure verified")

            # Verify required fields
            print("\n2. Verifying required fields:")
            required_fields = [
                "url",
                "name",
                "did",
                "owner",
                "description",
                "created",
                "interfaces",
            ]
            for field in required_fields:
                assert field in ad_data, f"Missing required field: {field}"
            print("✓ All required fields present")

            # Verify security definitions
            print("\n3. Verifying security definitions:")
            assert "securityDefinitions" in ad_data, "Missing securityDefinitions"
            assert "security" in ad_data, "Missing security"
            security_defs = ad_data["securityDefinitions"]
            assert "didwba_sc" in security_defs, "Missing didwba_sc security definition"
            print("✓ Security definitions verified")

            # Verify interfaces
            print("\n4. Checking interfaces:")
            interfaces = ad_data.get("interfaces", [])
            assert len(interfaces) > 0, "No interfaces found"

            openrpc_interface = None
            for interface in interfaces:
                assert (
                    interface.get("type") == "StructuredInterface"
                ), f"Invalid interface type: {interface.get('type')}"
                assert (
                    interface.get("protocol") == "openrpc"
                ), f"Invalid protocol: {interface.get('protocol')}"
                assert "content" in interface, "Missing interface content"

                # Get the OpenRPC content
                openrpc_content = interface["content"]
                assert (
                    openrpc_content.get("openrpc") == "1.3.2"
                ), f"Invalid OpenRPC version: {openrpc_content.get('openrpc')}"
                assert "methods" in openrpc_content, "Missing methods in OpenRPC"

                openrpc_interface = openrpc_content
                break

            # Verify OpenRPC methods
            methods = openrpc_interface["methods"]
            print(f"✓ Found {len(methods)} OpenRPC methods")

            # Display and verify methods
            print("\n5. Available methods:")
            external_methods = []
            both_methods = []

            for method in methods:
                method_name = method["name"]
                method_summary = method.get("summary", "No summary")
                print(f"   - {method_name}: {method_summary}")

                # All exposed methods should be either 'external' or 'both'
                # We need to check this based on the agent implementation
                if "message." in method_name:
                    if method_name in ["message.get_message_history"]:
                        external_methods.append(method_name)
                    elif method_name in [
                        "message.send_message",
                        "message.get_statistics",
                    ]:
                        both_methods.append(method_name)

            print(f"✓ External methods: {external_methods}")
            print(f"✓ Both (external+internal) methods: {both_methods}")

            # Verify that internal-only methods are NOT exposed
            all_method_names = [m["name"] for m in methods]
            internal_only_methods = ["message.receive_message", "message.clear_history"]
            for internal_method in internal_only_methods:
                assert (
                    internal_method not in all_method_names
                ), f"Internal method {internal_method} should not be exposed in OpenRPC"
            print("✓ Internal-only methods are correctly hidden")

            # Pretty print sample of the response
            print("\n6. Sample ad.json response structure:")
            sample_data = {
                "protocolType": ad_data["protocolType"],
                "protocolVersion": ad_data["protocolVersion"],
                "type": ad_data["type"],
                "name": ad_data["name"],
                "did": ad_data["did"],
                "interfaces_count": len(ad_data["interfaces"]),
                "methods_count": len(methods),
            }
            print(json.dumps(sample_data, indent=2))

            return True

        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            return False
        except AssertionError as e:
            print(f"❌ Validation Error: {e}")
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            traceback.print_exc()
            return False


async def test_jsonrpc_call(
    method: str, params: dict[str, Any] = None, should_succeed: bool = True
):
    """Test JSON-RPC call to an agent method."""
    print("\n" + "=" * 80)
    print(f"Testing JSON-RPC call: {method}")
    print("=" * 80)

    request_data = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": f"test-{method.replace('.', '-')}",
    }

    print(f"\nRequest: {json.dumps(request_data, indent=2)}")

    async with httpx.AsyncClient(**HTTP_CLIENT_CONFIG) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/agents/jsonrpc",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            print(f"\nResponse: {json.dumps(result, indent=2)}")

            if "error" in result:
                error_code = result["error"].get("code")
                error_message = result["error"].get("message")
                print(f"❌ Error ({error_code}): {error_message}")

                if should_succeed:
                    print("❌ Expected success but got error")
                    return False
                else:
                    print("✓ Expected error - access control working correctly")
                    return True
            else:
                print("✓ Success - method executed successfully")
                if not should_succeed:
                    print("❌ Expected error but got success")
                    return False
                else:
                    return True

        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            traceback.print_exc()
            return False


async def test_agents_list():
    """Test the /agents endpoint."""
    print("\n" + "=" * 80)
    print("Testing /agents endpoint")
    print("=" * 80)

    async with httpx.AsyncClient(**HTTP_CLIENT_CONFIG) as client:
        try:
            response = await client.get(f"{BASE_URL}/agents")
            response.raise_for_status()

            data = response.json()
            print(f"\nResponse: {json.dumps(data, indent=2)}")

            assert "agents" in data, "Missing 'agents' field in response"
            agents = data["agents"]
            print(f"✓ Found {len(agents)} registered agents")

            for agent in agents:
                required_fields = ["name", "description", "version"]
                for field in required_fields:
                    assert (
                        field in agent
                    ), f"Missing field '{field}' in agent {agent.get('name', 'unknown')}"

            print("✓ All agents have required fields")
            return True

        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            return False
        except AssertionError as e:
            print(f"❌ Validation Error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            traceback.print_exc()
            return False


async def test_agent_info(agent_name: str = "message"):
    """Test the /agents/{agent_name}/info endpoint."""
    print("\n" + "=" * 80)
    print(f"Testing /agents/{agent_name}/info endpoint")
    print("=" * 80)

    async with httpx.AsyncClient(**HTTP_CLIENT_CONFIG) as client:
        try:
            response = await client.get(f"{BASE_URL}/agents/{agent_name}/info")
            response.raise_for_status()

            data = response.json()
            print(f"\nResponse: {json.dumps(data, indent=2)}")

            # Verify required fields
            required_fields = ["name", "description", "version", "methods", "status"]
            for field in required_fields:
                assert field in data, f"Missing field '{field}' in agent info"

            assert (
                data["name"] == agent_name
            ), f"Expected agent name '{agent_name}', got '{data['name']}'"

            methods = data["methods"]
            print(f"✓ Agent has {len(methods)} methods")

            # Verify method structure
            for method_name, method_info in methods.items():
                method_required_fields = ["description", "parameters", "returns"]
                for field in method_required_fields:
                    assert (
                        field in method_info
                    ), f"Missing field '{field}' in method {method_name}"

            print("✓ All methods have required fields")
            return True

        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ Agent '{agent_name}' not found")
            else:
                print(f"❌ HTTP Error: {e}")
            return False
        except AssertionError as e:
            print(f"❌ Validation Error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            traceback.print_exc()
            return False


async def run_comprehensive_tests():
    """Run comprehensive test suite for all ad_router.py endpoints."""
    print("🎯 ANP ad.json and OpenRPC Comprehensive Test Suite")
    print("=" * 80)
    print(f"Target server: {BASE_URL}")
    print("=" * 80)

    # Test configuration
    test_results = []

    async def run_test(test_name: str, test_func, *args, **kwargs):
        """Helper to run a test and record results."""
        print(f"\n🧪 Running: {test_name}")
        try:
            result = await test_func(*args, **kwargs)
            test_results.append((test_name, result, None))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Result: {status}")
            return result
        except Exception as e:
            test_results.append((test_name, False, str(e)))
            print(f"Result: ❌ FAIL - {str(e)}")
            traceback.print_exc()
            return False

    # Test 1: Verify ad.json ANP format
    await run_test("ANP Format Validation", test_ad_json)

    # Test 2: Verify agents list endpoint
    await run_test("Agents List Endpoint", test_agents_list)

    # Test 3: Verify agent info endpoint
    await run_test("Agent Info Endpoint", test_agent_info, "message")

    # Test 4: JSON-RPC Access Control Tests
    print("\n" + "=" * 50)
    print("🔐 JSON-RPC Access Control Tests")
    print("=" * 50)

    # Test external method (should succeed)
    await run_test(
        "JSON-RPC External Method (send_message)",
        test_jsonrpc_call,
        "message.send_message",
        {
            "message_content": "Hello from JSON-RPC test",
            "recipient_did": "did:example:recipient123",
        },
        True,  # should_succeed
    )

    # Test both method (should succeed)
    await run_test(
        "JSON-RPC Both Method (get_statistics)",
        test_jsonrpc_call,
        "message.get_statistics",
        {},
        True,  # should_succeed
    )

    # Test external-only method (should succeed)
    await run_test(
        "JSON-RPC External Method (get_message_history)",
        test_jsonrpc_call,
        "message.get_message_history",
        {"other_did": "did:example:other123", "limit": 10},
        True,  # should_succeed
    )

    # Test internal method (should fail)
    await run_test(
        "JSON-RPC Internal Method (receive_message) - Should Fail",
        test_jsonrpc_call,
        "message.receive_message",
        {"message_content": "This should fail", "sender_did": "did:example:sender123"},
        False,  # should_succeed = False (we expect this to fail)
    )

    # Test another internal method (should fail)
    await run_test(
        "JSON-RPC Internal Method (clear_history) - Should Fail",
        test_jsonrpc_call,
        "message.clear_history",
        {},
        False,  # should_succeed = False (we expect this to fail)
    )

    # Test non-existent method (should fail)
    await run_test(
        "JSON-RPC Non-existent Method - Should Fail",
        test_jsonrpc_call,
        "message.non_existent_method",
        {},
        False,  # should_succeed = False (we expect this to fail)
    )

    # Test non-existent agent (should fail)
    await run_test(
        "JSON-RPC Non-existent Agent - Should Fail",
        test_jsonrpc_call,
        "non_existent.some_method",
        {},
        False,  # should_succeed = False (we expect this to fail)
    )

    # Generate test report
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 80)

    passed = 0
    failed = 0
    total = len(test_results)

    for test_name, result, error in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result and error:
            print(f"   └─ Error: {error}")

        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 80)
    print(f"📈 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print(
            "🎉 ALL TESTS PASSED! The ad_router.py implementation is working correctly."
        )
        return True
    else:
        print(f"⚠️  {failed} test(s) failed. Please check the implementation.")
        return False


def main():
    """Main entry point for the test suite."""
    try:
        # Run the async test suite
        result = asyncio.run(run_comprehensive_tests())

        # Exit with appropriate code
        sys.exit(0 if result else 1)

    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
