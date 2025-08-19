# Octopus 多智能体系统

Octopus 是一个基于装饰符和反射机制的多智能体架构系统，通过模块化的智能体设计提供高效、可扩展的任务处理能力。

## 核心特性

- **装饰符驱动**：使用 `@register_agent` 和 `@agent_method` 装饰符自动注册智能体和方法
- **反射机制**：自动发现智能体能力，提取方法签名和文档
- **智能路由**：基于任务需求自动选择和调度合适的智能体
- **OpenAI 集成**：主智能体使用 GPT-4 进行任务分析和结果综合
- **并行执行**：支持多智能体并行执行任务

## 快速开始

本项目使用 [uv](https://github.com/astral-sh/uv) 作为 Python 包管理器，提供快速的依赖解析和安装。

### 1. 安装依赖

使用 uv 安装依赖：

```bash
# 安装基础依赖
uv pip install -e .

# 安装开发依赖
uv pip install -e ".[dev]"

# 安装所有依赖
uv pip install -e ".[all]"
```

或使用 pip：

```bash
pip install -e .
```

### 可选依赖组

- `dev`: 开发工具（pytest, black, mypy 等）
- `data`: 数据处理（numpy, pandas, matplotlib）
- `distributed`: 分布式计算（redis, celery, dask）
- `communication`: 通信支持（websockets, pika, kafka）
- `all`: 所有可选依赖

### uv 常用命令

```bash
# 查看依赖树
uv tree

# 更新依赖
uv pip install --upgrade -e .

# 同步依赖（严格按照 pyproject.toml）
uv pip sync pyproject.toml

# 运行测试
uv run pytest

# 代码格式化
uv run black .

# 类型检查
uv run mypy octopus/
```

### 2. 设置环境变量

创建 `.env` 文件：

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7

# Application Configuration
DEBUG=false
LOG_LEVEL=INFO

# Agent Configuration
MAX_AGENTS=100
AGENT_TIMEOUT=300
```

或直接设置环境变量：

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 运行示例

```bash
# 运行完整的多智能体系统演示
uv run python octopus/example_usage.py

# 只运行直接智能体调用（不需要 OpenAI）
uv run python octopus/example_usage.py --direct
```

或直接使用 Python：

```bash
# 运行完整的多智能体系统演示
python octopus/example_usage.py

# 只运行直接智能体调用（不需要 OpenAI）
python octopus/example_usage.py --direct
```

## 创建新的智能体

### 1. 基本结构

```python
from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_method

@register_agent(
    name="my_agent",
    description="My custom agent",
    version="1.0.0",
    tags=["custom", "example"]
)
class MyAgent(BaseAgent):
    """My custom agent implementation."""

    def __init__(self):
        super().__init__(
            name="MyAgent",
            description="Handles custom tasks"
        )
```

### 2. 添加方法

```python
@agent_method(
    description="Process data",
    parameters={
        "data": {"type": "dict", "description": "Input data"},
        "options": {"type": "dict", "description": "Processing options", "required": False}
    },
    returns="dict"
)
def process_data(self, data: Dict[str, Any], options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process input data with given options.

    Args:
        data: Input data to process
        options: Optional processing parameters

    Returns:
        Processed results
    """
    # Implementation here
    return {"result": "processed"}
```

### 3. 自动注册

只需导入智能体类，装饰符会自动注册到路由器：

```python
from octopus.agents.my_agent import MyAgent

# 智能体已自动注册，可以通过路由器调用
result = router.execute_agent_method(
    agent_name="my_agent",
    method_name="process_data",
    parameters={"data": {"key": "value"}}
)
```

## 使用主智能体

主智能体 (MasterAgent) 负责：
1. 分析任务需求
2. 选择合适的子智能体
3. 创建执行计划
4. 调度任务执行
5. 综合结果

```python
from octopus.master_agent import MasterAgent

# 初始化主智能体
master = MasterAgent()

# 提交复杂任务
result = master.process_task(
    task="分析这段文本的情感倾向并提取关键词：...",
    context={"priority": "high"}
)

# 查看执行结果
if result["status"] == "success":
    print(result["results"]["synthesis"])
```

## 架构组件

### BaseAgent
所有智能体的基类，提供：
- 状态管理
- 生命周期管理
- 性能追踪
- 参数验证

### AgentRouter
中央路由器，负责：
- 智能体注册
- 方法发现
- 任务路由
- Schema 生成

### MasterAgent
主控制器，提供：
- 任务分析（使用 OpenAI）
- 执行计划生成
- 多智能体协调
- 结果综合

## 配置选项

在 `octopus/config/settings.py` 中配置：

```python
# OpenAI 设置
openai_api_key = "your-key"
openai_model = "gpt-4-turbo-preview"
openai_temperature = 0.7

# 智能体设置
max_agents = 100
agent_timeout = 300  # 秒
```

## 最佳实践

1. **单一职责**：每个智能体专注于特定领域
2. **清晰文档**：使用详细的 docstring 和装饰符参数
3. **类型提示**：使用 Python 类型提示提高代码可读性
4. **错误处理**：在智能体方法中实现健壮的错误处理
5. **性能优化**：对重型资源使用延迟初始化

## 示例智能体

系统包含一个文本处理智能体示例 (`TextProcessorAgent`)，提供：
- 词频统计
- 关键词提取
- 情感分析
- 文本摘要

## 扩展功能

- 支持异步执行
- 并行任务处理
- 任务历史记录
- 智能体状态监控

## 故障排除

1. **OpenAI API Key 错误**：确保设置了有效的 API key
2. **智能体未找到**：检查智能体是否正确注册
3. **方法调用失败**：验证参数是否符合方法签名

## 项目结构

```
octopus/
├── agents/                 # 智能体模块
│   ├── base_agent.py      # 基础智能体类
│   └── text_processor_agent.py  # 文本处理智能体示例
├── router/                # 路由器模块
│   └── agents_router.py   # 智能体路由器
├── config/                # 配置模块
│   └── settings.py        # 应用配置
├── master_agent.py        # 主智能体
├── example_usage.py       # 使用示例
└── README.md             # 项目说明
```

## uv 项目管理

本项目采用现代 Python 项目管理工具 uv，具有以下优势：

- ⚡ **快速**：比 pip 快 10-100 倍的依赖解析
- 🔒 **可靠**：确定性的依赖解析和锁定
- 📦 **完整**：支持 pyproject.toml 的所有功能
- 🎯 **简单**：统一的命令行界面

### 开发工作流

```bash
# 1. 克隆项目
git clone <repo-url>
cd octopus

# 2. 创建虚拟环境并安装依赖
uv pip install -e ".[dev]"

# 3. 运行测试
uv run pytest

# 4. 格式化代码
uv run black .

# 5. 运行示例
uv run python octopus/example_usage.py
```

## 开发路线图

- [ ] 支持更多 LLM 提供商
- [ ] 智能体热重载
- [ ] Web UI 界面
- [ ] 分布式执行
- [ ] 智能体市场
