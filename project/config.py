"""
配置文件 - 存放所有配置信息
"""
import os

# Neo4j 数据库配置
NEO4J_URI = "neo4j://10.77.50.200:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "thl123!@#"

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# 数据文件路径
DATA_FILE_PATH = "/home/thl/2025Fall/data/method2/high_entropy_alloy.json"

# 根节点配置
ROOT_ELEMENT_ID = "4:bf9f3e2f-61c2-430f-be08-580850049dc8:0"
ROOT_NAME = "材料"

# 分类层级配置
LAYER_CONFIGS = [
    {"name": "第一层", "use_inbound": False},  # 材料 -> 材料类型
    {"name": "第二层", "use_inbound": False},  # 金属材料 -> 子类型  
    {"name": "第三层", "use_inbound": True},   # 特殊用途金属材料 -> 具体类型
]

# 特殊节点名称（需要特殊处理的节点）
SPECIAL_NODE_NAME = "高熵合金"