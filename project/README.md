# 材料知识图谱自动挂载系统

基于 DeepSeek Function Calling 的材料知识图谱智能挂载系统。

## 🔄 核心流程

```
读取材料数据
    ↓
连接 Neo4j 数据库
    ↓
【While 循环分类】
    获取子节点 → Function Call 分类 → 更新当前节点
    ↓（直到到达特殊节点）
【特殊节点判断】
    检查当前节点是否为特殊节点（如"高熵合金"）
    ↓
【特殊分类】
    获取实例列表 → Function Call 选择实例
    ↓
【挂载节点】
    创建新节点 → 建立关系 → 保存信息
    ↓
【记录日志和结果】
    logs/*.log + results/*.json + cleanup/*.json
```

## 🚀 快速开始

### 1. 安装依赖

```bash
bash install.sh
```

### 2. 配置 API 密钥

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

### 3. 配置文件

编辑 `config.py`：

```python
# 数据文件路径
DATA_FILE_PATH = "/path/to/your/data.json"

# 特殊节点列表
SPECIAL_NODES = ["高熵合金"]
```

### 4. 运行程序

**方式1：Shell 脚本（推荐）**
```bash
bash run.sh
```

**方式2：Python 命令**
```bash
python3 main.py
```

## 📊 输出文件

```
logs/
  └── mount_log_YYYYMMDD_HHMMSS.log     # 详细日志

results/
  └── mount_result_YYYYMMDD_HHMMSS.json # 挂载结果（JSON格式）

cleanup/
  └── new_data1.json                     # 清理记录
```

## 🧹 清理挂载节点

```bash
# Shell 脚本
bash cleanup.sh

# Python 命令
python3 cleanup/delete_mounted_nodes.py
```

## 🎯 Function Call 工作原理

系统使用 DeepSeek Function Calling API 进行智能分类：

### 1. 层级分类函数

```python
{
  "name": "classify_to_subtype",
  "parameters": {
    "subtype": {
      "enum": ["金属材料", "非金属材料", ...]  # 动态生成
    },
    "reasoning": {
      "type": "string"  # 分类理由
    }
  }
}
```

### 2. 实例选择函数

```python
{
  "name": "select_instance",
  "parameters": {
    "instance": {
      "enum": ["Ti-13Nb-13Zr", "CoCrFeMnNi", ...]  # 动态生成
    },
    "reasoning": {
      "type": "string"  # 选择理由
    }
  }
}
```

**优势**：
- ✅ 自动验证（enum 限制，无需重试）
- ✅ 结构化输出（直接获取分类结果）
- ✅ 包含推理过程（debugging 友好）

详见 [FUNCTION_CALL_FLOW.md](FUNCTION_CALL_FLOW.md)

## 📁 项目结构

```
project/
├── config.py                    # 全局配置
├── main.py                      # 主程序入口
├── function_call_handler.py     # Function Call 封装
├── classifier.py                # 分类逻辑
├── neo4j_connector.py           # 数据库操作
├── node_mounter.py              # 节点挂载
├── data_loader.py               # 数据读取
├── logger.py                    # 日志模块
├── result_writer.py             # 结果输出
├── cleanup/                     # 清理模块
│   ├── save_mounted_nodes.py
│   └── delete_mounted_nodes.py
├── data/                        # 数据文件
├── logs/                        # 日志输出
├── results/                     # 结果输出
├── run.sh                       # 运行脚本
├── cleanup.sh                   # 清理脚本
└── install.sh                   # 安装脚本
```

## ⚙️ 配置说明

### config.py 关键配置

```python
# 数据文件
DATA_FILE_PATH = "/path/to/data.json"

# 特殊节点（需要特殊分类）
SPECIAL_NODES = ["高熵合金"]

# 分类最大深度（防止死循环）
MAX_CLASSIFICATION_DEPTH = 20
```

## 📖 详细文档

- [FUNCTION_CALL_FLOW.md](FUNCTION_CALL_FLOW.md) - Function Call 工作流程
- [USAGE_GUIDE.md](USAGE_GUIDE.md) - 使用指南
- [CLEANUP_USAGE.md](CLEANUP_USAGE.md) - 清理模块说明

## 🔧 常见问题

### Q: 如何处理大量数据？

程序会在处理超过 100 条数据时询问确认。可以在 main.py 中限制数量：

```python
all_materials = all_materials[:10]  # 只处理前10条
```

### Q: 如何添加新的特殊节点？

编辑 `config.py`：

```python
SPECIAL_NODES = ["高熵合金", "复合材料", "纳米材料"]
```

### Q: Function Call 失败怎么办？

检查：
1. API 密钥是否正确
2. 网络连接是否正常
3. 查看日志文件中的详细错误信息

## 📝 版本

**Version 2.0** - Function Call 版本
- 使用标准 DeepSeek Function Calling API
- 动态层级分类（不限制层数）
- 自动验证分类结果
- 完整的日志和结果记录

## 📄 许可

本项目仅供学习和研究使用。