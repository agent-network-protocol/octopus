# Octopus 多智能体架构说明

## 系统概述

Octopus 是一个面向连接的多智能体架构系统，旨在通过模块化的智能体设计，提供高效、可扩展的任务处理能力。系统采用主从架构模式，通过智能体路由器实现动态任务分发和协作。

## 架构设计

### 核心组件

1. **主智能体 (Master Agent)**
   - 文件：`master_agent.py`
   - 职责：任务接收、任务分析、子智能体调度、结果整合
   - 作为系统的核心调度器，负责整个任务流程的管控

2. **子智能体 (Sub Agents)**
   - 位置：`agents/` 目录下的各个专业智能体
   - 职责：专业领域任务处理，如数据分析、文本处理、图像处理等
   - 继承自 `BaseAgent` 基类，实现标准化接口

3. **智能体基类 (BaseAgent)**
   - 文件：`base_agent.py`
   - 功能：定义所有子智能体的通用接口和行为规范
   - 提供标准化的生命周期管理和通信协议

4. **智能体路由器 (Agents Router)**
   - 文件：`agents_router.py`
   - 功能：智能体注册管理、任务路由分发、能力匹配
   - 维护智能体注册表，提供智能体发现和调用服务

## 工作流程

### 1. 智能体自动注册机制

Octopus 采用**装饰符 + 反射机制**实现智能体的自动注册，确保开发体验的简洁性和功能的完整性。

#### 1.1 类级别注册
```python
# 使用装饰符注册智能体基本信息
@register_agent(
    name="data_analyzer",
    description="数据分析专家智能体",
    version="1.0.0"
)
class DataAnalyzerAgent(BaseAgent):
    """数据分析专家智能体，支持多种数据处理任务"""
    
    @agent_method(
        description="处理CSV格式数据",
        parameters={"file_path": "string", "options": "dict"},
        returns="dict"
    )
    def process_csv_data(self, file_path: str, options: dict = None):
        """Process CSV data with various options"""
        # 数据处理逻辑
        return {"status": "success", "data": processed_data}
    
    @agent_method(
        description="生成数据统计报告",
        parameters={"data": "dict"},
        returns="dict"
    )
    def generate_statistics(self, data: dict):
        """Generate statistical analysis report"""
        # 统计分析逻辑
        return {"report": statistical_report}
```

#### 1.2 自动发现机制
注册过程中，路由器会通过**反射机制**自动发现：
- 所有被 `@agent_method` 装饰的方法
- 方法的参数签名和类型提示
- 方法的文档字符串（docstring）
- 方法的返回值类型

**自动发现代码示例**：
```python
import inspect
from typing import get_type_hints

class AgentDiscovery:
    @staticmethod
    def discover_agent_methods(agent_class) -> Dict:
        """自动发现智能体的所有方法"""
        discovered_methods = {}
        
        # 1. 扫描类中的所有方法
        for method_name, method_obj in inspect.getmembers(agent_class, predicate=inspect.ismethod):
            # 2. 检查是否有 @agent_method 装饰符
            if hasattr(method_obj, '_agent_method_meta'):
                print(f"🔍 发现装饰方法: {method_name}")
                
                # 3. 获取方法签名
                signature = inspect.signature(method_obj)
                print(f"📝 方法签名: {signature}")
                
                # 4. 解析参数信息
                parameters = {}
                for param_name, param in signature.parameters.items():
                    if param_name != 'self':
                        param_info = {
                            "type": str(param.annotation),
                            "required": param.default == inspect.Parameter.empty,
                            "default": param.default if param.default != inspect.Parameter.empty else None
                        }
                        parameters[param_name] = param_info
                        print(f"  📋 参数 {param_name}: {param_info}")
                
                # 5. 获取返回值类型
                return_type = str(signature.return_annotation)
                print(f"📤 返回类型: {return_type}")
                
                # 6. 获取文档字符串
                docstring = inspect.getdoc(method_obj)
                print(f"📚 文档字符串: {docstring}")
                
                # 7. 合并所有信息
                discovered_methods[method_name] = {
                    "description": method_obj._agent_method_meta.get("description", ""),
                    "parameters": parameters,
                    "returns": return_type,
                    "docstring": docstring,
                    "signature": str(signature)
                }
        
        return discovered_methods

# 使用示例
@register_agent(name="example_agent", description="示例智能体")
class ExampleAgent(BaseAgent):
    
    @agent_method(description="处理文本数据")
    def process_text(self, text: str, options: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Process text data with various options
        
        Args:
            text: Input text to process
            options: Processing options
            
        Returns:
            Dict containing processed results
        """
        return {"processed_text": text.upper()}

# 自动发现过程演示
print("🚀 开始自动发现过程...")
discovered = AgentDiscovery.discover_agent_methods(ExampleAgent)

# 输出结果：
# 🔍 发现装饰方法: process_text
# 📝 方法签名: (text: str, options: Dict[str, Any] = None) -> Dict[str, str]
#   📋 参数 text: {'type': '<class 'str'>', 'required': True, 'default': None}
#   📋 参数 options: {'type': 'Dict[str, Any]', 'required': False, 'default': None}
# 📤 返回类型: Dict[str, str]
# 📚 文档字符串: Process text data with various options...
```

**直接从函数提取参数（无需装饰符）**：
```python
import inspect
from typing import get_type_hints, Union, Optional, Dict, List, Any

class AutoParameterExtractor:
    """无需装饰符的参数自动提取器"""
    
    @staticmethod
    def extract_function_schema(func) -> Dict:
        """直接从函数定义中提取完整的schema信息"""
        # 1. 获取函数基本信息
        func_name = func.__name__
        func_doc = inspect.getdoc(func) or ""
        
        # 2. 获取函数签名和类型提示
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        print(f"🔍 正在分析函数: {func_name}")
        print(f"📚 函数文档: {func_doc}")
        
        # 3. 解析参数
        properties = {}
        required = []
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':  # 跳过self参数
                continue
                
            # 获取类型提示
            param_type = type_hints.get(param_name, param.annotation)
            
            # 解析参数类型
            json_type = AutoParameterExtractor._python_type_to_json_type(param_type)
            
            # 构建参数信息
            param_info = {
                "type": json_type["type"],
                "description": f"Parameter {param_name}"  # 可以从docstring解析获得更详细描述
            }
            
            # 添加额外的类型信息
            if "items" in json_type:
                param_info["items"] = json_type["items"]
            
            properties[param_name] = param_info
            
            # 判断是否为必需参数
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                param_info["default"] = param.default
            
            print(f"  📋 参数 {param_name}: {param_info}")
        
        # 4. 构建OpenAI Function Calling格式
        return {
            "type": "function",
            "function": {
                "name": func_name,
                "description": func_doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        }
    
    @staticmethod
    def _python_type_to_json_type(python_type) -> Dict[str, Any]:
        """将Python类型转换为JSON Schema类型"""
        # 处理基础类型
        if python_type == str:
            return {"type": "string"}
        elif python_type == int:
            return {"type": "integer"}
        elif python_type == float:
            return {"type": "number"}
        elif python_type == bool:
            return {"type": "boolean"}
        elif python_type == dict or python_type == Dict:
            return {"type": "object"}
        elif python_type == list or python_type == List:
            return {"type": "array"}
        
        # 处理泛型类型
        if hasattr(python_type, '__origin__'):
            origin = python_type.__origin__
            args = python_type.__args__
            
            if origin is list or origin is List:
                if args:
                    item_type = AutoParameterExtractor._python_type_to_json_type(args[0])
                    return {"type": "array", "items": item_type}
                return {"type": "array"}
            
            elif origin is dict or origin is Dict:
                return {"type": "object"}
            
            elif origin is Union:
                # 处理Optional类型 (Union[T, None])
                if len(args) == 2 and type(None) in args:
                    non_none_type = args[0] if args[1] is type(None) else args[1]
                    return AutoParameterExtractor._python_type_to_json_type(non_none_type)
                # 处理其他Union类型，默认返回第一个类型
                return AutoParameterExtractor._python_type_to_json_type(args[0])
        
        # 未知类型默认为string
        return {"type": "string"}

# 直接提取示例
def process_user_data(
    users: List[Dict[str, str]], 
    filter_active: bool = True,
    batch_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process user data with filtering and batching options
    
    Args:
        users: List of user dictionaries
        filter_active: Whether to filter only active users
        batch_size: Size of processing batches
        
    Returns:
        Processed user data results
    """
    return {"processed": len(users), "filtered": filter_active}

# 自动提取函数schema
print("🚀 无装饰符的参数提取演示:")
schema = AutoParameterExtractor.extract_function_schema(process_user_data)
print("\n📋 提取的Schema:")
import json
print(json.dumps(schema, indent=2, ensure_ascii=False))

# 输出结果：
# 🔍 正在分析函数: process_user_data
# 📚 函数文档: Process user data with filtering and batching options...
#   📋 参数 users: {'type': 'array', 'items': {'type': 'object'}, 'description': 'Parameter users'}
#   📋 参数 filter_active: {'type': 'boolean', 'description': 'Parameter filter_active', 'default': True}
#   📋 参数 batch_size: {'type': 'integer', 'description': 'Parameter batch_size', 'default': None}
```

**增强版：从docstring自动提取参数描述**：
```python
import re
from typing import Dict, Optional

class EnhancedParameterExtractor(AutoParameterExtractor):
    """增强版参数提取器，支持从docstring解析参数描述"""
    
    @staticmethod
    def parse_docstring_params(docstring: str) -> Dict[str, str]:
        """从docstring中解析参数描述"""
        param_descriptions = {}
        
        if not docstring:
            return param_descriptions
        
        # 匹配Google风格的docstring参数
        # Args:
        #     param_name: description
        #     another_param: another description
        args_pattern = r'Args:\s*\n((?:\s+\w+[^:]*:.*\n?)*)'
        args_match = re.search(args_pattern, docstring, re.MULTILINE)
        
        if args_match:
            args_section = args_match.group(1)
            # 提取每个参数和描述
            param_pattern = r'\s+(\w+)[^:]*:\s*(.+?)(?=\n\s+\w+|\n\s*$|\Z)'
            param_matches = re.findall(param_pattern, args_section, re.MULTILINE | re.DOTALL)
            
            for param_name, description in param_matches:
                param_descriptions[param_name] = description.strip()
        
        return param_descriptions
    
    @staticmethod
    def extract_function_schema(func) -> Dict:
        """增强版函数schema提取，包含详细的参数描述"""
        # 1. 获取函数基本信息
        func_name = func.__name__
        func_doc = inspect.getdoc(func) or ""
        
        # 2. 解析docstring中的参数描述
        param_descriptions = EnhancedParameterExtractor.parse_docstring_params(func_doc)
        
        # 3. 获取函数签名和类型提示
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        print(f"🔍 正在分析函数: {func_name}")
        print(f"📚 解析到的参数描述: {param_descriptions}")
        
        # 4. 解析参数
        properties = {}
        required = []
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
                
            param_type = type_hints.get(param_name, param.annotation)
            json_type = AutoParameterExtractor._python_type_to_json_type(param_type)
            
            # 使用docstring中的描述，或者生成默认描述
            param_desc = param_descriptions.get(param_name, f"Parameter {param_name}")
            
            param_info = {
                "type": json_type["type"],
                "description": param_desc
            }
            
            if "items" in json_type:
                param_info["items"] = json_type["items"]
            
            properties[param_name] = param_info
            
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                param_info["default"] = param.default
        
        # 5. 提取函数描述（第一行或者整体描述）
        func_description = func_doc.split('\n')[0] if func_doc else f"Function {func_name}"
        
        return {
            "type": "function",
            "function": {
                "name": func_name,
                "description": func_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        }

# 测试增强版提取器
enhanced_schema = EnhancedParameterExtractor.extract_function_schema(process_user_data)
print("\n🎯 增强版Schema（包含详细描述）:")
print(json.dumps(enhanced_schema, indent=2, ensure_ascii=False))

# 输出结果：
# {
#   "type": "function",
#   "function": {
#     "name": "process_user_data",
#     "description": "Process user data with filtering and batching options",
#     "parameters": {
#       "type": "object",
#       "properties": {
#         "users": {
#           "type": "array",
#           "items": {"type": "object"},
#           "description": "List of user dictionaries"
#         },
#         "filter_active": {
#           "type": "boolean",
#           "description": "Whether to filter only active users",
#           "default": true
#         },
#         "batch_size": {
#           "type": "integer",
#           "description": "Size of processing batches",
#           "default": null
#         }
#       },
#       "required": ["users"],
#       "additionalProperties": false
#     }
#   }
# }



## 技术特性

### 装饰符 + 反射机制
Octopus 的核心创新在于采用了**装饰符 + 反射机制**实现智能体的自动注册和方法发现：

#### 自动注册机制
- **类级别装饰符**：`@register_agent` 自动将智能体类注册到路由器
- **方法级别装饰符**：`@agent_method` 自动发现和注册智能体方法
- **反射解析**：自动解析方法签名、类型提示和文档字符串
- **元数据提取**：自动提取参数类型、默认值、返回值类型等信息

#### 类型安全保障
```python
# 支持复杂类型提示
@agent_method(description="处理用户数据")
def process_user_data(
    self, 
    users: List[Dict[str, Union[str, int]]], 
    filter_options: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict], Dict[str, int]]:
    """处理用户数据并返回结果和统计信息"""
    # 系统会自动解析这些复杂类型
    pass
```

### 面向连接的架构
- **动态连接**：智能体之间可以动态建立连接关系
- **协作执行**：多个智能体可以协同完成复杂任务
- **松耦合设计**：智能体之间通过标准接口通信，降低耦合度
- **智能路由**：根据任务需求和方法签名自动选择最佳智能体

### 插件化扩展
- **热插拔**：新的智能体可以动态注册到系统中
- **能力发现**：自动发现和注册智能体的能力
- **版本管理**：支持智能体的版本控制和升级
- **依赖管理**：自动处理智能体间的依赖关系

## 开发指南

### 创建新的子智能体

#### 1. 基本结构
```python
from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_method
from typing import Dict, List, Optional

@register_agent(
    name="text_processor",
    description="文本处理专家智能体",
    version="1.0.0"
)
class TextProcessorAgent(BaseAgent):
    """文本处理专家智能体，提供多种文本分析和处理功能"""
    
    def __init__(self):
        super().__init__()
        # 初始化特定资源
        self.nlp_model = None
        self.logger.info("Text processor agent initialized")
```

#### 2. 方法定义与注册
```python
@agent_method(
    description="分析文本情感倾向",
    parameters={
        "text": "string",
        "language": "string",
        "detailed": "boolean"
    },
    returns="dict"
)
def analyze_sentiment(self, text: str, language: str = "zh", detailed: bool = False) -> Dict:
    """
    Analyze sentiment of the given text
    
    Args:
        text: Text to analyze
        language: Language code (zh, en, etc.)
        detailed: Whether to return detailed analysis
        
    Returns:
        Dictionary containing sentiment analysis results
    """
    # 情感分析逻辑
    result = {
        "sentiment": "positive",
        "confidence": 0.85,
        "language": language
    }
    
    if detailed:
        result["details"] = {
            "positive_score": 0.85,
            "negative_score": 0.15,
            "neutral_score": 0.0
        }
    
    return result

@agent_method(
    description="提取文本关键词",
    parameters={
        "text": "string",
        "max_keywords": "integer"
    },
    returns="list"
)
def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text
    
    Args:
        text: Source text
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of extracted keywords
    """
    # 关键词提取逻辑
    keywords = ["keyword1", "keyword2", "keyword3"]
    return keywords[:max_keywords]
```

#### 3. 装饰符参数说明

**@register_agent 参数**：
- `name`: 智能体唯一标识符
- `description`: 智能体功能描述
- `version`: 版本号
- `tags`: 可选，智能体标签列表
- `dependencies`: 可选，依赖的其他智能体或服务

**@agent_method 参数**：
- `description`: 方法功能描述
- `parameters`: 参数定义字典
- `returns`: 返回值类型
- `examples`: 可选，使用示例
- `deprecated`: 可选，是否已废弃

#### 4. 类型提示支持
系统支持 Python 类型提示，会自动解析：
```python
@agent_method(description="处理复杂数据结构")
def process_complex_data(
    self, 
    data: Dict[str, List[int]], 
    options: Optional[Dict] = None
) -> Dict[str, Any]:
    """处理复杂的数据结构"""
    return {"processed": True, "count": len(data)}
```

### 最佳实践

#### 1. 装饰符使用规范
```python
# ✅ 推荐：详细的装饰符配置
@register_agent(
    name="image_processor",
    description="图像处理专家智能体",
    version="2.1.0",
    tags=["image", "cv", "processing"],
    dependencies=["opencv", "pillow"]
)
class ImageProcessorAgent(BaseAgent):
    
    @agent_method(
        description="调整图像尺寸",
        parameters={
            "image_path": "string",
            "width": "integer", 
            "height": "integer",
            "keep_aspect_ratio": "boolean"
        },
        returns="dict",
        examples=[
            {
                "input": {"image_path": "/path/to/image.jpg", "width": 800, "height": 600},
                "output": {"status": "success", "new_path": "/path/to/resized.jpg"}
            }
        ]
    )
    def resize_image(self, image_path: str, width: int, height: int, keep_aspect_ratio: bool = True) -> Dict:
        """Resize image with specified dimensions"""
        pass
```

#### 2. 类型提示规范
```python
# ✅ 推荐：使用具体的类型提示
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass

@dataclass
class ProcessResult:
    status: str
    data: Dict
    metadata: Optional[Dict] = None

@agent_method(description="处理复杂数据结构")
def process_complex_data(
    self, 
    input_data: List[Dict[str, Union[str, int, float]]], 
    options: Optional[Dict[str, Any]] = None
) -> ProcessResult:
    """使用具体的类型提示提高代码可读性和类型安全"""
    pass
```

#### 3. 错误处理与日志
```python
# ✅ 推荐：标准化的错误处理
@agent_method(description="容错处理示例")
def reliable_method(self, data: Dict) -> Dict:
    """展示标准化的错误处理模式"""
    try:
        # 参数验证
        if not data:
            raise ValueError("Input data cannot be empty")
        
        # 业务逻辑
        result = self._process_business_logic(data)
        
        # 成功日志
        self.logger.info(f"Successfully processed {len(data)} items")
        return {"status": "success", "result": result}
        
    except ValueError as e:
        self.logger.warning(f"Validation error: {str(e)}")
        return {"status": "error", "error_type": "validation", "message": str(e)}
    except Exception as e:
        self.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "error_type": "system", "message": "Internal error occurred"}
```

#### 4. 性能优化建议
```python
# ✅ 推荐：资源管理和性能优化
class OptimizedAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self._cache = {}
        self._initialized = False
    
    def _lazy_init(self):
        """延迟初始化重型资源"""
        if not self._initialized:
            self._heavy_resource = self._load_heavy_resource()
            self._initialized = True
    
    @agent_method(description="高性能处理方法")
    def high_performance_method(self, data: List[Dict]) -> Dict:
        """使用缓存和延迟初始化优化性能"""
        self._lazy_init()
        
        # 使用缓存
        cache_key = self._generate_cache_key(data)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 处理逻辑
        result = self._process_data(data)
        self._cache[cache_key] = result
        return result
```

#### 5. 文档与注释规范
```python
# ✅ 推荐：完整的文档字符串
@agent_method(
    description="文本相似度计算",
    parameters={
        "text1": "string",
        "text2": "string", 
        "algorithm": "string"
    },
    returns="float"
)
def calculate_similarity(self, text1: str, text2: str, algorithm: str = "cosine") -> float:
    """
    Calculate similarity between two texts using specified algorithm.
    
    This method supports multiple similarity algorithms and provides
    normalized similarity scores between 0 and 1.
    
    Args:
        text1: First text for comparison
        text2: Second text for comparison  
        algorithm: Similarity algorithm ('cosine', 'jaccard', 'levenshtein')
        
    Returns:
        float: Similarity score between 0.0 and 1.0
        
    Raises:
        ValueError: If algorithm is not supported
        
    Examples:
        >>> agent.calculate_similarity("hello world", "hello there")
        0.816
        >>> agent.calculate_similarity("cat", "dog", algorithm="jaccard")
        0.0
    """
    pass
```

#### 6. 核心原则总结
1. **明确职责**：每个智能体专注于特定领域
2. **装饰符完整**：充分利用装饰符提供的元数据功能
3. **类型安全**：使用具体的类型提示和数据类
4. **错误处理**：实现标准化的错误处理模式
5. **性能意识**：考虑缓存、延迟初始化等优化策略
6. **文档完善**：提供详细的文档字符串和使用示例
7. **可测试性**：方法设计便于单元测试
8. **日志规范**：使用结构化日志记录关键信息

## 技术实现原理

### 装饰符工作机制
```python
# 装饰符的内部实现原理
def register_agent(name: str, description: str, **kwargs):
    """智能体注册装饰符"""
    def decorator(cls):
        # 1. 提取类的元数据
        agent_metadata = {
            "name": name,
            "description": description,
            "class_reference": cls,
            "module": cls.__module__,
            "methods": {}
        }
        
        # 2. 通过反射扫描类的方法
        for method_name, method_obj in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(method_obj, '_agent_method_meta'):
                # 3. 提取方法的元数据
                method_meta = method_obj._agent_method_meta
                
                # 4. 解析方法签名
                signature = inspect.signature(method_obj)
                parameters = {}
                
                for param_name, param in signature.parameters.items():
                    if param_name != 'self':
                        parameters[param_name] = {
                            "type": str(param.annotation),
                            "required": param.default == inspect.Parameter.empty,
                            "default": param.default if param.default != inspect.Parameter.empty else None
                        }
                
                agent_metadata["methods"][method_name] = {
                    "description": method_meta.get("description", ""),
                    "parameters": parameters,
                    "returns": str(signature.return_annotation),
                    "docstring": method_obj.__doc__
                }
        
        # 5. 注册到全局路由器
        AgentRouter.register(agent_metadata)
        
        return cls
    return decorator
```

### 反射机制详解
```python
# 方法装饰符的实现
def agent_method(description: str = "", **kwargs):
    """方法注册装饰符"""
    def decorator(func):
        # 将元数据附加到方法对象
        func._agent_method_meta = {
            "description": description,
            "parameters": kwargs.get("parameters", {}),
            "returns": kwargs.get("returns", "any"),
            "examples": kwargs.get("examples", [])
        }
        return func
    return decorator

# 类型提示解析器
class TypeHintParser:
    @staticmethod
    def parse_type_hint(type_hint) -> Dict:
        """解析复杂的类型提示"""
        if hasattr(type_hint, '__origin__'):
            # 处理泛型类型，如 List[str], Dict[str, int]
            origin = type_hint.__origin__
            args = type_hint.__args__
            
            if origin is list:
                return {"type": "list", "item_type": str(args[0])}
            elif origin is dict:
                return {"type": "dict", "key_type": str(args[0]), "value_type": str(args[1])}
            elif origin is Union:
                return {"type": "union", "types": [str(arg) for arg in args]}
        
        return {"type": str(type_hint)}
```





