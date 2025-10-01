# 材料知识图谱挂载系统

这是一个基于Neo4j和DeepSeek API的材料知识图谱自动挂载系统，能够将材料数据智能分类并挂载到知识图谱的合适位置。

## 📁 文件结构

```
project/
├── config.py              # 配置文件（数据库连接、API密钥等）
├── data_loader.py         # 数据加载模块
├── neo4j_connector.py     # Neo4j数据库连接器
├── prompt_generator.py    # Prompt生成模块
├── classifier.py          # 分类器（通用+特殊）
├── node_mounter.py        # 节点挂载模块
├── main.py               # 主程序入口
├── README.md             # 本文件
└── data/
    └── high_entropy_alloy.json  # 材料数据文件
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install neo4j openai

# 设置环境变量（DeepSeek API密钥）
export DEEPSEEK_API_KEY="your_api_key_here"
```

### 2. 配置文件

编辑 `config.py`，根据你的环境修改以下配置：

```python
# Neo4j 数据库配置
NEO4J_URI = "neo4j://10.77.50.200:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"

# 数据文件路径
DATA_FILE_PATH = "/path/to/your/high_entropy_alloy.json"

# 根节点配置
ROOT_ELEMENT_ID = "4:bf9f3e2f-61c2-430f-be08-580850049dc8:0"
ROOT_NAME = "材料"
```

### 3. 运行程序

```bash
python3 main.py
```

## 📝 模块说明

### config.py
存放所有配置信息，包括：
- Neo4j数据库连接信息
- DeepSeek API配置
- 数据文件路径
- 分类层级配置

### data_loader.py
负责数据读取和格式化：
- `load_material_data()`: 从JSON文件加载材料数据
- `format_material_for_prompt()`: 格式化数据用于Prompt

### neo4j_connector.py
Neo4j数据库操作类：
- `get_child_nodes_by_element_id()`: 获取子节点（支持出边/入边）
- `build_classification_info()`: 构建分类信息和例子
- `get_random_neighbor_by_name()`: 随机选择相邻节点（用于特殊分类）

### prompt_generator.py
Prompt生成模块：
- `generate_task_description()`: 调用API生成任务描述
- `build_classification_prompt()`: 构建完整的分类System Prompt

### classifier.py
分类器模块：
- `classify_material()`: 通用材料分类函数（带自动纠错）
- `classify_high_entropy_alloy()`: 高熵合金特殊分类函数

### node_mounter.py
节点挂载模块：
- `mount_material_node()`: 创建新节点并挂载到图谱
- `verify_mounting()`: 验证挂载是否成功

### main.py
主程序入口，执行完整流程：
1. 读取材料数据
2. 连接Neo4j数据库
3. 多层分类（三层）
4. 特殊分类判断（高熵合金）
5. 挂载新节点
6. 显示分类路径

## 🔧 工作流程

```
1. 读取材料数据 (data_loader)
   ↓
2. 连接Neo4j (neo4j_connector)
   ↓
3. 第一层分类: 材料 → 材料类型 (classifier + prompt_generator)
   ↓
4. 第二层分类: 金属材料 → 子类型 (classifier + prompt_generator)
   ↓
5. 第三层分类: 特殊用途金属材料 → 具体类型 (classifier + prompt_generator)
   ↓
6. 特殊分类判断
   ├─ 是 "高熵合金" → 随机选择相邻节点 (classifier)
   └─ 否 → 使用当前节点
   ↓
7. 挂载新材料节点 (node_mounter)
   ↓
8. 验证并显示结果
```

## 📊 输出示例

```
材料知识图谱挂载系统
======================================================================

【步骤1】读取材料数据
----------------------------------------------------------------------
✅ 成功读取材料数据

【步骤2】连接Neo4j数据库
----------------------------------------------------------------------
✅ Neo4j 数据库连接成功！

【步骤3】开始多层分类
======================================================================

第一层分类：材料 → 子类型
🎯 第一层分类结果: 金属材料

第二层分类：金属材料 → 子类型
🎯 第二层分类结果: 特殊用途金属材料

第三层分类：特殊用途金属材料 → 具体类型
🎯 第三层分类结果: 高熵合金

【步骤4】特殊分类判断
✅ 检测到特殊节点: 高熵合金
🎯 特殊分类结果: Ti-13Nb-13Zr

【步骤5】挂载新材料节点
✅ 成功创建并挂载新节点！
   新节点名称: Material_12345
   挂载关系: Material_12345 -[BELONGS_TO]-> Ti-13Nb-13Zr

🎉 材料节点挂载成功！

完整分类路径：
材料 → 金属材料 → 特殊用途金属材料 → 高熵合金 → Ti-13Nb-13Zr
======================================================================

✅ 程序执行完毕
```

## 🎯 扩展指南

### 添加新的分类层级
在 `config.py` 中修改 `LAYER_CONFIGS`：

```python
LAYER_CONFIGS = [
    {"name": "第一层", "use_inbound": False},
    {"name": "第二层", "use_inbound": False},
    {"name": "第三层", "use_inbound": True},
    {"name": "第四层", "use_inbound": False},  # 新增层级
]
```

### 添加新的特殊分类逻辑
在 `classifier.py` 中添加新的特殊分类函数：

```python
def classify_xxx_material(neo4j_conn, node_name):
    # 实现你的特殊分类逻辑
    pass
```

然后在 `main.py` 中调用：

```python
if current_name == "你的特殊节点名":
    special_result = classify_xxx_material(neo4j_conn, current_name)
```

## ⚠️ 注意事项

1. 确保Neo4j数据库运行正常且可访问
2. 确保设置了 `DEEPSEEK_API_KEY` 环境变量
3. 数据文件路径必须正确
4. 节点的 `elementId` 是唯一标识，必须准确
5. 第三层分类使用入边查询例子（历史原因）

## 🐛 常见问题

**Q: 为什么第三层使用入边查询？**
A: 这是历史原因导致的图谱结构问题，第三层的例子节点通过入边连接。

**Q: 如何修改挂载的关系类型？**
A: 在 `node_mounter.py` 的 `mount_material_node()` 函数中修改 `BELONGS_TO` 为你需要的关系类型。

**Q: 如何批量处理多条数据？**
A: 修改 `main.py`，在读取数据后添加循环：
```python
for i in range(len(all_data)):
    material_data = all_data[i]
    # 执行分类和挂载流程
```

## 📄 许可

本项目仅供学习和研究使用。