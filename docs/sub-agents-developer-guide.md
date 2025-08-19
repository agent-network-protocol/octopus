## 子智能体开发指导文档（基于 Octopus 框架）

### 目标读者
希望在 Octopus 多智能体系统中新增、维护或对外暴露能力的工程师。

### 阅读前提
- 熟悉 Python 3.10+ 与类型注解。
- 了解 `logging`、异步函数（async/await）。
- 已阅读项目结构文档与环境配置文档（`docs/project_structure.md`、`docs/environment_setup.md`）。

---

## 架构速览


+---------------------+         +---------------------------------------------+
| 客户端（Web/API）   |  --->   | FastAPI（`octopus/api/ad_router.py`）        |
+---------------------+         | - GET /ad.json -> OpenRPCGenerator（仅导出   |
                                |   access_level=external/both 的方法）        |
                                | - POST /agents/jsonrpc -> JSONRPCHandler     |
                                +-------------------------------^-------------+
                                                                |
                                                                v
+----------------------+       +---------------------------------------------+
| MasterAgent          |       | AgentRouter（单例，`octopus/router/agents_  |
| (`octopus/master...`)|       | router.py`）                                |
| - process_natural_   |       | - register()：注册Agent                     |
|   language()         |       | - list_agents()/get_agent()：发现Agent与方法 |
| - _select_agent()    |       | - execute_agent_method(_async)：统一执行     |
| - _execute_agent()   |       | - generate_openrpc_interface()：导出OpenRPC  |
+-----------^----------+       +------------------------------^--------------+
            | 使用                                               |
            |                                                    |
            |                                                    |
+-----------+----------------------------------+                 |
| 子智能体（继承 `BaseAgent`）                 |                 |
| `octopus/agents/...`                         |                 |
| - @register_agent：类装饰器，注册到Router     |                 |
| - @agent_interface：方法装饰器，描述参数/返回  |                 |
|   与 access_level                            |                 |
+-----------------------------^----------------+                 |
                              | 通过模块导入触发装饰器注册                     |
                              |                                               |
+-----------------------------+---------------------------+                   |
| `octopus/api/agent_loader.py`                           |                   |
| - import 子智能体模块以触发装饰器 -> Router 完成登记     |-------------------+
+---------------------------------------------------------+

交互流程概要
整体流程是：开发者创建子智能体类继承 BaseAgent，用 @register_agent 装饰类、用 @agent_interface 装饰对外/对内方法（给出 description、parameters、returns、access_level）。当模块被 agent_loader 导入时，装饰器借助反射收集方法签名和注解，生成 MethodInfo 并封装为 AgentRegistration 注册到 AgentRouter。

对外暴露时，/ad.json 通过 OpenRPCGenerator 仅导出 access_level ∈ {external, both} 的方法到 OpenRPC 规范；外部调用走 /agents/jsonrpc，由 JSONRPCHandler 解析 agent.method、校验访问级别，再委托 AgentRouter.execute_agent_method(_async) 调用子智能体方法。

系统内部使用时，MasterAgent 读取 router.list_agents()/get_agent() 的能力元数据，结合 LLM 进行方法选择后，调用 router.execute_agent_method_async() 执行；参数校验与默认值填充由 BaseAgent.validate_parameters() 处理，异步方法会被自动 await。


- **主智能体 `MasterAgent`（`octopus/master_agent.py`）**：
  - 自然语言入口，基于 `Agents Router` 的能力发现与委派。
  - 通过 `router.list_agents()` 汇总所有子智能体及方法元数据；调用 OpenAI 进行方法选择；再统一转发到路由执行。

- **路由与注册（`octopus/router/agents_router.py`）**：
  - `@register_agent`：类级注册装饰器，自动收集类中被 `@agent_interface` 标注的方法元数据。
  - `@agent_interface`：方法级装饰器，描述方法用途、参数、返回、访问级别等。
  - `router.execute_agent_method(_async)`：统一参数校验、同步/异步执行与统计。
  - `generate_openrpc_interface()`：仅导出 `access_level ∈ {external, both}` 的方法到 OpenRPC。

- **对外 API（`octopus/api/ad_router.py`）**：
  - `GET /ad.json`：返回 ANP AgentDescription，其中嵌入 OpenRPC 接口（外部/双向方法）。
  - `POST /agents/jsonrpc`：JSON‑RPC 入口，方法名格式为 `agent_name.method_name`。

- **示例子智能体**：
  - 文本处理（`octopus/agents/text_processor_agent.py`）。
  - 消息代理（`octopus/agents/message/message_agent.py`），演示 `access_level="external"`/`"both"` 的对外方法。

---

## 快速开始：最小可用子智能体

### 1) 新建文件
- 建议放置在 `octopus/agents/` 目录，命名为 `your_agent_name_agent.py`。
- 如需子包结构，也可放置于 `octopus/agents/your_agent/` 并在 `__init__.py` 中导出类。

### 2) 代码示例
```python
# File: octopus/agents/calculator_agent.py
from typing import Dict

from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_interface


@register_agent(
    name="calculator",  # 将成为 JSON-RPC 的前缀（agent_name）
    description="Simple calculator agent",
    version="1.0.0",
    tags=["demo", "math"]
)
class CalculatorAgent(BaseAgent):
    """Agent specialized in basic arithmetic operations."""

    def __init__(self):
        super().__init__(name="CalculatorAgent", description="Basic arithmetic operations")
        self.logger.info("CalculatorAgent initialized")  # logs in English

    @agent_interface(
        description="Add two integers",
        parameters={
            "a": {"description": "First operand"},
            "b": {"description": "Second operand"}
        },
        returns="dict",
        access_level="both"  # 对外可见，同时系统内部也可用
    )
    def add(self, a: int, b: int) -> Dict[str, int]:
        """Add two integers and return a JSON-serializable result.

        Args:
            a: First operand
            b: Second operand

        Returns:
            A dict with the sum result
        """
        result = {"sum": a + b}
        self.logger.info(f"add: {a} + {b} = {result['sum']}")
        return result

    @agent_interface(
        description="Divide two numbers (safe)",
        parameters={
            "numerator": {"description": "Numerator"},
            "denominator": {"description": "Denominator (> 0)"}
        },
        returns="dict",
        access_level="external"  # 仅对外可见
    )
    def divide(self, numerator: float, denominator: float) -> Dict[str, float]:
        """Safely divide two numbers.

        Args:
            numerator: Numerator
            denominator: Denominator (> 0)

        Returns:
            A dict with the division result
        """
        if denominator == 0:
            raise ValueError("Denominator cannot be zero")
        value = numerator / denominator
        self.logger.info(f"divide: {numerator} / {denominator} = {value}")
        return {"value": value}
```

要点：
- 使用 `@register_agent` 标记类，`name` 将成为 JSON‑RPC 方法前缀（如 `calculator.add`）。
- 使用 `@agent_interface` 标记方法：
  - `description` 必填（MasterAgent 的模型选择高度依赖描述质量）。
  - `parameters` 中建议仅提供 `description`，类型以注解为准（由路由反射解析）。
  - `returns` 建议返回 JSON‑可序列化结构，便于 JSON‑RPC 与 OpenRPC。
  - `access_level`：`internal`（默认，不导出）、`external`（对外）、`both`（内外可见）。
- 基类 `BaseAgent` 已内建：
  - 统一 `self.logger`（English logs）。
  - 参数校验 `validate_parameters()` 与执行统计 `execute_with_tracking()`。
  - 同步/异步方法统一调度（路由会自动识别异步方法并直接 `await`）。

### 3) 让系统加载你的智能体

`octopus/api/agent_loader.py` 负责集中导入与注册智能体。新增后将模块加入清单：

```python
# File: octopus/api/agent_loader.py (节选)
agent_modules = [
    ("octopus.agents.text_processor_agent", "TextProcessorAgent"),
    ("octopus.agents.calculator_agent", "CalculatorAgent"),  # 新增行
]
```

系统启动时加载这些模块即可完成注册（`router.register(...)` 由装饰器自动触发）。

---

## 与 MasterAgent 协作的设计要点

`MasterAgent` 会：
- 通过 `router.list_agents()` 与 `_get_agent_capabilities()` 汇总所有子智能体的方法、参数与描述。
- 将集合的能力信息与用户请求交给 LLM 做“方法选择”，再调用 `router.execute_agent_method_async(...)` 执行。

为了被更好地“选中”，请：
- 为类与方法撰写清晰简洁、领域特征明显的 `description` 与 docstring（Google 风格）。
- 方法名直观、动词开头，如 `analyze_sentiment`、`extract_keywords`、`send_message`。
- 参数命名清晰并提供 `parameters.{param}.description`，避免与业务领域无关的缩写。
- 对外暴露方法务必设置 `access_level="external"` 或 `"both"`，否则不会出现在 OpenRPC/JSON‑RPC 中。

---

## 对外接口（OpenRPC 与 JSON‑RPC）

- OpenRPC 由 `router.generate_openrpc_interface()` 自动生成，只包含 `external/both` 的方法，并被嵌入 `GET /ad.json`。
- JSON‑RPC 入口：`POST /agents/jsonrpc`，字段如下：
  - `jsonrpc`: 固定 `"2.0"`
  - `method`: `"{agent_name}.{method_name}"`（`agent_name` 即 `@register_agent(name=...)`）
  - `params`: 方法参数对象
  - `id`: 请求 ID（数字或字符串）

示例（调用上面的 `calculator.add`）：

```bash
curl -X POST http://localhost:8000/agents/jsonrpc \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "method": "calculator.add",
    "params": {"a": 3, "b": 5},
    "id": 1
  }'
```

成功响应：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {"sum": 8}
}
```

注意：若方法 `access_level` 为 `internal`，`/agents/jsonrpc` 会返回“Method not found”（由访问控制拦截）。

---

## 日志与运行

- 主入口需初始化日志（统一格式与落盘）。按规则在主入口调用：

```python
# main entry (示例)
from octopus.utils.log_base import setup_enhanced_logging

logger = setup_enhanced_logging()  # 初始化日志（全局生效）
logger.info("Octopus starting...")
```

- 子智能体内部使用 `self.logger`（由 `BaseAgent` 注入）记录关键事件；日志与注释请统一使用英文。

---

## 进阶：异步方法、参数与返回

- 异步方法支持：在 `@agent_interface` 标注的异步方法上，路由器将直接 `await` 执行（参见 `execute_agent_method_async`）。
- 参数来源：
  - 运行时由路由反射方法签名与注解进行校验（`validate_parameters`）。
  - `@agent_interface(parameters=...)` 的 `description` 将被合并进参数元数据，用于 UI/LLM 友好展示。
- 返回类型：
  - 建议返回 JSON‑可序列化的 `dict`/`list`/基础类型，以便 JSON‑RPC 与 OpenRPC 一致化。
  - 发生异常请抛出标准异常；路由与 API 层会包装为 JSON‑RPC 错误响应。

---

## 最佳实践与规范

- **类型提示**：所有公开方法与参数必须添加精确的类型注解。
- **文档与描述**：使用 Google 风格 docstring；`description` 应简明、具体、可被模型理解。
- **方法划分**：小而清晰的职责；避免臃肿方法；优先增加多个原子能力方法。
- **错误处理**：
  - 参数校验失败抛出 `ValueError`；外部异常统一记录 `self.logger.error(..., exc_info=True)`。
  - 对外方法避免返回非 JSON‑可序列化对象。
- **访问控制**：合理设置 `access_level`，仅对外暴露需要的能力。
- **命名约定**：
  - Agent `name` 使用短横线/下划线分隔的业务名（与路由一致即可）。
  - 方法名动词短语，语义明确；参数名采用全单词且英文。
- **与 Master 协作**：为能力提供可判定、可检索的描述与标签（`tags`）。

---

## 调试清单（Checklist）

- 代码组织：已在 `octopus/agents/` 下新建文件或子包，且类已被 `@register_agent` 标注。
- 方法标注：对外方法均添加了 `@agent_interface`，完善了 `description` 与参数 `description`。
- 加载注册：新增模块已加入 `octopus/api/agent_loader.py` 的 `agent_modules` 列表。
- 访问控制：对外方法设置了 `access_level="external"` 或 `"both"`。
- 可见性验证：
  - 访问 `GET /ad.json`，检查方法是否出现在 OpenRPC 中。
  - 通过 `POST /agents/jsonrpc` 调用方法，确认请求/响应正确。
- 日志：主入口已调用 `setup_enhanced_logging()`；子智能体内使用 `self.logger` 输出关键步骤。

---

## 参考实现（项目内）

- `octopus/agents/text_processor_agent.py`：文本处理示例，展示同步方法、参数提取与返回结构。
- `octopus/agents/message/message_agent.py`：
  - 展示对外方法（`access_level="external"/"both"`）。
  - 演示异步调用外部工具链（ANP Crawler + OpenAI Tools）。
- `octopus/router/agents_router.py`：注册、能力收集、参数校验、同步/异步执行、OpenRPC 集成。
- `octopus/master_agent.py`：自然语言到方法选择与委派的完整范式。
- `octopus/api/ad_router.py`：对外 JSON‑RPC 与 ANP OpenRPC 导出。

---

## 常见问题（FAQ）

- 为什么我的方法没有出现在 `/ad.json`？
  - 检查是否设置了 `access_level` 为 `external` 或 `both`。
  - 确认模块已在 `agent_loader.py` 中导入，确保装饰器触发注册。

- JSON‑RPC 调用报 “Method not found”？
  - 方法名格式必须是 `agent_name.method_name`，`agent_name` 等于 `@register_agent(name=...)` 的值。
  - `access_level` 为 `internal` 的方法不会对外暴露。

- 异步方法如何暴露？
  - 直接将方法声明为 `async def` 并使用 `@agent_interface` 标注；路由会在异步路径直接 `await` 执行。

- 与 MasterAgent 的联动失败？
  - 提升方法与参数的 `description` 质量，使用领域关键词；确保返回结构可读、稳定。













