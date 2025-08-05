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
1. 使用 anp_crawler 工具访问目标智能体的 AD.json 描述文档
2. 解析智能体的接口定义，重点关注消息接收功能
3. 识别正确的消息接收接口（如 receive_message）
4. 使用 anp_jsonrpc_call 工具向目标智能体发送消息
5. 返回详细的执行结果

## ANP 协议关键点
- AD.json 是智能体的标准描述文档，包含完整的接口定义
- 接口通常以 OpenRPC 格式定义，支持 JSON-RPC 调用
- 需要正确解析 StructuredInterface 中的 content 字段
- 查找 access_level 为 "external" 或 "both" 的接口
- 消息接收接口通常命名为 receive_message 或类似
- 需要提供正确的 DID 身份认证

## 工具使用说明
1. anp_crawler: 爬取和解析 AD.json 文档，获取接口列表
2. anp_jsonrpc_call: 执行具体的 JSON-RPC 方法调用

## 输出要求
提供完整的执行过程报告，包括：
- 智能体发现和解析过程
- 接口识别结果
- 消息发送状态和结果
- 任何异常或错误信息

现在开始执行任务...
"""
```

#### 2.3 ANP Crawler 工具定义

**anp_crawler 工具：**
```python
{
    "type": "function",
    "function": {
        "name": "anp_crawler",
        "description": "使用 ANP Crawler 获取智能体的 AD.json 描述文档并解析接口",
        "parameters": {
            "type": "object", 
            "properties": {
                "url": {
                    "type": "string",
                    "description": "智能体的 AD.json 描述文档 URL"
                },
                "cache_enabled": {
                    "type": "boolean",
                    "description": "是否启用缓存",
                    "default": True
                }
            },
            "required": ["url"]
        }
    }
}
```

**anp_jsonrpc_call 工具：**
```python
{
    "type": "function",
    "function": {
        "name": "anp_jsonrpc_call", 
        "description": "向目标智能体发起 JSON-RPC 方法调用",
        "parameters": {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "description": "智能体的基础 URL（从 AD.json 中提取）"
                },
                "method": {
                    "type": "string",
                    "description": "要调用的方法名（如 message.receive_message）"
                },
                "params": {
                    "type": "object", 
                    "description": "方法调用的参数字典"
                },
                "request_id": {
                    "type": "string",
                    "description": "JSON-RPC 请求 ID",
                    "default": "auto_generated"
                }
            },
            "required": ["base_url", "method", "params"]
        }
    }
}
```

#### 2.4 工具执行逻辑

**anp_crawler 工具实现：**
- 创建 ANPCrawler 实例
- 调用 `fetch_text(url)` 获取 AD.json 内容和接口列表
- 返回解析结果：智能体信息 + 可用接口列表

**anp_jsonrpc_call 工具实现：**
- 构造 JSON-RPC 请求
- 使用 DID 身份验证
- 向目标智能体的 `/agents/jsonrpc` 端点发送请求
- 解析并返回响应结果

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

### 3. Master Agent 的 ANP 消息路由增强

#### 3.1 消息发送请求检测

```python
def _detect_message_sending_request(self, user_input: str) -> bool:
    """检测是否为 ANP 消息发送请求"""
    message_patterns = [
        r'发送.*消息.*到.*(?:http|智能体)',
        r'向.*(?:智能体|agent).*发.*消息',
        r'send.*message.*to.*(?:http|agent)',
        r'给.*(?:http.*ad\.json).*发消息'
    ]
    return any(re.search(pattern, user_input, re.IGNORECASE) for pattern in message_patterns)
```

#### 3.2 ANP 消息委托处理

```python
async def _delegate_to_anp_message_agent(self, user_input: str, ad_json_url: str) -> str:
    """委托给 Message Agent 处理 ANP 消息发送"""
    # 提取消息内容
    message_content = self._extract_message_content(user_input)
    
    # 调用 Message Agent 的 send_message 方法
    result = await router.execute_agent_method(
        agent_name="message",
        method_name="send_message", 
        parameters={
            "message_content": message_content,
            "agent_ad_json_url": ad_json_url,
            "metadata": {"source": "master_agent", "timestamp": datetime.now().isoformat()}
        }
    )
    
    return self._format_anp_message_result(result)
```

## 测试场景设计

### 场景 1：完整的端到端消息收发测试

#### 测试步骤：

1. **启动服务**
   ```bash
   cd /Users/cs/work/agents/octopus
   uv run python octopus.py
   ```

2. **验证服务状态**
   ```bash
   # 检查服务健康状态
   curl http://localhost:9527/v1/status
   
   # 检查 AD.json 生成
   curl http://localhost:9527/ad.json
   ```

3. **在 Web 页面输入测试请求**

#### Web 页面输入示例：

**基础消息发送测试：**
```
请帮我向ANP智能体 http://localhost:9527/ad.json 发送一条消息："你好，这是一条测试消息！"

我想测试完整的ANP协议消息发送流程，请详细记录每个步骤。
```

**高级测试场景：**
```
使用ANP协议向智能体 http://localhost:9527/ad.json 发送以下消息：
"这是一个端到端测试消息，请确认收到并返回处理结果。"

要求：
1. 首先分析目标智能体的能力和接口
2. 选择正确的消息接收接口
3. 使用DID身份验证发送消息
4. 返回完整的执行日志和结果

元数据：{"test_type": "e2e", "priority": "high"}
```

#### 期望的处理流程（重构后）：

1. **请求路由识别**：Master Agent 检测到 ANP 消息发送请求
2. **消息委托**：Master Agent 将请求委托给 Message Agent 处理
3. **Message Agent 初始化**：启动 OpenAI 客户端和 ANP 工具
4. **ANP Crawler 执行**：
   - 访问 `http://localhost:9527/ad.json`
   - 解析智能体描述和接口定义
   - 识别消息接收接口（`message.receive_message`）
5. **JSON-RPC 调用准备**：
   - 构造正确的 JSON-RPC 请求
   - 准备 DID 身份验证头
   - 设置请求参数
6. **消息发送执行**：
   - 向 `http://localhost:9527/agents/jsonrpc` 发送请求
   - 处理身份验证和授权
   - 执行 `message.receive_message` 方法
7. **结果处理和返回**：
   - 解析 JSON-RPC 响应
   - 格式化执行报告
   - 返回详细的过程和结果


## 验证点

### 1. AD.json 生成验证
- ✅ 服务启动后能正常访问 `/ad.json` 端点
- ✅ 返回的 JSON 格式符合 ANP 协议规范
- ✅ `receive_message` 方法包含在 OpenRPC 接口中（access_level="external"）
- ✅ 访问级别过滤正常工作（只有 external 和 both 级别的方法出现）
- ✅ StructuredInterface 格式正确，content 字段包含完整的 OpenRPC 定义

### 2. Message Agent ANP 集成验证
- ✅ `send_message` 方法参数已更改为 `agent_ad_json_url`
- ✅ OpenAI 客户端正确初始化和配置
- ✅ ANP 专用提示词正确设置
- ✅ anp_crawler 和 anp_jsonrpc_call 工具正确定义
- ✅ 工具调用逻辑正确实现

### 3. ANP Crawler 工具验证
- ✅ anp_crawler 工具能够成功爬取本地的 AD.json
- ✅ 正确解析 StructuredInterface + OpenRPC + content 格式
- ✅ 返回格式包含智能体信息和接口列表
- ✅ $ref 引用解析正常工作
- ✅ 缓存功能正常运行

### 4. JSON-RPC 调用工具验证
- ✅ anp_jsonrpc_call 工具正确构造 JSON-RPC 请求
- ✅ DID 身份验证头正确生成和附加
- ✅ 请求发送到正确的端点（/agents/jsonrpc）
- ✅ 响应解析正确处理成功和错误情况
- ✅ 请求 ID 正确生成和传递

### 5. Master Agent 路由验证
- ✅ 正确检测包含 AD.json URL 的消息发送请求
- ✅ 消息发送请求正确委托给 Message Agent
- ✅ 非消息发送的 ANP 请求仍走原有流程
- ✅ 错误处理和回退机制正常工作

### 6. LLM 工具调用验证
- ✅ OpenAI 模型能够正确理解 ANP 协议提示词
- ✅ 模型正确选择 anp_crawler 工具获取智能体信息
- ✅ 模型能够识别消息接收接口（receive_message）
- ✅ 模型正确使用 anp_jsonrpc_call 工具发送消息
- ✅ 工具调用序列和参数传递正确

### 7. 端到端消息传递验证
- ✅ 消息能够通过 ANP 协议成功发送
- ✅ 目标智能体正确接收和处理消息
- ✅ 发送方和接收方信息正确记录
- ✅ 消息历史和统计信息正确更新
- ✅ 完整的执行日志和状态反馈

### 8. 身份验证和安全验证
- ✅ DID 身份验证流程在 ANP 调用中正常工作
- ✅ 认证头信息正确生成和验证
- ✅ 未授权请求被正确拒绝
- ✅ 认证失败时的错误处理正确

## 测试数据和配置

### DID 配置文件
确保以下文件存在并配置正确：
- `docs/user_public/did.json`
- `docs/user_public/private_keys.json`

### 环境变量
```bash
# 确保代理设置不干扰本地连接
export NO_PROXY="localhost,127.0.0.1,0.0.0.0,::1,*.local"
export no_proxy="localhost,127.0.0.1,0.0.0.0,::1,*.local"
```

### 服务器配置
```python
# octopus/config/settings.py
port: int = 9527  # 确保端口配置正确
```

## 预期输出示例

### 成功的 ANP 协议端到端消息发送输出：

```
🤖 AI响应：

我已经成功使用 ANP 协议完成了消息发送任务。以下是详细的执行过程：

## 📋 任务执行报告

### 1. **请求路由阶段**
   - 检测到 ANP 消息发送请求：✅
   - 目标智能体：http://localhost:9527/ad.json  
   - 请求委托给 Message Agent：✅

### 2. **ANP Crawler 执行阶段**
   ```
   🔍 正在使用 anp_crawler 工具访问目标智能体...
   
   执行结果：
   - 智能体名称：Octopus Multi-Agent System
   - 协议类型：ANP 1.0.0
   - 安全认证：DID WBA
   - 发现接口数量：4个
   ```

### 3. **接口分析阶段**
   ```
   📊 可用接口列表：
   ✅ message.send_message (access_level: both)
   ✅ message.receive_message (access_level: external) ← 目标接口
   ✅ message.get_message_history (access_level: external)  
   ✅ message.get_statistics (access_level: both)
   
   🎯 选择接口：message.receive_message
   理由：该接口专门用于接收外部消息，访问级别为 external
   ```

### 4. **JSON-RPC 调用执行阶段**
   ```
   🚀 正在使用 anp_jsonrpc_call 工具发送消息...
   
   请求详情：
   - 端点：http://localhost:9527/agents/jsonrpc
   - 方法：message.receive_message
   - 参数：
     {
       "message_content": "你好，这是一条测试消息！",
       "sender_did": "did:wba:didhost.cc:test:public",
       "metadata": {"source": "anp_protocol", "test_type": "e2e"}
     }
   - 认证：DID WBA 成功
   ```

### 5. **消息发送结果**
   ```json
   {
     "success": true,
     "message_id": "msg_20241231_154723_abc123", 
     "sender_did": "did:wba:didhost.cc:test:public",
     "content": "你好，这是一条测试消息！",
     "timestamp": "2024-12-31T15:47:23.123456Z",
     "status": "received",
     "metadata": {
       "source": "anp_protocol",
       "test_type": "e2e",
       "processing_time_ms": 245
     }
   }
   ```

### 6. **验证和统计信息**
   - ✅ 消息成功投递到目标智能体
   - ✅ 消息内容完整传递
   - ✅ DID 身份验证通过
   - ✅ JSON-RPC 调用成功
   - ✅ 响应时间：245ms
   - ✅ 消息已记录到历史中

## 🎉 **任务完成总结**

通过 ANP 协议成功向智能体 `http://localhost:9527/ad.json` 发送了消息："你好，这是一条测试消息！"

### 技术流程验证：
- ✅ ANP Crawler 智能体发现和接口解析
- ✅ OpenRPC 格式接口识别和调用
- ✅ DID 分布式身份认证
- ✅ JSON-RPC 协议消息传递
- ✅ 端到端消息收发确认

### 性能指标：
- 总执行时间：1.2秒
- ANP爬取时间：380ms
- JSON-RPC调用时间：245ms
- 网络延迟：<50ms

🔄 这证明了 Octopus 多智能体系统的 ANP 协议集成工作正常，可以与其他符合 ANP 标准的智能体进行互操作！
```

### ANP 协议错误处理示例：

```
🤖 AI响应：

在尝试使用 ANP 协议发送消息时遇到了问题：

## ⚠️ **执行报告 - 部分失败**

### 1. **ANP Crawler 执行**
   - ✅ 成功访问 AD.json 文档
   - ✅ 解析智能体信息成功
   - ❌ 未发现可用的消息接收接口

### 2. **问题分析**
   ```
   发现的接口列表：
   - message.send_message (access_level: internal) 
   - message.get_statistics (access_level: internal)
   
   问题：所有接口的访问级别都是 internal，无法从外部调用
   ```

### 3. **建议解决方案**
   1. 检查目标智能体的接口配置
   2. 确认 receive_message 方法的 access_level 设置为 "external" 
   3. 重新生成 AD.json 文档
   4. 验证智能体的对外服务配置

这说明了 ANP 协议的访问控制机制正确工作，只有明确标记为对外开放的接口才能被外部调用。
```

## 🎯 **方案特点和优势**

### 核心特性

#### 1. **完整的 ANP 协议支持**
- ✅ 标准的 Agent Description JSON 格式
- ✅ OpenRPC 接口定义和解析
- ✅ StructuredInterface + content 嵌入格式
- ✅ DID 分布式身份认证
- ✅ JSON-RPC 2.0 标准调用

#### 2. **智能的消息路由架构**
- 🧠 Master Agent 自动检测 ANP 消息发送请求
- 🎯 智能委托给专门的 Message Agent 处理
- 🔄 保持向后兼容，支持传统 DID 直接调用
- 🛡️ 访问级别控制（internal/external/both）

#### 3. **LLM 驱动的工具调用**
- 🤖 基于 anp_crawler/bakup 经验的专业提示词
- 🔧 anp_crawler 和 anp_jsonrpc_call 两个核心工具
- 📊 智能接口识别和方法选择
- 🔍 自动化的错误诊断和处理

#### 4. **端到端的可观测性**
- 📋 详细的执行过程日志
- ⏱️ 性能指标监控（响应时间、处理时间）
- 🔍 完整的调试信息和错误追踪
- 📊 消息历史和统计信息记录

### 技术优势

#### 1. **架构设计优势**
- **单一职责原则**：每个组件职责清晰
- **低耦合高内聚**：组件间依赖最小化
- **可扩展性**：支持新的 ANP 协议特性
- **可测试性**：每个组件都可独立测试

#### 2. **ANP 协议优势**
- **标准化**：符合 ANP 1.0.0 规范
- **互操作性**：与其他 ANP 智能体兼容
- **安全性**：DID 身份验证保障
- **灵活性**：支持多种接口访问级别

#### 3. **工具集成优势**
- **智能化**：LLM 自动选择合适的工具和接口
- **容错性**：多层错误处理和回退机制
- **效率性**：缓存机制减少重复请求
- **可监控**：全过程日志和状态跟踪

### 应用场景

#### 1. **多智能体协作**
- 支持 Octopus 与其他 ANP 智能体的协作
- 实现跨平台的智能体消息传递
- 构建分布式智能体网络

#### 2. **系统集成测试**
- 验证 ANP 协议实现的正确性
- 测试 DID 身份认证流程
- 确保接口访问控制有效性

#### 3. **开发和调试**
- 提供详细的执行过程可视化
- 支持问题快速定位和解决
- 便于新功能的开发和验证

### 扩展性考虑

#### 1. **支持更多 ANP 协议特性**
- 异步消息处理
- 消息路由和转发
- 智能体能力发现和匹配

#### 2. **增强安全性**
- 消息加密和数字签名
- 更细粒度的访问控制
- 审计日志和合规性支持

#### 3. **性能优化**
- 连接池和请求复用
- 智能缓存策略
- 负载均衡和故障转移

---

**这个完善的端到端测试方案为 Octopus 多智能体系统提供了强大的 ANP 协议支持，实现了真正的智能体间互操作！** 🚀
