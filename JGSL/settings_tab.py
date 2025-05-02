from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QComboBox, QLabel, QPushButton
from PyQt5.QtCore import QSettings, QTimer
import qdarkstyle
from loguru import logger

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        
        self.settings = QSettings('JimGrasscutterServerLauncher', 'Settings')
        
        # 主题设置
        self.theme_label = QLabel("界面主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['深色模式', '浅色模式'])
        
        # 语言设置
        self.lang_label = QLabel("显示语言:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['简体中文', 'English'])
        
        # 自动更新
        self.auto_update = QCheckBox("启用自动更新")
        
        # 保存按钮
        self.save_btn = QPushButton("保存设置")
        
        layout = QVBoxLayout()
        layout.addWidget(self.theme_label)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_combo)
        layout.addWidget(self.auto_update)
        layout.addWidget(self.save_btn)
        
        self.setLayout(layout)
        
        # 加载已保存设置
        self.load_settings()
        
        # 连接信号
        self.save_btn.clicked.connect(self.save_settings)
        
    def load_settings(self):
        try:
            theme = self.settings.value('Theme', 'dark', type=str)
            logger.debug(f'加载主题设置 {theme}')
            lang = self.settings.value('Language', 'zh_CN', type=str)
            auto_update = self.settings.value('AutoUpdate', True, type=bool)
        except Exception as e:
            logger.error(f'加载设置时出错: {e}')
            return
        
        self.theme_combo.setCurrentText('深色模式' if theme == 'dark' else '浅色模式')
        self.lang_combo.setCurrentText('简体中文' if lang == 'zh_CN' else 'English')
        self.auto_update.setChecked(auto_update)
        
    def save_settings(self):
        theme = 'dark' if self.theme_combo.currentText() == '深色模式' else 'light'
        lang = 'zh_CN' if self.lang_combo.currentText() == '简体中文' else 'en_US'
        auto_update = self.auto_update.isChecked()
        
        prev_theme = self.settings.value('Theme', 'dark', type=str)
        prev_lang = self.settings.value('Language', 'zh_CN', type=str)
        prev_auto_update = self.settings.value('AutoUpdate', True, type=bool)
        logger.info(f'配置变更 - 主题: {prev_theme} -> {theme}, 语言: {prev_lang} -> {lang}, 自动更新: {prev_auto_update} -> {auto_update}')
        
        try:
            self.settings.setValue('Theme', theme)
            self.settings.setValue('Language', lang)
            self.settings.setValue('AutoUpdate', auto_update)
            logger.success('配置已保存')
        except Exception as e:
            logger.error(f'保存设置时出错: {e}')
            return
        
        # 应用主题更改
        if theme == 'dark':
            self.window().setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        else:
            self.window().setStyleSheet('')