"""
删除挂载节点模块 - 从文件读取并删除所有测试挂载的节点
"""
import sys
import os

# 添加父目录到路径，以便导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from neo4j_connector import Neo4jConnector
from save_mounted_nodes import get_mounted_nodes, clear_mounted_records


def delete_node_by_element_id(neo4j_conn, element_id, node_name):
    """
    通过elementId删除节点及其关系
    
    Args:
        neo4j_conn: Neo4j连接器实例
        element_id: 节点的elementId
        node_name: 节点名称（用于日志）
    
    Returns:
        bool: 删除是否成功
    """
    if neo4j_conn.driver is None:
        return False
    
    with neo4j_conn.driver.session() as session:
        try:
            # 删除节点及其所有关系
            query = """
            MATCH (n)
            WHERE elementId(n) = $element_id
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            
            result = session.run(query, element_id=element_id)
            record = result.single()
            
            if record and record['deleted_count'] > 0:
                print(f"  ✅ 已删除节点: {node_name} ({element_id})")
                return True
            else:
                print(f"  ⚠️  节点不存在或已删除: {node_name} ({element_id})")
                return False
                
        except Exception as e:
            print(f"  ❌ 删除节点时出错: {e}")
            return False


def delete_all_mounted_nodes(confirm=True):
    """
    删除所有记录的挂载节点
    
    Args:
        confirm: 是否需要用户确认
    
    Returns:
        dict: 删除统计 {total, success, failed}
    """
    print("="*70)
    print("删除测试挂载的节点")
    print("="*70)
    
    # 读取挂载记录
    print("\n【步骤1】读取挂载记录")
    records = get_mounted_nodes()
    
    if not records:
        print("ℹ️  没有需要删除的节点")
        return {'total': 0, 'success': 0, 'failed': 0}
    
    print(f"✅ 找到 {len(records)} 条挂载记录")
    
    # 显示将要删除的节点
    print("\n将要删除的节点：")
    for i, record in enumerate(records, 1):
        print(f"  {i}. {record['node_name']} -> {record['target_name']}")
        if 'classification_path' in record:
            print(f"     路径: {record['classification_path']}")
        print(f"     挂载时间: {record['mounted_at']}")
    
    # 确认删除
    if confirm:
        print("\n" + "="*70)
        response = input("⚠️  确定要删除这些节点吗？(yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ 已取消删除操作")
            return {'total': len(records), 'success': 0, 'failed': 0}
    
    # 连接数据库
    print("\n【步骤2】连接Neo4j数据库")
    neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if neo4j_conn.driver is None:
        print("❌ 无法连接Neo4j，删除失败")
        return {'total': len(records), 'success': 0, 'failed': 0}
    
    # 删除节点
    print("\n【步骤3】删除节点")
    success_count = 0
    failed_count = 0
    
    for i, record in enumerate(records, 1):
        print(f"\n[{i}/{len(records)}] 正在删除: {record['node_name']}")
        
        if delete_node_by_element_id(neo4j_conn, record['node_id'], record['node_name']):
            success_count += 1
        else:
            failed_count += 1
    
    # 关闭数据库连接
    neo4j_conn.close()
    
    # 显示统计
    print("\n" + "="*70)
    print("删除统计：")
    print(f"  总计: {len(records)} 个节点")
    print(f"  成功: {success_count} 个")
    print(f"  失败: {failed_count} 个")
    print("="*70)
    
    # 如果全部删除成功，清空记录文件
    if failed_count == 0:
        print("\n【步骤4】清空挂载记录文件")
        clear_mounted_records()
    else:
        print("\n⚠️  有删除失败的节点，保留记录文件")
    
    return {
        'total': len(records),
        'success': success_count,
        'failed': failed_count
    }


def main():
    """主函数"""
    try:
        stats = delete_all_mounted_nodes(confirm=True)
        
        if stats['success'] > 0:
            print("\n✅ 清理完成！")
        else:
            print("\n⚠️  没有成功删除任何节点")
            
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")


if __name__ == "__main__":
    main()