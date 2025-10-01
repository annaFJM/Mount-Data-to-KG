"""
分类器模块 - 包含通用分类器和特殊分类器
"""
import json
import openai
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from prompt_generator import build_classification_prompt
from data_loader import format_material_for_prompt


def classify_material(material_data, parent_name, subtype_info, layer_name):
    """
    通用材料分类函数（带自动纠错）
    
    Args:
        material_data: 材料数据字典
        parent_name: 父类名称
        subtype_info: 子类信息 {子类名: {elementId, examples}}
        layer_name: 层级名称（用于日志）
    
    Returns:
        tuple: (分类结果名称, 分类结果elementId) 或 (None, None)
    """
    print(f"\n--- 正在调用DeepSeek API进行{layer_name}分类 ---")
    
    if not DEEPSEEK_API_KEY:
        print("❌ 错误：未找到 DEEPSEEK_API_KEY 环境变量。")
        return None, None
    
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    
    # 构建System Prompt
    system_prompt = build_classification_prompt(parent_name, subtype_info)
    
    # 构建User Prompt
    material_str = format_material_for_prompt(material_data)
    user_prompt = f"""
材料数据：
```json
{material_str}
```

请根据材料数据判断它属于哪个子类型。
"""
    
    # 打印System Prompt
    print("\n========== System Prompt ==========")
    print(system_prompt)
    print("===================================\n")
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    valid_subtypes = list(subtype_info.keys())
    max_retries = 3
    
    for attempt in range(max_retries):
        print(f"   - 正在发送请求 (第{attempt + 1}次)...")
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0,
                max_tokens=100
            )
            
            classification = response.choices[0].message.content.strip()
            print(f"✅ API返回: {classification}")
            
            if classification in valid_subtypes:
                print(f"✅ 验证通过！")
                element_id = subtype_info[classification]['elementId']
                return classification, element_id
            else:
                print(f"⚠️  警告：'{classification}' 不在候选列表中")
                print(f"   候选: {', '.join(valid_subtypes)}")
                
                if attempt < max_retries - 1:
                    messages.append({"role": "assistant", "content": classification})
                    correction_prompt = f"""
你的回答 "{classification}" 不在候选子类型列表中。

候选列表只有：{', '.join(valid_subtypes)}

请必须从上述列表中选择一个，不能回答具体的材料名称或例子。请重新判断。
"""
                    messages.append({"role": "user", "content": correction_prompt})
                    print(f"   - 正在重试...")
                else:
                    print(f"❌ 已达到最大重试次数")
                    return None, None
        except Exception as e:
            print(f"❌ API调用出错: {e}")
            return None, None
    
    return None, None


def classify_high_entropy_alloy(neo4j_conn, node_name="高熵合金"):
    """
    高熵合金特殊分类函数 - 随机选择一个相邻节点
    
    Args:
        neo4j_conn: Neo4j连接器实例
        node_name: 节点名称（默认为"高熵合金"）
    
    Returns:
        dict: {name, elementId} 或 None
    """
    print(f"\n--- 正在对 '{node_name}' 进行特殊分类（随机选择） ---")
    
    selected_node = neo4j_conn.get_random_neighbor_by_name(node_name)
    
    if selected_node:
        print(f"🎯 特殊分类结果: {selected_node['name']}")
        return selected_node
    else:
        print(f"❌ 特殊分类失败")
        return None