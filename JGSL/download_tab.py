from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QProgressBar, QLabel, QSlider, QHBoxLayout, QDialog, QDialogButtonBox, QMessageBox,QSpacerItem,QSizePolicy
from PyQt5.QtCore import QThread, pyqtSignal,Qt
import requests
import shutil
import os
from loguru import logger

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('选择目标实例')
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
        
        self.component_list = QListWidget()
        self.component_list.addItems(['MongoDB 数据库', 'Java 运行时', 'Grasscutter 服务端核心'])
        
        self.download_btn = QPushButton('下载选中项目')
        self.download_queue = {}
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
        QProgressBar {
        margin-left: 0px;  /* 与按钮左边界相同 */
        height: 20px;
        }
        """)
        self.status_label = QLabel('准备就绪')
        self.thread_count_label = QLabel('线程数: 4')
        self.thread_count_slider = QSlider(Qt.Horizontal)
        self.thread_count_slider.setRange(1, 8)
        self.thread_count_slider.setValue(4)
        self.thread_count_slider.valueChanged.connect(self.update_thread_count)
        self.thread_count = 4
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.addWidget(self.component_list)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.thread_count_label)
        layout.addWidget(self.thread_count_slider)
        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.setLayout(layout)
        self.download_btn.clicked.connect(self.start_download)
    
    def update_thread_count(self, value):
        self.thread_count = value
        self.thread_count_label.setText(f'线程数: {value}')
    
    def start_download(self):
        selected = self.component_list.currentItem().text()
        save_path = os.path.join(self.root_dir, 'DownloadTemp')
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        if selected == 'Grasscutter 服务端核心':
            dialog = InstanceSelectionDialog(self)
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
        save_path = os.path.join(save_path, selected)
        # 自动创建实例目录
        try:
            os.makedirs(save_path, exist_ok=True)
            self.logger.success(f'成功创建目录: {save_path}')
        except Exception as e:
            self.logger.error(f'目录创建失败: {e}')
            QMessageBox.critical(self, '错误', f'目录创建失败: {e}')
            return
        # 根据选择项匹配下载URL
        urls = {
            'MongoDB 数据库社区版': 'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.0.9.zip',
            'Java 运行时': 'https://www.azul.com/core-post-download/?endpoint=zulu&uuid=e92d2424-0b2b-4236-9d28-73278f5b0dd9',
            'Grasscutter 服务端核心': 'https://github.com/Grasscutters/Grasscutter/releases/download/v1.7.4/grasscutter-1.7.4.jar'
        }
        thread = DownloadThread(urls[selected], save_path)
        thread.progress_signal.connect(self.update_progress)
        thread.finished_signal.connect(self.download_finished)
        thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
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
        if 'MongoDB' in file_path:
            dest_dir = os.path.join(self.root_dir, 'Database')
        elif 'Java' in file_path:
            dest_dir = os.path.join(self.root_dir, 'Java')
        elif 'Grasscutter' in file_path:
            dest_dir = os.path.join(self.root_dir, 'Servers', self.current_instance)
        else:
            return
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        file_name = os.path.basename(file_path)
        dest_dir = os.path.abspath(dest_dir)
        dest_path = os.path.normpath(os.path.join(dest_dir, file_name))
        if os.path.exists(dest_path):
            os.remove(dest_path)
        try:
            shutil.move(file_path, dest_path)
        except Exception as e:
            self.logger.error(f'文件移动失败: {e}')
            QMessageBox.critical(self, '错误', f'文件移动失败: {e}')