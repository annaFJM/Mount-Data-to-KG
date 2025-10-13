"""
真实的函数实现 - 供 Function Call 调用

这些函数会被 LLM 通过 Function Calling 机制真正执行
"""
import json


def classify_to_subtype(subtype, reasoning, material_data, parent_name, subtype_info):
    """
    真正执行的分类函数：验证分类并获取详细信息
    
    注意：参数顺序很重要！
    - subtype, reasoning: 由 LLM 提供
    - material_data, parent_name, subtype_info: 通过 functools.partial 预先绑定
    
    Args:
        subtype: 模型选择的子类型
        reasoning: 分类理由
        material_data: 材料数据
        parent_name: 父节点名称
        subtype_info: 子类型信息（用于验证）
    
    Returns:
        dict: 分类结果
    """
    # 验证分类是否有效
    if subtype not in subtype_info:
        return {
            'success': False,
            'error': f"分类 '{subtype}' 不在有效选项中",
            'valid_options': list(subtype_info.keys())
        }
    
    # 获取详细信息
    element_id = subtype_info[subtype]['elementId']
    examples = subtype_info[subtype]['examples']
    
    # 提取材料标题
    material_title = 'Unknown'
    if 'data' in material_data:
        material_title = material_data['data'].get('MGE18_标题', 'Unknown')
    
    # 返回完整的分类信息
    result = {
        'success': True,
        'parent_name': parent_name,
        'classification': subtype,
        'element_id': element_id,
        'reasoning': reasoning,
        'examples': examples[:5] if examples else [],
        'material_title': material_title,
        'confidence': 'high' if reasoning and len(reasoning) > 20 else 'medium',
        'validation': {
            'is_valid': True,
            'checked_against': list(subtype_info.keys()),
            'total_options': len(subtype_info)
        }
    }
    
    return result


def select_instance(instance, reasoning, material_data, special_node_name, instance_info):
    """
    真正执行的实例选择函数
    
    注意：参数顺序很重要！
    - instance, reasoning: 由 LLM 提供
    - material_data, special_node_name, instance_info: 通过 functools.partial 预先绑定
    
    Args:
        instance: 模型选择的实例
        reasoning: 选择理由
        material_data: 材料数据
        special_node_name: 特殊节点名称
        instance_info: 实例信息（用于验证）
    
    Returns:
        dict: 选择结果
    """
    # 验证实例是否有效
    if instance not in instance_info:
        return {
            'success': False,
            'error': f"实例 '{instance}' 不在有效选项中",
            'valid_options': list(instance_info.keys())
        }
    
    # 获取详细信息
    element_id = instance_info[instance]['elementId']
    description = instance_info[instance].get('description', '')
    
    # 提取材料标题
    material_title = 'Unknown'
    if 'data' in material_data:
        material_title = material_data['data'].get('MGE18_标题', 'Unknown')
    
    result = {
        'success': True,
        'special_node': special_node_name,
        'selected_instance': instance,
        'element_id': element_id,
        'reasoning': reasoning,
        'description': description,
        'material_title': material_title,
        'confidence': 'high' if reasoning and len(reasoning) > 20 else 'medium',
        'validation': {
            'is_valid': True,
            'checked_against': list(instance_info.keys()),
            'total_options': len(instance_info)
        }
    }
    
    return result


# 如果需要添加更多函数，在这里定义
# 例如：
#
# def query_external_database(material_id):
#     """查询外部数据库"""
#     import requests
#     response = requests.get(f"https://api.example.com/materials/{material_id}")
#     return response.json()
#
# def calculate_properties(composition):
#     """计算材料性能"""
#     # 实际的计算逻辑
#     return {"hardness": 500, "density": 7.8}