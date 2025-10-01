"""
节点挂载模块 - 负责将新节点挂载到知识图谱
"""
import json
import uuid
from datetime import datetime


def mount_material_node(neo4j_conn, material_data, target_element_id, target_name):
    """
    创建新材料节点并挂载到目标节点
    
    Args:
        neo4j_conn: Neo4j连接器实例
        material_data: 材料数据字典
        target_element_id: 目标节点的elementId
        target_name: 目标节点的名称（用于日志）
    
    Returns:
        dict: 挂载信息 {success, node_id, node_name, mounted_at, target_name, target_id}
              失败返回 None
    """
    print(f"\n--- 正在挂载新材料节点到 '{target_name}' ---")
    
    if neo4j_conn.driver is None:
        print("❌ 数据库未连接")
        return None
    
    with neo4j_conn.driver.session() as session:
        try:
            # 生成随机节点名称和挂载时间
            node_name = f"Material_{uuid.uuid4().hex[:12]}"
            mounted_at = datetime.now().isoformat()
            
            # 将所有材料数据转为JSON字符串
            data_json = json.dumps(material_data, ensure_ascii=False)
            
            # 构建Cypher查询
            query = """
            MATCH (target)
            WHERE elementId(target) = $target_id
            CREATE (new_material:Material {
                name: $name,
                mounted_at: $mounted_at,
                data: $data
            })
            CREATE (new_material)-[:BELONGS_TO]->(target)
            RETURN elementId(new_material) as new_node_id
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
                new_node_id = record["new_node_id"]
                print(f"✅ 成功创建并挂载新节点！")
                print(f"   新节点名称: {node_name}")
                print(f"   新节点ID: {new_node_id}")
                print(f"   挂载时间: {mounted_at}")
                print(f"   挂载关系: {node_name} -[BELONGS_TO]-> {target_name}")
                
                # 返回挂载信息
                return {
                    'success': True,
                    'node_id': new_node_id,
                    'node_name': node_name,
                    'mounted_at': mounted_at,
                    'target_name': target_name,
                    'target_id': target_element_id
                }
            else:
                print("❌ 挂载失败：未返回结果")
                return None
                
        except Exception as e:
            print(f"❌ 挂载节点时出错: {e}")
            return None


def verify_mounting(neo4j_conn, target_element_id, target_name):
    """
    验证挂载是否成功（可选）
    
    Args:
        neo4j_conn: Neo4j连接器实例
        target_element_id: 目标节点的elementId
        target_name: 目标节点的名称
    
    Returns:
        int: 挂载到该节点的材料节点数量
    """
    if neo4j_conn.driver is None:
        return 0
    
    with neo4j_conn.driver.session() as session:
        try:
            query = """
            MATCH (material:Material)-[:BELONGS_TO]->(target)
            WHERE elementId(target) = $target_id
            RETURN count(material) as count
            """
            
            result = session.run(query, target_id=target_element_id)
            record = result.single()
            
            if record:
                count = record["count"]
                print(f"📊 '{target_name}' 节点当前有 {count} 个挂载的材料节点")
                return count
            else:
                return 0
                
        except Exception as e:
            print(f"❌ 验证挂载时出错: {e}")
            return 0