from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QProgressBar, QLabel, QSlider, QHBoxLayout, QDialog, QDialogButtonBox, QMessageBox, QTreeWidget, QTreeWidgetItem,QSpacerItem,QSizePolicy
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import requests
import shutil
import os
import json
from loguru import logger
import re

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.logger = logger
    
    def run(self):
        try:
            self.logger.info(f'开始下载 {self.url}')
            with requests.get(self.url, stream=True) as r:
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                with open(self.save_path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int(downloaded / total_size * 100)
                        self.logger.trace(f'下载进度 {progress}%')
                        self.progress_signal.emit(progress)
                self.finished_signal.emit(self.save_path)
        except Exception as e:
            self.logger.error(f'下载失败: {e} | URL: {self.url}')
            self.finished_signal.emit(f'Error: {str(e)}')

class InstanceSelectionDialog(QDialog):
    def __init__(self, category, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'选择 {category} 的目标实例')
        layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        self.refresh_instances()
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(self.list_widget)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def refresh_instances(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        servers_path = os.path.join(root_dir, 'Servers')
        valid_servers = [
            name for name in os.listdir(servers_path)
            if os.path.isdir(os.path.join(servers_path, name)) 
            and os.path.exists(os.path.join(servers_path, name, 'JGSL', 'Config.json'))
        ]
        self.list_widget.clear()
        self.list_widget.addItems(valid_servers)

class DownloadTab(QWidget):
    def __init__(self):
        super().__init__()
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.logger = logger
        self.current_instance = None
        self.category_paths = {
            'MongoDB 数据库社区版': os.path.join(self.root_dir, 'Database'),
            'Java运行时': os.path.join(self.root_dir, 'Java'),
            '服务端核心': os.path.join(self.root_dir, 'Servers'),
            '插件': os.path.join(self.root_dir, 'Servers'),
            '卡池配置文件': os.path.join(self.root_dir, 'Servers')
        }
        self.category_subdirs = {
            '插件': 'plugins',
            '卡池配置文件': 'data'
        }
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel('可下载组件')
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(15)
        self.tree.setStyleSheet('QTreeView::item { padding: 5px }')
        self._init_tree_data()
        
        self.download_btn = QPushButton('下载选中项目')
        self.download_queue = {}
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
        QProgressBar {
        margin-left: 0px;
        height: 20px;
        }
        """)
        self.status_label = QLabel('准备就绪')
        self.thread_count_label = QLabel('线程数: 64')
        self.thread_count_slider = QSlider(Qt.Horizontal)
        self.thread_count_slider.setRange(1, 128)
        self.thread_count_slider.setValue(64)
        self.thread_count_slider.valueChanged.connect(self.update_thread_count)
        self.thread_count = 64
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.addWidget(self.tree,7)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(self.thread_count_label)
        thread_layout.addWidget(self.thread_count_slider, stretch=8)
        thread_layout.addStretch(1)
        thread_layout.setSpacing(10)
        layout.addLayout(thread_layout)
        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.setLayout(layout)
        self.download_btn.clicked.connect(self.start_download)
    
    def _init_tree_data(self):
        # 从JSON配置文件加载下载列表
        config_path = os.path.join(self.root_dir, 'Config', 'download-list.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for category in data['categories']:
                    root = QTreeWidgetItem(self.tree)
                    root.setText(0, category['name'])
                    for item in category['items']:
                        child = QTreeWidgetItem(root)
                        child.setText(0, item['name'])
                        child.setData(0, 1, item['url'])
        except Exception as e:
            self.logger.error(f'加载下载列表失败: {e}')
            QMessageBox.critical(self, '错误', '下载列表配置文件损坏或不存在')

    def update_thread_count(self, value):
        self.thread_count = value
        self.thread_count_label.setText(f'线程数: {value}')
    
    def start_download(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        save_path = os.path.join(self.root_dir, 'DownloadTemp')
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        for selected_item in selected_items:
            category = selected_item.parent().text(0)
            if category in ['服务端核心', '插件', '卡池配置文件']:
                dialog = InstanceSelectionDialog(category, self)
                dialog.refresh_instances()
                if not dialog.list_widget.count() > 0:
                    QMessageBox.warning(self, '警告', '请先创建至少一个实例')
                    return
                if dialog.exec_() == QDialog.Accepted:
                    if dialog.list_widget.currentItem():
                        instance_name = dialog.list_widget.currentItem().text()
                        self.current_instance = instance_name
                        save_path = os.path.join(save_path, instance_name)
                    else:
                        QMessageBox.warning(self, '警告', '未选择实例')
                        return
                else:
                    return
            selected = selected_item.text(0)
            save_path = os.path.join(save_path, selected)
            # 自动创建实例目录
            try:
                os.makedirs(save_path, exist_ok=True)
                self.logger.success(f'成功创建目录: {save_path}')
            except Exception as e:
                self.logger.error(f'目录创建失败: {e}')
                QMessageBox.critical(self, '错误', f'目录创建失败: {e}')
                return
            # 获取下载URL
            url = selected_item.data(0, 1)
            thread = DownloadThread(url, save_path)
            thread.progress_signal.connect(self.update_progress)
            thread.finished_signal.connect(self.download_finished)
            thread.start()
            self.download_queue[thread] = thread
    
    def update_progress(self, value):
        total = sum(t.isRunning() for t in self.download_queue.values())
        if total > 0:
            progress = int(sum(t.progress_signal.emit(0) for t in self.download_queue.values()) / total)
        else:
            progress = 0
        self.progress_bar.setValue(progress)
    
    def download_finished(self, msg):
        if msg.startswith('Error'):
            self.logger.error(f'下载失败: {msg}')
            QMessageBox.critical(self, '错误', msg)
        else:
            self.logger.success(f'文件下载完成: {msg}')
        self.status_label.setText(msg)
        self.progress_bar.reset()
        self.move_file(msg)
    
    def move_file(self, file_path):
        if not os.path.exists(file_path):
            self.logger.error(f'文件不存在: {file_path}')
            QMessageBox.critical(self, '错误', f'文件不存在: {file_path}')
            return
        file_path = os.path.normpath(file_path)
        file_name = os.path.basename(file_path)
        selected_item = next((item for item in self.tree.findItems(file_name, Qt.MatchExactly | Qt.MatchRecursive, 0)), None)
        if not selected_item:
            self.logger.error(f'未找到下载项目: {file_name}')
            QMessageBox.critical(self, '错误', f'未找到下载项目: {file_name}')
            return
        category = selected_item.parent().text(0)
        dest_dir = self.category_paths.get(category)
        if not dest_dir:
            self.logger.error(f'未知分类: {category}')
            QMessageBox.critical(self, '错误', f'未知分类: {category}')
            return
        # 获取版本号
        version_match = re.search(r'(\d+\.\d+\.\d+)(?:unstable)?', file_name)
        version = version_match.group(1) if version_match else None
        if category in ['服务端核心', '插件', '卡池配置文件']:
            dest_dir = os.path.join(dest_dir, self.current_instance)
        if category in self.category_subdirs:
            dest_dir = os.path.join(dest_dir, self.category_subdirs[category])
        if category == '卡池配置文件':
            dest_dir = os.path.join(dest_dir, 'ExcelBinOutput')
        if version:
            dest_dir = os.path.join(dest_dir, version)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        dest_dir = os.path.abspath(dest_dir)
        dest_path = os.path.normpath(os.path.join(dest_dir, file_name))
        if os.path.exists(dest_path):
            os.remove(dest_path)
        try:
            shutil.move(file_path, dest_path)
        except Exception as e:
            self.logger.error(f'文件移动失败: {e}')
            QMessageBox.critical(self, '错误', f'文件移动失败: {e}')