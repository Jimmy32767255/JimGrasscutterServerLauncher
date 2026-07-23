import sys
import os
import subprocess

IS_WINDOWS = sys.platform == 'win32'

def get_base_path():
    if getattr(sys, 'frozen', False):
        # 打包后，sys.executable 是程序文件路径
        return os.path.dirname(sys.executable)
    else:
        # 未打包时，__file__ 是当前.py文件路径
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_java_executable_name():
    """返回当前平台下的 Java 可执行文件名。"""
    return 'java.exe' if IS_WINDOWS else 'java'

def get_mongod_executable_name():
    """返回当前平台下的 MongoDB 可执行文件名。"""
    return 'mongod.exe' if IS_WINDOWS else 'mongod'

def is_java_process(name: str) -> bool:
    """判断进程名是否为 Java 进程（兼容 Windows/Linux/macOS）。"""
    return bool(name) and name.lower().startswith('java')

def is_mongod_process(name: str) -> bool:
    """判断进程名是否为 MongoDB 进程（兼容 Windows/Linux/macOS）。"""
    return bool(name) and name.lower().startswith('mongod')

def get_invalid_filename_chars():
    """返回当前平台下文件/文件夹名称不允许使用的字符列表。"""
    if IS_WINDOWS:
        return ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    return ['/']

def get_creationflags():
    """返回适用于当前平台的 subprocess 创建标志（Windows 隐藏控制台窗口）。"""
    if IS_WINDOWS:
        return subprocess.CREATE_NO_WINDOW
    return 0

BASE_PATH = get_base_path()