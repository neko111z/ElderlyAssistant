#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
老年人智能出行助手系统入口文件
此文件用于启动Flask应用，是系统的主入口点
"""

import os
import sys

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 将backend目录添加到Python路径
backend_dir = os.path.join(current_dir, 'backend')
sys.path.append(backend_dir)

try:
    # 导入Flask应用
    from app import app
    
    if __name__ == '__main__':
        # 启动应用
        print("正在启动老年人智能出行助手系统...")
        print(f"请访问 http://localhost:8000 使用系统")
        app.run(host='0.0.0.0', port=8000, debug=True)
except ImportError as e:
    print(f"错误: 无法导入应用 - {e}")
    print(f"请确保backend/app.py文件存在并且包含Flask应用")
    sys.exit(1)
except Exception as e:
    print(f"启动应用时出错: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 