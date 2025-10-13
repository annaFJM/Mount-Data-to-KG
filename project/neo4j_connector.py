"""
Neo4j数据库连接器 - 负责所有数据库操作
"""
from neo4j import GraphDatabase
import random


class Neo4jConnector:
    """Neo4j数据库连接和操作类"""
    
    def __init__(self, uri, user, password):
        """
        初始化数据库连接
        
        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
        """
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
    
    def get_child_nodes_by_element_id(self, parent_element_id, use_inbound=False):
        """
        通过elementId获取子节点
        
        Args:
            parent_element_id: 父节点的elementId
            use_inbound: True=使用入边(<-)，False=使用出边(->)
        
        Returns:
            list: 子节点列表，每个元素是字典 {name, elementId}
        """
        if self.driver is None:
            return []
        
        with self.driver.session() as session:
            try:
                if use_inbound:
                    # 使用入边查询
                    query = """
                    MATCH (a)<-[r]-(b)
                    WHERE elementId(a) = $parent_id
                    RETURN b.name as name, elementId(b) as elementId
                    LIMIT 10
                    """
                else:
                    # 使用出边查询
                    query = """
                    MATCH (a)-[r]->(b)
                    WHERE elementId(a) = $parent_id
                    RETURN b.name as name, elementId(b) as elementId
                    LIMIT 10
                    """
                
                result = session.run(query, parent_id=parent_element_id)
                nodes = [{"name": record["name"], "elementId": record["elementId"]} 
                        for record in result]
                return nodes
            except Exception as e:
                print(f"❌ 查询子节点时出错 (elementId={parent_element_id}): {e}")
                return []
    
    def get_children_smart(self, parent_element_id):
        """
        智能获取子节点：优先用出边，如果没结果则用入边
        
        Args:
            parent_element_id: 父节点的elementId
        
        Returns:
            tuple: (子节点列表, 方向类型 'outbound'/'inbound'/'none')
        """
        # 先尝试出边
        children = self.get_child_nodes_by_element_id(parent_element_id, use_inbound=False)
        
        if children:
            return children, 'outbound'
        
        # 出边无结果，尝试入边
        children = self.get_child_nodes_by_element_id(parent_element_id, use_inbound=True)
        
        if children:
            print(f"⚠️  使用入边查询到 {len(children)} 个子节点")
            return children, 'inbound'
        
        return [], 'none'
    
    def build_classification_info(self, parent_element_id, parent_name, use_inbound_for_examples=False):
        """
        构建分类信息：获取父类的所有子类，以及每个子类的例子
        
        Args:
            parent_element_id: 父节点的elementId
            parent_name: 父节点的名称
            use_inbound_for_examples: 查询例子时是否使用入边
        
        Returns:
            dict: {子类名: {elementId, examples}}
        """
        print(f"--- 正在从Neo4j获取 '{parent_name}' 的分类信息 ---")
        
        # 获取所有子类（始终使用出边）
        subtypes = self.get_child_nodes_by_element_id(parent_element_id, use_inbound=False)
        
        if not subtypes:
            print(f"❌ 未找到 '{parent_name}' 的子类")
            return {}
        
        print(f"✅ 找到 {len(subtypes)} 个子类: {', '.join([n['name'] for n in subtypes])}")
        
        # 为每个子类获取例子
        subtype_info = {}
        for subtype in subtypes:
            subtype_name = subtype['name']
            subtype_element_id = subtype['elementId']
            
            # 根据参数决定使用入边还是出边查询例子
            examples = self.get_child_nodes_by_element_id(
                subtype_element_id, 
                use_inbound=use_inbound_for_examples
            )
            
            subtype_info[subtype_name] = {
                'elementId': subtype_element_id,
                'examples': [ex['name'] for ex in examples[:10]]
            }
            
            if subtype_info[subtype_name]['examples']:
                example_str = ', '.join(subtype_info[subtype_name]['examples'][:5])
                if len(subtype_info[subtype_name]['examples']) > 5:
                    example_str += '...'
                print(f"   - {subtype_name}: {example_str}")
            else:
                print(f"   - {subtype_name}: (无例子)")
        
        return subtype_info
    
    def get_instance_info_with_description(self, special_node_element_id):
        """
        获取实例信息（带描述）
        用于特殊分类
        
        Args:
            special_node_element_id: 特殊节点的 elementId
        
        Returns:
            dict: {实例名: {elementId, description}}
        """
        children, direction = self.get_children_smart(special_node_element_id)
        
        instance_info = {}
        for child in children:
            # 构建简单描述（后续可扩展为查询节点属性）
            instance_info[child['name']] = {
                'elementId': child['elementId'],
                'description': f"{child['name']} 材料实例"
            }
        
        return instance_info
    
    def get_random_neighbor_by_name(self, node_name):
        """
        通过节点名称查询，随机选择一个相邻节点（入边）
        （保留此方法以兼容旧代码）
        
        Args:
            node_name: 节点名称
        
        Returns:
            dict: {name, elementId} 或 None
        """
        if self.driver is None:
            return None
        
        with self.driver.session() as session:
            try:
                query = """
                MATCH (a{name: $node_name})<-[r]-(b)
                RETURN b.name as name, elementId(b) as elementId
                """
                
                result = session.run(query, node_name=node_name)
                neighbors = [{"name": record["name"], "elementId": record["elementId"]} 
                            for record in result]
                
                if neighbors:
                    selected = random.choice(neighbors)
                    print(f"✅ 从 '{node_name}' 的 {len(neighbors)} 个相邻节点中随机选择: {selected['name']}")
                    return selected
                else:
                    print(f"❌ 未找到 '{node_name}' 的相邻节点")
                    return None
                    
            except Exception as e:
                print(f"❌ 查询相邻节点时出错: {e}")
                return None