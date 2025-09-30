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

    def get_child_nodes_by_element_id(self, parent_element_id):
        """
        通过elementId获取子节点
        :param parent_element_id: 父节点的elementId
        :return: 返回列表，每个元素是字典 {name, elementId}
        """
        if self.driver is None:
            return []
        
        with self.driver.session() as session:
            try:
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

    def build_classification_info(self, parent_element_id, parent_name):
        """
        构建分类信息：获取父类的所有子类，以及每个子类的例子
        :param parent_element_id: 父节点的elementId
        :param parent_name: 父节点的名称（用于显示）
        :return: 字典 {子类名: {elementId, examples}}
        """
        print(f"\n--- 正在从Neo4j获取 '{parent_name}' (elementId={parent_element_id}) 的分类信息 ---")
        
        # 第一步：获取所有子类
        subtypes = self.get_child_nodes_by_element_id(parent_element_id)
        
        if not subtypes:
            print(f"❌ 未找到 '{parent_name}' 的子类")
            return {}
        
        print(f"✅ 找到 {len(subtypes)} 个子类: {', '.join([n['name'] for n in subtypes])}")
        
        # 第二步：为每个子类获取例子（最多10个）
        subtype_info = {}
        for subtype in subtypes:
            subtype_name = subtype['name']
            subtype_element_id = subtype['elementId']
            
            examples = self.get_child_nodes_by_element_id(subtype_element_id)
            
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

当前层级：{parent_name}
子类型列表：{', '.join(subtype_list)}

请生成"你的任务是..."这部分的描述，要求：
1. 简洁明了，不超过50字
2. 说明需要判断材料属于哪个子类型
3. 只返回任务描述文本，不要其他内容

示例格式：你的任务是判断给定的材料具体属于哪个材料类型。
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
        return f"你的任务是判断给定的材料具体属于哪个材料类型。"


def build_system_prompt(parent_name, subtype_info):
    """根据从Neo4j获取的信息构建system prompt"""
    
    # 固定开头
    prompt = "材料知识图谱是一个管理了各种材料的层次逻辑关系的树，你是这个智能图谱的节点挂载器。\n\n"
    
    # 动态生成任务描述
    subtype_list = list(subtype_info.keys())
    task_desc = generate_task_description(parent_name, subtype_list)
    prompt += task_desc + "\n\n"
    
    prompt += "请根据材料的性质和用途，从以下材料类型中选择一个最合适的分类：\n\n"
    
    # 为每个类型添加例子
    for material_type, info in subtype_info.items():
        prompt += f"- {material_type}"
        
        # 添加例子（最多10个）
        examples = info['examples']
        if examples:
            example_list = examples[:10]
            prompt += f"\n  例子：{', '.join(example_list)}"
        
        prompt += "\n\n"
    
    prompt += "请只输出材料类型名称，不要有其他解释。"
    
    return prompt


def classify_material(material_data, system_prompt, valid_types):
    """调用DeepSeek API进行材料分类，带自动纠错"""
    print("\n--- 正在调用DeepSeek API进行材料分类 ---")
    
    # 从环境变量获取API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 错误：未找到 DEEPSEEK_API_KEY 环境变量。")
        print("   请先设置密钥：export DEEPSEEK_API_KEY='your-api-key'")
        return None

    # 创建OpenAI客户端
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    # 将材料数据格式化为JSON字符串
    material_str = json.dumps(material_data, ensure_ascii=False, indent=2)
    
    # 构建用户提示词
    user_prompt = f"""
材料数据：
```json
{material_str}
```

请根据材料数据判断它属于哪个材料类型。
"""
    
    # 打印System Prompt
    print("\n========== System Prompt ==========")
    print(system_prompt)
    print("===================================\n")
    
    # 构建消息历史
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    max_retries = 3  # 最多重试3次
    
    for attempt in range(max_retries):
        print(f"   - 正在发送请求到DeepSeek API (第{attempt + 1}次)...")
        
        try:
            # 发起API调用
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0,
                max_tokens=100
            )
            
            classification = response.choices[0].message.content.strip()
            print(f"✅ API返回: {classification}")
            
            # 验证返回结果是否在有效列表中
            if classification in valid_types:
                print(f"✅ 验证通过！分类结果在候选列表中。")
                return classification
            else:
                print(f"⚠️  警告：返回结果 '{classification}' 不在候选列表中")
                print(f"   候选列表: {', '.join(valid_types)}")
                
                if attempt < max_retries - 1:
                    # 添加助手回复和纠正消息到对话历史
                    messages.append({"role": "assistant", "content": classification})
                    
                    correction_prompt = f"""
你的回答 "{classification}" 不在候选材料类型列表中。

候选材料类型列表只有以下选项：
{', '.join(valid_types)}

请注意：你必须从上述列表中选择一个，而不能回答具体的材料名称或例子。

请重新判断该材料属于哪个材料类型，只输出材料类型名称。
"""
                    messages.append({"role": "user", "content": correction_prompt})
                    print(f"   - 正在重试，要求从候选列表中选择...")
                else:
                    print(f"❌ 已达到最大重试次数，仍未得到有效结果")
                    return None
        
        except Exception as e:
            print(f"❌ 调用DeepSeek API时出错: {e}")
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
    
    # 步骤2：连接Neo4j并获取分类信息
    conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if conn.driver is None:
        print("❌ 无法连接Neo4j，终止程序")
        return
    
    # 使用已知的"材料"节点的elementId
    root_element_id = "4:bf9f3e2f-61c2-430f-be08-580850049dc8:0"
    root_name = "材料"
    
    # 获取"材料"的所有子类型及其例子
    subtype_info = conn.build_classification_info(root_element_id, root_name)
    
    if not subtype_info:
        print("❌ 无法获取分类信息")
        conn.close()
        return
    
    # 步骤3：构建system prompt
    system_prompt = build_system_prompt(root_name, subtype_info)
    
    # 步骤4：进行分类
    print("\n待分类材料数据:")
    print(json.dumps(material_data, ensure_ascii=False, indent=2))
    
    valid_types = list(subtype_info.keys())
    print(f"\n候选材料类型: {', '.join(valid_types)}")
    
    classification = classify_material(material_data, system_prompt, valid_types)
    
    # 步骤5：输出结果
    if classification:
        print(f"\n🎯 分类结果: {classification}")
    else:
        print("\n❌ 分类失败")
    
    # 关闭Neo4j连接
    conn.close()


if __name__ == "__main__":
    main()