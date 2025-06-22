from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
import os
import shutil
from loguru import logger

class PluginManagerDialog(QDialog):
    def __init__(self, parent, instance_name, instance_dir):
        super().__init__(parent)
        self.instance_name = instance_name
        self.instance_dir = instance_dir
        self.plugins_dir = os.path.join(self.instance_dir, 'plugins')
        self.root_dir = parent.root_dir # 获取根目录

        # 确保插件目录存在
        if not os.path.exists(self.plugins_dir):
            try:
                os.makedirs(self.plugins_dir)
                logger.info(f"为实例 '{self.instance_name}' 创建插件目录: {self.plugins_dir}")
            except OSError as e:
                logger.error(f"创建插件目录 {self.plugins_dir} 失败: {e}")
                QMessageBox.critical(self, "错误", f"无法创建插件目录: {e}")
                # 如果无法创建目录，则提前返回或禁用对话框功能
                return

        self.setWindowTitle(f"插件管理 - {self.instance_name}")
        self.setMinimumSize(400, 300)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout()

        self.plugin_list_widget = QListWidget()
        layout.addWidget(self.plugin_list_widget)

        button_layout = QHBoxLayout()
        self.add_plugin_btn = QPushButton("添加插件")
        self.remove_plugin_btn = QPushButton("移除插件")
        button_layout.addWidget(self.add_plugin_btn)
        button_layout.addWidget(self.remove_plugin_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.add_plugin_btn.clicked.connect(self.add_plugin)
        self.remove_plugin_btn.clicked.connect(self.remove_plugin)

        self.load_plugins()

    def load_plugins(self):
        self.plugin_list_widget.clear()
        if not os.path.exists(self.plugins_dir):
            logger.warning(f"插件目录不存在: {self.plugins_dir}")
            return
        
        logger.info(f"从 {self.plugins_dir} 加载插件")
        for item in os.listdir(self.plugins_dir):
            if item.endswith('.jar'):
                self.plugin_list_widget.addItem(item)
        logger.info(f"找到 {self.plugin_list_widget.count()} 个插件")

    def add_plugin(self):
        logger.info("打开文件对话框以添加插件")
        file_names, _ = QFileDialog.getOpenFileNames(self, "选择插件文件", "", "JAR 文件 (*.jar)")
        if file_names:
            added_count = 0
            for file_name in file_names:
                base_name = os.path.basename(file_name)
                destination_path = os.path.join(self.plugins_dir, base_name)
                try:
                    shutil.copy(file_name, destination_path)
                    logger.success(f"插件 '{base_name}' 已复制到 {destination_path}")
                    added_count += 1
                except Exception as e:
                    logger.error(f"复制插件 '{base_name}' 失败: {e}")
                    QMessageBox.warning(self, "复制失败", f"无法复制插件 {base_name}: {e}")
            if added_count > 0:
                self.load_plugins()
                QMessageBox.information(self, "成功", f"{added_count} 个插件已成功添加。")

    def remove_plugin(self):
        current_item = self.plugin_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个要移除的插件")
            return

        plugin_name = current_item.text()
        reply = QMessageBox.question(self, "确认移除", f"确定要移除插件 '{plugin_name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            try:
                os.remove(plugin_path)
                logger.success(f"插件 '{plugin_name}' 已从 {plugin_path} 移除")
                self.load_plugins()
                QMessageBox.information(self, "成功", f"插件 '{plugin_name}' 已成功移除。")
            except Exception as e:
                logger.error(f"移除插件 '{plugin_name}' 失败: {e}")
                QMessageBox.warning(self, "移除失败", f"无法移除插件 {plugin_name}: {e}")