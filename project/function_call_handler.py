"""
Function Call 处理模块 - 标准实现（支持对话历史）
"""
import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


class FunctionCallHandler:
    """处理 DeepSeek Function Calling 的标准实现"""
    
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise ValueError("未找到 DEEPSEEK_API_KEY 环境变量")
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    
    def call_function_standard(self, messages, tools, available_functions, temperature=0):
        """
        标准 Function Calling 流程（两次调用，返回更新后的对话历史）
        
        Args:
            messages: 消息列表
            tools: 函数定义列表
            available_functions: 可执行的函数字典 {函数名: 函数对象}
            temperature: 温度参数
        
        Returns:
            dict: {
                success, result, function_name, arguments, 
                final_answer, updated_messages
            }
        """
        try:
            # ===== 第一次调用：让模型决定调用什么函数 =====
            first_response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature
            )
            
            first_message = first_response.choices[0].message
            
            # 检查是否调用了函数
            if not first_message.tool_calls:
                return {
                    'success': False,
                    'error': '模型未调用函数',
                    'raw_response': first_message.content,
                    'updated_messages': messages
                }
            
            # 提取函数调用信息
            tool_call = first_message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # ===== 执行真实的 Python 函数 =====
            if function_name not in available_functions:
                return {
                    'success': False,
                    'error': f'函数 {function_name} 不可用',
                    'updated_messages': messages
                }
            
            function_to_call = available_functions[function_name]
            function_result = function_to_call(**function_args)
            
            # ===== 将函数结果追加到消息历史 =====
            updated_messages = messages.copy()
            updated_messages.append(first_message)  # 添加模型的函数调用消息
            updated_messages.append({
                "role": "tool",
                "content": json.dumps(function_result, ensure_ascii=False),
                "tool_call_id": tool_call.id
            })
            
            # ===== 第二次调用：让模型基于函数结果生成最终答案 =====
            second_response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=updated_messages,
                temperature=temperature
            )
            
            final_message = second_response.choices[0].message
            
            # 将最终回答也加入历史
            updated_messages.append(final_message)
            
            return {
                'success': True,
                'result': function_result,
                'function_name': function_name,
                'arguments': function_args,
                'final_answer': final_message.content,
                'updated_messages': updated_messages,
                'raw_response': final_message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'updated_messages': messages
            }