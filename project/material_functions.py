"""
真实的函数实现 - 供 Function Call 调用（修改版）
"""
import json


def calculate_composition_similarity(material_data, entity_data):
    """
    基于成分比重计算余弦相似度
    
    Args:
        material_data: 待挂载材料的数据
        entity_data: Entity节点的材料数据
    
    Returns:
        float: 相似度 [0, 1]
    """
    # 提取成分比重
    comp1 = material_data.get('data', {}).get('成分比重', {})
    
    # entity_data可能是完整结构或简化结构
    if 'data' in entity_data:
        comp2 = entity_data.get('data', {}).get('成分比重', {})
    else:
        comp2 = entity_data.get('成分比重', {})
    
    if not comp1 or not comp2:
        return 0.0
    
    # 所有元素的并集
    all_elements = set(comp1.keys()) | set(comp2.keys())
    
    if not all_elements:
        return 0.0
    
    # 构建向量
    vec1 = [comp1.get(elem, 0) for elem in all_elements]
    vec2 = [comp2.get(elem, 0) for elem in all_elements]
    
    # 余弦相似度
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    norm1 = (sum(v ** 2 for v in vec1)) ** 0.5
    norm2 = (sum(v ** 2 for v in vec2)) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


# ===== 函数1：导航到出边Class节点 =====
def navigate_outbound(next_node_name, reasoning, current_element_id, current_name, 
                      available_nodes, neo4j_conn):
    """
    函数1：选择一个出边Class节点并移动
    
    参数由LLM提供：
        next_node_name: 选择的下一个节点名称
        reasoning: 选择理由
    
    预先绑定的参数：
        current_element_id: 当前节点的elementId
        current_name: 当前节点名称
        available_nodes: 可用的出边节点列表
        neo4j_conn: Neo4j连接器
    
    Returns:
        dict: {
            'success': True,
            'action': 'move',
            'from_node': '材料',
            'to_node': '金属材料',
            'new_element_id': '...',
            'reasoning': '...'
        }
    """
    # 验证选择是否有效
    valid_node = None
    for node in available_nodes:
        if node['name'] == next_node_name:
            valid_node = node
            break
    
    if not valid_node:
        return {
            'success': False,
            'error': f"节点 '{next_node_name}' 不在可用选项中",
            'valid_options': [n['name'] for n in available_nodes]
        }
    
    return {
        'success': True,
        'action': 'move',
        'from_node': current_name,
        'to_node': next_node_name,
        'new_element_id': valid_node['elementId'],
        'reasoning': reasoning,
        'path_update': f"{current_name} → {next_node_name}"
    }


# ===== 函数2：查看入边Entity节点 =====
def navigate_inbound(reasoning, current_element_id, current_name, neo4j_conn):
    """
    函数2：查看入边指向的Entity节点
    
    参数由LLM提供：
        reasoning: 为什么要查看Entity节点
    
    预先绑定的参数：
        current_element_id: 当前节点的elementId
        current_name: 当前节点名称
        neo4j_conn: Neo4j连接器
    
    Returns:
        dict: {
            'success': True,
            'action': 'check_entities',
            'node_name': '高熵合金',
            'entity_count': 50,
            'entities': [...],
            'need_similarity_search': True
        }
    """
    # 获取入边Entity节点
    result = neo4j_conn.get_inbound_entity_nodes(current_element_id, limit=100)
    
    entity_count = result['count']
    entities = result['entities']
    
    if entity_count == 0:
        return {
            'success': False,
            'error': f"节点 '{current_name}' 没有入边Entity节点",
            'action': 'no_entities'
        }
    
    # 判断是否需要相似度搜索
    need_similarity = entity_count >= 20
    
    # 如果数量少，返回所有；如果数量多，只返回前20个概要
    if need_similarity:
        entity_summary = [
            {'name': e['name'], 'elementId': e['elementId']}
            for e in entities[:20]
        ]
    else:
        entity_summary = [
            {'name': e['name'], 'elementId': e['elementId']}
            for e in entities
        ]
    
    return {
        'success': True,
        'action': 'check_entities',
        'node_name': current_name,
        'entity_count': entity_count,
        'entities': entity_summary,
        'need_similarity_search': need_similarity,
        'reasoning': reasoning,
        'message': f"找到 {entity_count} 个Entity节点" + 
                   (f"，数量较多，建议使用相似度搜索" if need_similarity else "")
    }


# ===== 函数3：获取top5相似Entity =====
def get_similar_materials(reasoning, current_element_id, material_data, neo4j_conn):
    """
    函数3：从大量Entity中筛选top5相似的材料
    
    参数由LLM提供：
        reasoning: 为什么需要筛选
    
    预先绑定的参数：
        current_element_id: 当前Class节点的elementId
        material_data: 待挂载的材料数据
        neo4j_conn: Neo4j连接器
    
    Returns:
        dict: {
            'success': True,
            'action': 'filter',
            'top5': [
                {'name': '...', 'elementId': '...', 'similarity': 0.95},
                ...
            ]
        }
    """
    # 获取所有入边Entity节点
    result = neo4j_conn.get_inbound_entity_nodes(current_element_id, limit=100)
    entities = result['entities']
    
    if not entities:
        return {
            'success': False,
            'error': '没有可用的Entity节点'
        }
    
    # 计算每个Entity的相似度
    similarities = []
    for entity in entities:
        if entity['data']:
            similarity = calculate_composition_similarity(material_data, entity['data'])
            similarities.append({
                'name': entity['name'],
                'elementId': entity['elementId'],
                'similarity': similarity
            })
    
    # 按相似度排序，取top5
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    top5 = similarities[:5]
    
    return {
        'success': True,
        'action': 'filter',
        'top5': top5,
        'reasoning': reasoning,
        'message': f"基于成分相似度，从 {len(entities)} 个Entity中筛选出top5"
    }


# ===== 函数4：挂载材料 =====
def mount_to_entity(target_element_id, reasoning, material_data, neo4j_conn):
    """
    函数4：将材料挂载到选定的Entity节点
    
    参数由LLM提供：
        target_element_id: 选择的Entity节点的elementId
        reasoning: 为什么选择这个Entity
    
    预先绑定的参数：
        material_data: 待挂载的材料数据
        neo4j_conn: Neo4j连接器
    
    Returns:
        dict: {
            'success': True,
            'action': 'mount',
            'mounted_node_id': '...',
            'mounted_node_name': 'Material_xxx',
            'target_element_id': '...',
            'reasoning': '...'
        }
    """
    import uuid
    from datetime import datetime
    
    if neo4j_conn.driver is None:
        return {
            'success': False,
            'error': '数据库未连接'
        }
    
    with neo4j_conn.driver.session() as session:
        try:
            # 生成节点名称和时间
            node_name = f"Material_{uuid.uuid4().hex[:12]}"
            mounted_at = datetime.now().isoformat()
            data_json = json.dumps(material_data, ensure_ascii=False)
            
            # 创建节点并建立关系
            query = """
            MATCH (target)
            WHERE elementId(target) = $target_id
            CREATE (new_material:Material {
                name: $name,
                mounted_at: $mounted_at,
                data: $data
            })
            CREATE (new_material)-[:BELONGS_TO]->(target)
            RETURN elementId(new_material) as new_node_id, target.name as target_name
            """
            
            result = session.run(
                query,
                target_id=target_element_id,
                name=node_name,
                mounted_at=mounted_at,
                data=data_json
            )
            record = result.single()
            
            if record:
                return {
                    'success': True,
                    'action': 'mount',
                    'mounted_node_id': record['new_node_id'],
                    'mounted_node_name': node_name,
                    'mounted_at': mounted_at,
                    'target_element_id': target_element_id,
                    'target_name': record['target_name'],
                    'reasoning': reasoning
                }
            else:
                return {
                    'success': False,
                    'error': '挂载失败：未返回结果'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'挂载节点时出错: {str(e)}'
            }