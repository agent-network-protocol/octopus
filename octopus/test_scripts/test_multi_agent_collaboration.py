#!/usr/bin/env python3
"""
测试多智能体协作流程
演示 Master Agent 接收自然语言请求并调用 Message Agent 的功能
"""

import asyncio
import sys
import uuid
from datetime import datetime

# 添加项目路径到 Python 路径
sys.path.insert(0, ".")

from octopus.agents.message.message_agent import MessageAgent
from octopus.config.settings import get_settings
from octopus.master_agent import MasterAgent
from octopus.router.agents_router import router
from octopus.utils.log_base import get_logger


async def test_multi_agent_collaboration():
    """测试多智能体协作流程"""

    # 获取 logger - 日志系统自动初始化
    logger = get_logger(__name__)

    try:
        # 获取配置
        settings = get_settings()
        logger.info("=== 多智能体协作测试开始 ===")
        logger.info(f"使用模型: {settings.openai_model}")

        # 1. 初始化并注册 Message Agent
        logger.info("\n1. 初始化 Message Agent...")
        message_agent = MessageAgent()
        logger.info("Message Agent 初始化成功")

        # 2. 初始化 Master Agent
        logger.info("\n2. 初始化 Master Agent...")
        master_agent = MasterAgent()
        master_agent.initialize()
        logger.info("Master Agent 初始化成功")

        # 3. 查看当前可用的智能体
        logger.info("\n3. 查看可用的智能体:")
        available_agents = router.list_agents()
        for agent in available_agents:
            logger.info(f"   - {agent['name']}: {agent['description']}")

        # 4. 测试 Master Agent 状态
        logger.info("\n4. 获取 Master Agent 状态:")
        status = master_agent.get_status()
        logger.info(f"   Master Agent 状态: {status['status']}")
        logger.info(f"   使用模型: {status['model']}")
        logger.info(f"   可用智能体数量: {status['available_agents']}")
        logger.info(f"   智能体列表: {status['agents']}")

        # 5. 测试场景1: 发送消息
        logger.info("\n5. 测试场景1 - 通过自然语言发送消息:")
        request_id_1 = str(uuid.uuid4())
        nl_request_1 = "请帮我发送一条消息，内容是'你好，这是一条测试消息！'，接收者的DID是'test_recipient_did_001'"

        logger.info(f"   请求: {nl_request_1}")
        logger.info(f"   请求ID: {request_id_1}")

        result_1 = master_agent.process_natural_language(nl_request_1, request_id_1)
        logger.info(f"   响应: {result_1}")

        # 6. 测试场景2: 查询消息统计
        logger.info("\n6. 测试场景2 - 查询消息统计:")
        request_id_2 = str(uuid.uuid4())
        nl_request_2 = "查看消息统计信息"

        logger.info(f"   请求: {nl_request_2}")
        logger.info(f"   请求ID: {request_id_2}")

        result_2 = master_agent.process_natural_language(nl_request_2, request_id_2)
        logger.info(f"   响应: {result_2}")

        # 7. 测试场景3: 接收消息
        logger.info("\n7. 测试场景3 - 模拟接收消息:")
        request_id_3 = str(uuid.uuid4())
        nl_request_3 = (
            "接收一条来自'test_sender_did_002'的消息，内容是'这是一条回复消息'"
        )

        logger.info(f"   请求: {nl_request_3}")
        logger.info(f"   请求ID: {request_id_3}")

        result_3 = master_agent.process_natural_language(nl_request_3, request_id_3)
        logger.info(f"   响应: {result_3}")

        # 8. 测试场景4: 查看消息历史
        logger.info("\n8. 测试场景4 - 查看消息历史:")
        request_id_4 = str(uuid.uuid4())
        nl_request_4 = "查看与'test_recipient_did_001'的消息历史"

        logger.info(f"   请求: {nl_request_4}")
        logger.info(f"   请求ID: {request_id_4}")

        result_4 = master_agent.process_natural_language(nl_request_4, request_id_4)
        logger.info(f"   响应: {result_4}")

        # 9. 测试场景5: 复杂请求
        logger.info("\n9. 测试场景5 - 复杂请求:")
        request_id_5 = str(uuid.uuid4())
        nl_request_5 = "给用户'business_partner_001'发送一条业务消息，内容包含今天的日期和一个会议邀请"

        logger.info(f"   请求: {nl_request_5}")
        logger.info(f"   请求ID: {request_id_5}")

        result_5 = master_agent.process_natural_language(nl_request_5, request_id_5)
        logger.info(f"   响应: {result_5}")

        # 10. 直接调用 Message Agent 方法进行对比
        logger.info("\n10. 直接调用 Message Agent 方法（对比测试）:")
        direct_result = message_agent.send_message(
            message_content="这是直接调用发送的消息",
            recipient_did="direct_test_recipient",
            metadata={"test": True, "timestamp": datetime.now().isoformat()},
        )
        logger.info(f"   直接调用结果: {direct_result}")

        # 11. 测试错误处理
        logger.info("\n11. 测试错误处理 - 无法理解的请求:")
        request_id_6 = str(uuid.uuid4())
        nl_request_6 = "请帮我做一杯咖啡"

        logger.info(f"   请求: {nl_request_6}")
        logger.info(f"   请求ID: {request_id_6}")

        result_6 = master_agent.process_natural_language(nl_request_6, request_id_6)
        logger.info(f"   响应: {result_6}")

        logger.info("\n=== 多智能体协作测试完成 ===")

    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(test_multi_agent_collaboration())
