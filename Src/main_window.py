from loguru import logger
import os
from PyQt5.QtGui import QIcon
from about_tab import AboutTab
from manage_tab import ManageTab
from launch_tab import LaunchTab
from monitor_tab import MonitorTab
from cluster_tab import ClusterTab
from database_tab import DatabaseTab
from download_tab import DownloadTab
from settings_tab import SettingsTab
from activity_tab import ActivityTab
from PyQt5.QtCore import Qt, QProcess
from fe_core.blur_style import apply_blur_style, BLUR_STYLE
from fe_core.custom_title_bar import CustomTitleBar
from fe_core.background_effect import BackgroundEffect
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QApplication
from utils import BASE_PATH

class MainWindow(QMainWindow):
    def __init__(self, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager # 保存 theme_manager 实例
        self.background_effect = None # 初始化为 None 

        self.old_pos = None  # 用于窗口拖动
        # 窗口标题和图标将由 CustomTitleBar 管理
        self.setGeometry(0, 0, 1280, 720)
        self.setMinimumSize(495, 495)  # 设置最小窗口尺寸

        # 设置窗口属性以支持透明和模糊效果
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框窗口
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # 启用透明背景
        # 防止鼠标事件穿透
        self.setAttribute(Qt.WA_NoMousePropagation, True)

        # 居中窗口
        self._center_window()

        # 用于存储运行中的 QProcess 对象，以 PID 为键
        self.running_processes: dict[int, QProcess] = {}

        # 创建自定义标题栏
        self.title_bar = CustomTitleBar(self, window_title=self.tr('JimGrasscutterServerLauncher'), window_icon_path=os.path.join(BASE_PATH, 'Assets', 'JGSL-Logo.ico'))

        # 创建选项卡
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # 初始化各个功能页
        self.launch_tab = LaunchTab()
        self.monitor_tab = MonitorTab()
        self.manage_tab = ManageTab()
        self.download_tab = DownloadTab()
        self.settings_tab = SettingsTab(self)
        self.cluster_tab = ClusterTab()
        self.database_tab = DatabaseTab()
        self.activity_tab = ActivityTab() # 新增活动选项卡
        self.about_tab = AboutTab()

        # 连接 LaunchTab 的信号到 MainWindow 的方法
        self.launch_tab.process_created.connect(self.register_process)
        self.launch_tab.process_finished_signal.connect(self.unregister_process)

        # 选项卡
        self.tabs.addTab(self.launch_tab, self.tr('启动'))
        self.tabs.addTab(self.monitor_tab, self.tr('监控'))
        self.tabs.addTab(self.manage_tab, self.tr('管理'))
        self.tabs.addTab(self.database_tab, self.tr('数据库'))
        self.tabs.addTab(self.cluster_tab, self.tr('集群'))
        self.tabs.addTab(self.download_tab, self.tr('下载'))
        self.tabs.addTab(self.settings_tab, self.tr('设置'))
        self.tabs.addTab(self.activity_tab, self.tr('动态'))
        self.tabs.addTab(self.about_tab, self.tr('关于'))

        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 添加自定义标题栏和选项卡到主布局
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.tabs)

        # 创建中央部件并设置布局
        central_widget = QWidget()
        # 设置背景面板样式，确保鼠标事件不会穿透

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 安装事件过滤器，捕获所有鼠标事件
        self.installEventFilter(self)

    def apply_theme_effects(self, theme_config):
        enable_blur = theme_config.get('enable_blur', False)
        if enable_blur:
            apply_blur_style(self)
            if not self.background_effect:
                self.background_effect = BackgroundEffect(self)
            logger.info(self.tr("已应用背景模糊效果和透明样式"))
        else:
            # 如果不启用模糊，则移除模糊效果
            if self.background_effect:
                self.background_effect.remove_effect()
                self.background_effect = None
            else:
                logger.warning(self.tr("背景模糊效果未启用，无法移除"))
            # 移除样式表中的模糊样式
            current_style_sheet = self.styleSheet()
            # 简单粗暴地移除 BLUR_STYLE 中可能包含的样式，这里需要更精确的移除方式
            # 暂时先这样处理，后续可以优化
            for style_line in BLUR_STYLE.split(';'):
                if style_line.strip():
                    current_style_sheet = current_style_sheet.replace(style_line.strip(), '')
            self.setStyleSheet(current_style_sheet)
            logger.info(self.tr("已移除背景模糊效果和透明样式"))

    # 注册 QProcess 对象
    def register_process(self, pid: int, process: QProcess):
        if pid in self.running_processes:
            logger.warning(self.tr(f"尝试注册已存在的 PID: {pid}"))
        else:
            logger.info(self.tr(f"注册进程 PID: {pid}"))
            self.running_processes[pid] = process

    # 注销 QProcess 对象
    def unregister_process(self, pid: int):
        if pid in self.running_processes:
            logger.info(self.tr(f"注销进程 PID: {pid}"))
            del self.running_processes[pid]
        else:
            logger.warning(self.tr(f"尝试注销不存在的 PID: {pid}"))

    # 获取 QProcess 对象
    def get_process(self, pid: int) -> QProcess | None:
        process = self.running_processes.get(pid)
        if not process:
            logger.warning(self.tr(f"无法找到 PID: {pid} 对应的 QProcess 对象"))
        return process

    def _center_window(self):
        # 获取屏幕的尺寸
        screen_geometry = QApplication.desktop().screenGeometry()
        # 获取窗口的尺寸
        window_geometry = self.geometry()
        # 计算窗口居中时的左上角坐标
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        # 移动窗口到计算出的坐标
        self.move(x, y)

    def cleanup_and_exit(self):
        self.launch_tab.cleanup()
        QApplication.quit()

    def closeEvent(self, event):
        self.cleanup_and_exit()
        event.accept()

    def on_tab_changed(self, index):
        current_tab = self.tabs.widget(index)
        if isinstance(current_tab, MonitorTab):
            current_tab.scan_running_instances()
        elif isinstance(current_tab, ManageTab):
            current_tab.refresh_server_list()
        elif isinstance(current_tab, ActivityTab):
            current_tab.on_tab_selected()

    def paintEvent(self, event):
        """
        绘制窗口背景，支持高斯模糊透明效果
        """
        super().paintEvent(event)

    def mousePressEvent(self, event):
        """
        捕获鼠标按下事件，防止事件穿透
        """
        event.accept()  # 显式接受事件，防止传递到下层窗口