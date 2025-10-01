"""
数据加载模块 - 负责读取和解析材料数据
"""
import json


def load_material_data(file_path, index=0):
    """
    从JSON文件加载材料数据
    
    Args:
        file_path: JSON文件路径
        index: 要读取的数据索引（默认为第一条）
    
    Returns:
        dict: 材料数据字典，失败返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if isinstance(data, list):
                if len(data) > index:
                    print(f"✅ 成功读取材料数据 (索引: {index})")
                    return data[index]
                else:
                    print(f"❌ 数据索引超出范围 (索引: {index}, 总数: {len(data)})")
                    return None
            elif isinstance(data, dict):
                print(f"✅ 成功读取材料数据")
                return data
            else:
                print("❌ JSON格式不符合预期")
                return None
                
    except FileNotFoundError:
        print(f"❌ 文件未找到: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return None
    except Exception as e:
        print(f"❌ 读取数据时发生错误: {e}")
        return None


def format_material_for_prompt(material_data):
    """
    将材料数据格式化为适合Prompt的字符串
    
    Args:
        material_data: 材料数据字典
    
    Returns:
        str: 格式化后的JSON字符串
    """
    return json.dumps(material_data, ensure_ascii=False, indent=2)