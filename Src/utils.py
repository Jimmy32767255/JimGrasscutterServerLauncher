import sys
import os
import json
import subprocess

IS_WINDOWS = sys.platform == 'win32'

def get_base_path():
    # AppImage 等只读挂载场景下，通过环境变量指定可写数据目录
    appdata_dir = os.environ.get('JGSL_APPDATA_DIR')
    if appdata_dir:
        os.makedirs(appdata_dir, exist_ok=True)
        return appdata_dir
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

def load_jgsl_config():
    """读取并返回 Config/config.json 内容，文件不存在或解析失败时返回空字典。"""
    config_file = os.path.join(BASE_PATH, 'Config', 'config.json')
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger = __import__('loguru').logger
        logger.warning(f'读取配置文件 {config_file} 失败: {e}')
    return {}

def is_java_management_disabled():
    """是否禁用 JGSL 的 Java 管理（启用后使用系统 Java）。"""
    return load_jgsl_config().get('DisableJavaManagement', False)

def is_database_management_disabled():
    """是否禁用 JGSL 的数据库管理（启用后由外部/系统管理 MongoDB）。"""
    return load_jgsl_config().get('DisableDatabaseManagement', False)

BASE_PATH = get_base_path()