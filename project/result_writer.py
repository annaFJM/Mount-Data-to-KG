"""
结果输出模块 - 生成 JSON 格式的挂载结果
"""
import json
import os
from datetime import datetime
from config import RESULT_DIR, RESULT_FILE_PREFIX


class ResultWriter:
    """挂载结果记录器"""
    
    def __init__(self, result_dir=RESULT_DIR, result_prefix=RESULT_FILE_PREFIX):
        # 创建结果目录
        os.makedirs(result_dir, exist_ok=True)
        
        # 生成结果文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(result_dir, f"{result_prefix}_{timestamp}.json")
        
        self.result_file_path = result_file
        self.results = []
        
        print(f"结果文件将保存到: {result_file}")
    
    def add_success_record(self, material_index, material_data, 
                          classification_path, mount_info):
        """
        添加成功记录
        
        Args:
            material_index: 材料索引
            material_data: 原始材料数据
            classification_path: 分类路径 [{name, elementId}, ...]
            mount_info: 挂载信息 {node_id, node_name, mounted_at, ...}
        """
        record = {
            'status': 'success',
            'material_index': material_index,
            'timestamp': datetime.now().isoformat(),
            'classification_path': [
                {
                    'name': node['name'],
                    'element_id': node['elementId']
                }
                for node in classification_path
            ],
            'mounted_node': {
                'name': mount_info['node_name'],
                'element_id': mount_info['node_id'],
                'mounted_at': mount_info['mounted_at'],
                'data': material_data  # 完整的原始数据
            },
            'target_node': {
                'name': mount_info['target_name'],
                'element_id': mount_info['target_id']
            }
        }
        self.results.append(record)
    
    def add_error_record(self, material_index, material_data, error_message):
        """添加错误记录"""
        record = {
            'status': 'error',
            'material_index': material_index,
            'timestamp': datetime.now().isoformat(),
            'error': error_message,
            'material_data': material_data
        }
        self.results.append(record)
    
    def save(self):
        """保存结果到文件"""
        try:
            summary = {
                'total': len(self.results),
                'success': sum(1 for r in self.results if r['status'] == 'success'),
                'failed': sum(1 for r in self.results if r['status'] == 'error'),
                'generated_at': datetime.now().isoformat(),
                'results': self.results
            }
            
            with open(self.result_file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ 结果已保存到: {self.result_file_path}")
            return True
        except Exception as e:
            print(f"\n❌ 保存结果失败: {e}")
            return False