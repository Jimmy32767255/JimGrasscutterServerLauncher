import os
import json
from loguru import logger
from PyQt5.QtWidgets import QComboBox, QLabel
from utils import get_base_path

BASE_PATH = get_base_path()
CONFIG_FILE = os.path.join(BASE_PATH, 'Config', 'config.json')

class ThemeManager:
    def __init__(self, tr_func):
        self.parent_widget = None
        self.tr = tr_func
        self.theme_label = QLabel(self.tr("界面主题:"))
        self.theme_combo = QComboBox()
        self.load_themes()
        # 连接信号，确保后续可以断开和重新连接


    def load_themes(self):
        themes_dir = os.path.join(BASE_PATH, 'Themes')
        self.theme_map = {}
        for theme_name in os.listdir(themes_dir):
            theme_path = os.path.join(themes_dir, theme_name)
            if os.path.isdir(theme_path):
                config_file = os.path.join(theme_path, 'theme.json')
                if os.path.exists(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            theme_config = json.load(f)
                        display_name = theme_config.get('name', theme_name)
                        self.theme_combo.addItem(self.tr(display_name), theme_name)
                        self.theme_map[theme_name] = theme_config
                    except Exception as e:
                        logger.error(self.tr(f'加载主题配置文件 {config_file} 时出错: {e}'))

    def get_theme_widgets(self):
        return self.theme_label, self.theme_combo

    def _find_theme_index(self, theme_key):
        """根据主题键查找组合框中的索引。"""
        index = self.theme_combo.findData(theme_key)
        if index == -1:
            # 如果找不到，则尝试根据显示名称查找
            display_name = self.theme_map.get(theme_key, {}).get('name', theme_key)
            index = self.theme_combo.findText(self.tr(display_name))
        return index if index != -1 else 0 # 回退到第一个主题

    def load_theme_setting(self, config_data):
        theme_key = config_data.get('Theme', 'ModernDark') # 默认使用 ModernDark
        logger.debug(self.tr(f'加载主题设置 {theme_key}'))
        index = self._find_theme_index(theme_key)
        self.theme_combo.setCurrentIndex(index)
        # 不直接应用主题，只返回主题 key，等待 MainWindow 初始化完成后再应用
        return theme_key

    def save_theme_setting(self):
        # 保存当前选中的主题的 data (即文件夹名)
        theme_key = self.theme_combo.currentData()
        return theme_key

    def _apply_theme(self, theme_key):
        """辅助函数，用于应用主题。"""
        try:
            theme_config = self.theme_map.get(theme_key, {})
            style_sheet = []

            font_color = theme_config.get('font_color')
            if font_color:
                style_sheet.append(f'color: {font_color};')

            background_color = theme_config.get('background_color')
            if background_color:
                style_sheet.append(f'background-color: {background_color};')

            background_image_enabled = theme_config.get('background_image', False)
            if background_image_enabled:
                # 尝试加载 background.png
                image_path_png = os.path.join(BASE_PATH, 'Themes', theme_key, "background.png")
                # 尝试加载 background.jpg
                image_path_jpg = os.path.join(BASE_PATH, 'Themes', theme_key, "background.jpg")

                image_to_load = None
                if os.path.exists(image_path_png):
                    image_to_load = image_path_png
                elif os.path.exists(image_path_jpg):
                    image_to_load = image_path_jpg

                if image_to_load:
                    formatted_image_path = image_to_load.replace(os.sep, '/')
                    style_sheet.append(f'background-image: url("{formatted_image_path}");')
                    style_sheet.append('background-repeat: no-repeat;')
                    style_sheet.append('background-position: center;')
                    style_sheet.append('background-size: contain;')

            self.parent_widget.setStyleSheet(' '.join(style_sheet))
            logger.debug(self.tr(f'应用主题: {theme_key} '))
        except Exception as e:
            logger.error(self.tr(f'应用主题时出错: {e}'))

    def apply_theme_from_settings(self, theme_key):
        self._apply_theme(theme_key)

    def apply_initial_theme_to_window(self, main_window_instance):
        self.parent_widget = main_window_instance # 设置 parent_widget 为 MainWindow 实例



        # 从配置文件加载主题设置并应用
        config_file = os.path.join(BASE_PATH, 'Config', 'config.json')
        theme_key = 'ModernDark' # 默认主题
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                theme_key = config_data.get('Theme', 'ModernDark')
        except Exception as e:
            logger.warning(self.tr(f"读取配置文件时出错，使用默认主题ModernDark: {e}"))

        index = self._find_theme_index(theme_key)
        self.theme_combo.setCurrentIndex(index)

        # 重新连接信号
        self.theme_combo.currentIndexChanged.connect(self.apply_selected_theme)
        # 确保在设置完 parent_widget 后再连接信号，避免在初始化时触发
        self.theme_combo.currentIndexChanged.emit(self.theme_combo.currentIndex())

        self._apply_theme(self.theme_combo.currentData()) # 应用当前选中的主题

    def apply_selected_theme(self):
        logger.debug(self.tr("尝试应用选定主题..."))
        theme_key = self.theme_combo.currentData()
        self._apply_theme(theme_key)