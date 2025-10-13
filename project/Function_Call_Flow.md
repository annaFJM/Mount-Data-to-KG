# Function Call 工作流程详解

## 📋 什么是 Function Call

Function Calling 是大模型的一种能力，允许模型调用外部工具（函数），将自然语言理解与结构化操作结合。

### 核心优势

1. **结构化输出**：返回 JSON 格式，不是自由文本
2. **自动验证**：通过 `enum` 限制选项，避免错误输出
3. **推理透明**：包含 `reasoning` 字段，记录决策过程
4. **无需重试**：模型输出自动符合要求

---

## 🔄 系统中的 Function Call 流程

### 整体架构

```
main.py (主流程)
    ↓
classifier.py (分类逻辑)
    ↓
function_call_handler.py (Function Call 封装)
    ↓
DeepSeek API (模型推理)
    ↓
返回结构化结果
```

---

## 🎯 两种 Function Call

### 1. 层级分类 - `classify_to_subtype`

**用途**：在知识图谱中逐层分类材料

**函数定义**：

```python
{
  "type": "function",
  "function": {
    "name": "classify_to_subtype",
    "description": "将材料分类到某个子类型",
    "parameters": {
      "type": "object",
      "properties": {
        "subtype": {
          "type": "string",
          "enum": ["金属材料", "非金属材料", "复合材料", ...],  # 从 Neo4j 动态获取
          "description": "选择一个子类型"
        },
        "reasoning": {
          "type": "string",
          "description": "分类理由（根据材料成分、性质等判断）"
        }
      },
      "required": ["subtype", "reasoning"]
    }
  }
}
```

**工作流程**：

```
1. 从 Neo4j 获取当前节点的子节点列表
   例如："材料" → ["金属材料", "非金属材料", "复合材料", ...]

2. 动态构建 Function 定义
   将子节点名称放入 enum 列表

3. 构建 System Prompt
   包含：父节点名称、子节点列表、每个子节点的例子

4. 调用 DeepSeek API
   发送：材料数据 + Function 定义 + System Prompt

5. 解析返回结果
   提取：subtype（分类结果）、reasoning（分类理由）

6. 验证并获取 element_id
   从 Neo4j 获取选中节点的 element_id

7. 更新当前节点
   current_name = subtype
   current_element_id = element_id
```

**示例**：

输入材料：
```json
{
  "成分比重": {"Mn": 1.0, "Fe": 1.0, "Co": 1.0, ...},
  "预测硬度": 609.87,
  "MGE18_标题": "Mn1Fe1Co1Ni1Cu1Nb2"
}
```

API 返回：
```json
{
  "subtype": "金属材料",
  "reasoning": "该材料由多种金属元素组成，具有金属材料的典型特征"
}
```

---

### 2. 实例选择 - `select_instance`

**用途**：在特殊节点下选择具体实例

**函数定义**：

```python
{
  "type": "function",
  "function": {
    "name": "select_instance",
    "description": "从高熵合金的具体实例中选择最匹配的一个",
    "parameters": {
      "type": "object",
      "properties": {
        "instance": {
          "type": "string",
          "enum": ["Ti-13Nb-13Zr", "CoCrFeMnNi", "AlCoCrFeNi", ...],  # 从 Neo4j 动态获取
          "description": "选择最匹配的实例"
        },
        "reasoning": {
          "type": "string",
          "description": "选择理由"
        }
      },
      "required": ["instance", "reasoning"]
    }
  }
}
```

**工作流程**：

```
1. 检测到特殊节点（如"高熵合金"）

2. 从 Neo4j 获取实例列表
   例如：["Ti-13Nb-13Zr", "CoCrFeMnNi", "AlCoCrFeNi", ...]

3. 构建 Function 定义
   将实例名称放入 enum 列表

4. 调用 DeepSeek API
   发送：材料数据 + 实例列表 + Function 定义

5. 解析返回结果
   提取：instance（选中的实例）、reasoning（选择理由）

6. 获取实例的 element_id

7. 挂载到该实例
```

**示例**：

API 返回：
```json
{
  "instance": "Ti-13Nb-13Zr",
  "reasoning": "该材料包含 Ti、Nb 等元素，与 Ti-13Nb-13Zr 的成分特征最匹配"
}
```

---

## 💻 代码实现

### 1. Function Call Handler（封装层）

```python
# function_call_handler.py

class FunctionCallHandler:
    def call_function(self, messages, tools, temperature=0):
        """调用 DeepSeek Function Calling"""
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,              # Function 定义
            tool_choice="auto",       # 自动决定是否调用
            temperature=temperature
        )
        
        # 提取函数调用结果
        tool_call = response.choices[0].message.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        
        return {
            'success': True,
            'function_name': tool_call.function.name,
            'arguments': arguments,      # 包含 subtype 和 reasoning
            'reasoning': arguments.get('reasoning', '')
        }
```

### 2. 动态构建 Function 定义

```python
# classifier.py

def build_classification_tool(parent_name, subtype_info):
    """动态构建分类函数定义"""
    candidates = list(subtype_info.keys())  # 从 Neo4j 获取
    
    return [{
        "type": "function",
        "function": {
            "name": "classify_to_subtype",
            "parameters": {
                "properties": {
                    "subtype": {
                        "enum": candidates,  # 动态候选列表
                    },
                    "reasoning": {"type": "string"}
                }
            }
        }
    }]
```

### 3. 调用流程

```python
# classifier.py

def classify_material_with_function_call(material_data, parent_name, subtype_info, logger):
    # 1. 构建 tools
    tools = build_classification_tool(parent_name, subtype_info)
    
    # 2. 构建 messages
    system_prompt = f"当前任务：判断材料属于'{parent_name}'的哪个子类型..."
    user_prompt = f"材料数据：{json.dumps(material_data)}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 3. 调用 Function Call
    handler = FunctionCallHandler()
    result = handler.call_function(messages, tools)
    
    # 4. 提取结果
    classification = result['arguments']['subtype']
    reasoning = result['arguments']['reasoning']
    
    # 5. 获取 element_id
    element_id = subtype_info[classification]['elementId']
    
    return classification, element_id, reasoning
```

---

## 📊 完整示例

### 输入

**材料数据**：
```json
{
  "成分比重": {"Mn": 1.0, "Fe": 1.0, "Co": 1.0, "Ni": 1.0, "Cu": 1.0, "Nb": 2.0},
  "预测硬度": 609.87,
  "MGE18_标题": "Mn1Fe1Co1Ni1Cu1Nb2"
}
```

**当前节点**：材料

**候选子节点**：["金属材料", "非金属材料", "信息材料", "能源材料", "复合材料"]

### 处理过程

**1. 构建 Function 定义**

```json
{
  "name": "classify_to_subtype",
  "parameters": {
    "subtype": {
      "enum": ["金属材料", "非金属材料", "信息材料", "能源材料", "复合材料"]
    }
  }
}
```

**2. 构建 System Prompt**

```
你是材料知识图谱的智能分类器。

当前任务：判断材料属于"材料"的哪个子类型。

子类型及其例子：
- 金属材料
  例子: 钢, 铝合金, 铜, 钛合金, 镁合金
- 非金属材料
  例子: 陶瓷, 玻璃, 塑料, 橡胶
...
```

**3. API 调用**

```python
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": material_json}
    ],
    tools=tools
)
```

**4. API 返回**

```json
{
  "tool_calls": [{
    "function": {
      "name": "classify_to_subtype",
      "arguments": {
        "subtype": "金属材料",
        "reasoning": "该材料由 Mn、Fe、Co、Ni、Cu、Nb 等金属元素组成，具有金属材料的典型特征"
      }
    }
  }]
}
```

**5. 提取并验证**

```python
classification = "金属材料"  # 自动在 enum 中，无需验证
reasoning = "该材料由...金属元素组成..."
element_id = subtype_info["金属材料"]["elementId"]
```

### 输出

```
✅ 分类成功: 金属材料
   理由: 该材料由 Mn、Fe、Co、Ni、Cu、Nb 等金属元素组成，具有金属材料的典型特征
   Element ID: 4:bf9f3e2f-61c2-430f-be08-580850049dc8:1
```

---

## 🔍 与传统方法对比

### 传统方法（直接解析 content）

```python
# ❌ 问题多
response = client.chat.completions.create(
    messages=[{"role": "user", "content": "这是什么材料类型？"}]
)

classification = response.choices[0].message.content.strip()
# 可能返回: "这是金属材料" / "金属材料类" / "属于金属材料" / ...

# 需要手动验证
if classification not in valid_options:
    # 重试逻辑
    ...
```

### Function Call 方法

```python
# ✅ 优势明显
response = client.chat.completions.create(
    messages=[...],
    tools=[{
        "function": {
            "name": "classify",
            "parameters": {
                "type": {"enum": ["金属材料", "非金属材料"]}  # 强制限制
            }
        }
    }]
)

classification = response.tool_calls[0].function.arguments["type"]
# 保证返回: "金属材料" 或 "非金属材料"
# 无需验证，无需重试
```

## 🛠 调试技巧

### 1. 查看完整的 System Prompt

在 `classifier.py` 中启用：

```python
print("\n========== System Prompt ==========")
print(system_prompt)
print("===================================\n")
```

### 2. 记录 API 返回的原始数据

```python
result = handler.call_function(messages, tools)
print(f"API 返回: {json.dumps(result, indent=2, ensure_ascii=False)}")
```

### 3. 检查日志文件

```bash
# 查看详细的分类过程
cat logs/mount_log_*.log | grep "理由:"
```

---

## 💡 最佳实践

1. **动态构建 enum**：始终从 Neo4j 实时获取候选列表
2. **包含 examples**：在 System Prompt 中提供子类型的例子
3. **记录 reasoning**：便于调试和验证分类逻辑
4. **设置 temperature=0**：确保输出稳定
5. **使用 required 字段**：强制模型提供推理过程

---

## 🔗 相关文件

- `function_call_handler.py` - Function Call 封装
- `classifier.py` - 分类逻辑实现
- `config.py` - Function Call 相关配置
- DeepSeek API 文档: https://api-docs.deepseek.com/

---

**总结**：Function Calling 通过结构化的函数定义和自动验证，显著提高了分类的准确性和可靠性，是本系统的核心技术。