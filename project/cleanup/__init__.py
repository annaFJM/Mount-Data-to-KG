"""
清理模块 - 用于保存和删除测试挂载的节点
"""

from .save_mounted_nodes import save_mounted_node, get_mounted_nodes, clear_mounted_records

__all__ = ['save_mounted_node', 'get_mounted_nodes', 'clear_mounted_records']