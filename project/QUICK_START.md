# 快速开始指南

## 📦 安装（首次使用）

### 方式1：使用安装脚本
```bash
chmod +x install.sh
./install.sh
```

### 方式2：手动安装
```bash
pip3 install neo4j openai
```

## 🔑 配置

### 1. 设置API密钥
```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

### 2. 检查配置文件 `config.py`
确认以下配置正确：
- Neo4j连接信息（URI、用户名、密码）
- 数据文件路径
- 根节点配置

## 🚀 运行

### 方式1：使用运行脚本（推荐）
```bash
chmod +x run.sh
./run.sh
```

### 方式2：直接运行
```bash
python3 main.py
```

## 🧹 清理测试数据

### 方式1：使用清理脚本（推荐）
```bash
chmod +x cleanup.sh
./cleanup.sh
```

### 方式2：直接运行清理程序
```bash
python3 cleanup/delete_mounted_nodes.py
```

### 方式3：Python代码
```python
from cleanup.delete_mounted_nodes import delete_all_mounted_nodes

# 需要确认
delete_all_mounted_nodes(confirm=True)

# 无需确认
delete_all_mounted_nodes(confirm=False)
```

## 📋 完整流程示例

```bash
# 1. 首次安装依赖
./install.sh

# 2. 设置环境变量
export DEEPSEEK_API_KEY="your_key"

# 3. 运行程序
./run.sh

# 4. 查看挂载记录
cat cleanup/new_data1.json

# 5. 清理测试数据
./cleanup.sh
```

## 🔍 验证安装

### 检查Python环境
```bash
python3 --version
# 应输出: Python 3.x.x
```

### 检查依赖包
```bash
python3 -c "import neo4j; print('neo4j:', neo4j.__version__)"
python3 -c "import openai; print('openai:', openai.__version__)"
```

### 测试Neo4j连接
```bash
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('neo4j://10.77.50.200:7687', auth=('neo4j', 'thl123!@#'))
driver.verify_connectivity()
print('✅ Neo4j连接成功')
driver.close()
"
```

## ⚙️ 常见配置修改

### 修改数据文件路径
编辑 `config.py`:
```python
DATA_FILE_PATH = "/your/path/to/data.json"
```

### 修改Neo4j连接
编辑 `config.py`:
```python
NEO4J_URI = "neo4j://your_host:7687"
NEO4J_USER = "your_username"
NEO4J_PASSWORD = "your_password"
```

### 修改根节点
编辑 `config.py`:
```python
ROOT_ELEMENT_ID = "your_root_element_id"
ROOT_NAME = "your_root_name"
```

## 🐛 故障排查

### 问题1：找不到模块
```bash
# 确保在项目根目录运行
cd /path/to/project
python3 main.py
```

### 问题2：Neo4j连接失败
```bash
# 检查Neo4j服务是否运行
# 检查IP地址、端口、用户名、密码是否正确
# 检查防火墙设置
```

### 问题3：API调用失败
```bash
# 检查环境变量是否设置
echo $DEEPSEEK_API_KEY

# 重新设置
export DEEPSEEK_API_KEY="your_key"
```

### 问题4：无法写入文件
```bash
# 检查cleanup目录是否有写权限
chmod -R 755 cleanup/
```

## 📊 预期输出

### 成功运行
```
材料知识图谱挂载系统
======================================================================

【步骤1】读取材料数据
✅ 成功读取材料数据 (索引: 0)

【步骤2】连接Neo4j数据库
✅ Neo4j 数据库连接成功！

【步骤3】开始多层分类
...
🎯 第一层分类结果: 金属材料
🎯 第二层分类结果: 特殊用途金属材料
🎯 第三层分类结果: 高熵合金

【步骤4】特殊分类判断
✅ 检测到特殊节点: 高熵合金
🎯 特殊分类结果: Ti-13Nb-13Zr

【步骤5】挂载新材料节点
✅ 成功创建并挂载新节点！
📝 挂载信息已保存到: cleanup/new_data1.json
🎉 材料节点挂载成功！

完整分类路径：
材料 → 金属材料 → 特殊用途金属材料 → 高熵合金 → Ti-13Nb-13Zr

✅ 程序执行完毕
```

### 成功清理
```
删除测试挂载的节点
======================================================================
✅ 找到 1 条挂载记录
⚠️  确定要删除这些节点吗？(yes/no): yes
✅ Neo4j 数据库连接成功！
  ✅ 已删除节点: Material_xxx
删除统计：
  总计: 1 个节点
  成功: 1 个
  失败: 0 个
✅ 已清空挂载记录文件
✅ 清理完成！
```

## 🎓 下一步

- 阅读 [README.md](README.md) 了解详细功能
- 阅读 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 了解项目架构
- 修改 `config.py` 自定义配置
- 扩展 `classifier.py` 添加自定义分类逻辑

## 💡 提示

1. **首次运行前**：确保设置了 `DEEPSEEK_API_KEY`
2. **测试完成后**：记得运行清理脚本
3. **批量处理**：考虑添加进度显示
4. **生产环境**：移除或禁用 cleanup 模块