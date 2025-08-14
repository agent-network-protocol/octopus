# Octopus 项目结构说明

## 📁 项目目录结构

```
octopus/
├── README.md                   # 项目说明文档
├── pyproject.toml             # 项目配置和依赖管理
├── uv.lock                    # 锁定的依赖版本
├── .env.example               # 环境变量模板
├── .gitignore                 # Git 忽略文件
├── .gitmodules                # Git 子模块配置
├── LICENSE                    # 开源许可证
│
├── octopus/                   # 🏗️ 主要源码目录
│   ├── __init__.py            # 包初始化文件
│   ├── main.py                # FastAPI 应用入口点
│   │
│   ├── config/                # ⚙️ 配置管理
│   │   ├── __init__.py
│   │   └── settings.py        # 应用配置设置
│   │
│   ├── api/                   # 🌐 API 路由层
│   │   ├── __init__.py
│   │   └── v1/                # API 版本管理
│   │       ├── __init__.py
│   │       └── endpoints/     # API 端点实现
│   │           └── __init__.py
│   │
│   ├── core/                  # 🔧 核心业务逻辑
│   │   └── __init__.py
│   │
│   ├── agents/                # 🤖 代理系统
│   │   ├── __init__.py
│   │   ├── base_agent.py      # 基础代理类
│   │   ├── agent_manager.py   # 代理管理器
│   │   ├── sub_agents/        # 子代理实现
│   │   │   └── __init__.py
│   │   └── protocols/         # 代理协议
│   │       └── __init__.py
│   │
│   ├── models/                # 📊 数据模型
│   │   └── __init__.py
│   │
│   ├── services/              # 🔧 业务服务层
│   │   └── __init__.py
│   │
│   └── utils/                 # 🛠️ 工具类
│       ├── __init__.py
│       └── log_base.py        # 日志工具
│
├── tests/                     # 🧪 测试代码
│   ├── __init__.py
│   ├── unit/                  # 单元测试
│   │   └── __init__.py
│   ├── integration/           # 集成测试
│   │   └── __init__.py
│   └── fixtures/              # 测试数据
│       └── __init__.py
│
├── scripts/                   # 📜 脚本文件
│   ├── dev.py                 # 开发服务器启动脚本
│   └── hello.py               # 示例应用
│
├── docs/                      # 📚 文档
│   └── project_structure.md   # 项目结构说明
│
├── external/                  # 🔗 外部依赖
│   └── anp-open-sdk/          # ANP SDK 子模块
│
└── logs/                      # 📝 本地日志目录
    └── .gitkeep
```

## 🎯 设计理念

### 1. **模块化设计**
- 每个功能模块独立目录
- 清晰的职责分离
- 便于团队协作开发

### 2. **可扩展性**
- API 版本化管理 (`api/v1/`)
- 插件化代理系统 (`agents/sub_agents/`)
- 灵活的配置管理

### 3. **开发友好**
- 完整的测试框架
- 开发脚本集中管理
- 详细的日志系统

### 4. **生产就绪**
- 配置与代码分离
- 标准化的项目结构
- 容器化部署支持

## 🚀 如何使用

### 开发环境启动
```bash
# 开发模式（支持热重载）
cd scripts
uv run python dev.py

# 或者直接运行主应用
uv run python -m octopus.main
```

### 添加新的代理
1. 在 `octopus/agents/sub_agents/` 创建新的代理文件
2. 继承 `BaseAgent` 类
3. 在 `AgentManager` 中注册新代理

### 添加新的 API 端点
1. 在 `octopus/api/v1/endpoints/` 创建新的路由文件
2. 在 `octopus/api/v1/router.py` 中注册路由

### 运行测试
```bash
# 运行所有测试
uv run pytest tests/

# 运行特定测试
uv run pytest tests/unit/
uv run pytest tests/integration/
```

## 🔧 配置管理

配置文件位于 `octopus/config/settings.py`，支持：
- 环境变量配置
- `.env` 文件加载
- 类型安全的配置项

## 📝 日志系统

- 控制台彩色输出
- 文件日志记录
- 可配置的日志级别
- 包含文件名和行号信息

## 🤖 代理系统

- `BaseAgent`: 所有代理的基类
- `AgentManager`: 代理生命周期管理
- `sub_agents/`: 具体代理实现
- `protocols/`: 通信协议实现

这个结构为 Octopus 项目提供了一个坚实的基础，支持快速开发和长期维护。
