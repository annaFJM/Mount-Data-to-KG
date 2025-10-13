"""
紧急清理脚本 - 直接从 Neo4j 删除指定的节点
用于快速清理已知的挂载节点
"""
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


# 需要删除的节点列表（从日志中提取）
NODES_TO_DELETE = [
    'Material_9f53e9f1b2d2',
    'Material_c71f38ad2ea4',
    'Material_03705ecae9cb',
    'Material_05433c2a9aeb',
    'Material_edd70defb7c5',
    'Material_d656da99927d',
    'Material_1ba78758c40c',
    'Material_6969f6fc23d1'
]


def delete_nodes_directly(node_names):
    """
    直接通过 Neo4j 删除指定节点
    
    Args:
        node_names: 节点名称列表
    
    Returns:
        dict: 删除统计
    """
    print("="*70)
    print("紧急清理 - 直接删除指定节点")
    print("="*70)
    print()
    
    # 连接数据库
    print("连接 Neo4j...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("✅ 连接成功")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return {'success': 0, 'failed': len(node_names)}
    
    print()
    print(f"将要删除 {len(node_names)} 个节点:")
    for i, name in enumerate(node_names, 1):
        print(f"  {i}. {name}")
    print()
    
    # 确认
    response = input("确定要删除吗？(yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ 已取消")
        driver.close()
        return {'success': 0, 'failed': 0}
    
    print()
    print("开始删除...")
    print()
    
    # 删除节点
    success_count = 0
    failed_count = 0
    
    with driver.session() as session:
        for i, node_name in enumerate(node_names, 1):
            print(f"[{i}/{len(node_names)}] 删除: {node_name}")
            
            try:
                query = """
                MATCH (n:Material {name: $node_name})
                DETACH DELETE n
                RETURN count(n) as deleted_count
                """
                
                result = session.run(query, node_name=node_name)
                record = result.single()
                
                if record and record['deleted_count'] > 0:
                    print(f"  ✅ 已删除")
                    success_count += 1
                else:
                    print(f"  ⚠️  节点不存在或已删除")
                    failed_count += 1
                    
            except Exception as e:
                print(f"  ❌ 删除失败: {e}")
                failed_count += 1
    
    # 关闭连接
    driver.close()
    
    # 显示统计
    print()
    print("="*70)
    print("删除统计:")
    print(f"  总计: {len(node_names)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print("="*70)
    
    return {'success': success_count, 'failed': failed_count}


def verify_cleanup():
    """验证清理结果"""
    print()
    print("验证清理结果...")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            query = """
            MATCH (n:Material)
            WHERE n.name STARTS WITH 'Material_'
            RETURN count(n) as count
            """
            
            result = session.run(query)
            record = result.single()
            
            if record:
                count = record['count']
                if count == 0:
                    print("✅ 所有临时节点已清理")
                else:
                    print(f"⚠️  还有 {count} 个 Material_ 节点")
        
        driver.close()
    except Exception as e:
        print(f"❌ 验证失败: {e}")


def main():
    """主函数"""
    print()
    print("本脚本将删除以下节点（从日志中提取）：")
    for name in NODES_TO_DELETE:
        print(f"  - {name}")
    print()
    
    result = delete_nodes_directly(NODES_TO_DELETE)
    
    if result['success'] > 0:
        verify_cleanup()
    
    print()
    print("✅ 清理完成")


if __name__ == "__main__":
    main()