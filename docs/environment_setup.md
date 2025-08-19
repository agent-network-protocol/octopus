# 🔧 环境配置指南

## 概述

Octopus 支持多种配置方式，提供灵活的配置管理：
- 📄 **环境文件** (`.env`)
- 🖥️ **CLI 参数**（优先级更高）
- 🌐 **环境变量**

## 🚀 快速设置

### 1. 创建环境文件

从项目根目录运行：

```bash
cp .env.example .env
```

### 2. 基础配置

编辑 `.env` 文件：

```bash
# 🤖 AI Configuration
OPENAI_API_KEY=your_actual_openai_api_key_here
OPENAI_MODEL=openai/gpt-4o

# 🌐 Application Configuration
PORT=9527
HOST=0.0.0.0
DEBUG=false
LOG_LEVEL=INFO

# 📡 ANP Configuration
ANP_SDK_ENABLED=true
ANP_GATEWAY_WS_URL=wss://anpproxy.com/ws
ANP_GATEWAY_HTTP_URL=www.anpproxy.com
ANP__RECEIVER__LOCAL_PORT=8001
```

### 3. CLI 参数覆盖

CLI 参数具有最高优先级：

```bash
# 使用 CLI 覆盖配置
uv run python -m octopus.octopus --port 9529 --debug --log-level DEBUG

# ANP 配置覆盖
uv run python -m octopus.octopus --anp-gateway wss://anpproxy.com/ws

# 使用自定义配置文件
uv run python -m octopus.octopus --config .env.production
```

### 4. 多实例配置

为不同实例创建专用配置：

```bash
# 创建实例配置
cp .env.example .env.instance_a
cp .env.example .env.instance_b

# 编辑端口配置
# .env.instance_a: PORT=9527
# .env.instance_b: PORT=9529

# 启动不同实例
uv run python -m octopus.octopus --config .env.instance_a
uv run python -m octopus.octopus --config .env.instance_b
```

## 📋 配置参数说明

### 🎯 CLI 参数映射

| CLI 参数 | 环境变量 | 描述 | 默认值 |
|----------|----------|------|--------|
| `--port` | `PORT` | 服务器端口 | 9527 |
| `--host` | `HOST` | 服务器主机 | 0.0.0.0 |
| `--debug` | `DEBUG` | 调试模式 | false |
| `--log-level` | `LOG_LEVEL` | 日志级别 | INFO |
| `--anp-gateway` | `ANP_GATEWAY_WS_URL` | ANP 网关WebSocket地址 | wss://anpproxy.com/ws |
| `--anp/--no-anp` | `ANP_SDK_ENABLED` | ANP 启用状态 | true |

### 🤖 AI 配置

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | - | ✅ |
| `OPENAI_MODEL` | AI 模型名称 | openai/gpt-4o | ❌ |
| `OPENAI_BASE_URL` | API 基础地址 | https://openrouter.ai/api/v1 | ❌ |
| `OPENAI_TEMPERATURE` | 模型温度 | 0.7 | ❌ |
| `OPENAI_MAX_TOKENS` | 最大 token 数 | 4000 | ❌ |

### 📡 ANP 协议配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `ANP_SDK_ENABLED` | 启用 ANP 功能 | true |
| `ANP_GATEWAY_WS_URL` | ANP 网关 WebSocket 地址 | wss://anpproxy.com/ws |
| `ANP_GATEWAY_HTTP_URL` | ANP 网关 HTTP 地址 | www.anpproxy.com |
| `ANP__RECEIVER__LOCAL_PORT` | ANP 接收器本地端口 | 8001 |
| `ANP__RECEIVER__GATEWAY_URL` | ANP 接收器网关地址 | wss://anpproxy.com/ws |
| `ANP__RECEIVER__TIMEOUT_SECONDS` | ANP 连接超时(秒) | 30.0 |

### 🔐 DID 身份认证

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DID_DOCUMENT_PATH` | DID 文档路径 | - |
| `DID_PRIVATE_KEY_PATH` | DID 私钥路径 | - |
| `DID_DOMAIN` | DID 域名 | didhost.cc |
| `DID_PATH` | DID 路径 | test:public |

## ✅ 验证配置

### 快速验证

```bash
# 检查配置加载
uv run python -m octopus.octopus --help

# 验证配置并显示启动信息
uv run python -c "
from octopus.config.settings import get_settings
settings = get_settings()
print('✅ 配置验证成功')
print(f'🌐 服务器: {settings.host}:{settings.port}')
print(f'🤖 AI模型: {settings.openai_model}')
print(f'📡 ANP状态: {'启用' if settings.anp_sdk_enabled else '禁用'}')
"

# 测试启动（Ctrl+C 退出）
uv run python -m octopus.octopus --debug
```

### CLI 参数测试

```bash
# 测试端口覆盖
uv run python -m octopus.octopus --port 8080 --debug --log-level DEBUG

# 测试 ANP 配置
uv run python -m octopus.octopus --anp-gateway wss://anpproxy.com/ws --no-anp

# 测试配置文件
echo "PORT=7777" > test.env
uv run python -m octopus.octopus --config test.env
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
