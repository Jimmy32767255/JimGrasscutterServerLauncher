from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QTabWidget, QCheckBox, QLineEdit, QListWidgetItem, 
    QMessageBox, QSizePolicy
)
from PyQt5 import QtCore
import os
import json
from loguru import logger
import re

class ClusterConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('创建/编辑集群')
        self.resize(800, 600)

        # 可用服务器列表
        self.available_servers_list = QListWidget()
        available_servers_layout = QVBoxLayout()
        available_servers_layout.addWidget(QLabel('可用服务器实例:'))
        available_servers_layout.addWidget(self.available_servers_list)

        # 添加/移除按钮
        self.add_to_cluster_btn = QPushButton('加入集群 ↑')
        self.remove_from_cluster_btn = QPushButton('↓ 移出集群')
        middle_buttons_layout = QHBoxLayout()
        middle_buttons_layout.addWidget(self.add_to_cluster_btn)
        middle_buttons_layout.addWidget(self.remove_from_cluster_btn)

        # 使用 QTabWidget 实现标签页配置
        self.config_tabs = QTabWidget()

        # -- 调度标签页 --
        dispatch_tab = QWidget()
        dispatch_layout = QVBoxLayout(dispatch_tab) # 直接将布局设置给父控件
        self.dispatch_server_list = QListWidget() # 用于显示集群内的调度服务器
        self.dispatch_server_list.setSizePolicy(self.dispatch_server_list.sizePolicy().horizontalPolicy(), QSizePolicy.Expanding)

        self.dispatch_select_btn = QPushButton('选定为调度服务器')
        self.dispatch_select_btn.clicked.connect(self.select_dispatch_server)

        self.use_internal_dispatch_checkbox = QCheckBox('使用内置调度')
        self.use_internal_dispatch_checkbox.stateChanged.connect(self.toggle_internal_dispatch)

        # 顶部布局:列表和选择标签
        dispatch_layout.addWidget(QLabel("调度服务器列表:"))
        dispatch_layout.addWidget(self.dispatch_server_list, 1) # stretch factor 为 1，使其占用更多垂直空间
        dispatch_layout.addWidget(self.dispatch_select_btn) # 按钮放在列表下方

        # 底部布局:复选框
        dispatch_bottom_layout = QHBoxLayout()
        dispatch_bottom_layout.addWidget(self.use_internal_dispatch_checkbox)
        dispatch_bottom_layout.addStretch()

        dispatch_layout.addLayout(dispatch_bottom_layout)
        
        self.config_tabs.addTab(dispatch_tab, '调度')

        # -- 游戏标签页 --
        game_tab = QWidget()
        game_main_layout = QVBoxLayout()

        # 游戏服务器列表
        game_server_area_layout = QVBoxLayout()
        self.game_server_list = QListWidget()
        game_server_area_layout.addWidget(QLabel("集群内游戏服务器:"))
        game_server_area_layout.addWidget(self.game_server_list)
        game_main_layout.addLayout(game_server_area_layout, 1)

        # 添加/移除按钮 (从主布局移入)
        game_main_layout.addLayout(middle_buttons_layout)

        # 可用服务器列表 (从主布局移入)
        game_main_layout.addLayout(available_servers_layout, 1)

        # 游戏标签页底部的按钮
        game_bottom_widget = QWidget()
        game_bottom_layout = QHBoxLayout(game_bottom_widget)
        game_bottom_layout.setContentsMargins(0, 10, 0, 0)
        self.config_title_btn = QPushButton('配置标题')
        self.config_title_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        game_bottom_layout.addWidget(self.config_title_btn) # 配置标题按钮填满宽度
        game_server_area_layout.addWidget(game_bottom_widget)

        game_main_layout.addLayout(game_server_area_layout, 1)

        game_tab.setLayout(game_main_layout) # 设置游戏标签页的布局
        self.config_tabs.addTab(game_tab, '游戏')

        # -- 其它标签页 --
        other_tab = QWidget()
        other_layout = QVBoxLayout()
        self.cluster_name_input = QLineEdit()
        self.cluster_name_input.setPlaceholderText('请输入集群名称')
        self.game_server_count_label = QLabel('游戏服务器总数: N/A')
        other_bottom_widget = QWidget()
        other_bottom_layout = QHBoxLayout(other_bottom_widget)
        other_bottom_layout.setContentsMargins(0, 10, 0, 0)
        other_bottom_layout.addStretch()
        other_layout.addWidget(QLabel('请输入集群名称:'))
        other_layout.addWidget(self.cluster_name_input)
        other_layout.addStretch()
        other_layout.addWidget(self.game_server_count_label)
        other_layout.addWidget(other_bottom_widget)
        other_tab.setLayout(other_layout)
        self.config_tabs.addTab(other_tab, '其它')

        # 主布局
        main_columns_layout = QHBoxLayout()
        main_columns_layout.addWidget(self.config_tabs, 1) # TabWidget 占据所有空间

        # 底部按钮 (主对话框底部)
        self.ok_btn = QPushButton('确定')
        self.cancel_btn = QPushButton('取消')
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.addStretch()
        bottom_btn_layout.addWidget(self.ok_btn)
        bottom_btn_layout.addWidget(self.cancel_btn)

        # 整体布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(main_columns_layout)
        main_layout.addLayout(bottom_btn_layout)
        self.setLayout(main_layout)

        # 信号连接
        self.ok_btn.clicked.connect(self.accept) # 主确定按钮
        self.cancel_btn.clicked.connect(self.reject) # 主取消按钮
        self.add_to_cluster_btn.clicked.connect(self.add_server_to_cluster)
        self.remove_from_cluster_btn.clicked.connect(self.remove_server_from_cluster)
        self.config_title_btn.clicked.connect(self.open_title_config) # 保留标题配置按钮的连接
        self.setModal(True)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        # 存储服务器配置的地方
        self.server_configs = {}
        self.root_dir = parent.root_dir if parent and hasattr(parent, 'root_dir') else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.cluster_config_path = os.path.join(self.root_dir, 'Config', 'cluster-list.json')
        # 加载可用服务器列表 (示例)
        self.load_available_servers()
        # 当标签页内的列表变化时，更新游戏服务器计数
        self.game_server_list.model().rowsInserted.connect(self.update_game_server_count)
        self.game_server_list.model().rowsRemoved.connect(self.update_game_server_count)

    def get_instance_role(self, server_name):
        """获取服务器实例的角色信息
        
        Args:
            server_name (str): 服务器实例名称
            
        Returns:
            str: 服务器角色，可以是'DISPATCH_ONLY', 'GAME_ONLY'或'HYBRID'
        """
        # 尝试从父窗口获取角色信息
        if self.parent() and hasattr(self.parent(), 'get_instance_role'):
            return self.parent().get_instance_role(server_name)
        # 否则返回HYBRID作为默认值
        return 'HYBRID'

    def add_server_to_cluster(self):
        """将选中的可用服务器添加到游戏服务器列表中"""
        selected_items = self.available_servers_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            server_name = item.text()

            # 检查是否已在游戏列表中 (避免重复添加)
            in_game = any(self.game_server_list.item(i).text() == server_name for i in range(self.game_server_list.count()))

            if in_game:
                # 如果已经在游戏列表，只从可用列表移除
                self.available_servers_list.takeItem(self.available_servers_list.row(item))
                continue

            # 从可用列表移除
            row = self.available_servers_list.row(item)
            self.available_servers_list.takeItem(row)

            # 添加到游戏服务器列表
            self.game_server_list.addItem(QListWidgetItem(server_name))

        # 更新游戏服务器计数
        self.update_game_server_count()

    def remove_server_from_cluster(self):
        """将选中的游戏服务器从列表移回到可用列表中"""
        # 此按钮现在固定操作游戏服务器列表
        active_list = self.game_server_list

        selected_items = active_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            server_name = item.text()

            # 从游戏列表移除
            row = active_list.row(item)
            active_list.takeItem(row)

            # 检查是否还在调度列表中
            in_dispatch = any(self.dispatch_server_list.item(i).text() == server_name for i in range(self.dispatch_server_list.count()))

            # 如果调度列表也不包含该服务器了，则添加回可用列表
            if not in_dispatch:
                # 检查是否已在可用列表，避免重复添加
                is_available = any(self.available_servers_list.item(i).text() == server_name for i in range(self.available_servers_list.count()))
                if not is_available:
                    new_item = QListWidgetItem(server_name)
                    role = self.get_instance_role(server_name)
                    if role != 'HYBRID':
                        new_item.setBackground(QtCore.Qt.lightGray)
                        new_item.setToolTip('此服务器可能已属于其他集群或配置为集群角色，加入新集群将覆盖其配置')
                    else:
                        new_item.setBackground(QtCore.Qt.white)
                        new_item.setToolTip('')
                    self.available_servers_list.addItem(new_item)
            # 如果仍在调度列表，则不添加回可用列表

        # 更新游戏服务器计数
        self.update_game_server_count()

    def update_game_server_count(self):
        """更新游戏服务器总数标签"""
        count = self.game_server_list.count()
        self.game_server_count_label.setText(f'游戏服务器总数: {count}')

    def load_available_servers(self):
        """加载可用的服务器实例列表"""
        self.available_servers_list.clear()
        servers_dir = os.path.join(self.root_dir, 'Servers')
        if not os.path.exists(servers_dir):
            return

        # 获取当前集群已包含的所有服务器 (调度+游戏)
        cluster_servers = set()
        for i in range(self.dispatch_server_list.count()):
            cluster_servers.add(self.dispatch_server_list.item(i).text())
        for i in range(self.game_server_list.count()):
            cluster_servers.add(self.game_server_list.item(i).text())

        for server_name in os.listdir(servers_dir):
            server_path = os.path.join(servers_dir, server_name)
            jgsl_config_path = os.path.join(server_path, 'JGSL', 'Config.json')
            if os.path.isdir(server_path) and os.path.exists(jgsl_config_path):
                # 如果服务器不在当前编辑的集群中，才添加到可用列表
                if server_name not in cluster_servers:
                    item = QListWidgetItem(server_name)
                    role = self.get_instance_role(server_name)
                    if role != 'HYBRID':
                        item.setBackground(QtCore.Qt.lightGray)
                        item.setToolTip(f'此服务器当前角色为 {role}，可能已属于其他集群。加入新集群将覆盖其配置。')
                    else:
                        item.setBackground(QtCore.Qt.white)
                        item.setToolTip('可用的独立服务器实例')
                    self.available_servers_list.addItem(item)

    def select_dispatch_server(self):
        """将选中的服务器设为调度服务器"""
        selected = self.dispatch_server_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "警告", "请先在调度服务器列表中选择一个服务器")
            return
        
        server_name = selected.text()
        
        # 标记选中的调度服务器
        for i in range(self.dispatch_server_list.count()):
            item = self.dispatch_server_list.item(i)
            if item.text() == server_name:
                item.setBackground(QtCore.Qt.green)
                item.setToolTip('当前选定的调度服务器')
            else:
                item.setBackground(QtCore.Qt.white)
                item.setToolTip('')
        
        # 更新服务器配置
        if server_name in self.server_configs:
            self.server_configs[server_name]['is_dispatch'] = True
            
    def toggle_internal_dispatch(self, state):
        """切换内置调度功能
        
        Args:
            state: 复选框状态
        """
        
        enable_external = (state != QtCore.Qt.Checked)
        self.dispatch_server_list.setEnabled(enable_external)
        self.dispatch_select_btn.setEnabled(enable_external)

        if state == QtCore.Qt.Checked:
            # 清除调度服务器列表的选中状态和背景色
            self.dispatch_server_list.clearSelection()
            for i in range(self.dispatch_server_list.count()):
                item = self.dispatch_server_list.item(i)
                item.setBackground(QtCore.Qt.white)
                item.setToolTip('')

        
    def open_title_config(self):
        """打开标题配置对话框"""
        from JGSL.config_editor import ConfigEditorDialog
        
        # 获取当前选中的游戏服务器
        selected_items = self.game_server_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先在游戏服务器列表中选择一个服务器")
            return
            
        server_name = selected_items[0].text()
        
        # 创建并显示配置编辑器对话框
        config_path = os.path.join("Servers", server_name, "JGSL", "Config.json")
        dialog = ConfigEditorDialog(self, config_path)
        dialog.exec_()

    def accept(self):
        """处理确定按钮点击事件，保存集群配置"""
        print("主确定按钮点击，开始保存集群配置")
        # 1. 验证集群名称
        cluster_name = self.cluster_name_input.text().strip()
        if not cluster_name:
            QMessageBox.warning(self, "错误", "集群名称不能为空")
            self.config_tabs.setCurrentIndex(2) # 切换到"其它"标签页
            self.cluster_name_input.setFocus()
            return
            
        # 集群名称验证:只能包含字母、数字、下划线和中文
        if not re.match(r'^[\w\u4e00-\u9fa5]+$', cluster_name):
            QMessageBox.warning(self, "错误", "集群名称只能包含字母、数字、下划线和中文")
            self.config_tabs.setCurrentIndex(2)
            self.cluster_name_input.setFocus()
            return

        # 2. 获取调度服务器配置
        dispatch_servers = [self.dispatch_server_list.item(i).text() for i in range(self.dispatch_server_list.count())]
        use_internal = self.use_internal_dispatch_checkbox.isChecked()
        # 验证调度配置 (例如:必须至少有一个调度服务器，除非使用内置)
        if not use_internal and not dispatch_servers:
            QMessageBox.warning(self, "错误", "请指定一个调度服务器，或勾选\"使用内置调度\"")
            self.config_tabs.setCurrentIndex(0) # 切换到"调度"标签页
            return

        # 3. 获取游戏服务器配置
        game_servers = [self.game_server_list.item(i).text() for i in range(self.game_server_list.count())]
        # 获取游戏服务器标题配置 (如果实现了的话)
        # 暂不实现标题配置，保留为空字符串
        title = "" # self.cluster_title_input.text().strip() # 假设有标题输入框

        # 4. 组合集群配置数据
        cluster_config = {
            "name": cluster_name,
            "title": title,
            "dispatch_servers": dispatch_servers,
            "use_internal_dispatch": use_internal,
            "game_servers": game_servers,
        }
        print(f"准备保存的集群配置: {cluster_config}")

        # 5. 调用父窗口的方法来保存或更新集群
        if self.parent() and hasattr(self.parent(), 'save_cluster_config'):
            success = self.parent().save_cluster_config(cluster_config, self.original_cluster_name if hasattr(self, 'original_cluster_name') else None)
            if success:
                super().accept()
            # 如果保存失败，不关闭对话框
        else:
            QMessageBox.critical(self, "错误", "无法调用保存函数，请检查父窗口实现")

    def load_config(self, config):
        """加载集群配置到对话框"""
        print(f"加载集群配置: {config}") # 打印日志以确认加载
        try:
            self.cluster_name_input.setText(config.get('name', ''))
            # self.cluster_title_input.setText(config.get('title', '')) # 如果有标题输入框
            self.use_internal_dispatch_checkbox.setChecked(config.get('use_internal_dispatch', False))

            self.dispatch_server_list.clear()
            dispatch_servers = config.get('dispatch_servers', [])
            print(f"加载调度服务器: {dispatch_servers}")
            for server in dispatch_servers:
                self.dispatch_server_list.addItem(QListWidgetItem(server))
                # 可以在这里标记选定的调度服务器，如果配置中有此信息

            self.game_server_list.clear()
            game_servers = config.get('game_servers', [])
            print(f"加载游戏服务器: {game_servers}")
            for server in game_servers:
                self.game_server_list.addItem(QListWidgetItem(server))

            self.update_game_server_count()
            self.load_available_servers() # 重新加载可用服务器列表，排除当前集群的服务器
            # 记录原始名称，用于编辑时判断是否重命名
            self.original_cluster_name = config.get('name', '')
            print("集群配置加载完成")
        except Exception as e:
            print(f"加载集群配置时出错: {e}") # 使用 print 或 logger 记录错误
            QMessageBox.warning(self, "加载错误", f"加载集群配置时出错: {e}")


class ClusterTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('集群管理')
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")  # 设置背景透明
        
        # 获取根目录路径
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 控件
        self.cluster_list = QListWidget()
        self.cluster_list.setSelectionMode(QListWidget.SingleSelection)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton('创建集群')
        self.edit_btn = QPushButton('编辑集群')
        self.delete_btn = QPushButton('删除集群')
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        
        # 添加控件到布局
        layout.addWidget(QLabel('集群列表:'))
        layout.addWidget(self.cluster_list)
        layout.addLayout(btn_layout)
        
        # 设置布局
        self.setLayout(layout)
        
        # 连接信号
        self.create_btn.clicked.connect(self.create_cluster)
        self.edit_btn.clicked.connect(self.edit_cluster)
        self.delete_btn.clicked.connect(self.delete_cluster)
        
        # 加载现有集群
        self.load_clusters()
    
    def get_instance_role(self, server_name):
        """获取服务器实例角色信息

        Args:
            server_name (str): 服务器实例名称

        Returns:
            str: 服务器角色(DISPATCH_ONLY/GAME_ONLY/HYBRID)
        """
        config_path = os.path.join(self.root_dir, 'Servers', server_name, 'JGSL', 'Config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('cluster_role', 'HYBRID')
        except Exception as e:
            print(f"读取服务器角色配置出错: {e}")
            return 'HYBRID'
    
    def load_clusters(self):
        """加载现有集群列表"""
        self.cluster_list.clear()
        self.cluster_config_path = os.path.join(self.root_dir, 'Config', 'cluster-list.json')
        if not os.path.exists(self.cluster_config_path):
            # 如果文件不存在，尝试创建空的列表文件
            try:
                os.makedirs(os.path.dirname(self.cluster_config_path), exist_ok=True)
                with open(self.cluster_config_path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                logger.info(f"集群配置文件 {self.cluster_config_path} 不存在，已创建空文件")
                return # 文件刚创建，内容为空
            except Exception as e:
                logger.error(f"创建集群配置文件失败: {e}")
                QMessageBox.critical(self, "错误", f"无法创建集群配置文件:{e}")
                return

        try:
            with open(self.cluster_config_path, 'r', encoding='utf-8') as f:
                clusters_data = json.load(f)
            for cluster in clusters_data:
                self.cluster_list.addItem(cluster.get('name', '未知集群'))
        except json.JSONDecodeError:
            logger.error(f"集群配置文件 {self.cluster_config_path} 格式错误")
            QMessageBox.critical(self, "错误", "集群配置文件格式错误，请检查或删除后重试")
        except Exception as e:
            logger.error(f"加载集群列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载集群列表失败:{e}")
    
    def create_cluster(self):
        """创建新集群"""
        dialog = ClusterConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            logger.info("集群创建/编辑对话框已接受")
            self.load_clusters() # 重新加载集群列表
    
    def edit_cluster(self):
        """编辑现有集群"""
        selected = self.cluster_list.currentItem()
        if not selected:
            QMessageBox.warning(self, '警告', '请先选择一个集群')
            return
        
        cluster_name = selected.text()
        cluster_config = self._get_cluster_config(cluster_name)
        if not cluster_config:
            QMessageBox.critical(self, "错误", f"无法加载集群 {cluster_name} 的配置")
            return

        dialog = ClusterConfigDialog(self)
        dialog.original_cluster_name = cluster_name # 传递原始名称用于查找和更新
        dialog.load_config(cluster_config) # 加载配置到对话框

        if dialog.exec_() == QDialog.Accepted:
            logger.info(f"集群 {cluster_name} 更新成功")
            self.load_clusters() # 重新加载集群列表
    
    def delete_cluster(self):
        """删除集群"""
        selected = self.cluster_list.currentItem()
        if not selected:
            QMessageBox.warning(self, '警告', '请先选择一个集群')
            return
        
        reply = QMessageBox.question(self, '确认', f'确定要删除集群 {selected.text()} 吗？\n这不会删除集群中的服务器实例，但会清除它们的集群配置', 
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            cluster_name = selected.text()
            if self._delete_cluster_config(cluster_name):
                logger.info(f"集群 {cluster_name} 删除成功")
                self.load_clusters() # 重新加载集群列表
            else:
                QMessageBox.critical(self, "错误", f"删除集群 {cluster_name} 失败")
    
    def save_cluster_config(self, new_config, original_name=None):
        """保存或更新集群配置

        Args:
            new_config (dict): 新的集群配置信息
            original_name (str, optional): 如果是编辑操作，则为原始集群名称. Defaults to None.

        Returns:
            bool: 保存是否成功
        """
        logger.info(f"开始保存集群配置: {new_config}, 原始名称: {original_name}")
        cluster_name = new_config['name']

        try:
            # 读取现有集群列表
            clusters_data = []
            if os.path.exists(self.cluster_config_path):
                with open(self.cluster_config_path, 'r', encoding='utf-8') as f:
                    try:
                        clusters_data = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"集群配置文件 {self.cluster_config_path} 格式错误，将覆盖")
                        clusters_data = [] # 如果文件损坏，则创建一个新的列表

            # 检查新名称是否与现有集群冲突 (排除自身)
            for existing_cluster in clusters_data:
                if existing_cluster.get('name') == cluster_name and cluster_name != original_name:
                    QMessageBox.critical(self, "错误", f"集群名称 '{cluster_name}' 已存在")
                    return False

            # 查找要更新的集群或准备添加新集群
            updated = False
            servers_to_update = set(new_config.get('dispatch_servers', [])) | set(new_config.get('game_servers', []))
            old_servers = set()

            for i, cluster in enumerate(clusters_data):
                if cluster.get('name') == (original_name or cluster_name):
                    old_servers = set(cluster.get('dispatch_servers', [])) | set(cluster.get('game_servers', []))
                    clusters_data[i] = new_config
                    updated = True
                    break
            
            if not updated:
                clusters_data.append(new_config)

            # 保存更新后的集群列表到文件
            with open(self.cluster_config_path, 'w', encoding='utf-8') as f:
                json.dump(clusters_data, f, ensure_ascii=False, indent=4)

            # 更新服务器实例的角色配置
            # 需要重置角色的服务器 = 旧服务器集合 - 新服务器集合
            servers_to_reset = old_servers - servers_to_update
            for server in servers_to_reset:
                self._update_server_role(server, 'HYBRID', None) # 重置为独立

            # 更新新集群中的服务器角色
            dispatch_servers = set(new_config.get('dispatch_servers', []))
            game_servers = set(new_config.get('game_servers', []))
            use_internal = new_config.get('use_internal_dispatch', False)

            # 如果使用内置调度，所有服务器都标记为 GAME_ONLY
            if use_internal:
                for server in game_servers:
                    self._update_server_role(server, 'GAME_ONLY', cluster_name)
                # 如果有指定外部调度，也标记为 GAME_ONLY (因为内置优先)
                for server in dispatch_servers:
                     self._update_server_role(server, 'GAME_ONLY', cluster_name)
            else:
                # 处理外部调度
                for server in dispatch_servers:
                    if server in game_servers:
                        # 如果既是调度又是游戏，则为 HYBRID (虽然 Grasscutter 可能不支持，但逻辑上先这样处理)
                        # 或者根据实际情况，可能优先标记为 DISPATCH
                        self._update_server_role(server, 'DISPATCH_ONLY', cluster_name) # 优先标记为调度
                    else:
                        self._update_server_role(server, 'DISPATCH_ONLY', cluster_name)
                # 处理纯游戏服务器
                for server in game_servers:
                    if server not in dispatch_servers:
                        self._update_server_role(server, 'GAME_ONLY', cluster_name)

            logger.info(f"集群配置 '{cluster_name}' 保存成功")
            return True

        except Exception as e:
            logger.error(f"保存集群配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存集群配置失败:{e}")
            return False
    
    def _update_server_role(self, server_name, role, cluster_name):
        """更新服务器实例的角色配置
        
        Args:
            server_name (str): 服务器实例名称
            role (str): 新角色
            cluster_name (str): 所属集群名称
        """
        config_path = os.path.join(self.root_dir, 'Servers', server_name, 'JGSL', 'Config.json')
        try:
            # 确保目录存在
            jgsl_dir = os.path.dirname(config_path)
            os.makedirs(jgsl_dir, exist_ok=True)

            # 读取现有配置或创建新配置骨架
            config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"服务器配置文件 {config_path} 格式错误，将重新创建")
                    config = {} # 如果文件损坏，则创建一个新的字典
                except Exception as read_e:
                    logger.error(f"读取服务器配置文件 {config_path} 失败: {read_e}")
                    # 保留现有配置，避免覆盖重要信息，但记录错误
                    pass # 或者可以抛出异常让上层处理

            # 更新角色和集群信息
            config['cluster_role'] = role
            if cluster_name:
                config['cluster_name'] = cluster_name
            elif 'cluster_name' in config: # 如果 cluster_name 为 None 或空，则移除该字段
                del config['cluster_name']

            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            logger.info(f"已更新服务器 {server_name} 的角色为 {role}，所属集群为 {cluster_name or '无'} ")
        except Exception as e:
            logger.error(f"更新服务器 {server_name} 角色配置出错: {e}")
            # 可以选择性地通知用户

    def _get_cluster_config(self, cluster_name):
        """根据名称获取单个集群的配置"""
        try:
            if not os.path.exists(self.cluster_config_path):
                return None
            with open(self.cluster_config_path, 'r', encoding='utf-8') as f:
                clusters_data = json.load(f)
            for cluster in clusters_data:
                if cluster.get('name') == cluster_name:
                    return cluster
            return None
        except Exception as e:
            logger.error(f"获取集群 {cluster_name} 配置失败: {e}")
            return None

    def _delete_cluster_config(self, cluster_name):
        """删除指定名称的集群配置"""
        try:
            clusters_data = []
            servers_to_reset = set()
            if os.path.exists(self.cluster_config_path):
                with open(self.cluster_config_path, 'r', encoding='utf-8') as f:
                    try:
                        clusters_data = json.load(f)
                    except json.JSONDecodeError:
                        logger.error(f"集群配置文件 {self.cluster_config_path} 格式错误，无法删除")
                        return False

            new_clusters_data = []
            deleted = False
            for cluster in clusters_data:
                if cluster.get('name') == cluster_name:
                    # 记录需要重置角色的服务器
                    servers_to_reset.update(cluster.get('dispatch_servers', []))
                    servers_to_reset.update(cluster.get('game_servers', []))
                    deleted = True
                else:
                    new_clusters_data.append(cluster)

            if not deleted:
                logger.warning(f"尝试删除不存在的集群 {cluster_name} ")
                return False # 或者返回 True 表示操作完成(虽然没删东西)

            # 保存更新后的集群列表
            with open(self.cluster_config_path, 'w', encoding='utf-8') as f:
                json.dump(new_clusters_data, f, ensure_ascii=False, indent=4)

            # 重置相关服务器的角色
            for server in servers_to_reset:
                self._update_server_role(server, 'HYBRID', None)

            return True
        except Exception as e:
            logger.error(f"删除集群 {cluster_name} 配置失败: {e}")
            return False