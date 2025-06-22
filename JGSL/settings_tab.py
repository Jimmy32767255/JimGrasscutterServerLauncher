from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QComboBox, QLabel, QPushButton, QSpinBox, QHBoxLayout,QSpacerItem,QSizePolicy
from loguru import logger
from blur_style import BLUR_STYLE
import json
import os
from update_checker import UpdateCheckThread, VERSION
from monitor_tab import MonitorPanel

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Config', 'config.json')

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        
        # 主题设置
        self.theme_label = QLabel("界面主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['面子工程', 'Windows原生', '现代深色'])
        
        # 语言设置
        self.lang_label = QLabel("显示语言(实现中):")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['简体中文', 'English'])
        
        # 自动更新
        self.auto_update = QCheckBox("启用自动更新")
        self.update_status_label = QLabel(f"当前版本: {VERSION}") # 显示当前版本
        
        # 最大日志行数
        self.max_log_label = QLabel("最大日志行数:")
        self.max_log_spin = QSpinBox()
        self.max_log_spin.setRange(50, 1000)
        self.max_log_spin.setSingleStep(50)
        self.max_log_spin.setValue(100)
        log_line_layout = QHBoxLayout()
        log_line_layout.addWidget(self.max_log_label)
        log_line_layout.addWidget(self.max_log_spin)
        
        # 保存按钮
        self.save_btn = QPushButton("保存设置")

        # 调试按钮
        self.debug_monitor_btn = QPushButton("DEBUG: 打开监控面板")
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.addWidget(self.theme_label)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_combo)
        layout.addWidget(self.auto_update)
        layout.addWidget(self.update_status_label)
        layout.addLayout(log_line_layout)
        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(self.save_btn)
        # 把调试按钮加到布局里
        layout.addWidget(self.debug_monitor_btn)
        
        self.setLayout(layout)
        
        # 加载已保存设置
        self.load_settings()
        
        # 连接信号
        self.save_btn.clicked.connect(self.save_settings)
        self.auto_update.stateChanged.connect(self.toggle_auto_update) # 连接复选框状态变化信号
        # 连接调试按钮的点击信号
        self.debug_monitor_btn.clicked.connect(self.open_debug_monitor_panel)
        
    def load_settings(self):
        try:
            if not os.path.exists(CONFIG_FILE):
                logger.warning(f'配置文件 {CONFIG_FILE} 不存在，将使用默认设置')
                theme = 'fe'
                lang = 'zh_CN'
                auto_update = True
                max_log_lines = 100
            else:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                theme = config_data.get('Theme', 'fe')
                logger.debug(f'加载主题设置 {theme}')
                lang = config_data.get('Language', 'zh_CN')
                auto_update = config_data.get('AutoUpdate', True)
                max_log_lines = config_data.get('MaxLogLines', 100)
                self.max_log_spin.setValue(max_log_lines)

        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            logger.error(f'加载设置时出错: {e}，将使用默认设置')
            theme = 'fe'
            lang = 'zh_CN'
            auto_update = True
            max_log_lines = 100
            self.max_log_spin.setValue(max_log_lines)

        self.theme_combo.setCurrentText('面子工程' if theme == 'fe' else 'Windows原生')
        self.lang_combo.setCurrentText('简体中文' if lang == 'zh_CN' else 'English')
        self.auto_update.setChecked(auto_update)
        self._apply_theme(theme)

        # 如果启用了自动更新，就在加载设置后启动检查
        if auto_update:
            self.run_update_check()

    def save_settings(self):
        theme = 'fe' if self.theme_combo.currentText() == '面子工程' else 'light'
        lang = 'zh_CN' if self.lang_combo.currentText() == '简体中文' else 'en_US'
        auto_update = self.auto_update.isChecked()
        max_log_lines = self.max_log_spin.value()

        config_data = {}
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            logger.error(f'读取现有配置文件 {CONFIG_FILE} 时出错: {e}，将创建新的配置')
            config_data = {}

        config_data['Theme'] = theme
        config_data['Language'] = lang
        config_data['AutoUpdate'] = auto_update
        config_data['MaxLogLines'] = max_log_lines

        try:
            config_dir = os.path.dirname(CONFIG_FILE)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                logger.info(f'创建配置目录 {config_dir} ')

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            logger.success(f'配置已保存到 {CONFIG_FILE} ')
        except Exception as e:
            logger.error(f'保存设置到 {CONFIG_FILE} 时出错: {e}')
            return
        
        self._apply_theme(theme)

    def _apply_theme(self, theme):
        """Helper function to apply theme."""
        try:
            if theme == 'fe':
                self.window().setStyleSheet(BLUR_STYLE) # 应用自定义的粉紫渐变主题
            else:
                self.window().setStyleSheet('')
            logger.debug(f'应用主题: {theme} ')
        except Exception as e:
            logger.error(f'应用主题时出错: {e}')

    # 启动更新检查线程
    def run_update_check(self):
        logger.info("开始后台检查更新...")
        # 检查是否已有线程在运行，避免重复启动
        if hasattr(self, 'update_thread') and self.update_thread.isRunning():
            logger.warning("更新检查线程已在运行中")
            return
        self.update_thread = UpdateCheckThread()
        self.update_thread.update_check_result.connect(self.handle_update_result)
        self.update_thread.start()

    # 处理更新检查结果
    def handle_update_result(self, update_available, latest_version):
        if update_available:
            self.update_status_label.setText(f"发现新版本: {latest_version}！请前往 GitHub 下载")
            # 这里可以添加更明显的提示，比如修改标签样式或者弹窗
            logger.success(f"检查到新版本: {latest_version}")
        else:
            # 确保使用最新的 VERSION 显示状态
            self.update_status_label.setText(f"当前版本: {VERSION} (已是最新)")
            logger.info("未发现新版本或检查更新失败")

    # 处理复选框状态变化
    def toggle_auto_update(self, state):
        if state == 2: 
            self.run_update_check()
        else:
            # 如果取消勾选，可以考虑停止正在进行的检查(如果需要)
            if hasattr(self, 'update_thread') and self.update_thread.isRunning():
                logger.info("尝试终止更新检查线程...")
                self.update_thread.quit() # 请求线程退出
                self.update_thread.wait(1000) # 等待最多1秒
                if self.update_thread.isRunning():
                    logger.warning("更新检查线程未能正常退出，将强制终止")
                    self.update_thread.terminate() # 强制终止
                    self.update_thread.wait() # 等待终止完成
            # 恢复显示当前版本
            self.update_status_label.setText(f"当前版本: {VERSION}") 
            logger.info("自动更新已禁用")

    # 打开调试监控面板的方法
    def open_debug_monitor_panel(self):
        logger.info("打开调试模式的监控面板")
        # 传入 debug_mode=True 来启动调试模式
        try:
            # 注意这里要用 self.debug_monitor_panel 来存储引用，不然窗口会闪退
            self.debug_monitor_panel = MonitorPanel(instance_name="Debug Instance", pid=-1, log_path="N/A", debug_mode=True)
            self.debug_monitor_panel.show() # 使用 show() 而不是 exec_() 来避免阻塞主窗口
        except Exception as e:
            logger.error(f"打开调试监控面板时出错: {e}")