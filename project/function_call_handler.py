"""
Function Call 处理模块 - 封装通用的 function calling 逻辑
"""
import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


class FunctionCallHandler:
    """处理 DeepSeek Function Calling 的通用类"""
    
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise ValueError("未找到 DEEPSEEK_API_KEY 环境变量")
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    
    def call_function(self, messages, tools, temperature=0):
        """
        调用 function call
        
        Args:
            messages: 消息列表
            tools: 函数定义列表
            temperature: 温度参数
        
        Returns:
            dict: {success, function_name, arguments, reasoning, raw_response}
        """
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature
            )
            
            message = response.choices[0].message
            
            # 检查是否调用了函数
            if not message.tool_calls:
                return {
                    'success': False,
                    'error': '模型未调用函数',
                    'raw_response': message.content
                }
            
            # 提取第一个函数调用
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            return {
                'success': True,
                'function_name': function_name,
                'arguments': arguments,
                'reasoning': arguments.get('reasoning', ''),
                'raw_response': message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }