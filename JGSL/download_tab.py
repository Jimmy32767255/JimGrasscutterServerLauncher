from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QProgressBar, QLabel, QSlider, QHBoxLayout, QDialog, QDialogButtonBox, QMessageBox, QTreeWidget, QTreeWidgetItem,QSpacerItem,QSizePolicy,QComboBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import requests
import shutil
import os
import json
from loguru import logger
import patoolib
import webbrowser
import zipfile

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
                try:
                    try:
                        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                        test_file = os.path.join(os.path.dirname(self.save_path), 'test.tmp')
                        with open(test_file, 'w') as f:
                            f.write('test')
                        os.remove(test_file)
                    except Exception as e:
                        raise PermissionError(f'目录 {os.path.dirname(self.save_path)} 无写入权限: {e}')
                    with open(self.save_path, 'wb') as f:
                        for chunk in r.iter_content(1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = int(downloaded / total_size * 100)
                            else:
                                progress = 0 # 如果 total_size 为0，则进度为0
                            self.logger.trace(f'下载进度 {progress}%')
                            self.progress_signal.emit(progress)
                    self.finished_signal.emit(self.save_path)
                except PermissionError as e:
                    self.logger.error(f'文件写入权限检查失败: {e}')
                    self.finished_signal.emit(f'Error: {str(e)}')
                except Exception as e:
                    self.logger.error(f'文件写入失败: {e}')
                    self.finished_signal.emit(f'Error: {str(e)}')
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
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")  # 设置背景透明
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
        
        # 镜像源选择
        self.mirror_combo = QComboBox()
        self.load_mirrors()
        mirror_layout = QHBoxLayout()
        mirror_layout.addWidget(QLabel('GitHub镜像源(仅适用于GitHub资源):'))
        mirror_layout.addWidget(self.mirror_combo, stretch=1)
        layout.insertLayout(0, mirror_layout)
        
        self.setLayout(layout)
        self.download_btn.clicked.connect(self.start_download)
        self.mirror_combo.currentTextChanged.connect(self.on_mirror_changed)
    
    def load_mirrors(self):
        """从配置文件加载镜像源列表"""
        mirror_path = os.path.join(self.root_dir, 'Config', 'mirror-list.json')
        try:
            with open(mirror_path, 'r', encoding='utf-8') as f:
                mirrors = json.load(f)
                self.mirror_combo.clear()
                for mirror in mirrors:
                    self.mirror_combo.addItem(mirror['name'], mirror['url'])
        except Exception as e:
            self.logger.error(f'加载镜像源失败: {e}')
            self.mirror_combo.addItem('默认源', '')
    
    def on_mirror_changed(self, text):
        """镜像源变更处理"""
        self.current_mirror = self.mirror_combo.currentData()
    
    def _init_tree_data(self):
        # 从JSON配置文件加载下载列表
        config_path = os.path.join(self.root_dir, 'Config', 'download-list.json')
        self.tree.clear() # 清除现有项目以避免重复
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                categories_data = json.load(f)

                # 检查顶层是否为字典，并且是否包含 'categories' 键
                if not isinstance(categories_data, dict) or 'categories' not in categories_data:
                    self.logger.error(f"下载列表格式错误：顶层应为包含 'categories' 键的对象。文件: {config_path}")
                    QMessageBox.critical(self, '错误', f'下载列表配置文件 {os.path.basename(config_path)} 格式错误：顶层应为包含 \'categories\' 键的对象。')
                    return

                actual_categories_list = categories_data['categories']
                if not isinstance(actual_categories_list, list):
                    self.logger.error(f"下载列表格式错误：'categories' 字段应为列表。文件: {config_path}")
                    QMessageBox.critical(self, '错误', f'下载列表配置文件 {os.path.basename(config_path)} 格式错误：\'categories\' 字段应为列表。')
                    return

                for category_data in actual_categories_list:
                    # 检查分类数据是否为字典，并且是否包含 'name' 和 'items' 键
                    if not isinstance(category_data, dict) or 'name' not in category_data or 'items' not in category_data:
                        self.logger.warning(f"跳过无效的分类数据或缺少必要字段（需要 'name' 和 'items'）: {category_data}")
                        continue

                    category_name = category_data['name'] # 使用 'name' 键获取分类名称
                    category_item = QTreeWidgetItem(self.tree)
                    category_item.setText(0, category_name)
                    category_item.setFlags(category_item.flags() & ~Qt.ItemIsSelectable) # 分类不可选

                    items_list = category_data['items']
                    if not isinstance(items_list, list):
                        self.logger.warning(f"分类 '{category_name}' 中的 'items' 字段非列表类型。")
                        continue

                    for item_data in items_list:
                        if not isinstance(item_data, dict) or 'title' not in item_data: # 确保项目是字典且有 'title'
                            self.logger.warning(f"跳过分类 '{category_name}' 中无效的项目数据或缺少 'title': {item_data}")
                            continue
                        
                        # 确保 'download_url', 'target_filename', 'target_location' 也存在，否则下载会失败
                        if not all(key in item_data for key in ['download_url', 'target_filename', 'target_location']):
                            self.logger.warning(f"跳过分类 '{category_name}' 中缺少必要下载信息的项目 ('download_url', 'target_filename', 'target_location'): {item_data.get('title', '无标题项目')}")
                            continue

                        child_item = QTreeWidgetItem(category_item)
                        child_item.setText(0, item_data['title'])
                        child_item.setData(0, Qt.UserRole, item_data) # 存储完整的项目元数据
        except FileNotFoundError:
            self.logger.error(f'下载列表配置文件未找到: {config_path}')
            QMessageBox.critical(self, '错误', f'下载列表配置文件 {os.path.basename(config_path)} 未找到。')
        except json.JSONDecodeError as e:
            self.logger.error(f'下载列表配置文件JSON解析错误: {config_path} - {e}')
            QMessageBox.critical(self, '错误', f'下载列表配置文件 {os.path.basename(config_path)} 格式错误。')
        except Exception as e:
            self.logger.error(f'加载下载列表失败: {e}', exc_info=True)
            QMessageBox.critical(self, '错误', f'加载下载列表时发生未知错误: {e}')

    def update_thread_count(self, value):
        self.thread_count = value
        self.thread_count_label.setText(f'线程数: {value}')

    def move_file(self, downloaded_file_path, item_data):
        """处理下载完成后的文件移动或解压"""
        target_location = item_data.get('target_location')
        target_filename = item_data.get('target_filename')
        is_zipped = item_data.get('is_zipped', False)
        item_title = item_data.get('title', '未知项目')

        if not target_location or not target_filename:
            self.logger.error(f"移动文件失败: 项目 '{item_title}' 的元数据不完整 (target_location 或 target_filename 缺失)。")
            QMessageBox.critical(self, '错误', f"项目 '{item_title}' 的元数据不完整，无法移动文件。")
            return

        final_target_dir = ""

        if target_location.startswith('Servers/{instance_name}'):
            if not self.current_instance:
                self.logger.error(f"移动文件 '{target_filename}' 失败: 未选择实例。")
                QMessageBox.warning(self, '错误', f"移动文件 '{target_filename}' 失败: 需要选择实例但当前未选择。")
                return
            instance_base_path = os.path.join(self.root_dir, 'Servers', self.current_instance)
            location_parts = target_location.split('/')
            if len(location_parts) == 2: # e.g., "Servers/{instance_name}"
                final_target_dir = instance_base_path
            elif len(location_parts) > 2: # e.g., "Servers/{instance_name}/plugins"
                sub_dir_name = '/'.join(location_parts[2:]) # Handles nested subdirs like 'data/some/folder'
                final_target_dir = os.path.join(instance_base_path, sub_dir_name)
            else:
                self.logger.error(f"无法解析目标位置 '{target_location}' for instance '{self.current_instance}'.")
                QMessageBox.critical(self, '错误', f"无法解析实例 '{self.current_instance}' 的目标位置 '{target_location}'。")
                return
        elif target_location == 'Database':
            final_target_dir = os.path.join(self.root_dir, 'Database')
        elif target_location == 'Java':
            final_target_dir = os.path.join(self.root_dir, 'Java')
        elif target_location == 'Config':
            final_target_dir = os.path.join(self.root_dir, 'Config')
        else:
            # 尝试将 target_location 视为相对于 root_dir 的路径
            # 这适用于 download-list.json 中可能定义的自定义位置
            self.logger.info(f"目标位置 '{target_location}' 不属于标准分类，将作为根目录 '{self.root_dir}' 下的相对路径 '{target_location}' 处理。")
            final_target_dir = os.path.join(self.root_dir, target_location)

        if not final_target_dir:
            self.logger.error(f"无法确定项目 '{item_title}' 的目标目录，target_location: {target_location}")
            QMessageBox.critical(self, '错误', f"无法确定项目 '{item_title}' 的目标目录。")
            return

        try:
            if not os.path.exists(final_target_dir):
                os.makedirs(final_target_dir, exist_ok=True)
                self.logger.info(f"创建目录: {final_target_dir}")
            if not os.access(final_target_dir, os.W_OK):
                raise PermissionError(f"目录 {final_target_dir} 无写入权限")
        except PermissionError as e:
            self.logger.error(f"目标目录权限错误: {e}")
            QMessageBox.critical(self, '错误', str(e))
            return
        except Exception as e:
            self.logger.error(f"创建目标目录失败: {e}")
            QMessageBox.critical(self, '错误', f"创建目标目录失败: {e}")
            return

        try:
            if is_zipped:
                extract_destination = final_target_dir
                self.logger.info(f"开始解压 '{downloaded_file_path}' 到 '{extract_destination}'")
                
                # 使用zipfile库进行解压，替代patoolib
                if downloaded_file_path.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(downloaded_file_path, 'r') as zip_ref:
                            # 检查是否有权限写入目标目录
                            temp_test_file = os.path.join(extract_destination, '.write_test')
                            try:
                                with open(temp_test_file, 'w') as f:
                                    f.write('test')
                                os.remove(temp_test_file)
                            except Exception as e:
                                raise PermissionError(f"目录 {extract_destination} 无写入权限: {e}")
                                
                            # 解压所有文件
                            zip_ref.extractall(extract_destination)
                            self.logger.info(f"解压完成: '{item_title}' 已解压到 '{extract_destination}'")
                    except zipfile.BadZipFile:
                        raise Exception(f"文件 '{downloaded_file_path}' 不是有效的ZIP文件")
                else:
                    # 尝试使用patoolib处理其他格式的压缩文件
                    try:
                        patoolib.extract_archive(str(downloaded_file_path), outdir=str(extract_destination), verbosity=-1)
                    except patoolib.util.PatoolError as e:
                        raise Exception(f"不支持的压缩格式或解压失败: {e}")
                        
                self.status_label.setText(f'{item_title} 解压完成')
                try:
                    os.remove(downloaded_file_path) # 删除临时下载的压缩文件
                    self.logger.info(f"已删除临时压缩文件: {downloaded_file_path}")
                except Exception as e:
                    self.logger.error(f"删除临时压缩文件 '{downloaded_file_path}' 失败: {e}")
            else: # 非压缩文件，直接移动
                final_file_path = os.path.join(final_target_dir, target_filename)
                if os.path.exists(final_file_path):
                    self.logger.warning(f"目标文件 '{final_file_path}' 已存在，将被覆盖。")
                    # shutil.move 会覆盖文件，如果是目录则会出错，但这里是文件
                self.logger.info(f"开始移动 '{downloaded_file_path}' 到 '{final_file_path}'")
                shutil.move(str(downloaded_file_path), str(final_file_path))
                self.logger.info(f"移动完成: '{item_title}' 已移动到 '{final_file_path}'")
                self.status_label.setText(f'{item_title} 移动完成')
            
            QMessageBox.information(self, '成功', f'{item_title} 处理完成！')

        except PermissionError as e:
            self.logger.error(f"移动/解压文件 '{item_title}' 权限错误: {e}")
            QMessageBox.critical(self, '权限错误', f"处理 '{item_title}' 时发生权限错误: {e}")
        except Exception as e:
            self.logger.error(f"移动/解压文件 '{item_title}' 失败: {e}", exc_info=True)
            QMessageBox.critical(self, '错误', f"处理 '{item_title}' 时发生未知错误: {e}")
            # 保留下载的压缩文件以便用户手动处理

    def start_download(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        
        selected_item_data = selected_items[0].data(0, Qt.UserRole)
        if not selected_item_data:
            QMessageBox.warning(self, '错误', '无法获取选中项目的下载信息。')
            return

        url = selected_item_data.get('download_url')
        target_filename = selected_item_data.get('target_filename')
        target_location = selected_item_data.get('target_location')
        # is_zipped 在 download_finished 中根据 item_data 获取
        item_title = selected_item_data.get('title', '未知项目')

        if not url or not target_filename or not target_location:
            QMessageBox.warning(self, '错误', f'项目 "{item_title}" 的下载信息不完整 (需要 download_url, target_filename, target_location)。')
            return
            
        # 检查是否需要手动下载
        if selected_item_data.get('manual_download_only', False):
            webbrowser.open(url)
            QMessageBox.information(self, '提示', f'已为您打开浏览器下载链接: {url}')
            return

        # 根据 target_location 判断是否需要选择实例
        self.current_instance = None # 重置当前实例
        if target_location.startswith('Servers/{instance_name}'):
            # 使用项目标题作为对话框的提示信息
            category_for_dialog = item_title
            dialog = InstanceSelectionDialog(category_for_dialog, self)
            if dialog.exec_() == QDialog.Accepted:
                current_item = dialog.list_widget.currentItem()
                if current_item:
                    self.current_instance = current_item.text()
                    self.logger.info(f'为 {item_title} 选择了实例: {self.current_instance}')
                else:
                    QMessageBox.warning(self, '提示', '未选择实例，下载取消。')
                    return                    
            else:
                QMessageBox.warning(self, '提示', '未选择实例，下载取消。')
                return
        # 其他 target_location 类型 (如 'Java', 'Database', 'Config/...') 不需要选择实例

        # 处理GitHub镜像源
        if 'github.com' in url and hasattr(self, 'current_mirror') and self.current_mirror:
            original_url = url
            url = url.replace('https://github.com', self.current_mirror)
            self.logger.info(f'使用镜像源: {self.current_mirror} 替换 https://github.com. 原URL: {original_url}, 新URL: {url}')


        # 确定最终保存路径
        # 文件将首先下载到 DownloadTemp 目录
        temp_save_path = os.path.join(self.root_dir, 'DownloadTemp')
        try:
            if not os.path.exists(temp_save_path):
                os.makedirs(temp_save_path)
            if not os.access(temp_save_path, os.W_OK):
                raise PermissionError(f'目录 {temp_save_path} 无写入权限')
        except PermissionError as e:
            self.logger.error(f'下载目录权限错误: {e}')
            QMessageBox.critical(self, '错误', str(e))
            return
        except Exception as e:
            self.logger.error(f'创建下载目录失败: {e}')
            QMessageBox.critical(self, '错误', f'创建下载目录失败: {e}')
            return

        # 实际下载的文件名，使用 target_filename
        actual_save_file_path = os.path.join(temp_save_path, target_filename)

        # 检查是否已有相同任务在下载
        for thread, (item_title_in_queue, _) in self.download_queue.items():
            if item_title_in_queue == selected_item_data['title'] and thread.isRunning():
                QMessageBox.information(self, '提示', f'{selected_item_data["title"]} 已在下载队列中。')
                return

        self.logger.info(f'准备下载: {selected_item_data["title"]} 从 {url} 到 {actual_save_file_path}')
        self.status_label.setText(f'正在下载 {selected_item_data["title"]}...')
        self.progress_bar.setValue(0)
        
        thread = DownloadThread(url, actual_save_file_path)
        thread.progress_signal.connect(self.update_progress)
        thread.finished_signal.connect(self.download_finished)
        # 存储项目名和保存路径，用于 download_finished 中查找元数据
        self.download_queue[thread] = (selected_item_data['title'], actual_save_file_path) 
        thread.start()

    def update_progress(self, value):
        total = sum(t.isRunning() for t in self.download_queue.keys())
        if total > 0:
            current_progress = self.progress_bar.value()
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.reset()

    def download_finished(self, msg):
        if msg.startswith('Error'):
            self.logger.error(f'下载失败: {msg}')
            QMessageBox.critical(self, '错误', msg)
            self.status_label.setText(msg)
            self.progress_bar.reset()
            # 尝试移除下载队列中的线程
            finished_thread = None
            for thread, (item_name, path) in list(self.download_queue.items()): # 使用list迭代以允许修改
                if not thread.isRunning(): # 找到第一个非运行线程
                    # 无法直接通过msg（如 'Error:权限不足'）关联到特定path
                    # 因此，如果发生错误，我们可能需要更智能地清理，或者接受可能清理错误的线程
                    self.logger.warning(f'下载线程 {item_name} 可能已出错并停止。')
                    finished_thread = thread
                    break 
            if finished_thread and finished_thread in self.download_queue:
                del self.download_queue[finished_thread]
                self.logger.info(f'从队列中移除了可能出错的下载任务: {self.download_queue.get(finished_thread, ("未知项目",))[0]}')
            
            # 检查是否所有下载都完成了
            if not any(thread.isRunning() for thread in self.download_queue.keys()):
                self.progress_bar.reset()
                self.status_label.setText('部分下载失败，队列已空')
                self.current_instance = None # 重置当前实例
            return

        self.logger.success(f'文件下载完成: {msg}') # msg 现在是下载文件的完整路径
        self.status_label.setText(f'文件下载完成: {os.path.basename(msg)}')
        self.progress_bar.reset()

        downloaded_file_path = msg
        downloaded_file_name = os.path.basename(downloaded_file_path)

        # 从下载队列中找到对应的项目元数据和线程
        item_data = None
        item_name_for_tree_lookup = None
        finished_thread_key = None

        for thread, (name, path) in self.download_queue.items():
            if path == downloaded_file_path and not thread.isRunning(): # 确保是已完成的线程
                item_name_for_tree_lookup = name
                finished_thread_key = thread
                break
        
        if item_name_for_tree_lookup:
            # 通过 item_name_for_tree_lookup (即 selected_item_data['name']) 在树中找到对应的 QTreeWidgetItem
            items = self.tree.findItems(item_name_for_tree_lookup, Qt.MatchExactly | Qt.MatchRecursive, 0)
            if items:
                item_data = items[0].data(0, Qt.UserRole)
            else:
                self.logger.error(f'在树中未找到与名称 "{item_name_for_tree_lookup}" 匹配的项目以下载元数据。')
        
        if finished_thread_key and finished_thread_key in self.download_queue:
            del self.download_queue[finished_thread_key]
            self.logger.info(f'已完成并从队列移除下载任务: {item_name_for_tree_lookup}')

        if not item_data:
            self.logger.error(f'无法找到 {downloaded_file_name} (原始名称: {item_name_for_tree_lookup}) 的下载元数据。')
            QMessageBox.critical(self, '错误', f'处理下载文件 {downloaded_file_name} 失败：未找到元数据。')
            if os.path.exists(downloaded_file_path):
                try:
                    os.remove(downloaded_file_path)
                    self.logger.info(f'已删除未找到元数据的临时文件: {downloaded_file_path}')
                except Exception as e_rm:
                    self.logger.error(f'删除临时文件失败: {downloaded_file_path}, 错误: {e_rm}')
            return

        is_zipped = item_data.get('is_zipped', False)
        extracted_path = None

        if is_zipped:
            try:
                # 解压目标文件夹名基于 target_filename (下载时的文件名)
                extract_to_dir_name = f"{os.path.splitext(item_data.get('target_filename'))[0]}_extracted"
                extract_to_full_path = os.path.join(os.path.dirname(downloaded_file_path), extract_to_dir_name)
                os.makedirs(extract_to_full_path, exist_ok=True)
                self.logger.info(f'开始解压 {downloaded_file_path} 到 {extract_to_full_path}')
                self.status_label.setText(f'正在解压 {item_data.get("title")}...') 
                
                # 使用zipfile库进行解压，替代patoolib
                if downloaded_file_path.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(downloaded_file_path, 'r') as zip_ref:
                            # 检查是否有权限写入目标目录
                            temp_test_file = os.path.join(extract_to_full_path, '.write_test')
                            try:
                                with open(temp_test_file, 'w') as f:
                                    f.write('test')
                                os.remove(temp_test_file)
                            except Exception as e:
                                raise PermissionError(f"目录 {extract_to_full_path} 无写入权限: {e}")
                                
                            # 解压所有文件
                            zip_ref.extractall(extract_to_full_path)
                            self.logger.success(f'文件解压完成: {extract_to_full_path}')
                    except zipfile.BadZipFile:
                        raise Exception(f"文件 '{downloaded_file_path}' 不是有效的ZIP文件")
                else:
                    # 尝试使用patoolib处理其他格式的压缩文件
                    try:
                        patoolib.extract_archive(downloaded_file_path, outdir=extract_to_full_path, verbosity=-1)
                        self.logger.success(f'文件解压完成: {extract_to_full_path}')
                    except patoolib.util.PatoolError as e:
                        raise Exception(f"不支持的压缩格式或解压失败: {e}")
                
                extracted_path = extract_to_full_path
                # 传递 item_data 给 move_file
                self.move_file(extracted_path, item_data)
                try:
                    os.remove(downloaded_file_path) 
                    self.logger.info(f'已删除原始压缩包: {downloaded_file_path}')
                except Exception as e:
                    self.logger.error(f'删除原始压缩包失败: {downloaded_file_path},错误: {e}')

            except Exception as e:
                self.logger.error(f'解压过程中发生错误 ({item_data.get("title")}): {e}')
                QMessageBox.warning(self, '解压失败', f'解压 {item_data.get("title")} 失败: {e}\n将尝试直接移动原始文件。')
                self.move_file(downloaded_file_path, item_data) # 直接移动原始文件
        else:
            # 非压缩文件，直接移动，传递 item_data
            self.move_file(downloaded_file_path, item_data)

        # 再次检查并清理下载队列
        active_threads = False
        for thread in list(self.download_queue.keys()): # 使用list迭代以允许修改
            if not thread.isRunning():
                del self.download_queue[thread]
            else:
                active_threads = True
        if not active_threads:
            self.progress_bar.reset()
            self.status_label.setText('所有下载已完成或队列已空')
            self.current_instance = None # 所有操作完成后重置当前实例