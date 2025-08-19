# 重构后的RPC架构设计

## 设计原则

本次重构严格遵循面向对象设计的**单一职责原则（SRP）**，将原本混合在一起的功能分离到专门的类中。

## 架构概览

```
AgentRouter (agents_router.py)
├── 核心职责：Agent注册、发现、实例管理
└── RPC集成：直接使用专门的RPC服务类

rpc_services.py
├── OpenRPCGenerator：专门生成OpenRPC规范
└── JSONRPCHandler：专门处理JSON-RPC请求
```

## 类职责分工

### 1. AgentRouter
**职责：** Agent生命周期管理
- ✅ Agent注册和发现
- ✅ Agent实例创建和管理
- ✅ 方法执行和参数验证
- ✅ Schema生成（用于LLM）
- ✅ 通过委托提供RPC服务接口

**不负责：**
- ❌ OpenRPC规范生成的具体逻辑
- ❌ JSON-RPC请求解析和响应格式化
- ❌ 访问控制的具体实现

### 2. OpenRPCGenerator
**职责：** OpenRPC规范生成
- ✅ 解析Agent方法定义
- ✅ 转换为OpenRPC 1.3.2格式
- ✅ 应用访问级别过滤
- ✅ 生成完整的OpenRPC文档

**不负责：**
- ❌ Agent管理
- ❌ JSON-RPC请求处理

### 3. JSONRPCHandler
**职责：** JSON-RPC请求处理
- ✅ JSON-RPC请求解析
- ✅ 访问级别验证
- ✅ 方法调用委托
- ✅ 错误处理和响应格式化

**不负责：**
- ❌ Agent管理
- ❌ OpenRPC规范生成



## 依赖关系

```
AgentRouter → {OpenRPCGenerator, JSONRPCHandler}
     ↑                        ↑
     └────────────────────────┘
        (通过构造函数注入AgentRouter引用)
```

## 使用示例

### 生成OpenRPC规范
```python
# 通过AgentRouter的简洁接口
openrpc_spec = agent_router.generate_openrpc_interface(
    base_url="http://localhost:8000",
    app_version="1.0.0"
)

# 或者直接使用专门的生成器
from octopus.router.rpc_services import OpenRPCGenerator
generator = OpenRPCGenerator(agent_router)
openrpc_spec = generator.generate_interface(base_url, app_version)
```

### 处理JSON-RPC请求
```python
# 通过AgentRouter的简洁接口
response = agent_router.handle_jsonrpc_call(
    method="message.send_message",
    params={"message_content": "Hello", "recipient_did": "did:example:123"},
    request_id="req-123"
)

# 或者直接使用专门的处理器
from octopus.router.rpc_services import JSONRPCHandler
handler = JSONRPCHandler(agent_router)
response = handler.handle_call(method, params, request_id)
```

## 扩展性

### 添加新的RPC协议
只需要：
1. 创建新的协议处理器类（如`GraphQLHandler`）
2. 在`AgentRouter`中添加懒加载方法和委托接口

### 修改OpenRPC生成逻辑
只需要修改`OpenRPCGenerator`类，不影响其他组件。

### 修改访问控制策略
只需要修改`JSONRPCHandler`类中的`_is_method_accessible`方法。

## 测试策略

### 单元测试
- `OpenRPCGenerator`：测试规范生成逻辑
- `JSONRPCHandler`：测试请求处理和访问控制
- `AgentRouter`：测试核心Agent管理功能

### 集成测试
- `AgentRouter`与RPC服务的集成：测试委托调用
- 端到端流程：从HTTP请求到Agent方法执行

## 性能考虑

### 懒加载
- RPC服务类采用懒加载模式，只在首次使用时创建
- 避免了启动时的性能开销

### 缓存
- OpenRPC规范可以缓存，避免重复生成
- Agent实例复用，避免重复创建

## 总结

重构后的架构具有以下优势：

1. **清晰的职责分离**：每个类都有明确的单一职责
2. **更好的可测试性**：独立的类更容易进行单元测试
3. **更强的扩展性**：新功能可以独立添加，不影响现有代码
4. **更好的可维护性**：相关逻辑集中，修改影响范围可控
5. **保持向后兼容**：外部接口保持不变，内部实现优化

这是一个符合SOLID原则的优秀架构设计！
