"""
分类器模块 - 标准 Function Call 实现
"""
import json
from functools import partial
from config import SPECIAL_NODES
from function_call_handler import FunctionCallHandler
from data_loader import format_material_for_prompt
from material_functions import classify_to_subtype, select_instance


def is_special_node(node_info):
    """
    判断是否为特殊节点（需要特殊分类）
    
    Args:
        node_info: 节点信息字典 {name, elementId, properties (可选)}
    
    Returns:
        bool: 是否为特殊节点
    """
    node_name = node_info.get('name', '')
    return node_name in SPECIAL_NODES


def build_classification_tool(parent_name, subtype_info):
    """
    动态构建分类函数定义
    
    Args:
        parent_name: 父节点名称
        subtype_info: 子类型信息 {子类名: {elementId, examples}}
    
    Returns:
        list: tools 定义
    """
    candidates = list(subtype_info.keys())
    
    tool = {
        "type": "function",
        "function": {
            "name": "classify_to_subtype",
            "description": f"将材料分类到 {parent_name} 的某个子类型。此函数会验证分类结果并返回详细信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "subtype": {
                        "type": "string",
                        "enum": candidates,
                        "description": f"选择一个 {parent_name} 的子类型"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "分类理由（根据材料成分、性质等判断）"
                    }
                },
                "required": ["subtype", "reasoning"]
            }
        }
    }
    
    return [tool]


def build_instance_selection_tool(special_node_name, instance_info):
    """
    动态构建实例选择函数定义
    
    Args:
        special_node_name: 特殊节点名称（如"高熵合金"）
        instance_info: 实例信息 {实例名: {elementId, description (可选)}}
    
    Returns:
        list: tools 定义
    """
    candidates = list(instance_info.keys())
    
    # 构建候选描述
    enum_descriptions = []
    for inst_name, info in instance_info.items():
        desc = info.get('description', inst_name)
        enum_descriptions.append(f"{inst_name}: {desc}")
    
    tool = {
        "type": "function",
        "function": {
            "name": "select_instance",
            "description": f"从 {special_node_name} 的具体实例中选择最匹配的一个。此函数会验证选择并返回详细信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance": {
                        "type": "string",
                        "enum": candidates,
                        "description": f"选择最匹配的 {special_node_name} 实例。候选: " + "; ".join(enum_descriptions)
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "选择理由（根据材料成分、性质等判断）"
                    }
                },
                "required": ["instance", "reasoning"]
            }
        }
    }
    
    return [tool]


def classify_material_with_function_call(material_data, parent_name, subtype_info, logger):
    """
    使用标准 Function Call 进行材料分类（两次调用）
    
    Args:
        material_data: 材料数据字典
        parent_name: 父节点名称
        subtype_info: 子类型信息
        logger: 日志记录器
    
    Returns:
        tuple: (分类结果名称, 分类结果elementId, 分类理由) 或 (None, None, None)
    """
    logger.debug(f"开始分类，父节点: {parent_name}")
    
    # 构建 tools
    tools = build_classification_tool(parent_name, subtype_info)
    
    # 构建 messages
    system_prompt = f"""你是材料知识图谱的智能分类器。

当前任务：判断材料属于"{parent_name}"的哪个子类型。

子类型及其例子：
"""
    for subtype_name, info in subtype_info.items():
        system_prompt += f"\n- {subtype_name}"
        if info['examples']:
            examples_str = ', '.join(info['examples'][:5])
            system_prompt += f"\n  例子: {examples_str}"
    
    system_prompt += "\n\n请根据材料的成分、性质和用途进行判断。"
    
    material_str = format_material_for_prompt(material_data)
    user_prompt = f"""请分析以下材料数据：

```json
{material_str}
```

请调用 classify_to_subtype 函数，选择最合适的子类型。
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 准备可执行的函数
    # 使用 partial 绑定参数（注意：函数名必须与 tools 中的 name 一致）
    classify_func = partial(
        classify_to_subtype,
        material_data=material_data,
        parent_name=parent_name,
        subtype_info=subtype_info
    )
    
    available_functions = {
        'classify_to_subtype': classify_func
    }
    
    # 调用标准 function call
    handler = FunctionCallHandler()
    result = handler.call_function_standard(messages, tools, available_functions)
    
    if not result['success']:
        logger.error(f"Function call 失败: {result.get('error')}")
        return None, None, None
    
    # 提取函数执行结果
    func_result = result['result']
    
    if not func_result['success']:
        logger.error(f"分类验证失败: {func_result.get('error')}")
        return None, None, None
    
    classification = func_result['classification']
    element_id = func_result['element_id']
    reasoning = func_result['reasoning']
    
    logger.debug(f"分类成功: {classification}")
    logger.debug(f"理由: {reasoning}")
    logger.debug(f"LLM 最终回答: {result['final_answer']}")
    
    return classification, element_id, reasoning


def select_instance_with_function_call(material_data, special_node_name, 
                                      instance_info, logger):
    """
    使用标准 Function Call 选择具体实例（两次调用）
    
    Args:
        material_data: 材料数据
        special_node_name: 特殊节点名称
        instance_info: 实例信息
        logger: 日志记录器
    
    Returns:
        tuple: (实例名称, elementId, 选择理由) 或 (None, None, None)
    """
    logger.debug(f"开始选择实例，特殊节点: {special_node_name}")
    
    # 构建 tools
    tools = build_instance_selection_tool(special_node_name, instance_info)
    
    # 构建 messages
    system_prompt = f"""你是材料知识图谱的智能分类器。

当前任务：将材料分配到"{special_node_name}"的某个具体实例。

可选实例：
"""
    for inst_name, info in instance_info.items():
        desc = info.get('description', '无详细描述')
        system_prompt += f"\n- {inst_name}: {desc}"
    
    system_prompt += "\n\n请根据材料的成分特征选择最匹配的实例。"
    
    material_str = format_material_for_prompt(material_data)
    user_prompt = f"""请分析以下材料数据：

```json
{material_str}
```

请调用 select_instance 函数，选择最匹配的实例。
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 准备可执行的函数
    select_func = partial(
        select_instance,
        material_data=material_data,
        special_node_name=special_node_name,
        instance_info=instance_info
    )
    
    available_functions = {
        'select_instance': select_func
    }
    
    # 调用标准 function call
    handler = FunctionCallHandler()
    result = handler.call_function_standard(messages, tools, available_functions)
    
    if not result['success']:
        logger.error(f"Function call 失败: {result.get('error')}")
        return None, None, None
    
    # 提取函数执行结果
    func_result = result['result']
    
    if not func_result['success']:
        logger.error(f"实例选择验证失败: {func_result.get('error')}")
        return None, None, None
    
    instance = func_result['selected_instance']
    element_id = func_result['element_id']
    reasoning = func_result['reasoning']
    
    logger.debug(f"选择成功: {instance}")
    logger.debug(f"理由: {reasoning}")
    logger.debug(f"LLM 最终回答: {result['final_answer']}")
    
    return instance, element_id, reasoning