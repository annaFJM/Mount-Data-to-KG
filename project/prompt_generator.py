"""
Prompt生成模块 - 负责生成各种分类任务的Prompt
"""
import openai
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


def generate_task_description(parent_name, subtype_list):
    """
    调用API生成任务描述
    
    Args:
        parent_name: 父类名称
        subtype_list: 子类列表
    
    Returns:
        str: 任务描述字符串
    """
    print(f"\n--- 正在调用API生成任务描述 ---")
    
    if not DEEPSEEK_API_KEY:
        print("⚠️  未找到API密钥，使用默认任务描述")
        return f"你的任务是判断给定的材料具体属于{parent_name}的哪个子类型。"
    
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    
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


def build_classification_prompt(parent_name, subtype_info):
    """
    构建完整的分类System Prompt
    
    Args:
        parent_name: 父类名称
        subtype_info: 子类信息字典 {子类名: {elementId, examples}}
    
    Returns:
        str: 完整的System Prompt
    """
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
        
        examples = info['examples']
        if examples:
            prompt += f"\n  例子：{', '.join(examples)}"
        
        prompt += "\n\n"
    
    prompt += "请只输出子类型名称，不要有其他解释。"
    
    return prompt