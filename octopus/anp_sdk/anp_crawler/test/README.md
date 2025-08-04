# ANP Crawler 测试

此目录包含了 ANP Crawler 模块的完整测试套件。

## 文件说明

- `test_anp_crawler.py` - 主要测试文件，包含所有测试用例
- `run_tests.py` - 测试运行脚本
- `test_data_agent_description.json` - Agent Description 测试数据
- `test_data_openrpc.json` - OpenRPC 接口测试数据

## 测试覆盖范围

### ANPCrawler 类测试
- ✅ 初始化和组件配置
- ✅ `fetch_text()` - 文本内容获取
- ✅ Agent Description 文档解析
- ✅ OpenRPC 文档解析和 $ref 引用解析
- ✅ 错误处理机制
- ✅ `fetch_image()`, `fetch_video()`, `fetch_audio()` - 多媒体接口（pass 实现）
- ✅ `fetch_auto()` - 自动检测接口（pass 实现）
- ✅ 缓存功能测试
- ✅ 会话管理（访问历史、URL 参数清理）

### ANPDocumentParser 类测试
- ✅ Agent Description 文档解析
- ✅ OpenRPC 文档解析
- ✅ 无效 JSON 处理

### ANPInterface 类测试
- ✅ OpenRPC 方法转换为 OpenAI Tools 格式
- ✅ $ref 引用解析
- ✅ 函数名称规范化
- ✅ 不支持接口类型处理

## 运行测试

### 方法1：使用测试运行脚本
```bash
cd octopus/anp_sdk/anp_crawler/test
python run_tests.py
```

### 方法2：直接运行测试文件
```bash
cd octopus/anp_sdk/anp_crawler/test
python test_anp_crawler.py
```

### 方法3：使用 unittest 模块
```bash
cd octopus/anp_sdk/anp_crawler/test
python -m unittest test_anp_crawler -v
```

## 测试数据

### Agent Description 测试数据
`test_data_agent_description.json` 包含一个完整的 Grand Hotel Assistant 智能体描述文档，包括：
- 智能体基本信息
- 产品和信息资源
- 多种协议的接口定义
- DID 认证信息

### OpenRPC 测试数据
`test_data_openrpc.json` 包含 Grand Hotel Services API 的 OpenRPC 规范，包括：
- 房间搜索接口 (`searchRooms`)
- 预订创建接口 (`makeReservation`)
- 完整的 components/schemas 定义
- $ref 引用示例

## 依赖要求

测试需要以下模块正常工作：
- `octopus.utils.log_base` - 日志系统
- `agent_connect.authentication` - DID 认证（测试中会被 mock）
- `aiohttp` - HTTP 客户端
- `unittest.mock` - 测试 mock 功能

## 测试结果

成功运行测试后，你将看到：
- 每个测试用例的执行状态
- 测试覆盖的功能点
- 最终的成功率统计

例如：
```
Tests run: 19
Failures: 0
Errors: 0
Success rate: 100.0%
✅ All tests passed!
```

## 注意事项

1. 测试使用 mock 来模拟 DID 认证和 HTTP 请求，无需真实的网络连接
2. 多媒体接口（`fetch_image`, `fetch_video`, `fetch_audio`, `fetch_auto`）目前是 pass 实现，测试验证它们返回 None
3. 所有测试都是异步的，使用 `unittest.IsolatedAsyncioTestCase` 基类