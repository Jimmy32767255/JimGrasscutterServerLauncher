from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QInputDialog, QDialog, QFormLayout, QLineEdit, QFileDialog, QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os, json
from pathlib import Path
from loguru import logger
import shutil
import psutil
from config_editor import ConfigEditorDialog
from plugin_manager import PluginManagerDialog # 导入插件管理器对话框


class InstanceConfigDialog(QDialog):
    def __init__(self, parent=None, config=None, root_dir=None):
        super().__init__(parent)
        self.root_dir = root_dir or parent.root_dir
        self.setWindowTitle('实例配置')
        self.setWindowModality(Qt.ApplicationModal)
        layout = QFormLayout()

        self.global_config = self.load_global_config()

        self.instance_name = QLineEdit()
        self.java_path = QLineEdit()
        self.java_path.setPlaceholderText('留空使用全局配置')
        self.jvm_pre_args = QLineEdit()
        self.jvm_pre_args.setPlaceholderText('留空使用全局配置')
        self.jvm_post_args = QLineEdit()
        self.jvm_post_args.setPlaceholderText('留空使用全局配置')
        self.grasscutter_path = QLineEdit()
        self.grasscutter_path.setPlaceholderText('Grasscutter.jar路径')
        self.grasscutter_path_btn = QPushButton('选择Grasscutter.jar')
        self.grasscutter_path_btn.clicked.connect(self.select_grasscutter_path)

        layout.addRow('实例名称:', self.instance_name)
        layout.addRow('Java.exe路径:', self.java_path)
        layout.addRow('jvm前置参数:', self.jvm_pre_args)
        layout.addRow('jvm后置参数:', self.jvm_post_args)
        layout.addRow('Grasscutter.jar路径:', self.grasscutter_path)
        layout.addRow(self.grasscutter_path_btn)

        self.accept_btn = QPushButton('保存')
        self.accept_btn.clicked.connect(self.accept)
        layout.addRow(self.accept_btn)

        self.setLayout(layout)

        if config:
            self.instance_name.setText(config.get('instance_name', ''))
            java_path = config.get('java_path', '')
            if java_path == '':
                java_path = self.global_config['default_java_version']
                if java_path == '':
                    java_path = self.find_latest_java()
            self.java_path.setText(java_path)
            self.jvm_pre_args.setText(' '.join(config.get('jvm_pre_args', [])))
            self.jvm_post_args.setText(' '.join(config.get('jvm_post_args', [])))
            self.grasscutter_path.setText(config.get('grasscutter_path', ''))

    def load_global_config(self):
        logger.info('加载全局配置')
        global_config_path = os.path.join(self.root_dir, 'Config', 'JGSL.json')
        if os.path.exists(global_config_path):
            with open(global_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'default_java_version': '',
            'default_jvm_pre_args': [],
            'default_jvm_post_args': []
        }

    def find_latest_java(self):
        java_dir = os.path.join(self.root_dir, 'Java')
        if not os.path.exists(java_dir):
            return ''
        latest_version = None
        latest_version_path = None
        for version_dir in os.listdir(java_dir):
            version_path = os.path.join(java_dir, version_dir)
            if os.path.isdir(version_path):
                java_executable = os.path.join(version_path, 'bin', 'java.exe')
                if os.path.exists(java_executable):
                    if latest_version is None or version_dir > latest_version:
                        latest_version = version_dir
                        latest_version_path = java_executable
        return latest_version_path or ''

    def select_grasscutter_path(self):
        file_name, _ = QFileDialog.getOpenFileName(self, '选择Grasscutter.jar文件', '', 'JAR文件 (*.jar)')
        if file_name:
            self.grasscutter_path.setText(file_name)
            logger.debug(f'选择Grasscutter路径: {file_name}')

    def accept(self):
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        instance_name = self.instance_name.text()
        if any(char in instance_name for char in invalid_chars):
            QMessageBox.warning(self, '错误', '实例名称包含非法字符: \\ / : * ? " < > |')
            return
        if not Path(self.grasscutter_path.text()).exists():
            QMessageBox.warning(self, '错误', 'Grasscutter.jar路径不存在')
            return
        self.instance_config = {
            'instance_name': instance_name,
            'java_path': self.java_path.text() or self.global_config['default_java_version'],
            'jvm_pre_args': self.jvm_pre_args.text().split() or self.global_config['default_jvm_pre_args'],
            'jvm_post_args': self.jvm_post_args.text().split() or self.global_config.get('default_jvm_post_args', []),
            'grasscutter_path': self.grasscutter_path.text(),
            'cluster_role': 'HYBRID'  # 确保新实例默认为独立角色
        }
        super().accept()


class ManageTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")  # 设置背景透明 
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.server_list = QListWidget()
        self.create_btn = QPushButton('新建实例')
        self.edit_config_btn = QPushButton('编辑Grasscutter配置文件')
        self.edit_btn = QPushButton('修改实例配置')
        self.delete_btn = QPushButton('删除实例')
        self.clone_btn = QPushButton('克隆实例')
        self.plugin_btn = QPushButton('插件管理')

        # 用于在进度对话框中显示状态和当前文件
        self.current_operation_status = ""
        self.current_operation_file = ""

        layout = QVBoxLayout()
        layout.addWidget(self.server_list)

        # 第1行布局
        button_1_layout = QHBoxLayout()
        button_1_layout.addWidget(self.create_btn)
        button_1_layout.addWidget(self.edit_btn)
        button_1_layout.addWidget(self.clone_btn)
        button_1_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_1_layout)

        # 第2行按钮布局
        button_2_layout = QHBoxLayout()
        button_2_layout.addWidget(self.plugin_btn)
        button_2_layout.addWidget(self.edit_config_btn)
        layout.addLayout(button_2_layout)

        self.setLayout(layout)

        # 自动扫描实例
        servers_path = os.path.join(self.root_dir, "Servers")
        if not os.path.exists(servers_path):
            os.makedirs(servers_path, exist_ok=True)
        valid_servers = [
            instance_name for instance_name in os.listdir(servers_path)
            if os.path.isdir(os.path.join(servers_path, instance_name)) and os.path.exists(os.path.join(servers_path, instance_name, 'JGSL', 'Config.json'))
        ]
        self.server_list.addItems(valid_servers)

        self.create_btn.clicked.connect(self.create_instance)
        self.edit_config_btn.clicked.connect(self.open_config_editor)
        self.edit_btn.clicked.connect(self.edit_instance)
        self.delete_btn.clicked.connect(self.delete_instance)
        self.clone_btn.clicked.connect(self.clone_instance) # 连接克隆按钮的信号
        self.plugin_btn.clicked.connect(self.open_plugin_manager) # 连接插件管理按钮的信号

    def _update_progress_dialog_label(self):
        # 更新进度对话框的标签文本
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            text_parts = []
            if self.current_operation_status:
                text_parts.append(self.current_operation_status)
            if self.current_operation_file:
                text_parts.append(f"当前文件: {self.current_operation_file}")
            self.progress_dialog.setLabelText("\n".join(text_parts) + "")

    def _handle_progress_update(self, value, status_text):
        # 处理来自线程的进度更新信号
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.current_operation_status = status_text
            self._update_progress_dialog_label()

    def _handle_current_file_update(self, file_name):
        # 处理来自线程的当前文件更新信号
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.current_operation_file = file_name
            self._update_progress_dialog_label()

    # 异步操作工作线程
    class OperationThread(QThread):
        progress_signal = pyqtSignal(int, str) # 当前进度值, 状态文本
        current_file_signal = pyqtSignal(str) # 新增信号:当前正在处理的文件名
        finished_signal = pyqtSignal(bool, str) # 是否成功, 消息文本
        _should_stop = False # 用于外部请求停止线程

        def __init__(self, operation_type, **kwargs):
            super().__init__()
            self.operation_type = operation_type
            self.kwargs = kwargs
            self._should_stop = False

        def request_stop(self):
            self._should_stop = True
            logger.info("请求停止操作线程")

        def _get_total_files_dirs(self, path):
            total = 0
            for _, dirs, files in os.walk(path):
                if self._should_stop: return -1 # 检查是否需要停止
                total += len(dirs) + len(files)
            return total

        def _clone_instance(self):
            original_instance_dir = self.kwargs['original_instance_dir']
            new_instance_dir = self.kwargs['new_instance_dir']
            new_instance_name = self.kwargs['new_instance_name']
            original_instance_name = self.kwargs['original_instance_name']

            try:
                self.progress_signal.emit(0, f'正在准备克隆 "{original_instance_name}" 到 "{new_instance_name}"...')
                if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return

                total_items = self._get_total_files_dirs(original_instance_dir)
                if total_items == -1: self.finished_signal.emit(False, '操作已取消'); return # 检查是否在计算总数时被取消
                
                # 复制文件阶段占总进度的 0% - 80%
                # 更新配置文件阶段占总进度的 80% - 100%
                copied_items = 0

                # 创建目标根目录
                if not os.path.exists(new_instance_dir):
                    os.makedirs(new_instance_dir)
                    self.current_file_signal.emit(f'创建目录: {new_instance_dir}')

                for src_dir, dirs, files in os.walk(original_instance_dir):
                    if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                    dst_dir = src_dir.replace(original_instance_dir, new_instance_dir, 1)

                    for d in dirs:
                        if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                        dst_path = os.path.join(dst_dir, d)
                        if not os.path.exists(dst_path):
                            os.makedirs(dst_path)
                        self.current_file_signal.emit(f'创建目录: {d}')
                        copied_items += 1
                        progress = int((copied_items / total_items) * 80) if total_items > 0 else 0
                        self.progress_signal.emit(progress, f'正在复制目录 ({copied_items}/{total_items})...')

                    for f_name in files:
                        if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                        src_file = os.path.join(src_dir, f_name)
                        dst_file = os.path.join(dst_dir, f_name)
                        shutil.copy2(src_file, dst_file)
                        self.current_file_signal.emit(f'复制文件: {f_name}')
                        copied_items += 1
                        progress = int((copied_items / total_items) * 80) if total_items > 0 else 0
                        self.progress_signal.emit(progress, f'正在复制文件 ({copied_items}/{total_items})...')
                
                if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                self.progress_signal.emit(80, f'文件复制完成，正在更新配置文件...')
                self.current_file_signal.emit('更新 JGSL/Config.json')

                cloned_config_path = os.path.join(new_instance_dir, 'JGSL', 'Config.json')
                if os.path.exists(cloned_config_path):
                    try:
                        with open(cloned_config_path, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        if 'instance_name' in config_data:
                            config_data['instance_name'] = new_instance_name
                            with open(cloned_config_path, 'w', encoding='utf-8') as f:
                                json.dump(config_data, f, ensure_ascii=False, indent=4)
                        self.progress_signal.emit(95, f'配置文件更新完毕')
                    except Exception as e:
                        logger.error(f'更新克隆实例 "{new_instance_name}" 配置文件失败: {e}')
                        self.finished_signal.emit(True, f'实例克隆完成，但更新配置文件失败: {e}')
                        return
                else:
                    self.progress_signal.emit(95, f'克隆实例的 JGSL/Config.json 不存在，跳过更新')
                
                if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                self.progress_signal.emit(100, f'克隆完成!')
                self.finished_signal.emit(True, f'实例 "{original_instance_name}" 已成功克隆为 "{new_instance_name}" ')
            except Exception as e:
                logger.error(f'克隆实例 "{original_instance_name}" 失败: {e}')
                self.finished_signal.emit(False, f'克隆实例失败: {e}')

        def _delete_instance(self):
            instance_dir = self.kwargs['instance_dir']
            instance_name = self.kwargs['instance_name']
            try:
                self.progress_signal.emit(0, f'正在准备删除实例 "{instance_name}"...')
                if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return

                total_items = self._get_total_files_dirs(instance_dir)
                if total_items == -1: self.finished_signal.emit(False, '操作已取消'); return
                deleted_items = 0

                # shutil.rmtree 不能很好地报告单个文件进度，所以我们手动删除
                for root, dirs, files in os.walk(instance_dir, topdown=False): # topdown=False 确保先删除子内容
                    if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                    for name in files:
                        if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                        file_path = os.path.join(root, name)
                        try:
                            os.remove(file_path)
                            self.current_file_signal.emit(f'删除文件: {name}')
                            deleted_items += 1
                            progress = int((deleted_items / total_items) * 100) if total_items > 0 else 0
                            self.progress_signal.emit(progress, f'正在删除文件 ({deleted_items}/{total_items})...')
                        except OSError as e:
                            logger.error(f"删除文件 {file_path} 失败: {e}")
                            # 可以选择在这里停止或继续

                    if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                    for name in dirs:
                        if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                        dir_path = os.path.join(root, name)
                        try:
                            os.rmdir(dir_path) # rmdir 只能删除空目录
                            self.current_file_signal.emit(f'删除目录: {name}')
                            deleted_items += 1
                            progress = int((deleted_items / total_items) * 100) if total_items > 0 else 0
                            self.progress_signal.emit(progress, f'正在删除目录 ({deleted_items}/{total_items})...')
                        except OSError as e:
                            logger.error(f"删除目录 {dir_path} 失败: {e}")
                    
                    if self._should_stop: self.finished_signal.emit(False, '操作已取消'); return
                    # 最后删除实例根目录本身
                    try:
                        os.rmdir(instance_dir)
                        self.current_file_signal.emit(f'删除实例根目录: {instance_name}')
                    except OSError as e:
                        logger.error(f"删除实例根目录 {instance_dir} 失败: {e}")

                    self.progress_signal.emit(100, f'删除完成!')
                    self.finished_signal.emit(True, f'实例 {instance_name} 已成功删除')

            except Exception as e:
                logger.error(f'删除实例 {instance_name} 失败: {e}')
                self.finished_signal.emit(False, f'删除实例失败: {e}')

        def run(self):
            if self.operation_type == "clone":
                self._clone_instance()
            elif self.operation_type == "delete":
                self._delete_instance()

    def open_plugin_manager(self):
        logger.info("打开插件管理器")
        current_item = self.server_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '提示', '请先选择一个实例')
            return
        instance_name = current_item.text()
        instance_dir = os.path.join(self.root_dir, 'Servers', instance_name)
        plugin_manager_dialog = PluginManagerDialog(self, instance_name, instance_dir)
        plugin_manager_dialog.exec_()

    def create_instance(self):
        dialog = InstanceConfigDialog(self, root_dir=self.root_dir)
        if dialog.exec_():
            self.save_config(dialog.instance_config, is_new=True)

    def open_config_editor(self):
        current_item = self.server_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请选择一个实例')
            return
        instance_name = current_item.text()
        instance_dir = os.path.join(self.root_dir, 'Servers', instance_name)
        config_path = os.path.join(instance_dir, 'config.json')
        if not os.path.exists(config_path):
            QMessageBox.warning(self, '错误', 'config.json不存在')
            return
        config_editor = ConfigEditorDialog(self, config_path)
        config_editor.exec_()

    def edit_instance(self):
        current_item = self.server_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请选择一个实例')
            return
        instance_name = current_item.text()
        instance_dir = os.path.join(self.root_dir, 'Servers', instance_name)
        config_path = os.path.join(instance_dir, 'JGSL', 'Config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"实例配置文件 {config_path} 解析失败: {e}")
            QMessageBox.warning(self, '错误', f"实例配置文件 {config_path} 解析失败")
            return
        except Exception as e:
            logger.error(f"读取实例配置文件 {config_path} 时发生未知错误: {e}")
            QMessageBox.warning(self, '错误', f"读取实例配置文件 {config_path} 时发生未知错误")
            return
        config['instance_name'] = instance_name
        original_instance_name = instance_name # 保存原始实例名称
        dialog = InstanceConfigDialog(self, config, root_dir=self.root_dir)
        if dialog.exec_():
            self.save_config(dialog.instance_config, is_new=False, original_instance_name=original_instance_name)

    def save_config(self, config, is_new=True, original_instance_name=None):
        logger.info('正在保存实例配置')
        new_instance_name = config['instance_name']
        new_instance_dir = os.path.join(self.root_dir, 'Servers', new_instance_name)
        config_dir = os.path.join(new_instance_dir, 'JGSL')
        config_path = os.path.join(config_dir, 'Config.json')

        # 处理重命名逻辑
        if not is_new and original_instance_name and original_instance_name != new_instance_name:
            original_instance_dir = os.path.join(self.root_dir, 'Servers', original_instance_name)
            if os.path.exists(original_instance_dir):
                try:
                    # 检查新名称是否已存在
                    if os.path.exists(new_instance_dir):
                        QMessageBox.warning(self, '错误', f'实例名称 "{new_instance_name}" 已存在，请选择其他名称。')
                        return
                    # 重命名文件夹
                    shutil.move(original_instance_dir, new_instance_dir)
                    logger.info(f'实例文件夹已从 "{original_instance_name}" 重命名为 "{new_instance_name}"')
                except OSError as e:
                    logger.error(f'重命名实例文件夹失败: {e}')
                    QMessageBox.warning(self, '错误', f'重命名实例文件夹失败: {e}')
                    return
            else:
                logger.warning(f'原始实例文件夹 "{original_instance_dir}" 不存在，无法重命名。将创建新实例。')
                # 如果原始文件夹不存在，则按新实例处理，确保目录存在
                os.makedirs(config_dir, exist_ok=True)
        else:
            # 确保新实例或未重命名的实例目录存在
            os.makedirs(config_dir, exist_ok=True)

        if is_new and os.path.exists(os.path.join(new_instance_dir, 'JGSL', 'Config.json')):
            # 检查新实例的配置文件是否存在，而不是检查目录是否存在
            # 因为重命名逻辑可能已经创建了目录
            QMessageBox.warning(self, '错误', '实例已存在')
            return
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            if is_new:
                # 创建标准目录结构
                dirs_to_create = ['resources', 'data', 'packets', 'plugins', 'cache']
                for directory in dirs_to_create:
                    dir_path = Path(new_instance_dir) / directory # 使用新的实例目录
                    try:
                        dir_path.mkdir(exist_ok=True)
                    except (PermissionError, FileExistsError) as e:
                        logger.error(f"创建目录 {dir_path} 失败: {e}")
                        QMessageBox.warning(self, '错误', f"创建目录 {dir_path} 失败: {e}")
                logger.success("成功创建实例目录结构")
            self.refresh_server_list()
            logger.success(f'实例 {new_instance_name} 配置已保存') # 使用新的实例名称
        except OSError as e:
            logger.error(f"保存实例配置文件失败 | 路径: {config_path} | 错误: {str(e)}")
            QMessageBox.warning(self, '错误', f'保存配置文件失败，请检查目录权限\n错误详情: {str(e)}')
            return

    def refresh_server_list(self):
        self.server_list.clear()
        servers_path = os.path.join(self.root_dir, 'Servers')
        if os.path.exists(servers_path):
            for instance_name in os.listdir(servers_path):
                instance_dir = os.path.join(servers_path, instance_name)
                if os.path.isdir(instance_dir) and os.path.exists(os.path.join(instance_dir, 'JGSL')):
                    self.server_list.addItem(instance_name)

    def clone_instance(self):
        current_item = self.server_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请选择一个要克隆的实例')
            return
        original_instance_name = current_item.text()

        new_instance_name, ok = QInputDialog.getText(self, '克隆实例', f'为克隆的实例 "{original_instance_name}" 输入新名称:')
        if ok and new_instance_name:
            if new_instance_name == original_instance_name:
                QMessageBox.warning(self, '错误', '新实例名称不能与原实例名称相同')
                return
            invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
            if any(char in new_instance_name for char in invalid_chars):
                QMessageBox.warning(self, '错误', '实例名称包含非法字符: \\ / : * ? " < > |')
                return
            
            servers_path = os.path.join(self.root_dir, "Servers")
            original_instance_dir = os.path.join(servers_path, original_instance_name)
            new_instance_dir = os.path.join(servers_path, new_instance_name)

            if os.path.exists(new_instance_dir):
                QMessageBox.warning(self, '错误', f'实例 "{new_instance_name}" 已存在')
                return

            self.progress_dialog = QProgressDialog(f'正在克隆实例 "{original_instance_name}" 为 "{new_instance_name}"...', '取消', 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumDuration(0) # 立即显示
            self.progress_dialog.setValue(0)
            self.current_operation_status = f'准备克隆 "{original_instance_name}" 到 "{new_instance_name}"...'
            self.current_operation_file = ""
            self._update_progress_dialog_label()

            self.operation_thread = self.OperationThread(
                operation_type="clone",
                original_instance_dir=original_instance_dir,
                new_instance_dir=new_instance_dir,
                new_instance_name=new_instance_name,
                original_instance_name=original_instance_name
            )
            self.operation_thread.progress_signal.connect(self._handle_progress_update)
            self.operation_thread.current_file_signal.connect(self._handle_current_file_update)
            self.operation_thread.finished_signal.connect(self.on_operation_finished)
            self.progress_dialog.canceled.connect(self.operation_thread.request_stop)
            self.operation_thread.start()
            self.progress_dialog.exec_() # 显示并等待对话框关闭
        elif ok and not new_instance_name:
            QMessageBox.warning(self, '提示', '实例名称不能为空')

    def delete_instance(self):
        current_item = self.server_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请选择一个要删除的实例')
            return
        instance_name = current_item.text()
        reply = QMessageBox.question(self, '确认删除', f'确定要删除实例 "{instance_name}" 吗？此操作不可恢复！', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            instance_dir = os.path.join(self.root_dir, "Servers", instance_name)
            
            self.progress_dialog = QProgressDialog(f'正在删除实例 "{instance_name}"...', '取消', 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)
            self.current_operation_status = f'准备删除实例 "{instance_name}"...'
            self.current_operation_file = ""
            self._update_progress_dialog_label()

            self.operation_thread = self.OperationThread(
                operation_type="delete",
                instance_dir=instance_dir,
                instance_name=instance_name
            )
            self.operation_thread.progress_signal.connect(self._handle_progress_update)
            self.operation_thread.current_file_signal.connect(self._handle_current_file_update)
            self.operation_thread.finished_signal.connect(self.on_operation_finished)
            self.progress_dialog.canceled.connect(self.operation_thread.request_stop)
            self.operation_thread.start()
            self.progress_dialog.exec_()

    def on_operation_finished(self, success, message):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close() # 关闭进度对话框
            self.progress_dialog = None # 清理引用
        
        self.current_operation_status = ""
        self.current_operation_file = ""

        if success:
            QMessageBox.information(self, '操作完成', message + "")
            self.refresh_server_list() # 刷新列表
        else:
            QMessageBox.warning(self, '操作失败', message + "")
        logger.info(message)
        self.operation_thread = None # 清理线程引用

    def refresh_server_list(self):
        self.server_list.clear()
        servers_path = os.path.join(self.root_dir, 'Servers')
        if os.path.exists(servers_path):
            for instance_name in os.listdir(servers_path):
                instance_dir = os.path.join(servers_path, instance_name)
                if os.path.isdir(instance_dir) and os.path.exists(os.path.join(instance_dir, 'JGSL')):
                    self.server_list.addItem(instance_name)

    def is_instance_running(self, instance_name):
        # 检查实例是否正在运行的逻辑 (基于之前的代码，可能需要调整以适应 JGSL 的具体情况)
        # 这里的实现方式是检查是否有Java进程的命令行参数包含了该实例的路径特征
        # 注意:这可能不是100%准确，但对于大多数情况应该有效
        instance_server_path_part = os.path.join('Servers', instance_name).replace('\\', '/') # 规范化路径分隔符
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] and proc.info['name'].lower() == 'java.exe':
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        # 检查命令行参数中是否包含实例路径相关的特征字符串
                        # 例如，Grasscutter.jar的路径或者实例的特定配置
                        for arg in cmdline:
                            if instance_server_path_part in arg.replace('\\', '/'):
                                logger.info(f"检测到实例 {instance_name} 正在运行，PID: {proc.info['pid']}")
                                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.warning(f"检查进程时出错: {e}")
        return False