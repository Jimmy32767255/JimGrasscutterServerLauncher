import sys
import os

def get_base_path():
    if getattr(sys, 'frozen', False):
        # 打包后，sys.executable 是exe文件路径
        return os.path.dirname(sys.executable)
    else:
        # 未打包时，__file__ 是当前.py文件路径
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_PATH = get_base_path()