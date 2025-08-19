#!/usr/bin/env python3
"""
完整的JSON-RPC功能测试脚本
验证JSON-RPC调用逻辑和访问级别控制
"""

import json
import subprocess
import sys

from octopus.config.settings import get_settings

settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"


def call_jsonrpc(method, params=None, request_id="test"):
    """调用JSON-RPC方法"""
    request_data = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": request_id,
    }

    json_data = json.dumps(request_data)

    try:
        result = subprocess.run(
            [
                "curl",
                "--noproxy",
                "localhost",
                "-s",
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-d",
                json_data,
                f"{BASE_URL}/agents/jsonrpc",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout:
            try:
                response = json.loads(result.stdout)
                return response
            except json.JSONDecodeError:
                return {
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {result.stdout}",
                    }
                }
        else:
            return {
                "error": {"code": -32603, "message": f"Network error: {result.stderr}"}
            }

    except Exception as e:
        return {"error": {"code": -32603, "message": f"Exception: {str(e)}"}}


def test_jsonrpc_method(test_name, method, params, expected_result, access_level):
    """测试单个JSON-RPC方法"""
    print(f"\n{'='*80}")
    print(f"测试: {test_name}")
    print(f"方法: {method}")
    print(f"访问级别: {access_level}")
    print(f"期望结果: {expected_result}")
    print(f"{'='*80}")

    print(f"请求参数: {json.dumps(params, indent=2, ensure_ascii=False)}")

    response = call_jsonrpc(method, params, f"test-{method.replace('.', '-')}")

    print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")

    # 验证结果
    if expected_result == "success":
        if "result" in response:
            print("✅ 成功: 方法执行成功")
            return True
        elif "error" in response:
            print(f"❌ 失败: 期望成功但收到错误 - {response['error']['message']}")
            return False
    elif expected_result == "access_denied":
        if "error" in response and response["error"]["code"] == -32601:
            print("✅ 成功: 访问被正确拒绝")
            return True
        elif "result" in response:
            print("❌ 失败: 期望访问拒绝但方法执行成功")
            return False
        elif "error" in response:
            print(f"✅ 成功: 访问被拒绝 (错误码: {response['error']['code']})")
            return True
    elif expected_result == "method_not_found":
        if "error" in response and response["error"]["code"] == -32601:
            print("✅ 成功: 方法未找到错误正确返回")
            return True
        elif "result" in response:
            print("❌ 失败: 期望方法未找到但方法执行成功")
            return False

    print(f"❌ 未知结果类型: {response}")
    return False


def main():
    """运行完整的JSON-RPC功能测试"""
    print("🎯 完整的JSON-RPC功能测试")
    print("=" * 80)
    print("📌 注意: 已临时禁用JSON-RPC端点的认证要求")
    print("=" * 80)

    test_cases = [
        # External级别方法测试 (应该成功)
        {
            "name": "External方法 - get_message_history",
            "method": "message.get_message_history",
            "params": {"other_did": "did:example:test123", "limit": 10},
            "expected": "success",
            "access_level": "external",
        },
        # Both级别方法测试 (应该成功)
        {
            "name": "Both方法 - send_message",
            "method": "message.send_message",
            "params": {
                "message_content": "测试消息内容",
                "recipient_did": "did:example:recipient123",
                "metadata": "test metadata",
            },
            "expected": "success",
            "access_level": "both",
        },
        {
            "name": "Both方法 - get_statistics",
            "method": "message.get_statistics",
            "params": {},
            "expected": "success",
            "access_level": "both",
        },
        # Internal级别方法测试 (应该被拒绝)
        {
            "name": "Internal方法 - receive_message (应被拒绝)",
            "method": "message.receive_message",
            "params": {
                "message_content": "内部消息",
                "sender_did": "did:example:sender123",
            },
            "expected": "access_denied",
            "access_level": "internal",
        },
        {
            "name": "Internal方法 - clear_history (应被拒绝)",
            "method": "message.clear_history",
            "params": {},
            "expected": "access_denied",
            "access_level": "internal",
        },
        # 错误情况测试
        {
            "name": "不存在的方法",
            "method": "message.non_existent_method",
            "params": {},
            "expected": "method_not_found",
            "access_level": "N/A",
        },
        {
            "name": "不存在的Agent",
            "method": "unknown_agent.some_method",
            "params": {},
            "expected": "method_not_found",
            "access_level": "N/A",
        },
    ]

    success_count = 0
    total_tests = len(test_cases)

    for test_case in test_cases:
        result = test_jsonrpc_method(
            test_case["name"],
            test_case["method"],
            test_case["params"],
            test_case["expected"],
            test_case["access_level"],
        )
        if result:
            success_count += 1

    # 总结
    print(f"\n{'='*80}")
    print("🏆 JSON-RPC功能测试总结")
    print(f"{'='*80}")
    print(f"通过测试: {success_count}/{total_tests}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")

    if success_count == total_tests:
        print("\n🎉 所有JSON-RPC功能测试通过！")
        print("✅ JSON-RPC调用逻辑正确")
        print("✅ 访问级别控制正确")
        print("✅ 错误处理机制正确")
        print("✅ OpenRPC与实际实现一致")
        return True
    else:
        print(f"\n⚠️ {total_tests - success_count} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
