"""
Neo4j数据库连接器 - 负责所有数据库操作（修改版）
"""
from neo4j import GraphDatabase
import json


class Neo4jConnector:
    """Neo4j数据库连接和操作类"""
    
    def __init__(self, uri, user, password):
        """初始化数据库连接"""
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("✅ Neo4j 数据库连接成功！")
        except Exception as e:
            print(f"❌ Neo4j连接失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self.driver is not None:
            self.driver.close()
            print("🔌 Neo4j 数据库连接已关闭。")
    
    def get_node_labels(self, element_id):
        """
        获取节点的labels
        
        Returns:
            list: ['Class'] 或 ['Entity'] 或 []
        """
        if self.driver is None:
            return []
        
        with self.driver.session() as session:
            try:
                query = """
                MATCH (n)
                WHERE elementId(n) = $element_id
                RETURN labels(n) as labels
                """
                result = session.run(query, element_id=element_id)
                record = result.single()
                
                if record:
                    return record['labels']
                return []
            except Exception as e:
                print(f"❌ 获取节点labels时出错: {e}")
                return []
    
    def get_outbound_class_nodes(self, element_id):
        """
        获取出边指向的Class节点
        
        Returns:
            list: [{'name': '金属材料', 'elementId': '...'}]
        """
        if self.driver is None:
            return []
        
        with self.driver.session() as session:
            try:
                query = """
                MATCH (a)-[r]->(b:Class)
                WHERE elementId(a) = $element_id
                RETURN b.name as name, elementId(b) as elementId
                LIMIT 20
                """
                result = session.run(query, element_id=element_id)
                nodes = [
                    {"name": record["name"], "elementId": record["elementId"]} 
                    for record in result
                ]
                return nodes
            except Exception as e:
                print(f"❌ 获取出边Class节点时出错: {e}")
                return []
    
    def get_inbound_entity_nodes(self, element_id, limit=100):
        """
        获取入边指向的Entity节点
        
        Returns:
            dict: {
                'count': 50,
                'entities': [{'name': '...', 'elementId': '...', 'data': {...}}]
            }
        """
        if self.driver is None:
            return {'count': 0, 'entities': []}
        
        with self.driver.session() as session:
            try:
                # 先查询总数
                count_query = """
                MATCH (a:Entity)-[r]->(b)
                WHERE elementId(b) = $element_id
                RETURN count(a) as total
                """
                count_result = session.run(count_query, element_id=element_id)
                total = count_result.single()['total']
                
                # 查询具体节点（限制数量）
                query = """
                MATCH (a:Entity)-[r]->(b)
                WHERE elementId(b) = $element_id
                RETURN a.name as name, elementId(a) as elementId, a.data as data
                LIMIT $limit
                """
                result = session.run(query, element_id=element_id, limit=limit)
                
                entities = []
                for record in result:
                    entity_data = None
                    if record['data']:
                        try:
                            entity_data = json.loads(record['data'])
                        except:
                            entity_data = None
                    
                    entities.append({
                        'name': record['name'],
                        'elementId': record['elementId'],
                        'data': entity_data
                    })
                
                return {
                    'count': total,
                    'entities': entities
                }
            except Exception as e:
                print(f"❌ 获取入边Entity节点时出错: {e}")
                return {'count': 0, 'entities': []}
    
    def get_entity_data_by_element_id(self, element_id):
        """
        获取Entity节点的完整数据
        
        Returns:
            dict: 节点的data字段解析后的字典
        """
        if self.driver is None:
            return None
        
        with self.driver.session() as session:
            try:
                query = """
                MATCH (n:Entity)
                WHERE elementId(n) = $element_id
                RETURN n.data as data
                """
                result = session.run(query, element_id=element_id)
                record = result.single()
                
                if record and record['data']:
                    try:
                        return json.loads(record['data'])
                    except:
                        return None
                return None
            except Exception as e:
                print(f"❌ 获取Entity数据时出错: {e}")
                return None