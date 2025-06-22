from PyQt5.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QIcon
from launch_tab import LaunchTab
from monitor_tab import MonitorTab
from manage_tab import ManageTab
from download_tab import DownloadTab
from settings_tab import SettingsTab
from cluster_tab import ClusterTab
from database_tab import DatabaseTab
from about_tab import AboutTab
from background_effect import BackgroundEffect
from loguru import logger
from custom_title_bar import CustomTitleBar
from blur_style import apply_blur_style


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")  # 设置背景透明
        self.old_pos = None  # 用于窗口拖动
        self.setWindowTitle('JimGrasscutterServerLauncher')
        self.setGeometry(0, 0, 760, 600)
        self.setMinimumSize(495, 495)  # 设置最小窗口尺寸
        self.setWindowIcon(QIcon('Assets/JGSL-Logo.ico'))
        
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
        self.title_bar = CustomTitleBar(self)
        
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
        self.settings_tab = SettingsTab()
        self.cluster_tab = ClusterTab()
        self.database_tab = DatabaseTab()
        self.about_tab = AboutTab()

        # 连接 LaunchTab 的信号到 MainWindow 的方法
        self.launch_tab.process_created.connect(self.register_process)
        self.launch_tab.process_finished_signal.connect(self.unregister_process)

        # 选项卡
        self.tabs.addTab(self.launch_tab, '启动')
        self.tabs.addTab(self.monitor_tab, '监控')
        self.tabs.addTab(self.manage_tab, '管理')
        self.tabs.addTab(self.database_tab, '数据库')
        self.tabs.addTab(self.cluster_tab, '集群')
        self.tabs.addTab(self.download_tab, '下载')
        self.tabs.addTab(self.settings_tab, '设置')
        self.tabs.addTab(self.about_tab, '关于')

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
        central_widget.setStyleSheet("background-color: rgba(255, 255, 255, 0.01); opacity: 0;")  # 完全透明但可捕获鼠标事件
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 应用高斯模糊透明样式
        apply_blur_style(self)
        
        # 应用背景模糊效果
        self.background_effect = BackgroundEffect(self)
        logger.info("已应用背景模糊效果和透明样式")
        
        # 安装事件过滤器，捕获所有鼠标事件
        self.installEventFilter(self)

    # 注册 QProcess 对象
    def register_process(self, pid: int, process: QProcess):
        if pid in self.running_processes:
            logger.warning(f"尝试注册已存在的 PID: {pid}")
        else:
            logger.info(f"注册进程 PID: {pid}")
            self.running_processes[pid] = process

    # 注销 QProcess 对象
    def unregister_process(self, pid: int):
        if pid in self.running_processes:
            logger.info(f"注销进程 PID: {pid}")
            del self.running_processes[pid]
        else:
            logger.warning(f"尝试注销不存在的 PID: {pid}")

    # 获取 QProcess 对象
    def get_process(self, pid: int) -> QProcess | None:
        process = self.running_processes.get(pid)
        if not process:
            logger.warning(f"无法找到 PID: {pid} 对应的 QProcess 对象")
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
            
    def paintEvent(self, event):
        """
        绘制窗口背景，支持高斯模糊透明效果
        """
        # 此方法为空是有意的，因为背景绘制由BackgroundEffect和样式表处理
        # 但必须存在此方法以确保Qt正确处理背景绘制
        super().paintEvent(event)
        
    def mousePressEvent(self, event):
        """
        捕获鼠标按下事件，防止事件穿透
        """
        event.accept()  # 显式接受事件，防止传递到下层窗口
        
    def mouseReleaseEvent(self, event):
        """
        捕获鼠标释放事件，防止事件穿透
        """
        event.accept()  # 显式接受事件，防止传递到下层窗口
        
    def mouseMoveEvent(self, event):
        """
        捕获鼠标移动事件，防止事件穿透
        """
        event.accept()  # 显式接受事件，防止传递到下层窗口
