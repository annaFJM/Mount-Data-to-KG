"""
日志模块 - 记录详细的运行信息
"""
import os
import logging
from datetime import datetime
from config import LOG_DIR, LOG_FILE_PREFIX


class MountLogger:
    """挂载系统的日志记录器"""
    
    def __init__(self, log_dir=LOG_DIR, log_prefix=LOG_FILE_PREFIX):
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 生成日志文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{log_prefix}_{timestamp}.log")
        
        # 配置日志
        self.logger = logging.getLogger("MaterialMount")
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已有的处理器（避免重复）
        self.logger.handlers.clear()
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.log_file_path = log_file
        self.logger.info(f"日志文件已创建: {log_file}")
    
    def info(self, message):
        """记录信息"""
        self.logger.info(message)
    
    def debug(self, message):
        """记录调试信息"""
        self.logger.debug(message)
    
    def warning(self, message):
        """记录警告"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误"""
        self.logger.error(message)
    
    def log_classification(self, depth, parent_name, candidates, result, reasoning):
        """记录分类过程"""
        self.logger.info(f"【层级 {depth}】分类: {parent_name}")
        self.logger.debug(f"  候选: {', '.join(candidates)}")
        self.logger.info(f"  结果: {result}")
        if reasoning:
            self.logger.debug(f"  理由: {reasoning}")
    
    def log_special_classification(self, node_name, candidates, result, reasoning):
        """记录特殊分类"""
        self.logger.info(f"【特殊分类】{node_name}")
        self.logger.debug(f"  候选: {', '.join(candidates)}")
        self.logger.info(f"  结果: {result}")
        if reasoning:
            self.logger.debug(f"  理由: {reasoning}")
    
    def log_mount(self, node_name, target_name, path):
        """记录挂载"""
        self.logger.info(f"【挂载成功】{node_name} → {target_name}")
        self.logger.info(f"  路径: {' → '.join(path)}")
    
    def log_error_record(self, material_index, error_message):
        """记录错误"""
        self.logger.error(f"【处理失败】材料索引 {material_index}: {error_message}")