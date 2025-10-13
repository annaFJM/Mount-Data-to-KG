"""
删除挂载节点模块 - 从 result 文件读取并删除所有挂载的节点
支持：
1. 从 cleanup/new_data1.json 读取（旧版兼容）
2. 从 results/*.json 读取（新版推荐）
3. 删除日志保存到 results/ 文件夹
"""
import sys
import os
import json
from datetime import datetime

# 添加父目录到路径，以便导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from neo4j_connector import Neo4jConnector
from cleanup.save_mounted_nodes import get_mounted_nodes, clear_mounted_records, extract_nodes_from_result_file


class CleanupLogger:
    """清理日志记录器"""
    
    def __init__(self, log_dir='results'):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"cleanup_log_{timestamp}.txt")
        self.logs = []
    
    def log(self, message, print_console=True):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        self.logs.append(log_line)
        if print_console:
            print(message)
    
    def save(self):
        """保存日志到文件"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.logs))
            print(f"\n📝 删除日志已保存到: {self.log_file}")
            return True
        except Exception as e:
            print(f"❌ 保存日志失败: {e}")
            return False


def delete_node_by_element_id(neo4j_conn, element_id, node_name, logger):
    """
    通过elementId删除节点及其关系
    
    Args:
        neo4j_conn: Neo4j连接器实例
        element_id: 节点的elementId
        node_name: 节点名称（用于日志）
        logger: 日志记录器
    
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
                msg = f"  ✅ 已删除节点: {node_name} (ID: {element_id})"
                logger.log(msg)
                return True
            else:
                msg = f"  ⚠️  节点不存在或已删除: {node_name} (ID: {element_id})"
                logger.log(msg)
                return False
                
        except Exception as e:
            msg = f"  ❌ 删除节点时出错: {e}"
            logger.log(msg)
            return False


def find_latest_result_file():
    """查找最新的 result 文件"""
    result_dir = 'results'
    if not os.path.exists(result_dir):
        return None
    
    result_files = [
        f for f in os.listdir(result_dir) 
        if f.startswith('mount_result_') and f.endswith('.json')
    ]
    
    if not result_files:
        return None
    
    # 按时间排序，取最新的
    result_files.sort(reverse=True)
    return os.path.join(result_dir, result_files[0])


def delete_nodes_from_result_file(result_file_path, confirm=True):
    """
    从 result 文件读取并删除节点
    
    Args:
        result_file_path: result 文件路径
        confirm: 是否需要确认
    
    Returns:
        dict: 删除统计
    """
    logger = CleanupLogger()
    
    logger.log("="*70)
    logger.log(f"从 Result 文件删除挂载节点")
    logger.log("="*70)
    logger.log("")
    
    # 提取节点信息
    logger.log(f"【步骤1】读取 Result 文件")
    logger.log(f"文件路径: {result_file_path}")
    
    nodes = extract_nodes_from_result_file(result_file_path)
    
    if not nodes:
        logger.log("ℹ️  没有需要删除的节点")
        logger.save()
        return {'total': 0, 'success': 0, 'failed': 0}
    
    logger.log(f"✅ 找到 {len(nodes)} 个挂载节点")
    logger.log("")
    
    # 显示节点信息
    logger.log("将要删除的节点：")
    for i, node in enumerate(nodes, 1):
        logger.log(f"  {i}. {node['node_name']}")
        logger.log(f"     目标: {node['target_name']}")
        logger.log(f"     路径: {node['classification_path']}")
        logger.log(f"     ID: {node['node_id']}")
    
    # 确认删除
    if confirm:
        logger.log("")
        logger.log("="*70)
        response = input("⚠️  确定要删除这些节点吗？(yes/no): ")
        logger.log(f"用户输入: {response}", print_console=False)
        
        if response.lower() not in ['yes', 'y']:
            logger.log("❌ 已取消删除操作")
            logger.save()
            return {'total': len(nodes), 'success': 0, 'failed': 0}
    
    # 连接数据库
    logger.log("")
    logger.log("【步骤2】连接Neo4j数据库")
    neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if neo4j_conn.driver is None:
        logger.log("❌ 无法连接Neo4j，删除失败")
        logger.save()
        return {'total': len(nodes), 'success': 0, 'failed': 0}
    
    # 删除节点
    logger.log("")
    logger.log("【步骤3】删除节点")
    success_count = 0
    failed_count = 0
    
    for i, node in enumerate(nodes, 1):
        logger.log(f"\n[{i}/{len(nodes)}] 正在删除: {node['node_name']}")
        
        if delete_node_by_element_id(neo4j_conn, node['node_id'], node['node_name'], logger):
            success_count += 1
        else:
            failed_count += 1
    
    # 关闭数据库连接
    neo4j_conn.close()
    
    # 显示统计
    logger.log("")
    logger.log("="*70)
    logger.log("删除统计：")
    logger.log(f"  总计: {len(nodes)} 个节点")
    logger.log(f"  成功: {success_count} 个")
    logger.log(f"  失败: {failed_count} 个")
    logger.log("="*70)
    
    # 保存删除记录
    logger.log("")
    logger.log("【步骤4】保存删除记录")
    save_deletion_record(result_file_path, nodes, success_count, failed_count, logger)
    
    # 保存日志
    logger.save()
    
    return {
        'total': len(nodes),
        'success': success_count,
        'failed': failed_count
    }


def save_deletion_record(result_file_path, nodes, success_count, failed_count, logger):
    """
    保存删除记录到 results 文件夹
    
    Args:
        result_file_path: 原 result 文件路径
        nodes: 节点列表
        success_count: 成功数量
        failed_count: 失败数量
        logger: 日志记录器
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        deletion_file = f"results/deletion_record_{timestamp}.json"
        
        record = {
            'deleted_at': datetime.now().isoformat(),
            'source_file': result_file_path,
            'total': len(nodes),
            'success': success_count,
            'failed': failed_count,
            'deleted_nodes': nodes
        }
        
        with open(deletion_file, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        logger.log(f"✅ 删除记录已保存到: {deletion_file}")
        
    except Exception as e:
        logger.log(f"⚠️  保存删除记录失败: {e}")


def delete_all_mounted_nodes(confirm=True):
    """
    删除所有记录的挂载节点（兼容旧版本）
    从 cleanup/new_data1.json 读取
    
    Args:
        confirm: 是否需要用户确认
    
    Returns:
        dict: 删除统计 {total, success, failed}
    """
    logger = CleanupLogger()
    
    logger.log("="*70)
    logger.log("删除测试挂载的节点（从 cleanup 文件）")
    logger.log("="*70)
    
    # 读取挂载记录
    logger.log("\n【步骤1】读取挂载记录")
    records = get_mounted_nodes()
    
    if not records:
        logger.log("ℹ️  没有需要删除的节点")
        logger.save()
        return {'total': 0, 'success': 0, 'failed': 0}
    
    logger.log(f"✅ 找到 {len(records)} 条挂载记录")
    
    # 显示将要删除的节点
    logger.log("\n将要删除的节点：")
    for i, record in enumerate(records, 1):
        logger.log(f"  {i}. {record['node_name']} -> {record['target_name']}")
        if 'classification_path' in record:
            logger.log(f"     路径: {record['classification_path']}")
        logger.log(f"     挂载时间: {record['mounted_at']}")
    
    # 确认删除
    if confirm:
        logger.log("\n" + "="*70)
        response = input("⚠️  确定要删除这些节点吗？(yes/no): ")
        logger.log(f"用户输入: {response}", print_console=False)
        
        if response.lower() not in ['yes', 'y']:
            logger.log("❌ 已取消删除操作")
            logger.save()
            return {'total': len(records), 'success': 0, 'failed': 0}
    
    # 连接数据库
    logger.log("\n【步骤2】连接Neo4j数据库")
    neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if neo4j_conn.driver is None:
        logger.log("❌ 无法连接Neo4j，删除失败")
        logger.save()
        return {'total': len(records), 'success': 0, 'failed': 0}
    
    # 删除节点
    logger.log("\n【步骤3】删除节点")
    success_count = 0
    failed_count = 0
    
    for i, record in enumerate(records, 1):
        logger.log(f"\n[{i}/{len(records)}] 正在删除: {record['node_name']}")
        
        if delete_node_by_element_id(neo4j_conn, record['node_id'], record['node_name'], logger):
            success_count += 1
        else:
            failed_count += 1
    
    # 关闭数据库连接
    neo4j_conn.close()
    
    # 显示统计
    logger.log("\n" + "="*70)
    logger.log("删除统计：")
    logger.log(f"  总计: {len(records)} 个节点")
    logger.log(f"  成功: {success_count} 个")
    logger.log(f"  失败: {failed_count} 个")
    logger.log("="*70)
    
    # 如果全部删除成功，清空记录文件
    if failed_count == 0:
        logger.log("\n【步骤4】清空挂载记录文件")
        clear_mounted_records()
    else:
        logger.log("\n⚠️  有删除失败的节点，保留记录文件")
    
    # 保存日志
    logger.save()
    
    return {
        'total': len(records),
        'success': success_count,
        'failed': failed_count
    }


def main():
    """主函数"""
    print("\n材料知识图谱 - 节点清理工具")
    print("="*70)
    
    # 检查是否有命令行参数指定 result 文件
    if len(sys.argv) > 1:
        result_file = sys.argv[1]
        print(f"\n使用指定的 result 文件: {result_file}")
    else:
        # 查找最新的 result 文件
        result_file = find_latest_result_file()
        
        if result_file:
            print(f"\n找到最新的 result 文件: {result_file}")
            print("\n选择删除模式：")
            print("  1. 从 result 文件删除（推荐）")
            print("  2. 从 cleanup 文件删除（旧版兼容）")
            
            choice = input("\n请选择 (1/2，默认1): ").strip()
            
            if choice == '2':
                result_file = None
        else:
            print("\n⚠️  未找到 result 文件，将使用 cleanup 文件")
            result_file = None
    
    try:
        if result_file:
            # 从 result 文件删除
            stats = delete_nodes_from_result_file(result_file, confirm=True)
        else:
            # 从 cleanup 文件删除（旧版）
            stats = delete_all_mounted_nodes(confirm=True)
        
        if stats['success'] > 0:
            print("\n✅ 清理完成！")
        else:
            print("\n⚠️  没有成功删除任何节点")
            
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()