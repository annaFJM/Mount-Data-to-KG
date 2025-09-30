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

    def get_child_nodes(self, parent_name):
        """获取指定节点的所有子节点名称"""
        if self.driver is None:
            return []
        
        with self.driver.session() as session:
            try:
                query = f"MATCH (a{{name: '{parent_name}'}})-[r]->(b) RETURN b.name"
                result = session.run(query)
                child_names = [record["b.name"] for record in result]
                return child_names
            except Exception as e:
                print(f"❌ 查询子节点时出错 (parent={parent_name}): {e}")
                return []

    def build_classification_info(self, parent_category):
        """
        构建分类信息：获取父类的所有子类，以及每个子类的例子
        返回字典: {子类名: [例子列表]}
        """
        print(f"\n--- 正在从Neo4j获取 '{parent_category}' 的分类信息 ---")
        
        # 第一步：获取所有子类
        subtypes = self.get_child_nodes(parent_category)
        
        if not subtypes:
            print(f"❌ 未找到 '{parent_category}' 的子类")
            return {}
        
        print(f"✅ 找到 {len(subtypes)} 个子类: {', '.join(subtypes)}")
        
        # 第二步：为每个子类获取例子
        subtype_examples = {}
        for subtype in subtypes:
            examples = self.get_child_nodes(subtype)
            subtype_examples[subtype] = examples
            if examples:
                print(f"   - {subtype}: {', '.join(examples)}")
            else:
                print(f"   - {subtype}: (无例子)")
        
        return subtype_examples


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


def build_system_prompt(subtype_examples):
    """根据从Neo4j获取的信息构建system prompt"""
    
    prompt = """材料知识图谱是一个管理了各种材料的层次逻辑关系的树，你是这个智能图谱的节点挂载器。

已知给定的材料属于"金属材料"大类，你的任务是判断该材料具体属于金属材料的哪个子类型。

请根据材料的成分、性质和用途，从以下金属材料子类型中选择一个最合适的分类：

"""
    
    # 为每个子类型添加描述和例子
    descriptions = {
        "钢铁": "主要由铁和碳组成的合金",
        "有色金属材料": "铁以外的金属及其合金（如铜、铝、镁、钛等）",
        "金属功能材料": "具有特殊物理、化学或生物功能的金属材料",
        "特殊用途金属材料": "用于特定应用场景的金属材料",
        "粉末冶金材料": "通过粉末冶金工艺制造的金属材料"
    }
    
    for subtype, examples in subtype_examples.items():
        # 添加子类型名称和描述
        desc = descriptions.get(subtype, "")
        prompt += f"- {subtype}"
        if desc:
            prompt += f"：{desc}"
        
        # 添加例子
        if examples:
            prompt += f"\n  例子：{', '.join(examples)}"
        
        prompt += "\n\n"
    
    prompt += "请只输出子类型名称，不要有其他解释。"
    
    return prompt


def classify_metal_subtype(material_data, system_prompt, valid_subtypes):
    """调用DeepSeek API进行金属材料子类型分类，带自动纠错"""
    print("\n--- 正在调用DeepSeek API进行金属材料子类型分类 ---")
    
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

已知该材料属于"金属材料"大类。

请根据材料数据判断它属于金属材料的哪个子类型。
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
            if classification in valid_subtypes:
                print(f"✅ 验证通过！分类结果在候选列表中。")
                return classification
            else:
                print(f"⚠️  警告：返回结果 '{classification}' 不在候选列表中")
                print(f"   候选列表: {', '.join(valid_subtypes)}")
                
                if attempt < max_retries - 1:
                    # 添加助手回复和纠正消息到对话历史
                    messages.append({"role": "assistant", "content": classification})
                    
                    correction_prompt = f"""
你的回答 "{classification}" 不在候选子类型列表中。

候选子类型列表只有以下选项：
{', '.join(valid_subtypes)}

请注意：你必须从上述列表中选择一个，而不能回答具体的材料名称或例子。

请重新判断该材料属于哪个子类型，只输出子类型名称。
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
    
    # 获取金属材料的子类型及其例子
    subtype_examples = conn.build_classification_info("金属材料")
    
    if not subtype_examples:
        print("❌ 无法获取分类信息")
        conn.close()
        return
    
    # 步骤3：构建system prompt
    system_prompt = build_system_prompt(subtype_examples)
    
    # 步骤4：进行分类
    print("\n待分类材料数据:")
    print(json.dumps(material_data, ensure_ascii=False, indent=2))
    print(f"\n已知材料大类: 金属材料")
    
    valid_subtypes = list(subtype_examples.keys())
    print(f"候选子类型: {', '.join(valid_subtypes)}")
    
    classification = classify_metal_subtype(material_data, system_prompt, valid_subtypes)
    
    # 步骤5：输出结果
    if classification:
        print(f"\n🎯 金属材料子类型分类结果: {classification}")
    else:
        print("\n❌ 分类失败")
    
    # 关闭Neo4j连接
    conn.close()


if __name__ == "__main__":
    main()