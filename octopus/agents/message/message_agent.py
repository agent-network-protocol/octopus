"""
Message Agent - Agent for handling message sending and receiving operations.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from openai import AsyncOpenAI

from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_interface
from octopus.config.settings import get_settings


@dataclass
class Message:
    """Message data structure."""
    id: str
    content: str
    sender_did: str
    recipient_did: str
    timestamp: datetime
    status: str = "pending"  # pending, sent, delivered, read, failed
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@register_agent(
    name="message",
    description="Agent for handling message sending and receiving operations",
    version="1.0.0",
    tags=["message", "communication", "did"]
)
class MessageAgent(BaseAgent):
    """Agent specialized in message handling and communication."""
    
    def __init__(self):
        """Initialize the message agent."""
        super().__init__(
            name="MessageAgent",
            description="Handles message sending and receiving operations"
        )
        
        # Message storage
        self.sent_messages: List[Message] = []
        self.received_messages: List[Message] = []
        self.message_history: Dict[str, List[Message]] = {}
        
        # Message statistics
        self.stats = {
            "total_sent": 0,
            "total_received": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0
        }
        
        # Initialize OpenAI client for ANP protocol
        settings = get_settings()
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.openai_model or "gpt-4-turbo-preview"
        
        # ANP Crawler instance (will be created per request)
        self._anp_crawler = None
        
        self.logger.info("MessageAgent initialized successfully with ANP protocol support")
    
    @agent_interface(
        description="Send a message to an agent using ANP protocol",
        parameters={
            "message_content": {"description": "Content of the message to send"},
            "agent_ad_json_url": {"description": "URL of the target agent's AD.json description document"},
            "metadata": {"description": "Additional metadata for the message"}
        },
        returns="dict",
        access_level="external"  # Made external for web access
    )
    async def send_message(self, message_content: str, agent_ad_json_url: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message to an agent using ANP protocol.
        
        Args:
            message_content: Content of the message to send
            agent_ad_json_url: URL of the target agent's AD.json description document
            metadata: Additional metadata for the message
            
        Returns:
            Dictionary containing message details and send status
        """
        try:
            # Generate unique message ID
            message_id = str(uuid.uuid4())
            
            self.logger.info(f"Starting ANP message sending process: {message_id}")
            self.logger.info(f"Target agent URL: {agent_ad_json_url}")
            self.logger.info(f"Message content: {message_content}")
            
            # Use ANP protocol to send message
            anp_result = await self._send_message_via_anp(
                message_content=message_content,
                agent_ad_json_url=agent_ad_json_url,
                message_id=message_id,
                metadata=metadata or {}
            )
            
            if anp_result["success"]:
                # Create message object for successful send
                message = Message(
                    id=message_id,
                    content=message_content,
                    sender_did=self.agent_id,
                    recipient_did=anp_result.get("recipient_did", agent_ad_json_url),
                    timestamp=datetime.now(),
                    status="sent",
                    metadata=metadata or {}
                )
                
                # Store sent message
                self.sent_messages.append(message)
                
                # Update conversation history
                conversation_key = f"{self.agent_id}:{anp_result.get('recipient_did', agent_ad_json_url)}"
                if conversation_key not in self.message_history:
                    self.message_history[conversation_key] = []
                self.message_history[conversation_key].append(message)
                
                # Update statistics
                self.stats["total_sent"] += 1
                self.stats["successful_deliveries"] += 1
                
                self.logger.info(f"Message sent successfully via ANP: {message_id}")
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "agent_ad_json_url": agent_ad_json_url,
                    "content": message_content,
                    "timestamp": message.timestamp.isoformat(),
                    "status": "sent",
                    "anp_result": anp_result,
                    "metadata": message.metadata
                }
            else:
                # Handle ANP failure
                self.stats["failed_deliveries"] += 1
                self.logger.error(f"Failed to send message via ANP: {anp_result.get('error', 'Unknown error')}")
                
                return {
                    "success": False,
                    "message_id": message_id,
                    "agent_ad_json_url": agent_ad_json_url,
                    "content": message_content,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": anp_result.get("error", "ANP sending failed"),
                    "anp_result": anp_result
                }
                
        except Exception as e:
            self.stats["failed_deliveries"] += 1
            self.logger.error(f"Failed to send message: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "agent_ad_json_url": agent_ad_json_url,
                "content": message_content,
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
    
    @agent_interface(
        description="Receive a message from a sender",
        parameters={
            "message_content": {"description": "Content of the received message"},
            "sender_did": {"description": "DID (Decentralized Identifier) of the message sender"},
            "metadata": {"description": "Additional metadata for the message"}
        },
        returns="dict",
        access_level="external"  # Made external for end-to-end testing
    )
    def receive_message(self, message_content: str, sender_did: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Receive a message from a specified sender.
        
        Args:
            message_content: Content of the received message
            sender_did: DID of the message sender
            metadata: Additional metadata for the message
            
        Returns:
            Dictionary containing message details and receive status
        """
        try:
            # Generate unique message ID
            message_id = str(uuid.uuid4())
            
            # Create message object
            message = Message(
                id=message_id,
                content=message_content,
                sender_did=sender_did,
                recipient_did=self.agent_id,  # Use agent ID as recipient DID
                timestamp=datetime.now(),
                status="received",
                metadata=metadata or {}
            )
            
            # Store received message
            self.received_messages.append(message)
            
            # Update conversation history
            conversation_key = f"{sender_did}:{self.agent_id}"
            if conversation_key not in self.message_history:
                self.message_history[conversation_key] = []
            self.message_history[conversation_key].append(message)
            
            # Update statistics
            self.stats["total_received"] += 1
            
            # Log the operation
            self.logger.info(f"Message received successfully: {message_id} from {sender_did}")
            
            return {
                "success": True,
                "message_id": message_id,
                "sender_did": sender_did,
                "content": message_content,
                "timestamp": message.timestamp.isoformat(),
                "status": "received",
                "metadata": message.metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to receive message: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "sender_did": sender_did,
                "content": message_content,
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
    
    @agent_interface(
        description="Get message statistics",
        parameters={},
        returns="dict",
        access_level="external"  # Made external for end-to-end testing
    )
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get message statistics.
        
        Returns:
            Dictionary containing message statistics
        """
        try:
            return {
                "success": True,
                "statistics": {
                    "total_sent": self.stats["total_sent"],
                    "total_received": self.stats["total_received"],
                    "successful_deliveries": self.stats["successful_deliveries"],
                    "failed_deliveries": self.stats["failed_deliveries"],
                    "active_conversations": len(self.message_history),
                    "agent_did": self.agent_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "statistics": {}
            }
    
    async def _send_message_via_anp(self, message_content: str, agent_ad_json_url: str, 
                                   message_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 ANP 协议发送消息的核心方法。
        
        Args:
            message_content: 消息内容
            agent_ad_json_url: 目标智能体的 AD.json URL
            message_id: 消息ID
            metadata: 元数据
            
        Returns:
            发送结果字典
        """
        try:
            # 第一步：使用 ANP Crawler 获取目标智能体的接口信息
            self.logger.info(f"Step 1: Fetching agent description from {agent_ad_json_url}")
            
            # 获取 ANP Crawler 实例
            crawler = self._get_anp_crawler()
            
            # 获取智能体描述和工具列表
            content_json, interfaces_list = await crawler.fetch_text(agent_ad_json_url)
            
            self.logger.info(f"Successfully fetched agent description, found {len(interfaces_list)} tools")
            
            if not interfaces_list:
                return {
                    "success": False,
                    "error": "No tools found in target agent description",
                    "agent_ad_json_url": agent_ad_json_url
                }
            
            # 第二步：使用 OpenAI 模型分析和调用合适的工具
            self.logger.info("Step 2: Using OpenAI to analyze and call appropriate tools")
            
            # 准备 ANP 专用提示词（包含智能体描述信息）
            anp_prompt = self._build_anp_prompt(message_content, agent_ad_json_url, content_json)
            
            # 调用 OpenAI 进行工具选择和执行
            tool_call_result = await self._call_openai_with_tools(
                anp_prompt, 
                interfaces_list, 
                message_content, 
                crawler
            )
            
            return tool_call_result
            
        except Exception as e:
            self.logger.error(f"Error in ANP message sending: {str(e)}")
            return {
                "success": False,
                "error": f"ANP protocol error: {str(e)}",
                "agent_ad_json_url": agent_ad_json_url
            }
    
    def _get_anp_crawler(self):
        """获取 ANP Crawler 实例。"""
        if self._anp_crawler is None:
            from octopus.anp_sdk.anp_crawler.anp_crawler import ANPCrawler
            settings = get_settings()
            
            self._anp_crawler = ANPCrawler(
                did_document_path=settings.did_document_path,
                private_key_path=settings.did_private_key_path,
                cache_enabled=True
            )
            
        return self._anp_crawler
    
    def _build_anp_prompt(self, message_content: str, agent_ad_json_url: str, content_json: dict) -> str:
        """构建 ANP 专用提示词，包含目标智能体的完整描述信息。"""
        import json
        
        # 将content_json转换为格式化的JSON字符串
        content_json_str = json.dumps(content_json, ensure_ascii=False, indent=2)
        
        return f"""你是一个专业的 ANP (Agent Network Protocol) 智能体消息发送助手。你的任务是使用 ANP 协议向目标智能体发送消息。

## 当前任务
发送消息: {message_content}
目标智能体: {agent_ad_json_url}

## 目标智能体完整信息
{content_json_str}

## 工作流程
1. 我已经为你获取了目标智能体的接口定义（tools）和完整的智能体描述信息
2. 请仔细分析目标智能体的功能、描述和可用接口
3. 找到合适的消息接收功能（通常是 receive_message 或类似的方法）
4. 使用正确的参数调用该接口来发送消息

## 重要说明
- 你的目标是将消息"{message_content}"发送给目标智能体
- 优先寻找名为 "receive_message" 或包含 "message" 关键词的接口
- 根据上面显示的目标智能体描述和功能，选择最合适的接口
- 确保使用正确的参数格式调用接口，特别注意：
  * message_content 参数：填入要发送的消息内容 "{message_content}"
  * sender_did 参数：使用发送方ID，应填入 "{self.agent_id}"
  * metadata 参数：如果需要，可以传入空字典 {{}}
  * 其他必需参数请根据接口定义和智能体描述正确填写
- 如果找不到合适的接口，请详细说明原因和可用的接口列表

请仔细分析目标智能体的信息和可用工具，然后选择合适的工具执行消息发送。"""
    
    async def _call_openai_with_tools(self, prompt: str, tools: List[Dict], 
                                     message_content: str, crawler) -> Dict[str, Any]:
        """使用 OpenAI 调用工具的核心方法。"""
        try:
            self.logger.info(f"Calling OpenAI with {len(tools)} tools available")
            
            # 调用 OpenAI 模型
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"请发送消息: {message_content}"}
                ],
                tools=tools,
                tool_choice="auto",
                temperature=0.3
            )
            
            message = response.choices[0].message
            
            # 检查是否有工具调用
            if not message.tool_calls:
                return {
                    "success": False,
                    "error": "OpenAI did not choose any tools to call",
                    "openai_response": message.content
                }
            
            # 执行工具调用
            self.logger.info(f"OpenAI chose to call {len(message.tool_calls)} tool(s)")
            
            results = []
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                arguments_str = tool_call.function.arguments
                
                try:
                    arguments = json.loads(arguments_str)
                    self.logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
                    
                    # 使用 ANP Crawler 执行工具调用
                    execution_result = await crawler.execute_tool_call(tool_name, arguments)
                    
                    results.append({
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": execution_result
                    })
                    
                    # 如果这是消息发送工具且成功了，返回成功
                    if (execution_result.get("success", False) and 
                        ("receive_message" in tool_name.lower() or "message" in tool_name.lower())):
                        
                        self.logger.info(f"Message successfully sent via {tool_name}")
                        return {
                            "success": True,
                            "tool_results": results,
                            "message_sent_via": tool_name,
                            "recipient_did": arguments.get("sender_did", "unknown")
                        }
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse tool arguments: {arguments_str}")
                    results.append({
                        "tool_name": tool_name,
                        "error": f"Invalid JSON arguments: {str(e)}"
                    })
                except Exception as e:
                    self.logger.error(f"Failed to execute tool {tool_name}: {str(e)}")
                    results.append({
                        "tool_name": tool_name,
                        "error": str(e)
                    })
            
            # 如果到这里说明没有成功的消息发送
            return {
                "success": False,
                "error": "No successful message sending tool found",
                "tool_results": results
            }
            
        except Exception as e:
            self.logger.error(f"Error calling OpenAI with tools: {str(e)}")
            return {
                "success": False,
                "error": f"OpenAI API error: {str(e)}"
            }
    