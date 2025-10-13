"""
分类器模块 - 动态构建tools（修改版）
"""
from functools import partial
from material_functions import (
    navigate_outbound,
    navigate_inbound,
    get_similar_materials,
    mount_to_entity
)


def build_tools_for_class_node(current_element_id, current_name, neo4j_conn):
    """
    为Class节点构建可用工具（函数1、2）
    
    Args:
        current_element_id: 当前Class节点的elementId
        current_name: 当前Class节点名称
        neo4j_conn: Neo4j连接器
    
    Returns:
        tuple: (tools列表, available_functions字典, 辅助数据字典)
    """
    # 获取出边Class节点
    outbound_nodes = neo4j_conn.get_outbound_class_nodes(current_element_id)
    
    tools = []
    available_functions = {}
    helper_data = {'outbound_nodes': outbound_nodes}
    
    # 函数1：导航到出边节点（如果有出边Class节点）
    if outbound_nodes:
        tools.append({
            "type": "function",
            "function": {
                "name": "navigate_outbound",
                "description": f"从当前节点'{current_name}'移动到下一级Class节点。选择最符合材料特征的子类别。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "next_node_name": {
                            "type": "string",
                            "enum": [node['name'] for node in outbound_nodes],
                            "description": f"选择下一个要移动到的Class节点。可用选项: {', '.join([n['name'] for n in outbound_nodes])}"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "为什么选择这个节点？根据材料的成分、性质等特征说明理由。"
                        }
                    },
                    "required": ["next_node_name", "reasoning"]
                }
            }
        })
        
        # 绑定函数
        available_functions['navigate_outbound'] = partial(
            navigate_outbound,
            current_element_id=current_element_id,
            current_name=current_name,
            available_nodes=outbound_nodes,
            neo4j_conn=neo4j_conn
        )
    
    # 函数2：查看入边Entity节点（总是可用，但要根据是否有出边调整描述）
    if outbound_nodes:
        # 有出边Class节点 - 不建议调用此函数
        inbound_description = f"查看'{current_name}'下的具体材料实例（Entity节点）。⚠️ 警告：当前还有子分类可用，建议先使用 navigate_outbound 继续细分。"
    else:
        # 没有出边Class节点 - 这是唯一选择
        inbound_description = f"查看'{current_name}'下的具体材料实例（Entity节点）。当前已到达分类树的叶子节点，没有更细的子分类。"
    
    tools.append({
        "type": "function",
        "function": {
            "name": "navigate_inbound",
            "description": inbound_description,
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "为什么要查看Entity节点？"
                    }
                },
                "required": ["reasoning"]
            }
        }
    })
    
    available_functions['navigate_inbound'] = partial(
        navigate_inbound,
        current_element_id=current_element_id,
        current_name=current_name,
        neo4j_conn=neo4j_conn
    )
    
    return tools, available_functions, helper_data


def build_tools_for_entity_selection(entities, need_similarity, current_element_id,
                                     material_data, neo4j_conn):
    """
    为Entity选择构建可用工具（函数3、4）
    
    Args:
        entities: Entity节点列表
        need_similarity: 是否需要相似度搜索
        current_element_id: 当前Class节点的elementId
        material_data: 待挂载的材料数据
        neo4j_conn: Neo4j连接器
    
    Returns:
        tuple: (tools列表, available_functions字典)
    """
    tools = []
    available_functions = {}
    
    # 函数3：相似度搜索（仅在Entity数量>=20时提供）
    if need_similarity:
        tools.append({
            "type": "function",
            "function": {
                "name": "get_similar_materials",
                "description": f"从 {len(entities)}+ 个Entity节点中筛选出top5最相似的材料牌号。基于成分比重的相似度计算。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "为什么需要使用相似度筛选？"
                        }
                    },
                    "required": ["reasoning"]
                }
            }
        })
        
        available_functions['get_similar_materials'] = partial(
            get_similar_materials,
            current_element_id=current_element_id,
            material_data=material_data,
            neo4j_conn=neo4j_conn
        )
    
    # 函数4：挂载材料（总是提供）
    # 如果Entity数量较少，提供所有选项；否则建议先用相似度搜索
    if not need_similarity and len(entities) > 0:
        # Entity数量少，直接列举所有选项
        description = f"将材料挂载到选定的Entity节点。当前有 {len(entities)} 个可选Entity。"
    else:
        description = "将材料挂载到选定的Entity节点。建议先使用相似度搜索筛选后再挂载。"
    
    tools.append({
        "type": "function",
        "function": {
            "name": "mount_to_entity",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target_element_id": {
                        "type": "string",
                        "description": "选择的Entity节点的elementId（从之前的查询结果中获取）"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "为什么选择这个Entity节点？基于材料特征的匹配说明。"
                    }
                },
                "required": ["target_element_id", "reasoning"]
            }
        }
    })
    
    available_functions['mount_to_entity'] = partial(
        mount_to_entity,
        material_data=material_data,
        neo4j_conn=neo4j_conn
    )
    
    return tools, available_functions