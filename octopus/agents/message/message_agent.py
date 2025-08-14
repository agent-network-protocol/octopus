"""
Message Agent - Agent for handling message sending and receiving operations.
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI

from octopus.agents.base_agent import BaseAgent
from octopus.config.settings import get_settings
from octopus.router.agents_router import agent_interface, register_agent


@dataclass
class Message:
    """Message data structure."""

    id: str
    content: str
    sender_did: str
    recipient_did: str
    timestamp: datetime
    status: str = "pending"  # pending, sent, delivered, read, failed
    metadata: dict[str, Any] = {}

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@register_agent(
    name="message",
    description="Agent for handling message sending and receiving operations",
    version="1.0.0",
    tags=["message", "communication", "did"],
)
class MessageAgent(BaseAgent):
    """Agent specialized in message handling and communication."""

    def __init__(self):
        """Initialize the message agent."""
        super().__init__(
            name="MessageAgent",
            description="Handles message sending and receiving operations",
        )

        # Message storage
        self.sent_messages: list[Message] = []
        self.received_messages: list[Message] = []
        self.message_history: dict[str, list[Message]] = {}

        # Message statistics
        self.stats = {
            "total_sent": 0,
            "total_received": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
        }

        # Initialize OpenAI client for ANP protocol
        settings = get_settings()
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key, base_url=settings.openai_base_url
        )
        self.model = settings.openai_model or "gpt-4-turbo-preview"

        # ANP Crawler instance (will be created per request)
        self._anp_crawler = None

        self.logger.info(
            "MessageAgent initialized successfully with ANP protocol support"
        )

    @agent_interface(
        description="Send a message to an agent using ANP protocol",
        parameters={
            "message_content": {"description": "Content of the message to send"},
            "agent_ad_json_url": {
                "description": "URL of the target agent's AD.json description document"
            },
            "metadata": {"description": "Additional metadata for the message"},
        },
        returns="dict",
        access_level="external",  # Made external for web access
    )
    async def send_message(
        self,
        message_content: str,
        agent_ad_json_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
                metadata=metadata or {},
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
                    metadata=metadata or {},
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
                    "metadata": message.metadata,
                }
            else:
                # Handle ANP failure
                self.stats["failed_deliveries"] += 1
                self.logger.error(
                    f"Failed to send message via ANP: {anp_result.get('error', 'Unknown error')}"
                )

                return {
                    "success": False,
                    "message_id": message_id,
                    "agent_ad_json_url": agent_ad_json_url,
                    "content": message_content,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": anp_result.get("error", "ANP sending failed"),
                    "anp_result": anp_result,
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
                "status": "failed",
            }

    @agent_interface(
        description="Receive a message from a sender",
        parameters={
            "message_content": {"description": "Content of the received message"},
            "sender_did": {
                "description": "DID (Decentralized Identifier) of the message sender"
            },
            "metadata": {"description": "Additional metadata for the message"},
        },
        returns="dict",
        access_level="external",  # Made external for end-to-end testing
    )
    def receive_message(
        self,
        message_content: str,
        sender_did: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
                metadata=metadata or {},
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
            self.logger.info(
                f"Message received successfully: {message_id} from {sender_did}"
            )
            self.logger.info(f"Message content: {message_content}")

            return {
                "success": True,
                "message_id": message_id,
                "sender_did": sender_did,
                "content": message_content,
                "timestamp": message.timestamp.isoformat(),
                "status": "received",
                "metadata": message.metadata,
            }

        except Exception as e:
            self.logger.error(f"Failed to receive message: {str(e)}")

            return {
                "success": False,
                "error": str(e),
                "sender_did": sender_did,
                "content": message_content,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
            }

    @agent_interface(
        description="Get message statistics",
        parameters={},
        returns="dict",
        access_level="external",  # Made external for end-to-end testing
    )
    def get_statistics(self) -> dict[str, Any]:
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
                    "agent_did": self.agent_id,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {"success": False, "error": str(e), "statistics": {}}

    async def _send_message_via_anp(
        self,
        message_content: str,
        agent_ad_json_url: str,
        message_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Core method for sending messages using ANP protocol.

        Args:
            message_content: Message content
            agent_ad_json_url: Target agent's AD.json URL
            message_id: Message ID
            metadata: Metadata

        Returns:
            Sending result dictionary
        """
        try:
            # Step 1: Use ANP Crawler to get target agent's interface information
            self.logger.info(
                f"Step 1: Fetching agent description from {agent_ad_json_url}"
            )

            # Get ANP Crawler instance
            crawler = self._get_anp_crawler()

            # Get agent description and tool list
            content_json, interfaces_list = await crawler.fetch_text(agent_ad_json_url)

            self.logger.info(
                f"🟡 [MESSAGE AGENT] Successfully fetched agent description, found {len(interfaces_list)} tools"
            )
            self.logger.info(f"🟡 [MESSAGE AGENT] Available tools: {interfaces_list}")

            if not interfaces_list:
                return {
                    "success": False,
                    "error": "No tools found in target agent description",
                    "agent_ad_json_url": agent_ad_json_url,
                }

            # Step 2: Use OpenAI model to analyze and call appropriate tools
            self.logger.info(
                "🟡 [MESSAGE AGENT] Step 2: Using OpenAI to analyze and call appropriate tools"
            )

            # Prepare ANP-specific prompt (including agent description information)
            anp_prompt = self._build_anp_prompt(
                message_content, agent_ad_json_url, content_json
            )

            # Call OpenAI for tool selection and execution
            tool_call_result = await self._call_openai_with_tools(
                anp_prompt, interfaces_list, message_content, crawler
            )

            return tool_call_result

        except Exception as e:
            self.logger.error(f"Error in ANP message sending: {str(e)}")
            return {
                "success": False,
                "error": f"ANP protocol error: {str(e)}",
                "agent_ad_json_url": agent_ad_json_url,
            }

    def _get_anp_crawler(self):
        """Get ANP Crawler instance."""
        if self._anp_crawler is None:
            from octopus.anp_sdk.anp_crawler.anp_crawler import ANPCrawler

            settings = get_settings()

            self._anp_crawler = ANPCrawler(
                did_document_path=settings.did_document_path,
                private_key_path=settings.did_private_key_path,
                cache_enabled=True,
            )

        return self._anp_crawler

    def _build_anp_prompt(
        self, message_content: str, agent_ad_json_url: str, content_json: dict
    ) -> str:
        """Build ANP-specific prompt, including complete description information of the target agent."""
        import json

        # Convert content_json to formatted JSON string
        content_json_str = json.dumps(content_json, ensure_ascii=False, indent=2)

        return f"""You are a professional ANP (Agent Network Protocol) agent message sending assistant. Your task is to send messages to target agents using the ANP protocol.

## Current Task
Send message: {message_content}
Target agent: {agent_ad_json_url}

## Complete Target Agent Information
{content_json_str}

## Workflow
1. I have already obtained the interface definitions (tools) and complete agent description information for the target agent
2. Please carefully analyze the target agent's functions, descriptions, and available interfaces
3. Find the appropriate message receiving function (usually receive_message or similar methods)
4. Use the correct parameters to call the interface to send the message

## Important Notes
- Your goal is to send the message "{message_content}" to the target agent
- Prioritize interfaces named "receive_message" or containing "message" keywords
- Based on the target agent description and functions shown above, choose the most suitable interface
- Ensure correct parameter format when calling the interface, especially:
  * message_content parameter: Fill in the message content to be sent "{message_content}"
  * sender_did parameter: Use sender ID, should be filled with "{self.agent_id}"
  * metadata parameter: If needed, you can pass an empty dictionary {{}}
  * Other required parameters should be filled correctly according to interface definition and agent description
- If no suitable interface is found, please explain the reason in detail and list available interfaces

Please carefully analyze the target agent's information and available tools, then choose the appropriate tool to execute message sending."""

    async def _call_openai_with_tools(
        self, prompt: str, tools: list[dict], message_content: str, crawler
    ) -> dict[str, Any]:
        """Core method for calling tools using OpenAI."""
        try:
            self.logger.info(
                f"🟡 [MESSAGE AGENT] Calling OpenAI with {len(tools)} tools available"
            )

            # Call OpenAI model
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": f"Please send message: {message_content}",
                    },
                ],
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
            )

            message = response.choices[0].message

            # Check if there are tool calls
            if not message.tool_calls:
                return {
                    "success": False,
                    "error": "OpenAI did not choose any tools to call",
                    "openai_response": message.content,
                }

            # Execute tool calls
            self.logger.info(
                f"🟡 [MESSAGE AGENT] OpenAI chose to call {len(message.tool_calls)} tool(s)"
            )

            results = []
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                arguments_str = tool_call.function.arguments

                try:
                    arguments = json.loads(arguments_str)
                    self.logger.info(
                        f"🟡 [MESSAGE AGENT] Executing tool: {tool_name} with arguments: {arguments}"
                    )

                    # Use ANP Crawler to execute tool call
                    execution_result = await crawler.execute_tool_call(
                        tool_name, arguments
                    )

                    results.append({
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": execution_result,
                    })

                    # If this is a message sending tool and it succeeded, return success
                    if execution_result.get("success", False) and (
                        "receive_message" in tool_name.lower()
                        or "message" in tool_name.lower()
                    ):
                        self.logger.info(
                            f"🟢 [MESSAGE AGENT] Message successfully sent via {tool_name}"
                        )
                        return {
                            "success": True,
                            "tool_results": results,
                            "message_sent_via": tool_name,
                            "recipient_did": arguments.get("sender_did", "unknown"),
                        }

                except json.JSONDecodeError as e:
                    self.logger.error(
                        f"Failed to parse tool arguments: {arguments_str}"
                    )
                    results.append({
                        "tool_name": tool_name,
                        "error": f"Invalid JSON arguments: {str(e)}",
                    })
                except Exception as e:
                    self.logger.error(f"Failed to execute tool {tool_name}: {str(e)}")
                    results.append({"tool_name": tool_name, "error": str(e)})

            # If we reach here, it means no successful message sending
            return {
                "success": False,
                "error": "No successful message sending tool found",
                "tool_results": results,
            }

        except Exception as e:
            self.logger.error(f"Error calling OpenAI with tools: {str(e)}")
            return {"success": False, "error": f"OpenAI API error: {str(e)}"}
