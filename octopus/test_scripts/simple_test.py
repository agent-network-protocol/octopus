#!/usr/bin/env python3
"""
简单的测试脚本，验证ad_router.py的功能
"""

import json
import subprocess
import sys


def run_curl_test(url, description):
    """使用curl进行测试，绕过Python的代理问题"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    try:
        # 使用curl直接测试，禁用代理
        result = subprocess.run(
            [
                "curl",
                "--noproxy",
                "localhost",
                "-s",
                "-w",
                "\\nHTTP_STATUS:%{http_code}\\n",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout.strip()
        if "HTTP_STATUS:" in output:
            parts = output.rsplit("\\nHTTP_STATUS:", 1)
            content = parts[0]
            status_code = int(parts[1])
        else:
            content = output
            status_code = result.returncode

        print(f"状态码: {status_code}")

        if status_code == 200:
            print("✅ 请求成功")
            try:
                # 尝试解析JSON
                if content:
                    data = json.loads(content)
                    print(f"响应类型: {type(data)}")
                    if isinstance(data, dict):
                        print(f"主要字段: {list(data.keys())}")
                        if "protocolType" in data:
                            print(f"协议类型: {data['protocolType']}")
                        if "interfaces" in data:
                            print(f"接口数量: {len(data['interfaces'])}")
                            if (
                                data["interfaces"]
                                and "content" in data["interfaces"][0]
                            ):
                                openrpc = data["interfaces"][0]["content"]
                                if "methods" in openrpc:
                                    print(f"OpenRPC方法数量: {len(openrpc['methods'])}")
                                    for method in openrpc["methods"]:
                                        print(
                                            f"  - {method.get('name')}: {method.get('summary', 'No summary')}"
                                        )
                else:
                    print("响应为空")
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"原始内容: {content[:200]}...")
        else:
            print(f"❌ 请求失败: {status_code}")
            if content:
                print(f"错误内容: {content}")

        return status_code == 200

    except subprocess.TimeoutExpired:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_jsonrpc_call(method, params=None):
    """测试JSON-RPC调用"""
    print(f"\n{'='*60}")
    print(f"测试JSON-RPC: {method}")
    print(f"{'='*60}")

    request_data = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": f"test-{method.replace('.', '-')}",
    }

    json_data = json.dumps(request_data)
    print(f"请求数据: {json_data}")

    try:
        # 使用curl发送POST请求
        result = subprocess.run(
            [
                "curl",
                "--noproxy",
                "localhost",
                "-s",
                "-w",
                "\\nHTTP_STATUS:%{http_code}\\n",
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-d",
                json_data,
                "http://localhost:9527/agents/jsonrpc",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout.strip()
        if "HTTP_STATUS:" in output:
            parts = output.rsplit("\\nHTTP_STATUS:", 1)
            content = parts[0]
            status_code = int(parts[1])
        else:
            content = output
            status_code = result.returncode

        print(f"状态码: {status_code}")

        if status_code == 200 and content:
            try:
                response_data = json.loads(content)
                print(
                    f"响应: {json.dumps(response_data, indent=2, ensure_ascii=False)}"
                )

                if "error" in response_data:
                    error_code = response_data["error"].get("code")
                    error_message = response_data["error"].get("message")
                    print(f"❌ JSON-RPC错误 ({error_code}): {error_message}")
                    return "error"
                else:
                    print("✅ JSON-RPC调用成功")
                    return "success"

            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"原始内容: {content}")
                return "parse_error"
        else:
            print(f"❌ HTTP请求失败: {status_code}")
            if content:
                print(f"错误内容: {content}")
            return "http_error"

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return "exception"


def main():
    """运行所有测试"""
    print("🎯 Octopus ad_router.py 功能测试")
    print("=" * 80)

    # 测试基本端点
    tests = [
        ("http://localhost:9527/ad.json", "ANP格式的Agent描述"),
        ("http://localhost:9527/agents", "Agent列表"),
        ("http://localhost:9527/agents/message/info", "消息Agent信息"),
    ]

    success_count = 0
    total_tests = len(tests)

    for url, desc in tests:
        if run_curl_test(url, desc):
            success_count += 1

    # 测试JSON-RPC调用
    print(f"\n{'='*60}")
    print("JSON-RPC访问控制测试")
    print(f"{'='*60}")

    rpc_tests = [
        (
            "message.send_message",
            {"message_content": "测试消息", "recipient_did": "did:example:test"},
            "both",
            "success",
        ),
        ("message.get_statistics", {}, "both", "success"),
        (
            "message.get_message_history",
            {"other_did": "did:example:test", "limit": 10},
            "external",
            "success",
        ),
        (
            "message.receive_message",
            {"message_content": "内部消息", "sender_did": "did:example:sender"},
            "internal",
            "error",
        ),
        ("message.clear_history", {}, "internal", "error"),
    ]

    rpc_success = 0
    rpc_total = len(rpc_tests)

    for method, params, access_level, expected in rpc_tests:
        print(f"\n访问级别: {access_level}, 期望结果: {expected}")
        result = test_jsonrpc_call(method, params)
        if (expected == "success" and result == "success") or (
            expected == "error" and result == "error"
        ):
            print("✅ 测试符合预期")
            rpc_success += 1
        else:
            print(f"❌ 测试不符合预期: 期望 {expected}, 实际 {result}")

    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    print(f"基本端点测试: {success_count}/{total_tests} 通过")
    print(f"JSON-RPC测试: {rpc_success}/{rpc_total} 通过")
    print(
        f"总体通过率: {(success_count + rpc_success)}/{(total_tests + rpc_total)} ({((success_count + rpc_success)/(total_tests + rpc_total)*100):.1f}%)"
    )

    if success_count + rpc_success == total_tests + rpc_total:
        print("🎉 所有测试通过！ad_router.py功能正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查实现")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
