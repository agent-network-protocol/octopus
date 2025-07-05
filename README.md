# Octopus

A Open Source Personal Agent - 一个开源的个人智能体系统

## 项目简介

Octopus 是一个基于 FastAPI 的多智能体系统，提供了以下功能：
- 智能体注册和发现机制
- 任务分析和分解
- 智能体协调和执行
- 基于 OpenAI 的任务处理

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
   cp .env_template .env
   ```

2. 编辑 `.env` 文件，填入您的实际配置：
   ```bash
   # OpenAI Configuration
   OPENAI_API_KEY=your_actual_openai_api_key
   OPENAI_MODEL=gpt-4-turbo-preview
   
   # Application Configuration
   APP_NAME=Octopus
   APP_PORT=9880
   LOG_LEVEL=INFO
   ```

**重要提示：** `.env` 文件包含敏感信息，已被 `.gitignore` 忽略，不会被提交到版本控制系统。

## 运行项目

### 1. 启动 FastAPI 服务器

```bash
# 使用内置的 main 函数启动（推荐）
uv run python -m octopus.octopus

# 或者使用 uvicorn 直接启动
uv run uvicorn octopus.octopus:app --host 0.0.0.0 --port 9880 --reload
```

### 2. 访问 API

服务器启动后，您可以访问：
- 根路径：http://localhost:9880/
- 健康检查：http://localhost:9880/health
- 应用信息：http://localhost:9880/api/v1/info

## 项目结构

```
octopus/
├── octopus/                    # 主要代码包
│   ├── agents/                 # 智能体相关代码
│   │   ├── base_agent.py       # 基础智能体类
│   │   └── text_processor_agent.py  # 文本处理智能体
│   ├── router/                 # 路由管理
│   │   └── agents_router.py    # 智能体路由器
│   ├── utils/                  # 工具类
│   │   └── log_base.py         # 日志配置
│   ├── config/                 # 配置管理
│   │   └── settings.py         # 应用设置
│   ├── master_agent.py         # 主智能体
│   └── octopus.py              # FastAPI 应用入口
├── .env_template               # 环境变量模板
├── pyproject.toml              # 项目配置
└── README.md                   # 项目说明
```

## 开发说明

### 日志系统

项目使用统一的日志系统：
- 主入口 `octopus.py` 使用 `setup_enhanced_logging()` 初始化日志
- 其他模块使用 `logging.getLogger(__name__)` 获取日志器
- 日志文件位置：`~/Library/Logs/octopus/octopus.log`（macOS）

### 智能体开发

1. 继承 `BaseAgent` 类
2. 使用 `@register_agent` 装饰器注册智能体
3. 使用 `@agent_method` 装饰器注册方法

示例：
```python
@register_agent(name="my_agent", description="My custom agent")
class MyAgent(BaseAgent):
    @agent_method(description="Process text")
    def process_text(self, text: str) -> str:
        return f"Processed: {text}"
```

## 许可证

本项目采用开源许可证，详见 [LICENSE](LICENSE) 文件。
