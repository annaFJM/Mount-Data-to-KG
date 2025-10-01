# 项目结构详解

## 📂 完整目录结构

```
project/
├── config.py                          # 全局配置
├── data_loader.py                     # 数据加载
├── neo4j_connector.py                 # 数据库操作
├── prompt_generator.py                # Prompt生成
├── classifier.py                      # 分类逻辑
├── node_mounter.py                    # 节点挂载
├── main.py                           # 主程序
│
├── cleanup/                          # 清理模块（测试用）
│   ├── __init__.py                   # 模块初始化
│   ├── save_mounted_nodes.py         # 保存挂载记录
│   ├── delete_mounted_nodes.py       # 删除节点脚本
│   └── new_data1.json               # 挂载记录（自动生成）
│
├── data/                             # 数据文件夹
│   └── high_entropy_alloy.json      # 材料数据
│
├── install.sh                        # 安装依赖
├── run.sh                           # 运行程序
├── cleanup.sh                       # 快速清理
├── README.md                        # 使用文档
└── PROJECT_STRUCTURE.md             # 本文件
```

## 🔄 数据流

```
1. 读取数据
   data/high_entropy_alloy.json
        ↓
   data_loader.py
        ↓
   material_data (dict)

2. 多层分类
   material_data
        ↓
   classifier.py + prompt_generator.py
        ↓
   neo4j_connector.py (查询子类)
        ↓
   DeepSeek API (分类判断)
        ↓
   (节点名称, elementId)

3. 特殊分类
   if 节点 == "高熵合金":
       classifier.py (随机选择)
            ↓
   (目标节点名称, elementId)

4. 挂载节点
   material_data + target_element_id
        ↓
   node_mounter.py
        ↓
   CREATE (:Material {name, mounted_at, data})
        ↓
   CREATE (Material)-[:BELONGS_TO]->(Target)
        ↓
   mount_info (dict)

5. 保存记录
   mount_info + classification_path
        ↓
   cleanup/save_mounted_nodes.py
        ↓
   cleanup/new_data1.json

6. 清理节点（测试后）
   cleanup/new_data1.json
        ↓
   cleanup/delete_mounted_nodes.py
        ↓
   DETACH DELETE (Material)
        ↓
   清空 new_data1.json
```

## 🎯 核心模块职责

### 主流程模块

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `config.py` | 配置管理 | - | 配置常量 |
| `data_loader.py` | 数据读取 | JSON文件路径 | 材料数据字典 |
| `neo4j_connector.py` | 数据库操作 | URI, 认证信息 | 查询结果 |
| `prompt_generator.py` | 提示词生成 | 父类名, 子类列表 | System Prompt |
| `classifier.py` | 分类逻辑 | 材料数据, 分类信息 | (类别名, elementId) |
| `node_mounter.py` | 节点创建 | 材料数据, 目标ID | 挂载信息 |
| `main.py` | 流程控制 | - | 完整执行 |

### 清理模块（测试用）

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `save_mounted_nodes.py` | 记录保存 | 挂载信息 | JSON文件 |
| `delete_mounted_nodes.py` | 批量删除 | JSON文件 | 删除统计 |

## 💾 数据结构

### 挂载节点结构
```json
{
  "node_id": "4:xxxx-xxxx-xxxx",
  "node_name": "Material_a3f9c8d12e4b",
  "mounted_at": "2025-10-01T14:30:45.123456",
  "target_name": "Ti-13Nb-13Zr",
  "target_id": "4:yyyy-yyyy-yyyy",
  "classification_path": "材料 → 金属材料 → 特殊用途金属材料 → 高熵合金 → Ti-13Nb-13Zr",
  "saved_at": "2025-10-01T14:30:45.789012"
}
```

### Neo4j节点属性
```cypher
(:Material {
  name: "Material_a3f9c8d12e4b",
  mounted_at: "2025-10-01T14:30:45.123456",
  data: "{\"MGE18_标题\": \"Mn1Fe1Co1Ni1Cu1Nb2\", ...}"
})
```

## 🚀 使用场景

### 场景1：测试单条数据挂载
```bash
# 1. 运行主程序
python3 main.py

# 2. 检查挂载记录
cat cleanup/new_data1.json

# 3. 清理测试数据
bash cleanup.sh
# 或
python3 cleanup/delete_mounted_nodes.py
```

### 场景2：批量挂载（扩展）
```python
# 修改 main.py
materials = load_all_materials(DATA_FILE_PATH)
for material in materials:
    # 执行分类和挂载流程
    ...
```

### 场景3：保留测试数据
```python
# 在 cleanup/delete_mounted_nodes.py 中
# 选择性删除特定时间段的节点
records = [r for r in get_mounted_nodes() 
           if r['mounted_at'] < '2025-10-01']
```

## 🔧 扩展点

### 1. 添加新的分类层级
**修改位置**: `config.py`
```python
LAYER_CONFIGS = [
    {"name": "第一层", "use_inbound": False},
    {"name": "第二层", "use_inbound": False},
    {"name": "第三层", "use_inbound": True},
    {"name": "第四层", "use_inbound": False},  # 新增
]
```

### 2. 自定义特殊分类
**修改位置**: `classifier.py` + `main.py`
```python
# classifier.py
def classify_custom_material(neo4j_conn, node_name):
    # 自定义分类逻辑
    pass

# main.py
if current_name == "你的特殊节点":
    special_result = classify_custom_material(neo4j_conn, current_name)
```

### 3. 修改节点属性结构
**修改位置**: `node_mounter.py`
```python
# 添加更多属性
CREATE (new_material:Material {
    name: $name,
    mounted_at: $mounted_at,
    data: $data,
    version: "1.0",           # 新增
    source: "experiment_1"    # 新增
})
```

### 4. 更改关系类型
**修改位置**: `node_mounter.py`
```python
# 从 BELONGS_TO 改为其他关系
CREATE (new_material)-[:CLASSIFIED_AS]->(target)
```

## 🛠 维护建议

### 日常使用
1. 测试完成后及时清理节点
2. 定期备份 `cleanup/new_data1.json`
3. 监控挂载节点数量

### 代码维护
1. 每个模块保持单一职责
2. 新功能优先考虑独立模块
3. 配置项统一放在 `config.py`
4. 测试相关代码放在 `cleanup/`

### 性能优化
1. 批量挂载时使用事务
2. 大量数据时考虑分批处理
3. 添加进度显示和日志记录

## 📌 注意事项

1. **elementId 的重要性**：始终使用 `elementId` 唯一标识节点
2. **数据序列化**：复杂数据必须转为JSON字符串存储
3. **清理机制**：测试环境必须配置清理功能
4. **历史兼容**：第三层使用入边查询（历史原因）
5. **API配额**：注意DeepSeek API调用次数限制