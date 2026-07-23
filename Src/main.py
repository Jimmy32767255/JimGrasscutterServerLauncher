import os
import sys
import json
import signal
import webbrowser
import os
from loguru import logger
from PyQt5.QtCore import Qt, QTranslator
from main_window import MainWindow
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QMessageBox
from update_checker import UpdateCheckThread, VERSION
from utils import get_base_path

# 切换工作目录到基础路径
BASE_PATH = get_base_path()
os.chdir(BASE_PATH)

# 全局翻译器实例
g_translator = None
g_app = None

def main():
    def load_font_async(font_path):
        try:
            if not os.path.exists(font_path):
                raise FileNotFoundError(f"字体文件 {font_path} 不存在")

            if not os.access(font_path, os.R_OK):
                raise PermissionError(f"字体文件 {font_path} 不可读")

            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id == -1:
                raise ValueError(f"字体文件 {font_path} 无效或损坏")

            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if not font_families:
                raise ValueError(f"字体文件 {font_path} 不包含有效字体")

            return font_families[0]
        except Exception as e:
            logger.warning(f"字体加载失败: {e}")
            return "Arial"

    font_path = r"./Assets/HanYiWenHei-85W-Heavy.ttf"
    global g_app
    g_app = QApplication(sys.argv)

    # 设置应用程序属性以支持高DPI
    g_app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # 使用高DPI图像
    g_app.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # 启用高DPI缩放

    # 加载翻译
    load_translator(g_app)

    # 初始化 ThemeManager
    from theme_manager import ThemeManager
    theme_manager = ThemeManager(g_app.tr)

    # 加载字体
    font_family = load_font_async(font_path)
    font = QFont(font_family)
    font.setPointSize(10)
    g_app.setFont(font)

    # 创建并显示主窗口
    window = MainWindow(theme_manager)
    window.show()

    # 在主窗口显示后，应用初始主题配置
    theme_manager.apply_initial_theme_to_window(window)

    # 在显示主窗口后检查更新
    check_for_updates_on_startup()

    signal.signal(signal.SIGINT, lambda s, f: window.cleanup_and_exit())
    sys.exit(g_app.exec_())

# 更新检查
def load_translator(app):
    global g_translator
    if g_translator:
        app.removeTranslator(g_translator)
        g_translator = None

    config_file = os.path.join(BASE_PATH, 'Config', 'config.json')
    lang = 'zh_CN' # 默认语言
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            lang = config_data.get('Language', 'zh_CN')
    except Exception as e:
        logger.warning(f"读取配置文件时出错，使用默认语言zh_CN: {e}")

    translator = QTranslator()
    # 假设翻译文件在 Translations 目录下，命名为 JimGrasscutterServerLauncher_xx_YY.qm
    qm_file = os.path.join(BASE_PATH, 'Translations', f'JimGrasscutterServerLauncher_{lang}.qm')
    
    if translator.load(qm_file):
        app.installTranslator(translator)
        g_translator = translator
        logger.info(f"成功加载翻译文件: {qm_file}")
    else:
        logger.warning(f"无法加载翻译文件: {qm_file}，使用默认语言")

def check_for_updates_on_startup():
    # 读取配置文件检查是否启用自动更新
    config_file = os.path.join(BASE_PATH, 'Config', 'config.json')
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            if not config_data.get('AutoUpdate', True):
                logger.info("自动更新已禁用，跳过启动时检查")
                return
    except Exception as e:
        logger.error(f"读取配置文件时出错: {e}，将默认检查更新")

    logger.info("启动时检查更新...")
    # 创建一个临时的检查线程
    # 注意:这里直接在主线程等待结果可能会阻塞UI，更好的方式是异步处理或在启动画面中进行
    # 但为了简单起见，暂时这样处理
    update_thread = UpdateCheckThread()
    update_available, latest_version = update_thread.check_for_latest_release() # 直接调用检查方法

    if update_available:
        logger.success(f"启动时检测到新版本: {latest_version}")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("发现新版本")
        msg_box.setText(f"启动器有新版本 ({latest_version}) 可用\n当前版本: {VERSION}\n\n是否前往 GitHub 下载最新版本")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        ret = msg_box.exec_()
        if ret == QMessageBox.Yes:
            webbrowser.open(f"https://github.com/{update_thread.REPO_OWNER}/{update_thread.REPO_NAME}/releases/latest")
    else:
        logger.info("启动时未发现新版本或检查失败")

if __name__ == '__main__':
    main()