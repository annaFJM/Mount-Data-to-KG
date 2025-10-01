"""
主程序 - 材料知识图谱挂载系统
"""
from config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
    DATA_FILE_PATH, ROOT_ELEMENT_ID, ROOT_NAME,
    LAYER_CONFIGS, SPECIAL_NODE_NAME
)
from data_loader import load_material_data
from neo4j_connector import Neo4jConnector
from classifier import classify_material, classify_high_entropy_alloy
from node_mounter import mount_material_node, verify_mounting


def main():
    """主流程"""
    
    print("="*70)
    print("材料知识图谱挂载系统")
    print("="*70)
    
    # 步骤1：读取材料数据
    print("\n【步骤1】读取材料数据")
    print("-"*70)
    material_data = load_material_data(DATA_FILE_PATH)
    
    if material_data is None:
        print("❌ 无法读取材料数据，程序终止")
        return
    
    # 步骤2：连接Neo4j数据库
    print("\n【步骤2】连接Neo4j数据库")
    print("-"*70)
    neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if neo4j_conn.driver is None:
        print("❌ 无法连接Neo4j，程序终止")
        return
    
    # 步骤3：多层分类
    print("\n【步骤3】开始多层分类")
    print("="*70)
    
    # 初始化：从根节点开始
    current_element_id = ROOT_ELEMENT_ID
    current_name = ROOT_NAME
    classification_path = [ROOT_NAME]
    
    # 执行三层分类
    for i, layer_config in enumerate(LAYER_CONFIGS):
        layer_name = layer_config["name"]
        use_inbound = layer_config["use_inbound"]
        
        print(f"\n{'='*70}")
        print(f"{layer_name}分类：{current_name} → 子类型")
        print(f"{'='*70}")
        
        # 获取分类信息
        subtype_info = neo4j_conn.build_classification_info(
            current_element_id, 
            current_name, 
            use_inbound_for_examples=use_inbound
        )
        
        if not subtype_info:
            print(f"❌ 无法获取{layer_name}分类信息，程序终止")
            neo4j_conn.close()
            return
        
        # 进行分类
        classification_result, result_element_id = classify_material(
            material_data, 
            current_name, 
            subtype_info, 
            layer_name
        )
        
        if not classification_result:
            print(f"❌ {layer_name}分类失败，程序终止")
            neo4j_conn.close()
            return
        
        print(f"\n🎯 {layer_name}分类结果: {classification_result}")
        
        # 更新当前节点
        current_name = classification_result
        current_element_id = result_element_id
        classification_path.append(classification_result)
    
    # 步骤4：判断是否需要特殊分类
    print(f"\n{'='*70}")
    print("【步骤4】特殊分类判断")
    print(f"{'='*70}")
    
    if current_name == SPECIAL_NODE_NAME:
        print(f"✅ 检测到特殊节点: {SPECIAL_NODE_NAME}")
        print(f"   执行特殊分类流程...")
        
        # 执行高熵合金特殊分类
        special_result = classify_high_entropy_alloy(neo4j_conn, SPECIAL_NODE_NAME)
        
        if special_result:
            # 更新目标节点为特殊分类结果
            target_name = special_result['name']
            target_element_id = special_result['elementId']
            classification_path.append(target_name)
        else:
            print(f"❌ 特殊分类失败，使用原节点作为挂载目标")
            target_name = current_name
            target_element_id = current_element_id
    else:
        print(f"ℹ️  当前节点 '{current_name}' 不需要特殊分类")
        target_name = current_name
        target_element_id = current_element_id
    
    # 步骤5：挂载新节点
    print(f"\n{'='*70}")
    print("【步骤5】挂载新材料节点")
    print(f"{'='*70}")
    
    mount_info = mount_material_node(
        neo4j_conn, 
        material_data, 
        target_element_id, 
        target_name
    )
    
    if mount_info and mount_info['success']:
        print("\n🎉 材料节点挂载成功！")
        
        # 保存挂载信息到文件（用于后续清理）
        from cleanup.save_mounted_nodes import save_mounted_node
        save_mounted_node(mount_info, classification_path)
        
        # 验证挂载（可选）
        verify_mounting(neo4j_conn, target_element_id, target_name)
    else:
        print("\n❌ 材料节点挂载失败")
    
    # 步骤6：显示完整分类路径
    print(f"\n{'='*70}")
    print("完整分类路径：")
    print(" → ".join(classification_path))
    print(f"{'='*70}\n")
    
    # 关闭数据库连接
    neo4j_conn.close()
    
    print("✅ 程序执行完毕")


if __name__ == "__main__":
    main()