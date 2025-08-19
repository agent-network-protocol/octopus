# Azure OpenAI 配置指南

## 问题诊断

目前遇到的 404 错误是由于 Azure OpenAI 的 URL 配置不正确导致的。

## Azure OpenAI URL 格式

Azure OpenAI 的正确 URL 格式有两种：

### 方法 1: 标准 Azure OpenAI URL
```bash
# 基础 URL (推荐)
OPENAI_BASE_URL=https://{your-resource-name}.openai.azure.com/

# 完整示例
OPENAI_BASE_URL=https://tekan.openai.azure.com/
OPENAI_MODEL=gpt-4o  # 这应该是你的 deployment name
```

### 方法 2: 包含完整路径的 URL
```bash
# 包含 API 版本的完整 URL
OPENAI_BASE_URL=https://tekan.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15-preview

# 或者使用最新的 API 版本
OPENAI_BASE_URL=https://tekan.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-06-01
```

## 推荐配置

建议使用方法 1，因为 OpenAI Python SDK 会自动构建正确的 URL。

### .env 文件示例：
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_BASE_URL=https://tekan.openai.azure.com/
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

## 验证步骤

1. 确认你的 Azure OpenAI 资源名称是 `tekan`
2. 确认你的部署名称是 `gpt-4o`（可能需要替换为实际的部署名称）
3. 确认 API key 是有效的

## 常见问题

### Q: 如何查看我的 Azure OpenAI 配置？
A: 登录 Azure Portal > 找到你的 OpenAI 资源 > 查看 "Keys and Endpoint" 页面

### Q: 部署名称在哪里查看？
A: Azure Portal > OpenAI 资源 > Model deployments > 查看部署列表

### Q: 如果仍然是 404 错误怎么办？
A:
1. 检查资源名称是否正确
2. 检查部署名称是否正确
3. 确保 API key 有效
4. 尝试在 Azure Portal 中测试模型

## 测试配置

修改 .env 文件后，运行以下命令测试：
```bash
uv run python -m test_scripts.simple_openai_test
```
