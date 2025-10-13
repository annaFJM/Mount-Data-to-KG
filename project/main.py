"""
主程序 - 材料知识图谱自动挂载系统（Function Call 版本）
"""
from config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
    DATA_FILE_PATH, ROOT_ELEMENT_ID, ROOT_NAME,
    MAX_CLASSIFICATION_DEPTH
)
from data_loader import load_all_materials
from neo4j_connector import Neo4jConnector
from classifier import (
    is_special_node, 
    classify_material_with_function_call,
    select_instance_with_function_call
)
from node_mounter import mount_material_node
from logger import MountLogger
from result_writer import ResultWriter


def process_single_material(material_data, material_index, neo4j_conn, logger):
    """
    处理单条材料数据
    
    Args:
        material_data: 材料数据字典
        material_index: 材料索引
        neo4j_conn: Neo4j连接器
        logger: 日志记录器
    
    Returns:
        dict: {success, classification_path, mount_info, error}
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"开始处理材料 #{material_index}")
    logger.info(f"{'='*70}")
    
    # 初始化
    current_element_id = ROOT_ELEMENT_ID
    current_name = ROOT_NAME
    classification_path = [{'name': ROOT_NAME, 'elementId': ROOT_ELEMENT_ID}]
    depth = 0
    
    try:
        # ===== 逻辑1：循环层级分类 =====
        while depth < MAX_CLASSIFICATION_DEPTH:
            depth += 1
            logger.info(f"\n【层级 {depth}】当前节点: {current_name}")
            
            # 检查是否为特殊节点
            node_info = {'name': current_name, 'elementId': current_element_id}
            if is_special_node(node_info):
                logger.info(f"✅ 检测到特殊节点: {current_name}")
                break
            
            # 获取子节点
            children, direction = neo4j_conn.get_children_smart(current_element_id)
            
            if not children:
                # 到达叶子节点
                error_msg = f"节点 '{current_name}' 没有子节点（叶子节点）"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            logger.debug(f"找到 {len(children)} 个子节点（方向: {direction}）")
            
            # 构建分类信息
            subtype_info = neo4j_conn.build_classification_info(
                current_element_id,
                current_name,
                use_inbound_for_examples=(direction == 'inbound')
            )
            
            if not subtype_info:
                error_msg = f"无法获取节点 '{current_name}' 的分类信息"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 调用 function call 分类
            candidates = list(subtype_info.keys())
            classification, element_id, reasoning = classify_material_with_function_call(
                material_data, current_name, subtype_info, logger
            )
            
            if not classification:
                error_msg = f"层级 {depth} 分类失败"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 记录分类结果
            logger.log_classification(depth, current_name, candidates, classification, reasoning)
            
            # 更新当前节点
            current_name = classification
            current_element_id = element_id
            classification_path.append({'name': current_name, 'elementId': current_element_id})
        
        # 检查是否超过最大深度
        if depth >= MAX_CLASSIFICATION_DEPTH:
            error_msg = f"超过最大分类深度 {MAX_CLASSIFICATION_DEPTH}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # ===== 逻辑2：特殊节点实例选择 =====
        logger.info(f"\n【特殊分类】开始为 '{current_name}' 选择具体实例")
        
        # 获取实例信息
        instance_info = neo4j_conn.get_instance_info_with_description(current_element_id)
        
        if not instance_info:
            error_msg = f"特殊节点 '{current_name}' 没有可选实例"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # 调用 function call 选择实例
        candidates = list(instance_info.keys())
        instance_name, instance_element_id, reasoning = select_instance_with_function_call(
            material_data, current_name, instance_info, logger
        )
        
        if not instance_name:
            error_msg = "实例选择失败"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # 记录特殊分类结果
        logger.log_special_classification(current_name, candidates, instance_name, reasoning)
        
        # 更新目标节点
        target_name = instance_name
        target_element_id = instance_element_id
        classification_path.append({'name': target_name, 'elementId': target_element_id})
        
        # ===== 挂载节点 =====
        logger.info(f"\n【挂载】挂载到目标节点: {target_name}")
        
        mount_info = mount_material_node(
            neo4j_conn, material_data, target_element_id, target_name
        )
        
        if not mount_info or not mount_info['success']:
            error_msg = "节点挂载失败"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # 记录挂载结果
        path_names = [node['name'] for node in classification_path]
        logger.log_mount(mount_info['node_name'], target_name, path_names)
        
        return {
            'success': True,
            'classification_path': classification_path,
            'mount_info': mount_info
        }
        
    except Exception as e:
        error_msg = f"处理过程异常: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.debug(traceback.format_exc())
        return {'success': False, 'error': error_msg}


def main():
    """主函数 - 批量处理"""
    
    print("="*70)
    print("材料知识图谱自动挂载系统 (Function Call 版本)")
    print("="*70)
    
    # 初始化日志和结果记录器
    logger = MountLogger()
    result_writer = ResultWriter()
    
    logger.info("系统启动")
    
    # 读取所有材料数据
    logger.info(f"读取数据文件: {DATA_FILE_PATH}")
    all_materials = load_all_materials(DATA_FILE_PATH)
    
    if not all_materials:
        logger.error("未能加载任何材料数据，程序终止")
        return
    
    logger.info(f"共加载 {len(all_materials)} 条材料数据")
    
    # 连接Neo4j
    logger.info("连接Neo4j数据库")
    neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if neo4j_conn.driver is None:
        logger.error("无法连接Neo4j，程序终止")
        return
    
    # 批量处理
    logger.info(f"\n开始批量处理 {len(all_materials)} 条材料数据\n")
    
    for idx, material_data in enumerate(all_materials):
        result = process_single_material(material_data, idx, neo4j_conn, logger)
        
        if result['success']:
            result_writer.add_success_record(
                idx, material_data,
                result['classification_path'],
                result['mount_info']
            )
        else:
            result_writer.add_error_record(idx, material_data, result['error'])
            logger.log_error_record(idx, result['error'])
    
    # 关闭连接
    neo4j_conn.close()
    
    # 保存结果
    logger.info("\n保存结果文件")
    result_writer.save()
    
    # 统计
    total = len(all_materials)
    success = sum(1 for r in result_writer.results if r['status'] == 'success')
    failed = total - success
    
    logger.info(f"\n{'='*70}")
    logger.info(f"处理完成！")
    logger.info(f"  总计: {total} 条")
    logger.info(f"  成功: {success} 条")
    logger.info(f"  失败: {failed} 条")
    logger.info(f"{'='*70}")
    logger.info(f"\n日志文件: {logger.log_file_path}")
    logger.info(f"结果文件: {result_writer.result_file_path}")
    logger.info(f"\n{'='*70}")
    
    print("\n✅ 程序执行完毕")


if __name__ == "__main__":
    main()