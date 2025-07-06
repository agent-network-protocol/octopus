# Test Scripts

这个目录包含了 Octopus 多智能体系统的测试脚本。

## 测试脚本说明

### 1. example_usage.py
- **功能**: 演示 MasterAgent 自然语言接口的使用
- **运行**: `uv run python -m test_scripts.example_usage`
- **描述**: 测试中文自然语言请求的处理，包括情感分析、词频统计、关键词提取等

### 2. debug_agents.py
- **功能**: 调试智能体注册和路由器状态
- **运行**: `uv run python -m test_scripts.debug_agents`
- **描述**: 检查智能体注册、方法发现、路由器状态等

### 3. test_openai_response.py
- **功能**: 测试 OpenAI 响应格式和智能体选择
- **运行**: `uv run python -m test_scripts.test_openai_response`
- **描述**: 测试 OpenAI 模型的响应格式和智能体选择逻辑

### 4. simple_openai_test.py
- **功能**: 基础 OpenAI 连接测试
- **运行**: `uv run python -m test_scripts.simple_openai_test`
- **描述**: 测试 OpenAI API 连接是否正常，验证配置是否正确

## 使用方法

1. 确保已安装依赖：
   ```bash
   uv sync
   ```

2. 配置环境变量：
   ```bash
   cp .env_template .env
   # 编辑 .env 文件，设置正确的 OpenAI API key 和配置
   ```

3. 运行测试脚本：
   ```bash
   uv run python -m test_scripts.<script_name>
   ```

## 注意事项

- 所有测试脚本需要有效的 OpenAI API 配置才能正常工作
- 测试脚本会创建智能体实例，确保系统资源足够
- 日志会输出到 `~/Library/Logs/octopus/octopus.log`

## OpenAI 配置问题排查

如果遇到 404 错误，请检查：

1. **Azure OpenAI URL 格式**：
   ```bash
   # 正确格式 (推荐)
   OPENAI_BASE_URL=https://tekan.openai.azure.com/
   
   # 错误格式
   OPENAI_BASE_URL=https://tekan.openai.azure.com/openai/deployments/gpt4o
   ```

2. **验证配置**：
   - 确认 Azure OpenAI 资源名称正确
   - 确认部署名称正确 (OPENAI_MODEL)
   - 确认 API key 有效

3. **详细配置指南**：
   请参考 `docs/azure_openai_config.md` 获取完整配置说明。 