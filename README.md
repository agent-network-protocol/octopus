# 🐙 Octopus Multi-Agent AI System

A modern, distributed multi-agent AI system with ANP (Agent Network Protocol) support.

## ✨ 特性

- 🤖 **多智能体架构**: 基于装饰符的智能体注册和发现机制
- 🌐 **分布式通信**: 支持 ANP 协议的跨节点智能体通信
- 🎯 **任务协调**: 自然语言任务分析、分解和智能分发
- ⚡ **高性能**: 基于 FastAPI 的异步处理框架
- 🛠️ **开发友好**: 丰富的 CLI 工具和配置选项
- 🔐 **安全认证**: 支持 DID 去中心化身份认证

## 环境配置

### 1. 安装依赖

本项目使用 [uv](https://github.com/astral-sh/uv) 作为包管理工具：

```bash
# 安装 uv（如果还没有安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步项目依赖
uv sync
```

### 2. 环境变量配置

1. 复制环境变量模板文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入您的实际配置：
   ```bash
   # OpenAI Configuration
   OPENAI_API_KEY=your_actual_openai_api_key
   OPENAI_MODEL=openai/gpt-4o

   # Application Configuration
   PORT=9527
   HOST=0.0.0.0
   LOG_LEVEL=INFO

   # ANP Configuration
   ANP_SDK_ENABLED=true
   ANP_GATEWAY_WS_URL=wss://anpproxy.com/ws
   ANP_GATEWAY_HTTP_URL=www.anpproxy.com
   ANP__RECEIVER__LOCAL_PORT=8001
   ```

**重要提示：** `.env` 文件包含敏感信息，已被 `.gitignore` 忽略，不会被提交到版本控制系统。

## 🚀 快速开始

### 1. 基础启动

```bash
# 默认启动（端口 9527）
uv run python -m octopus.octopus

# 查看所有选项
uv run python -m octopus.octopus --help

# 检查版本
uv run python -m octopus.octopus --version
```

### 2. CLI 选项

```bash
# 自定义端口
uv run python -m octopus.octopus --port 9529

# 调试模式
uv run python -m octopus.octopus --debug --log-level DEBUG

# 禁用 ANP（单机模式）
uv run python -m octopus.octopus --no-anp

# 使用自定义配置文件
uv run python -m octopus.octopus --config .env.production
```

### 3. 多实例部署

启动两个 Octopus 实例进行 ANP 通信：

```bash
# 终端 1: 启动 ANP-Proxy（如需本地测试）
cd /path/to/anp-proxy
uv run python -m anp_proxy

# 终端 2: 启动 Octopus-A
uv run python -m octopus.octopus --port 9527 --anp-gateway wss://anpproxy.com/ws

# 终端 3: 启动 Octopus-B
uv run python -m octopus.octopus --port 9529 --anp-gateway wss://anpproxy.com/ws
```

### 4. 访问 API

服务器启动后，可以访问（默认端口 9527）：
- 🏠 主页面：http://localhost:9527/
- 💚 健康检查：http://localhost:9527/health
- ℹ️ 应用信息：http://localhost:9527/v1/info
- 🤖 智能体描述：http://localhost:9527/ad.json
- 📡 ANP 状态：http://localhost:9527/anp/status

*注意：如果修改了端口配置，请相应调整URL*

## 📁 项目结构

```
octopus/
├── octopus/                    # 主要代码包
│   ├── agents/                 # 智能体相关代码
│   │   ├── base_agent.py       # 基础智能体类
│   │   ├── message/            # 消息处理智能体
│   │   └── text_processor_agent.py  # 文本处理智能体
│   ├── core/                   # 核心功能模块
│   │   └── receiver/           # ANP 接收器
│   ├── router/                 # 路由管理
│   │   └── agents_router.py    # 智能体路由器
│   ├── api/                    # API 接口
│   │   ├── chat_router.py      # 聊天接口
│   │   └── ad_router.py        # 智能体描述接口
│   ├── config/                 # 配置管理
│   │   └── settings.py         # 应用设置（支持 CLI 覆盖）
│   ├── utils/                  # 工具类
│   │   └── log_base.py         # 增强日志系统
│   ├── master_agent.py         # 主智能体协调器
│   └── octopus.py              # CLI 和 FastAPI 应用入口
├── .env.example                # 环境变量模板
├── pyproject.toml              # 项目配置（包含 Click CLI）
├── docs/                       # 项目文档
│   ├── environment_setup.md    # 环境配置指南
│   └── azure_openai_config.md  # Azure OpenAI 配置
└── README.md                   # 项目说明
```

## 🛠️ 开发指南

### 智能体开发

创建自定义智能体的步骤：

1. 继承 `BaseAgent` 类
2. 使用 `@register_agent` 装饰器注册智能体
3. 使用 `@agent_method` 装饰器注册方法

示例：
```python
from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_method

@register_agent(name="my_agent", description="My custom agent")
class MyAgent(BaseAgent):
    @agent_method(description="Process text")
    async def process_text(self, text: str) -> str:
        return f"Processed: {text}"
```

### 日志系统

- 📝 **增强日志**: 彩色输出，位置信息，文件记录
- 📂 **日志文件**: `~/Library/Logs/octopus/octopus.log`（macOS）
- 🎚️ **日志级别**: 通过 `--log-level` 或环境变量控制

### 配置系统

支持多层级配置优先级：
1. **CLI 参数**（最高优先级）
2. **环境变量**
3. **配置文件**（最低优先级）

## 🧪 测试和开发

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试类别
uv run pytest -m unit        # 单元测试
uv run pytest -m integration # 集成测试
uv run pytest -m "not slow"  # 跳过慢速测试
```

### 代码质量

```bash
# 格式化代码
uv run black octopus/

# 代码检查
uv run flake8 octopus/

# 类型检查
uv run mypy octopus/
```

### ANP 集成测试

系统包含 ANP 协议的集成测试功能：

```bash
# 手动运行 ANP 爬虫测试
uv run python -m octopus.test_scripts.test_anp_crawler

# 测试 ANP 功能（需要 anp-proxy 运行）
uv run python -m octopus.test_scripts.test_anp_functionality
```

## 🔧 技术栈

- **Python**: 3.11+
- **Web 框架**: FastAPI + Uvicorn
- **CLI 框架**: Click
- **配置管理**: Pydantic Settings
- **包管理**: uv
- **AI 集成**: OpenAI API
- **协议支持**: ANP (Agent Network Protocol)
- **身份认证**: DID (Decentralized Identity)

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
