"""
保存挂载节点信息模块 - 用于记录所有挂载的节点，便于后续清理
"""
import json
import os
from datetime import datetime


# 默认保存文件路径
DEFAULT_SAVE_FILE = "cleanup/new_data1.json"


def extract_nodes_from_result_file(result_file_path):
    """
    从 results 文件中提取需要删除的节点信息
    
    Args:
        result_file_path: result JSON 文件路径
    
    Returns:
        list: 节点信息列表 [{node_id, node_name, target_name, mounted_at, classification_path}]
    """
    if not os.path.exists(result_file_path):
        print(f"❌ 文件不存在: {result_file_path}")
        return []
    
    try:
        with open(result_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        nodes = []
        for result in data.get('results', []):
            if result.get('status') == 'success':
                mounted_node = result.get('mounted_node', {})
                target_node = result.get('target_node', {})
                classification_path = result.get('classification_path', [])
                
                # 构建分类路径字符串
                path_str = ' → '.join([node['name'] for node in classification_path])
                
                node_info = {
                    'node_id': mounted_node.get('element_id'),
                    'node_name': mounted_node.get('name'),
                    'mounted_at': mounted_node.get('mounted_at'),
                    'target_name': target_node.get('name'),
                    'target_id': target_node.get('element_id'),
                    'classification_path': path_str,
                    'saved_at': datetime.now().isoformat()
                }
                nodes.append(node_info)
        
        print(f"✅ 从 result 文件中提取到 {len(nodes)} 个节点")
        return nodes
        
    except Exception as e:
        print(f"❌ 提取节点信息时出错: {e}")
        return []


def save_mounted_node(mount_info, classification_path=None):
    """
    将挂载的节点信息保存到文件
    
    Args:
        mount_info: 挂载信息字典 {node_id, node_name, mounted_at, target_name, target_id}
        classification_path: 分类路径列表（可选）
    
    Returns:
        bool: 保存是否成功
    """
    try:
        # 确保cleanup目录存在
        os.makedirs(os.path.dirname(DEFAULT_SAVE_FILE), exist_ok=True)
        
        # 准备要保存的记录
        record = {
            'node_id': mount_info['node_id'],
            'node_name': mount_info['node_name'],
            'mounted_at': mount_info['mounted_at'],
            'target_name': mount_info['target_name'],
            'target_id': mount_info['target_id'],
            'saved_at': datetime.now().isoformat()
        }
        
        if classification_path:
            record['classification_path'] = ' → '.join(classification_path)
        
        # 读取已有记录
        existing_records = []
        if os.path.exists(DEFAULT_SAVE_FILE):
            try:
                with open(DEFAULT_SAVE_FILE, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            except json.JSONDecodeError:
                print("⚠️  现有文件格式错误，将创建新文件")
                existing_records = []
        
        # 添加新记录
        existing_records.append(record)
        
        # 保存到文件
        with open(DEFAULT_SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, ensure_ascii=False, indent=2)
        
        print(f"📝 挂载信息已保存到: {DEFAULT_SAVE_FILE}")
        print(f"   当前共有 {len(existing_records)} 条挂载记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 保存挂载信息时出错: {e}")
        return False


def get_mounted_nodes():
    """
    读取所有挂载的节点信息
    
    Returns:
        list: 节点信息列表
    """
    if not os.path.exists(DEFAULT_SAVE_FILE):
        print(f"ℹ️  未找到挂载记录文件: {DEFAULT_SAVE_FILE}")
        return []
    
    try:
        with open(DEFAULT_SAVE_FILE, 'r', encoding='utf-8') as f:
            records = json.load(f)
        return records
    except Exception as e:
        print(f"❌ 读取挂载记录时出错: {e}")
        return []


def clear_mounted_records():
    """
    清空挂载记录文件
    
    Returns:
        bool: 清空是否成功
    """
    try:
        if os.path.exists(DEFAULT_SAVE_FILE):
            os.remove(DEFAULT_SAVE_FILE)
            print(f"✅ 已清空挂载记录文件: {DEFAULT_SAVE_FILE}")
            return True
        else:
            print(f"ℹ️  记录文件不存在: {DEFAULT_SAVE_FILE}")
            return True
    except Exception as e:
        print(f"❌ 清空记录文件时出错: {e}")
        return False