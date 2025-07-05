# 环境变量配置指南

## 概述

Octopus 使用环境变量来管理应用程序的配置。所有的配置都定义在 `.env` 文件中，该文件从 `.env_template` 模板创建。

## 设置步骤

### 1. 创建 .env 文件

从项目根目录运行以下命令：

```bash
cp .env_template .env
```

### 2. 配置 OpenAI API 密钥

编辑 `.env` 文件，设置您的 OpenAI API 密钥：

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

**如何获取 OpenAI API 密钥：**

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 登录您的账户
3. 前往 "API Keys" 页面
4. 创建一个新的 API 密钥
5. 复制密钥并粘贴到 `.env` 文件中

### 3. 配置应用程序设置

```bash
# Application Configuration
APP_NAME=Octopus
APP_VERSION=0.1.0
DEBUG=false
HOST=0.0.0.0
PORT=9880

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=

# Agent Configuration
MAX_AGENTS=100
AGENT_TIMEOUT=300

# ANP SDK Configuration
ANP_SDK_ENABLED=true
```

## 环境变量说明

### 应用程序配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `APP_NAME` | 应用程序名称 | Octopus |
| `APP_VERSION` | 应用程序版本 | 0.1.0 |
| `DEBUG` | 调试模式 | false |
| `HOST` | 服务器主机地址 | 0.0.0.0 |
| `PORT` | 服务器端口 | 9880 |

### 日志配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `LOG_LEVEL` | 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL) | INFO |
| `LOG_FILE` | 日志文件路径 (为空时使用默认路径) | (empty) |

### 智能体配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `MAX_AGENTS` | 最大智能体数量 | 100 |
| `AGENT_TIMEOUT` | 智能体超时时间（秒） | 300 |

### OpenAI 配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | (必需) |
| `OPENAI_MODEL` | 使用的 OpenAI 模型 | gpt-4-turbo-preview |
| `OPENAI_TEMPERATURE` | 模型温度参数 | 0.7 |
| `OPENAI_MAX_TOKENS` | 最大 token 数量 | 4000 |

### ANP SDK 配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `ANP_SDK_ENABLED` | 是否启用 ANP SDK | true |

## 验证配置

运行以下命令验证配置是否正确：

```bash
# 验证基本配置
uv run python -c "from octopus.config.settings import get_settings; settings = get_settings(); print('✓ 配置加载成功'); print(f'端口: {settings.port}'); print(f'主机: {settings.host}'); print(f'OpenAI 模型: {settings.openai_model}')"

# 测试 OpenAI API 密钥是否可用（需要设置真实的 API 密钥）
uv run python -c "from octopus.master_agent import MasterAgent; agent = MasterAgent(); print('✓ MasterAgent 初始化成功')"
```

## 安全提醒

- **永远不要**将 `.env` 文件提交到版本控制系统
- `.env` 文件已被 `.gitignore` 忽略，确保不会被意外提交
- 定期轮换您的 API 密钥
- 在生产环境中使用强密钥和安全的配置

## 故障排除

### 常见问题

1. **OpenAI API 密钥无效**
   - 确保密钥格式正确（以 `sk-` 开头）
   - 检查密钥是否已过期
   - 验证 OpenAI 账户是否有足够的额度

2. **端口已被占用**
   - 修改 `.env` 文件中的 `PORT` 设置
   - 或者停止占用该端口的其他服务

3. **配置不生效**
   - 确认 `.env` 文件位于项目根目录
   - 检查环境变量名称是否正确匹配
   - 重启应用程序以应用新配置

### 调试命令

```bash
# 查看当前配置
uv run python -c "from octopus.config.settings import get_settings; import json; settings = get_settings(); print(json.dumps(settings.model_dump(), indent=2, default=str))"

# 测试环境变量加载
uv run python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('PORT:', os.getenv('PORT')); print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
``` 