# -*- coding: utf-8 -*-
from .config import init_logging  # 显式导出函数
__all__ = ['init_logging', 'config', 'loader.py', 'calculator', 'visualizer']

# 在 config.py 末尾添加
__all__ = ['init_logging', 'settings']  # 明确导出对象

# 添加load_config兼容函数（如果主程序需要）
def load_config():
    """兼容旧版调用的包装函数"""
    return settings

