"""
主程序 - 材料知识图谱自动挂载系统（无历史记录版本）
"""
from config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
    DATA_FILE_PATH, ROOT_ELEMENT_ID, ROOT_NAME,
    MAX_CONVERSATION_ROUNDS, ENTITY_SIMILARITY_THRESHOLD
)
from data_loader import load_all_materials, format_material_for_prompt
from neo4j_connector import Neo4jConnector
from classifier import (
    build_tools_for_class_node,
    build_tools_for_entity_selection
)
from function_call_handler import FunctionCallHandler
from logger import MountLogger
from result_writer import ResultWriter


def process_single_material(material_data, material_index, neo4j_conn, logger):
    """
    处理单条材料数据 - 每次调用都是新对话
    
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
    handler = FunctionCallHandler()
    
    # 格式化材料信息
    material_str = format_material_for_prompt(material_data)
    
    for round_num in range(1, MAX_CONVERSATION_ROUNDS + 1):
        logger.info(f"\n【轮次 {round_num}】当前节点: {current_name}")
        
        try:
            labels = neo4j_conn.get_node_labels(current_element_id)
            
            if not labels:
                error_msg = f"无法获取节点 '{current_name}' 的labels"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            if 'Class' in labels:
                logger.debug("当前在Class节点，构建导航工具")
                tools, available_functions, helper_data = build_tools_for_class_node(
                    current_element_id, current_name, neo4j_conn
                )
                
                # 获取是否有出边节点
                outbound_nodes = helper_data.get('outbound_nodes', [])
                
                # 根据是否有子分类，构建不同的 system_prompt
                if outbound_nodes:
                    # 情况1：还有子分类可选
                    logger.debug(f"发现 {len(outbound_nodes)} 个子分类，提示LLM使用 navigate_outbound")
                    
                    system_prompt = f"""你是材料知识图谱的导航助手。

当前位置：{current_name}
状态：🔽 **还有 {len(outbound_nodes)} 个子分类可选**

⚠️ 重要：当前必须调用 navigate_outbound 继续向下分类，不要调用 navigate_inbound。

任务：
1. 仔细阅读每个子分类选项后的【例子】
2. 根据材料特征，选择最匹配的子分类
3. 调用 navigate_outbound 移动到该子分类

材料信息：
{material_str}

请调用 navigate_outbound 函数。"""
                else:
                    # 情况2：已到达叶子节点，没有子分类
                    logger.debug("当前节点是叶子节点（无子分类），提示LLM使用 navigate_inbound")
                    
                    system_prompt = f"""你是材料知识图谱的导航助手。

当前位置：{current_name}
状态：🎯 **已到达分类树的叶子节点（没有更细的子分类）**

下一步：必须调用 navigate_inbound 查看该分类下的具体材料实例（Entity节点）。

任务：
1. 调用 navigate_inbound 查看当前分类下的材料实例
2. 系统会返回可用的Entity节点列表
3. 如果数量较多，会提供相似度搜索功能

材料信息：
{material_str}

请调用 navigate_inbound 函数。"""
                
                messages = [{"role": "user", "content": system_prompt}]
                
            elif 'Entity' in labels:
                # 在Entity节点（理论上不应该到这里）
                logger.debug("当前在Entity节点，只能挂载")
                tools, available_functions = build_tools_for_entity_selection(
                    entities=[{'name': current_name, 'elementId': current_element_id}],
                    need_similarity=False,
                    current_element_id=current_element_id,
                    material_data=material_data,
                    neo4j_conn=neo4j_conn
                )
                
                system_prompt = f"""直接挂载材料到当前Entity节点。

目标节点：{current_name}
材料信息：{material_str}

调用 mount_to_entity 完成挂载。"""

                messages = [{"role": "user", "content": system_prompt}]
            
            else:
                error_msg = f"节点 '{current_name}' 的labels异常: {labels}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 调用LLM（每次都是新对话）
            logger.debug(f"调用LLM，可用函数: {list(available_functions.keys())}")
            result = handler.call_function_standard(
                messages, tools, available_functions, temperature=0
            )
            
            if not result['success']:
                error_msg = f"Function call 失败: {result.get('error')}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 提取函数执行结果
            func_result = result['result']
            function_name = result['function_name']
            
            logger.info(f"✅ 调用函数: {function_name}")
            logger.debug(f"函数返回: {func_result}")
            
            # 根据action处理结果
            action = func_result.get('action')
            
            if action == 'move':
                # 移动到新节点
                new_element_id = func_result['new_element_id']
                new_name = func_result['to_node']
                reasoning = func_result.get('reasoning', '')
                
                logger.info(f"  移动: {current_name} → {new_name}")
                logger.debug(f"  理由: {reasoning}")
                
                # 更新当前位置
                current_element_id = new_element_id
                current_name = new_name
                classification_path.append({'name': current_name, 'elementId': current_element_id})
                
                # 继续下一轮
                continue
            
            elif action == 'no_entities':
                # 当前节点下没有Entity
                logger.warning(f"  ⚠️  节点 '{current_name}' 下没有Entity节点")
                
                # 检查是否有出边Class节点
                outbound_nodes = neo4j_conn.get_outbound_class_nodes(current_element_id)
                
                if outbound_nodes:
                    # 有出边但LLM没看到 - 说明是代码逻辑问题
                    error_msg = f"节点 '{current_name}' 有 {len(outbound_nodes)} 个子分类但未提供给LLM"
                    logger.error(f"  ❌ {error_msg}")
                    logger.debug(f"  子分类: {[n['name'] for n in outbound_nodes]}")
                    return {'success': False, 'error': error_msg}
                else:
                    # 既没有出边也没有Entity - 这是数据问题
                    error_msg = f"节点 '{current_name}' 既没有子分类也没有Entity实例，无法继续"
                    logger.error(f"  ❌ {error_msg}")
                    return {'success': False, 'error': error_msg}
            
            elif action == 'check_entities':
                # 查看Entity节点
                entity_count = func_result['entity_count']
                entities = func_result['entities']
                need_similarity = func_result['need_similarity_search']
                
                logger.info(f"  找到 {entity_count} 个Entity节点")
                
                if entity_count == 0:
                    error_msg = "没有可用的Entity节点"
                    logger.error(error_msg)
                    return {'success': False, 'error': error_msg}
                
                # 如果需要相似度搜索
                if need_similarity:
                    logger.info(f"  Entity数量较多，开始相似度搜索...")
                    
                    # 构建工具（包含相似度搜索）
                    tools_entity, funcs_entity = build_tools_for_entity_selection(
                        entities, need_similarity, current_element_id, material_data, neo4j_conn
                    )
                    
                    # 调用相似度搜索
                    system_prompt_sim = f"""从 {entity_count} 个Entity中筛选top5最相似的材料。

材料信息：{material_str}

调用 get_similar_materials 筛选。"""
                    
                    messages_sim = [{"role": "user", "content": system_prompt_sim}]
                    
                    result_sim = handler.call_function_standard(
                        messages_sim, tools_entity, funcs_entity, temperature=0
                    )
                    
                    if result_sim['success']:
                        func_result_sim = result_sim['result']
                        if func_result_sim.get('action') == 'filter':
                            top5 = func_result_sim['top5']
                            logger.info(f"  相似度筛选完成，top5:")
                            for i, item in enumerate(top5, 1):
                                logger.info(f"    {i}. {item['name']} (相似度: {item['similarity']:.4f})")
                            
                            # 用top5替换entities
                            entities = top5
                            need_similarity = False
                
                # 构建挂载工具（基于筛选后的entities）
                tools_mount, funcs_mount = build_tools_for_entity_selection(
                    entities, False, current_element_id, material_data, neo4j_conn
                )
                
                # 构建Entity选择提示
                entity_list = "\n".join([
                    f"{i}. {e['name']} (ID: {e['elementId']})" + 
                    (f" - 相似度: {e.get('similarity', 0):.4f}" if 'similarity' in e else "")
                    for i, e in enumerate(entities[:10], 1)
                ])
                
                system_prompt_mount = f"""选择最合适的Entity节点进行挂载。

可选Entity节点：
{entity_list}

材料信息：{material_str}

调用 mount_to_entity 完成挂载。请选择最匹配的Entity的elementId。"""
                
                messages_mount = [{"role": "user", "content": system_prompt_mount}]
                
                result_mount = handler.call_function_standard(
                    messages_mount, tools_mount, funcs_mount, temperature=0
                )
                
                if not result_mount['success']:
                    error_msg = f"挂载失败: {result_mount.get('error')}"
                    logger.error(error_msg)
                    return {'success': False, 'error': error_msg}
                
                func_result_mount = result_mount['result']
                
                if func_result_mount.get('action') == 'mount':
                    # 挂载成功！
                    logger.info(f"  ✅ 挂载成功！")
                    logger.info(f"  新节点: {func_result_mount['mounted_node_name']}")
                    logger.info(f"  目标: {func_result_mount['target_name']}")
                    
                    mount_info = {
                        'success': True,
                        'node_id': func_result_mount['mounted_node_id'],
                        'node_name': func_result_mount['mounted_node_name'],
                        'mounted_at': func_result_mount['mounted_at'],
                        'target_name': func_result_mount['target_name'],
                        'target_id': func_result_mount['target_element_id']
                    }
                    
                    # 记录完整路径
                    path_names = [node['name'] for node in classification_path]
                    logger.info(f"  分类路径: {' → '.join(path_names)}")
                    
                    return {
                        'success': True,
                        'classification_path': classification_path,
                        'mount_info': mount_info
                    }
                else:
                    error_msg = "挂载操作未返回mount action"
                    logger.error(error_msg)
                    return {'success': False, 'error': error_msg}
            
            else:
                error_msg = f"未知的action: {action}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
        
        except Exception as e:
            error_msg = f"轮次 {round_num} 异常: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.debug(traceback.format_exc())
            return {'success': False, 'error': error_msg}
    
    # 超过最大轮次
    error_msg = f"超过最大对话轮次 {MAX_CONVERSATION_ROUNDS}"
    logger.error(error_msg)
    return {'success': False, 'error': error_msg}


def main():
    """主函数 - 批量处理"""
    
    print("="*70)
    print("材料知识图谱自动挂载系统 (无历史记录版本)")
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