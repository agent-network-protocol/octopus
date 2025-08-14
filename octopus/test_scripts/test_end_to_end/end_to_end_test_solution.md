# Octopus 端到端测试方案

## 测试目标

验证 Octopus 多智能体系统的完整端到端流程，包括：
- AD.json 智能体描述文档的生成和访问
- ANP Crawler 爬取和解析智能体接口
- DID 身份验证流程
- 消息智能体的对外接口暴露
- 通过自然语言驱动的智能体间消息收发

## 测试架构图

```
[Web页面] → [Chat Router] → [Master Agent] → [ANP Crawler] → [本地AD.json]
    ↓                                              ↓
[用户输入] → [LLM + Tools] → [Message Agent] → [JSON-RPC调用] → [自身接收]
```

## 测试前准备工作

### 1. 修改 Message Agent 访问级别

需要将 `receive_message` 方法改为对外访问：

```python
# 文件：octopus/agents/message/message_agent.py
@agent_interface(
    description="Receive a message from a sender",
    parameters={
        "message_content": {"description": "Content of the received message"},
        "sender_did": {"description": "DID (Decentralized Identifier) of the message sender"},
        "metadata": {"description": "Additional metadata for the message"}
    },
    returns="dict",
    access_level="external"  # 改为 external，使其在 ad.json 中对外暴露
)
def receive_message(self, message_content: str, sender_did: str,
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
```

### 2. 重构 Message Agent 的 ANP 协议支持

#### 2.1 send_message 方法参数变更

**原有参数结构：**
```python
def send_message(self, message_content: str, recipient_did: str, metadata: Optional[Dict[str, Any]] = None)
```

**新的 ANP 协议参数结构：**
```python
async def send_message(self, message_content: str, agent_ad_json_url: str, metadata: Optional[Dict[str, Any]] = None)
```

#### 2.2 集成 OpenAI 模型和 ANP Crawler 工具

**ANP 专用提示词设计（基于 anp_crawler/bakup 经验）：**

```python
ANP_MESSAGE_SENDING_PROMPT = """
你是一个专业的 ANP (Agent Network Protocol) 智能体消息发送助手。你的任务是使用 ANP 协议向目标智能体发送消息。

## 当前任务
发送消息: {message_content}
目标智能体: {agent_ad_json_url}

## 工作流程
1. 使用 anp_fetch_text_content 工具访问目标智能体的 AD.json 描述文档
2. 解析智能体的接口定义，重点关注消息接收功能
3. 识别正确的消息接收接口（如 receive_message）
4. 调用争取的tools发送消息。

"""
```

#### 2.3 ANP Crawler 工具定义

1. 使用 anp_fetch_text_content 工具访问目标智能体的 AD.json 描述文档
在使用ANPCrawler的方法fetch_text获得ad.json的内容，以及tools。将tools作为OpenAI api的tools传入。这里要构造一个新的工具传递给模型，然后模型调用的时候，调用到ANPCrawler中。

使用ANPCrawler调用tools的方法进行调用。

#### 2.5 Message Agent 的 OpenAI 集成

```python
# 在 send_message 方法中集成 OpenAI 客户端
class MessageAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化 OpenAI 客户端
        settings = get_settings()
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.openai_model

    async def send_message(self, message_content: str, agent_ad_json_url: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        使用 ANP 协议向目标智能体发送消息
        """
        # 1. 准备提示词和工具
        # 2. 调用 OpenAI 模型
        # 3. 处理工具调用
        # 4. 返回结果
```


## web输入示例

我要给一个智能体发送一个消息，消息内容是：你好。
智能体的URL是：https://127.0.0.1:8000/agent/ad.json
