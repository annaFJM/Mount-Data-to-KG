# 使用指南

## 🚀 快速开始

### 1. 首次安装

```bash
# 安装依赖
bash install.sh

# 设置 API 密钥
export DEEPSEEK_API_KEY="your_api_key"
```

### 2. 配置数据文件

编辑 `config.py`：

```python
DATA_FILE_PATH = "/path/to/your/data.json"
```

### 3. 运行程序

**方式1：Shell 脚本**
```bash
bash run.sh
```

**方式2：Python 命令**
```bash
python3 main.py
```

---

## 📊 输出文件位置

```
logs/
  └── mount_log_20251013_143025.log      # 详细日志

results/
  └── mount_result_20251013_143025.json  # 挂载结果

cleanup/
  └── new_data1.json                      # 清理记录
```

---

## 🧹 清理挂载节点

**方式1：Shell 脚本**
```bash
bash cleanup.sh
```

**方式2：Python 命令**
```bash
python3 cleanup/delete_mounted_nodes.py
```

**自动选择**：程序会自动找到最新的 result 文件并清理

---

## ⚙️ 常用配置

### 修改数据文件

```python
# config.py
DATA_FILE_PATH = "/home/user/data.json"
```

### 添加特殊节点

```python
# config.py
SPECIAL_NODES = ["高熵合金", "复合材料", "纳米材料"]
```

### 限制处理数量

```python
# main.py 中添加
all_materials = all_materials[:10]  # 只处理前10条
```

### 修改最大深度

```python
# config.py
MAX_CLASSIFICATION_DEPTH = 20  # 默认20层
```

---

## 📝 查看结果

### 查看日志

```bash
# 最新日志
cat logs/mount_log_*.log | tail -n 50

# 查看分类理由
cat logs/mount_log_*.log | grep "理由:"
```

### 查看结果文件

```bash
# 格式化输出
cat results/mount_result_*.json | python3 -m json.tool

# 统计
python3 -c "
import json
data = json.load(open('results/mount_result_*.json'))
print(f'总计: {data[\"total\"]}')
print(f'成功: {data[\"success\"]}')
print(f'失败: {data[\"failed\"]}')
"
```

---

## 🔍 验证挂载

在 Neo4j Browser 中查询：

```cypher
// 查看所有挂载的节点
MATCH (n:Material)
WHERE n.name STARTS WITH 'Material_'
RETURN n.name, n.mounted_at, elementId(n)
ORDER BY n.mounted_at DESC
LIMIT 10

// 统计挂载数量
MATCH (n:Material)
WHERE n.mounted_at IS NOT NULL
RETURN count(n) as total

// 查看某个材料的分类路径
MATCH path = (n:Material)-[:BELONGS_TO*]->(root)
WHERE n.name = 'Material_47fe554e3721'
RETURN path
```

---

## ❌ 故障排查

### API 调用失败

**检查**：
```bash
# 检查 API 密钥
echo $DEEPSEEK_API_KEY

# 重新设置
export DEEPSEEK_API_KEY="your_key"
```

### Neo4j 连接失败

**检查**：
```python
# config.py
NEO4J_URI = "neo4j://10.77.50.200:7687"  # 确认地址正确
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"
```

### 数据文件读取失败

**检查**：
```bash
# 文件是否存在
ls -lh /path/to/data.json

# 文件格式是否正确
python3 -c "import json; json.load(open('/path/to/data.json'))"
```

### 日志或结果文件无法创建

**检查权限**：
```bash
mkdir -p logs results cleanup
chmod 755 logs results cleanup
```

---

## 🔧 高级用法

### 批量处理多个文件

```python
# 修改 main.py
import glob

data_files = glob.glob('/path/to/*.json')
for file in data_files:
    materials = load_all_materials(file)
    # 处理...
```

### 自定义分类逻辑

在 `classifier.py` 中添加新的分类函数：

```python
def classify_custom_material(material_data, ...):
    # 自定义逻辑
    pass
```

在 `main.py` 中调用：

```python
if current_name == "自定义节点":
    result = classify_custom_material(material_data, ...)
```

---

## 📚 相关文档

- [README.md](README.md) - 项目概览
- [FUNCTION_CALL_FLOW.md](FUNCTION_CALL_FLOW.md) - Function Call 详解
- [CLEANUP_USAGE.md](CLEANUP_USAGE.md) - 清理模块详解

---

## 💡 提示

1. **首次运行**：建议先用少量数据测试
2. **API 配额**：注意 DeepSeek API 的调用限制
3. **日志文件**：定期清理旧日志，避免占用空间
4. **数据备份**：重要数据建议先备份
5. **测试环境**：建议先在测试数据库上运行

---

**需要帮助？** 查看日志文件或在项目中搜索相关错误信息。