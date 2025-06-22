import sys
import os
import json
from loguru import logger
from PyQt5.QtWidgets import QApplication, QMessageBox  QMessageBox 
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtCore import Qt
from main_window import MainWindow
import signal
import webbrowser
# 导入更新检查器和设置版本号的函数
from update_checker import UpdateCheckThread, VERSION

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
    app = QApplication(sys.argv)
    
    # 设置应用程序属性以支持高斯模糊透明效果
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # 使用高DPI图像
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # 启用高DPI缩放
    
    # 加载字体
    font_family = load_font_async(font_path)
    font = QFont(font_family)
    font.setPointSize(10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 在显示主窗口后检查更新
    check_for_updates_on_startup()

    signal.signal(signal.SIGINT, lambda s, f: window.cleanup_and_exit())
    sys.exit(app.exec_())

# 更新检查
def check_for_updates_on_startup():
    # 读取配置文件检查是否启用自动更新
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Config', 'config.json')
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