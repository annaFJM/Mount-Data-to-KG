import os
import json
import openai  # 用于调用DeepSeek API
from neo4j import GraphDatabase

# Neo4j 配置
NEO4J_URI = "neo4j://10.77.50.200:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "thl123!@#"

class Neo4jConnector:
    """用于处理Neo4j数据库连接和查询的类"""
    def __init__(self, uri, user, password):
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

    def get_child_nodes_by_element_id(self, parent_element_id, use_undirected=False):
        """
        通过elementId获取子节点
        :param parent_element_id: 父节点的elementId
        :param use_undirected: 是否使用无向边（第三层查询例子时使用）
        :return: 返回列表，每个元素是字典 {name, elementId}
        """
        if self.driver is None:
            return []
        
        with self.driver.session() as session:
            try:
                # 根据是否使用无向边选择查询语句
                if use_undirected:
                    query = """
                    MATCH (a)-[r]-(b)
                    WHERE elementId(a) = $parent_id
                    RETURN b.name as name, elementId(b) as elementId
                    LIMIT 10
                    """
                else:
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

    def build_classification_info(self, parent_element_id, parent_name, is_third_layer=False):
        """
        构建分类信息：获取父类的所有子类，以及每个子类的例子
        :param parent_element_id: 父节点的elementId
        :param parent_name: 父节点的名称（用于显示）
        :param is_third_layer: 是否是第三层（第三层查询例子时使用无向边）
        :return: 字典 {子类名: {elementId, examples}}
        """
        print(f"\n--- 正在从Neo4j获取 '{parent_name}' (elementId={parent_element_id}) 的分类信息 ---")
        
        # 第一步：获取所有子类（用有向边）
        subtypes = self.get_child_nodes_by_element_id(parent_element_id, use_undirected=False)
        
        if not subtypes:
            print(f"❌ 未找到 '{parent_name}' 的子类")
            return {}
        
        print(f"✅ 找到 {len(subtypes)} 个子类: {', '.join([n['name'] for n in subtypes])}")
        
        # 第二步：为每个子类获取例子
        subtype_info = {}
        for subtype in subtypes:
            subtype_name = subtype['name']
            subtype_element_id = subtype['elementId']
            
            # 如果是第三层，查询例子时使用无向边
            examples = self.get_child_nodes_by_element_id(
                subtype_element_id, 
                use_undirected=is_third_layer
            )
            
            subtype_info[subtype_name] = {
                'elementId': subtype_element_id,
                'examples': [ex['name'] for ex in examples[:10]]  # 最多10个例子
            }
            
            if subtype_info[subtype_name]['examples']:
                example_str = ', '.join(subtype_info[subtype_name]['examples'][:5])
                if len(subtype_info[subtype_name]['examples']) > 5:
                    example_str += '...'
                print(f"   - {subtype_name}: {example_str}")
            else:
                print(f"   - {subtype_name}: (无例子)")
        
        return subtype_info


def read_material_from_json(file_path):
    """从JSON文件读取第一条材料数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            elif isinstance(data, dict):
                return data
            else:
                print("JSON格式不符合预期")
                return None
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
        return None
    except json.JSONDecodeError:
        print("JSON解析错误")
        return None


def generate_task_description(parent_name, subtype_list):
    """
    调用API生成任务描述
    :param parent_name: 父类名称
    :param subtype_list: 子类列表
    :return: 任务描述字符串
    """
    print(f"\n--- 正在调用API生成任务描述 ---")
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️  未找到API密钥，使用默认任务描述")
        return f"你的任务是判断给定的材料具体属于{parent_name}的哪个子类型。"
    
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    prompt = f"""
请生成一个简洁的任务描述。

背景：材料知识图谱是一个管理了各种材料的层次逻辑关系的树，你是这个智能图谱的节点挂载器。

当前层级：已知材料属于"{parent_name}"
子类型列表：{', '.join(subtype_list)}

请生成"你的任务是..."这部分的描述，要求：
1. 简洁明了，不超过50字
2. 说明需要判断材料属于哪个子类型
3. 只返回任务描述文本，不要其他内容

示例格式：你的任务是判断给定的材料具体属于{parent_name}的哪个子类型。
"""
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
        task_desc = response.choices[0].message.content.strip()
        print(f"✅ 生成的任务描述: {task_desc}")
        return task_desc
    except Exception as e:
        print(f"⚠️  生成任务描述失败: {e}，使用默认描述")
        return f"你的任务是判断给定的材料具体属于{parent_name}的哪个子类型。"


def build_system_prompt(parent_name, subtype_info):
    """根据从Neo4j获取的信息构建system prompt"""
    
    # 固定开头
    prompt = "材料知识图谱是一个管理了各种材料的层次逻辑关系的树，你是这个智能图谱的节点挂载器。\n\n"
    
    # 动态生成任务描述
    subtype_list = list(subtype_info.keys())
    task_desc = generate_task_description(parent_name, subtype_list)
    prompt += task_desc + "\n\n"
    
    prompt += f'已知材料属于"{parent_name}"大类。\n\n'
    prompt += f"请根据材料的成分、性质和用途，从以下{parent_name}子类型中选择一个最合适的分类：\n\n"
    
    # 为每个子类型添加例子
    for subtype_name, info in subtype_info.items():
        prompt += f"- {subtype_name}"
        
        # 添加例子（最多10个）
        examples = info['examples']
        if examples:
            prompt += f"\n  例子：{', '.join(examples)}"
        
        prompt += "\n\n"
    
    prompt += "请只输出子类型名称，不要有其他解释。"
    
    return prompt


def classify_with_retry(material_data, system_prompt, valid_subtypes, layer_name):
    """调用DeepSeek API进行分类，带自动纠错"""
    print(f"\n--- 正在调用DeepSeek API进行{layer_name}分类 ---")
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 错误：未找到 DEEPSEEK_API_KEY 环境变量。")
        return None

    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    material_str = json.dumps(material_data, ensure_ascii=False, indent=2)
    
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
                return classification
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
                    return None
        except Exception as e:
            print(f"❌ API调用出错: {e}")
            return None
    
    return None


def main():
    # 步骤1：读取材料数据
    file_path = "/home/thl/2025Fall/data/method2/high_entropy_alloy.json"
    
    print(f"--- 步骤1：正在从文件读取数据 ---")
    material_data = read_material_from_json(file_path)
    
    if material_data is None:
        print("❌ 无法读取材料数据")
        return
    
    print("✅ 成功读取材料数据")
    
    # 步骤2：连接Neo4j
    conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if conn.driver is None:
        print("❌ 无法连接Neo4j")
        return
    
    # 步骤3：第一层 - 材料
    root_element_id = "4:bf9f3e2f-61c2-430f-be08-580850049dc8:0"
    root_name = "材料"
    
    print("\n" + "="*60)
    print("第一层分类：材料 → 材料类型")
    print("="*60)
    
    layer1_info = conn.build_classification_info(root_element_id, root_name, is_third_layer=False)
    if not layer1_info:
        print("❌ 无法获取第一层分类信息")
        conn.close()
        return
    
    system_prompt_1 = build_system_prompt(root_name, layer1_info)
    valid_types_1 = list(layer1_info.keys())
    
    print(f"\n候选类型: {', '.join(valid_types_1)}")
    classification_1 = classify_with_retry(material_data, system_prompt_1, valid_types_1, "第一层")
    
    if not classification_1:
        print("❌ 第一层分类失败")
        conn.close()
        return
    
    print(f"\n🎯 第一层分类结果: {classification_1}")
    layer1_element_id = layer1_info[classification_1]['elementId']
    
    # 步骤4：第二层 - 金属材料子类型
    print("\n" + "="*60)
    print(f"第二层分类：{classification_1} → 子类型")
    print("="*60)
    
    layer2_info = conn.build_classification_info(layer1_element_id, classification_1, is_third_layer=False)
    if not layer2_info:
        print("❌ 无法获取第二层分类信息")
        conn.close()
        return
    
    system_prompt_2 = build_system_prompt(classification_1, layer2_info)
    valid_types_2 = list(layer2_info.keys())
    
    print(f"\n候选子类型: {', '.join(valid_types_2)}")
    classification_2 = classify_with_retry(material_data, system_prompt_2, valid_types_2, "第二层")
    
    if not classification_2:
        print("❌ 第二层分类失败")
        conn.close()
        return
    
    print(f"\n🎯 第二层分类结果: {classification_2}")
    layer2_element_id = layer2_info[classification_2]['elementId']
    
    # 步骤5：第三层 - 特殊用途金属材料子类型（使用无向边查询例子）
    print("\n" + "="*60)
    print(f"第三层分类：{classification_2} → 具体类型")
    print("="*60)
    
    layer3_info = conn.build_classification_info(
        layer2_element_id, 
        classification_2, 
        is_third_layer=True  # 第三层使用无向边查询例子
    )
    
    if not layer3_info:
        print("❌ 无法获取第三层分类信息")
        conn.close()
        return
    
    system_prompt_3 = build_system_prompt(classification_2, layer3_info)
    valid_types_3 = list(layer3_info.keys())
    
    print(f"\n候选具体类型: {', '.join(valid_types_3)}")
    classification_3 = classify_with_retry(material_data, system_prompt_3, valid_types_3, "第三层")
    
    if classification_3:
        print(f"\n🎯 第三层分类结果: {classification_3}")
        print("\n" + "="*60)
        print("完整分类路径：")
        print(f"{root_name} → {classification_1} → {classification_2} → {classification_3}")
        print("="*60)
    else:
        print("❌ 第三层分类失败")
    
    # 关闭连接
    conn.close()


if __name__ == "__main__":
    main()