"""
Message Agent - Agent for handling message sending and receiving operations.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_method


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
    name="message_agent",
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
        
        self.logger.info("MessageAgent initialized successfully")
    
    @agent_method(
        description="Send a message to a recipient",
        parameters={
            "message_content": {"description": "Content of the message to send"},
            "recipient_did": {"description": "DID (Decentralized Identifier) of the message recipient"},
            "metadata": {"description": "Additional metadata for the message"}
        },
        returns="dict"
    )
    def send_message(self, message_content: str, recipient_did: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message to a specified recipient.
        
        Args:
            message_content: Content of the message to send
            recipient_did: DID of the message recipient
            metadata: Additional metadata for the message
            
        Returns:
            Dictionary containing message details and send status
        """
        try:
            # Generate unique message ID
            message_id = str(uuid.uuid4())
            
            # Create message object
            message = Message(
                id=message_id,
                content=message_content,
                sender_did=self.agent_id,  # Use agent ID as sender DID
                recipient_did=recipient_did,
                timestamp=datetime.now(),
                status="sent",
                metadata=metadata or {}
            )
            
            # Store sent message
            self.sent_messages.append(message)
            
            # Update conversation history
            conversation_key = f"{self.agent_id}:{recipient_did}"
            if conversation_key not in self.message_history:
                self.message_history[conversation_key] = []
            self.message_history[conversation_key].append(message)
            
            # Update statistics
            self.stats["total_sent"] += 1
            self.stats["successful_deliveries"] += 1
            
            # Log the operation
            self.logger.info(f"Message sent successfully: {message_id} to {recipient_did}")
            
            return {
                "success": True,
                "message_id": message_id,
                "recipient_did": recipient_did,
                "content": message_content,
                "timestamp": message.timestamp.isoformat(),
                "status": "sent",
                "metadata": message.metadata
            }
            
        except Exception as e:
            self.stats["failed_deliveries"] += 1
            self.logger.error(f"Failed to send message: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "recipient_did": recipient_did,
                "content": message_content,
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
    
    @agent_method(
        description="Receive a message from a sender",
        parameters={
            "message_content": {"description": "Content of the received message"},
            "sender_did": {"description": "DID (Decentralized Identifier) of the message sender"},
            "metadata": {"description": "Additional metadata for the message"}
        },
        returns="dict"
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
    
    @agent_method(
        description="Get message history for a specific conversation",
        parameters={
            "other_did": {"description": "DID of the other party in the conversation"},
            "limit": {"description": "Maximum number of messages to return"}
        },
        returns="dict"
    )
    def get_message_history(self, other_did: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get message history for a specific conversation.
        
        Args:
            other_did: DID of the other party in the conversation
            limit: Maximum number of messages to return
            
        Returns:
            Dictionary containing conversation history
        """
        try:
            # Try both conversation key formats
            conversation_key_1 = f"{self.agent_id}:{other_did}"
            conversation_key_2 = f"{other_did}:{self.agent_id}"
            
            messages = []
            if conversation_key_1 in self.message_history:
                messages.extend(self.message_history[conversation_key_1])
            if conversation_key_2 in self.message_history:
                messages.extend(self.message_history[conversation_key_2])
            
            # Sort messages by timestamp
            messages.sort(key=lambda x: x.timestamp)
            
            # Apply limit
            if limit > 0:
                messages = messages[-limit:]
            
            # Convert to dict format
            message_dicts = [msg.to_dict() for msg in messages]
            
            return {
                "success": True,
                "conversation_with": other_did,
                "message_count": len(message_dicts),
                "messages": message_dicts
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get message history: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "conversation_with": other_did,
                "message_count": 0,
                "messages": []
            }
    
    @agent_method(
        description="Get message statistics",
        parameters={},
        returns="dict"
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
    
    @agent_method(
        description="Clear message history",
        parameters={
            "conversation_did": {"description": "DID to clear conversation with (optional, clears all if not specified)"}
        },
        returns="dict"
    )
    def clear_history(self, conversation_did: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear message history.
        
        Args:
            conversation_did: DID to clear conversation with (optional)
            
        Returns:
            Dictionary containing clear operation status
        """
        try:
            if conversation_did:
                # Clear specific conversation
                conversation_key_1 = f"{self.agent_id}:{conversation_did}"
                conversation_key_2 = f"{conversation_did}:{self.agent_id}"
                
                cleared_count = 0
                if conversation_key_1 in self.message_history:
                    cleared_count += len(self.message_history[conversation_key_1])
                    del self.message_history[conversation_key_1]
                if conversation_key_2 in self.message_history:
                    cleared_count += len(self.message_history[conversation_key_2])
                    del self.message_history[conversation_key_2]
                
                self.logger.info(f"Cleared conversation history with {conversation_did}")
                
                return {
                    "success": True,
                    "cleared_conversation": conversation_did,
                    "messages_cleared": cleared_count
                }
            else:
                # Clear all history
                total_messages = sum(len(msgs) for msgs in self.message_history.values())
                self.message_history.clear()
                self.sent_messages.clear()
                self.received_messages.clear()
                
                # Reset statistics
                self.stats = {
                    "total_sent": 0,
                    "total_received": 0,
                    "successful_deliveries": 0,
                    "failed_deliveries": 0
                }
                
                self.logger.info("Cleared all message history")
                
                return {
                    "success": True,
                    "cleared_all": True,
                    "messages_cleared": total_messages
                }
                
        except Exception as e:
            self.logger.error(f"Failed to clear history: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 