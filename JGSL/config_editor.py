from PyQt5.QtWidgets import QDialog, QTabWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHBoxLayout, QComboBox, QSpinBox, QGroupBox
from PyQt5.QtCore import Qt
import json
from pathlib import Path
from loguru import logger


class ConfigEditorDialog(QDialog):
    def __init__(self, parent=None, config_path=None):
        super().__init__(parent)
        self.setWindowTitle('服务器配置编辑器')
        self.setGeometry(100, 100, 800, 600)
        self.setWindowModality(Qt.ApplicationModal)
        self.config_path = config_path

        # 创建标签页容器
        self.tab_widget = QTabWidget()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        # 初始化各配置模块
        self.init_ui()
        self.load_config()
        # 添加保存按钮
        self.save_btn = QPushButton('保存配置')
        self.save_btn.clicked.connect(self.save_config)
        self.main_layout.addWidget(self.save_btn)

    def init_ui(self):
        # 文件结构标签页
        self.structure_tab = QWidget()
        structure_layout = QFormLayout()
        self.resources_path = QLineEdit()
        # 初始化所有路径输入框
        self.resources_path = QLineEdit()
        self.data_path = QLineEdit()
        self.packets_path = QLineEdit()
        self.scripts_path = QLineEdit()
        self.plugins_path = QLineEdit()
        
        # 添加路径选择行
        structure_layout.addRow('资源目录:', self.resources_path)
        structure_layout.addRow('数据目录:', self.data_path)
        structure_layout.addRow('包目录:', self.packets_path)
        structure_layout.addRow('脚本目录:', self.scripts_path)
        structure_layout.addRow('插件目录:', self.plugins_path)
        self.structure_tab.setLayout(structure_layout)

        # 数据库标签页
        self.database_tab = QWidget()
        database_layout = QFormLayout()
        self.db_uri = QLineEdit()
        database_layout.addRow('数据库URI:', self.db_uri)
        self.db_collection = QLineEdit()
        database_layout.addRow('集合名称:', self.db_collection)
        self.database_tab.setLayout(database_layout)

        # 服务器设置标签页
        self.server_tab = QWidget()
        server_layout = QFormLayout()
        self.http_port = QLineEdit()
        server_layout.addRow('调度端口（HTTP）:', self.http_port)
        self.game_port = QLineEdit()
        server_layout.addRow('游戏端口（UDP）:', self.game_port)
        self.enable_console = QCheckBox('启用控制台')
        server_layout.addRow(self.enable_console)
        # 新增：树脂容量
        self.resin_capacity = QSpinBox()
        self.resin_capacity.setRange(0, 9999)
        server_layout.addRow('树脂容量:', self.resin_capacity)
        # 新增：树脂恢复时间
        self.resin_recovery_time = QSpinBox()
        self.resin_recovery_time.setRange(0, 9999)
        server_layout.addRow('树脂恢复时间:', self.resin_recovery_time)
        # 新增：背包限制配置
        self.inventory_limit_group = QGroupBox('背包限制')
        self.inventory_limit_layout = QFormLayout()
        self.weapon_limit = QSpinBox()
        self.weapon_limit.setRange(0, 999999)
        self.inventory_limit_layout.addRow('武器限制:', self.weapon_limit)
        self.reliquary_limit = QSpinBox()
        self.reliquary_limit.setRange(0, 999999)
        self.inventory_limit_layout.addRow('圣遗物限制:', self.reliquary_limit)
        self.material_limit = QSpinBox()
        self.material_limit.setRange(0, 999999)
        self.inventory_limit_layout.addRow('材料限制:', self.material_limit)
        self.furniture_limit = QSpinBox()
        self.furniture_limit.setRange(0, 999999)
        self.inventory_limit_layout.addRow('家具限制:', self.furniture_limit)
        self.inventory_limit_group.setLayout(self.inventory_limit_layout)
        server_layout.addRow(self.inventory_limit_group)
        # 新增：角色限制配置
        self.character_limit_group = QGroupBox('角色限制')
        self.character_limit_layout = QFormLayout()
        self.single_char_limit = QSpinBox()
        self.single_char_limit.setRange(0, 100)
        self.character_limit_layout.addRow('单人队伍限制:', self.single_char_limit)
        self.party_limit = QSpinBox()
        self.party_limit.setRange(0, 100)
        self.character_limit_layout.addRow('多人队伍限制:', self.party_limit)
        self.character_limit_group.setLayout(self.character_limit_layout)
        server_layout.addRow(self.character_limit_group)
        # 新增：游戏功能开关
        self.enable_fishing = QCheckBox('启用钓鱼')
        server_layout.addRow(self.enable_fishing)
        self.enable_housing = QCheckBox('启用家园')
        server_layout.addRow(self.enable_housing)
        self.enable_gacha = QCheckBox('启用祈愿')
        server_layout.addRow(self.enable_gacha)
        # 新增：视觉设置配置
        self.view_settings_group = QGroupBox('视觉设置')
        self.view_settings_layout = QFormLayout()
        self.view_distance_table = QTableWidget(0, 3)
        self.view_distance_table.setHorizontalHeaderLabels(['名称', '可视距离', '网格宽度'])
        self.view_distance_table.setColumnWidth(0, 100)
        self.view_distance_table.setColumnWidth(1, 150)
        self.view_distance_table.setColumnWidth(2, 100)
        view_button_layout = QHBoxLayout()
        add_view_button = QPushButton('添加')
        add_view_button.clicked.connect(self.add_view_distance)
        delete_view_button = QPushButton('删除')
        delete_view_button.clicked.connect(self.delete_view_distance)
        view_button_layout.addWidget(add_view_button)
        view_button_layout.addWidget(delete_view_button)
        self.view_settings_layout.addRow(self.view_distance_table)
        self.view_settings_layout.addRow(view_button_layout)
        self.view_settings_group.setLayout(self.view_settings_layout)
        server_layout.addRow(self.view_settings_group)
        # 新增：调试模式配置
        self.debug_mode_group = QGroupBox('调试模式')
        self.debug_mode_layout = QFormLayout()
        self.log_level = QComboBox()
        self.log_level.addItems(['INFO', 'WARN', 'ERROR'])
        self.debug_mode_layout.addRow('日志级别:', self.log_level)
        self.show_packet_content = QCheckBox('显示数据包内容')
        self.debug_mode_layout.addRow(self.show_packet_content)
        self.debug_mode_group.setLayout(self.debug_mode_layout)
        server_layout.addRow(self.debug_mode_group)
        self.server_tab.setLayout(server_layout)

        # 调度服务器标签页
        self.dispatch_tab = QWidget()
        dispatch_layout = QFormLayout()
        self.dispatch_url = QLineEdit()
        dispatch_layout.addRow('调度服务器URL:', self.dispatch_url)
        self.automatic_register_key = QLineEdit()
        dispatch_layout.addRow('自动注册密钥:', self.automatic_register_key)
        self.default_area_name = QLineEdit()
        dispatch_layout.addRow('默认区域名:', self.default_area_name)
        self.encryption_key = QLineEdit()
        dispatch_layout.addRow('加密密钥:', self.encryption_key)
        self.area_servers_table = QTableWidget(0, 4)
        self.area_servers_table.setHorizontalHeaderLabels(['区域名称', '显示名', 'IP', '端口'])
        self.area_servers_table.setColumnWidth(0, 100)
        self.area_servers_table.setColumnWidth(1, 100)
        self.area_servers_table.setColumnWidth(2, 100)
        self.area_servers_table.setColumnWidth(3, 100)
        button_layout = QHBoxLayout()
        add_button = QPushButton('添加')
        add_button.clicked.connect(self.add_area_server)
        delete_button = QPushButton('删除')
        delete_button.clicked.connect(self.delete_area_server)
        button_layout.addWidget(add_button)
        button_layout.addWidget(delete_button)
        dispatch_layout.addRow(self.area_servers_table)
        dispatch_layout.addRow(button_layout)
        self.dispatch_tab.setLayout(dispatch_layout)

        # 语言设置标签页
        self.language_tab = QWidget()
        language_layout = QFormLayout()
        self.primary_language = QComboBox()
        self.primary_language.addItems(['zh_CN', 'en_US', 'ja_JP', 'ko_KR'])
        language_layout.addRow('主语言:', self.primary_language)
        self.secondary_language = QComboBox()
        self.secondary_language.addItems(['zh_CN', 'en_US', 'ja_JP', 'ko_KR'])
        language_layout.addRow('备用语言:', self.secondary_language)
        self.document_language = QComboBox()
        self.document_language.addItems(['CHS', 'CHT', 'DE', 'EN', 'ES', 'FR', 'ID', 'IT', 'JP', 'KR', 'PT', 'RU', 'TH', 'TR', 'VI'])
        language_layout.addRow('文档语言:', self.document_language)
        self.language_tab.setLayout(language_layout)

        # 账户系统标签页
        self.account_tab = QWidget()
        account_layout = QFormLayout()
        self.auto_create_account = QCheckBox('自动创建账户')
        account_layout.addRow(self.auto_create_account)
        self.avatar_id = QSpinBox()
        self.avatar_id.setRange(10000000, 99999999)
        account_layout.addRow('头像ID:', self.avatar_id)
        self.name_card_id = QSpinBox()
        self.name_card_id.setRange(0, 99999999)
        account_layout.addRow('名片ID:', self.name_card_id)
        self.nickname = QLineEdit()
        account_layout.addRow('昵称:', self.nickname)
        self.signature = QLineEdit()
        account_layout.addRow('签名:', self.signature)
        self.world_level = QSpinBox()
        self.world_level.setRange(0, 9)
        account_layout.addRow('世界等级:', self.world_level)
        self.permission_table = QTableWidget(0, 2)
        self.permission_table.setHorizontalHeaderLabels(['权限', '描述'])
        account_layout.addRow(self.permission_table)
        self.account_tab.setLayout(account_layout)

        # 欢迎邮件标签页
        self.welcome_mail_tab = QWidget()
        welcome_mail_layout = QFormLayout()
        self.welcome_mail_title = QLineEdit()
        welcome_mail_layout.addRow('标题:', self.welcome_mail_title)
        self.welcome_mail_sender = QLineEdit()
        welcome_mail_layout.addRow('发件人:', self.welcome_mail_sender)
        self.welcome_mail_content = QLineEdit()
        welcome_mail_layout.addRow('内容:', self.welcome_mail_content)
        self.welcome_mail_attachments = QTableWidget(0, 2)
        self.welcome_mail_attachments.setHorizontalHeaderLabels(['物品ID', '数量'])
        welcome_mail_layout.addRow(self.welcome_mail_attachments)
        self.welcome_mail_tab.setLayout(welcome_mail_layout)

        # 添加标签页
        self.tab_widget.addTab(self.structure_tab, "文件结构")
        self.tab_widget.addTab(self.database_tab, "数据库")
        self.tab_widget.addTab(self.server_tab, "服务器设置")
        self.tab_widget.addTab(self.dispatch_tab, "调度服务器")
        self.tab_widget.addTab(self.language_tab, "语言设置")
        self.tab_widget.addTab(self.account_tab, "账户系统")
        self.tab_widget.addTab(self.welcome_mail_tab, "欢迎邮件")
        self.main_layout.addWidget(self.tab_widget)

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)

            # 加载文件结构配置
            self.resources_path.setText(config.get('folderStructure', {}).get('resources', ''))
            self.data_path.setText(config.get('folderStructure', {}).get('data', ''))
            self.packets_path.setText(config.get('folderStructure', {}).get('packets', ''))
            self.scripts_path.setText(config.get('folderStructure', {}).get('scripts', ''))
            self.plugins_path.setText(config.get('folderStructure', {}).get('plugins', ''))

            # 加载数据库配置
            self.db_uri.setText(config.get('database', {}).get('server', {}).get('connectionUri', ''))
            self.db_collection.setText(config.get('database', {}).get('server', {}).get('collection', ''))

            # 加载服务器配置
            server_config = config.get('server', {})
            http_config = server_config.get('http', {})
            game_config = server_config.get('game', {})
            debug_config = server_config.get('debug', {})

            self.http_port.setText(str(http_config.get('bindPort', '')))
            self.game_port.setText(str(game_config.get('bindPort', '')))
            self.enable_console.setChecked(game_config.get('enableConsole', False))
            # 新增：加载树脂配置
            resin_options = game_config.get('resinOptions', {})
            self.resin_capacity.setValue(resin_options.get('cap', 160))
            self.resin_recovery_time.setValue(resin_options.get('rechargeTime', 8))
            # 新增：加载背包限制配置
            inventory_limits = game_config.get('inventory', {})
            self.weapon_limit.setValue(inventory_limits.get('weaponLimit', 2000))
            self.reliquary_limit.setValue(inventory_limits.get('reliquaryLimit', 2000))
            self.material_limit.setValue(inventory_limits.get('materialLimit', 2000))
            self.furniture_limit.setValue(inventory_limits.get('furnitureLimit', 2000))
            # 新增：加载角色限制配置
            character_limits = game_config.get('character', {})
            self.single_char_limit.setValue(character_limits.get('singleCharacterLimit', 10))
            self.party_limit.setValue(character_limits.get('partyLimit', 4))
            # 新增：加载游戏功能开关
            self.enable_fishing.setChecked(game_config.get('enableFishing', False))
            self.enable_housing.setChecked(game_config.get('enableHousing', False))
            self.enable_gacha.setChecked(game_config.get('enableGacha', False))
            # 新增：加载视觉设置配置
            vision_options = game_config.get('visionOptions', [])
            self.view_distance_table.setRowCount(len(vision_options))
            for row, setting in enumerate(vision_options):
                self.view_distance_table.setItem(row, 0, QTableWidgetItem(setting.get('name', '')))
                self.view_distance_table.setItem(row, 1, QTableWidgetItem(str(setting.get('visionRange', 0))))
                self.view_distance_table.setItem(row, 2, QTableWidgetItem(str(setting.get('gridWidth', 0))))
            # 新增：加载调试模式配置
            self.log_level.setCurrentText(debug_config.get('logLevel', 'INFO'))
            self.show_packet_content.setChecked(debug_config.get('showPacketContent', False))

            # 加载调度服务器配置
            dispatch_config = config.get('dispatch', {})
            # Assuming single region structure based on save logic
            region_config = dispatch_config.get('regions', [{}])[0]
            self.dispatch_url.setText(region_config.get('dispatchUrl', ''))
            self.automatic_register_key.setText(region_config.get('secretKey', '')) # Key name mismatch between load/save
            self.default_area_name.setText(region_config.get('title', '')) # Key name mismatch between load/save
            self.encryption_key.setText(region_config.get('encryptionKey', ''))
            area_servers = region_config.get('servers', []) # Key name mismatch between load/save
            self.area_servers_table.setRowCount(len(area_servers))
            for row, server in enumerate(area_servers):
                self.area_servers_table.setItem(row, 0, QTableWidgetItem(server.get('name', '')))
                self.area_servers_table.setItem(row, 1, QTableWidgetItem(server.get('displayName', '')))
                self.area_servers_table.setItem(row, 2, QTableWidgetItem(server.get('ip', '')))
                self.area_servers_table.setItem(row, 3, QTableWidgetItem(str(server.get('port', 0))))

            # 加载语言设置配置
            self.primary_language.setCurrentText(config.get('language', {}).get('primary', 'zh_CN'))
            self.secondary_language.setCurrentText(config.get('language', {}).get('secondary', 'en_US'))
            self.document_language.setCurrentText(config.get('language', {}).get('documentLanguage', 'CHS'))

            # 加载账户系统配置
            self.auto_create_account.setChecked(config.get('account', {}).get('autoCreate', False))
            logger.debug('成功加载所有配置项')

            self.avatar_id.setValue(config.get('account', {}).get('default', {}).get('avatarId', 10000000))
            self.name_card_id.setValue(config.get('account', {}).get('default', {}).get('nameCardId', 0))
            self.nickname.setText(config.get('account', {}).get('default', {}).get('nickname', ''))
            self.signature.setText(config.get('account', {}).get('default', {}).get('signature', ''))
            self.world_level.setValue(config.get('account', {}).get('default', {}).get('worldLevel', 0))
            permissions = config.get('account', {}).get('permissions', [])
            self.permission_table.setRowCount(len(permissions))
            for row, perm in enumerate(permissions):
                self.permission_table.setItem(row, 0, QTableWidgetItem(perm.get('name', '')))
                self.permission_table.setItem(row, 1, QTableWidgetItem(perm.get('description', '')))

            # 加载欢迎邮件配置
            welcome_mail_config = config.get('welcomeMail', {})
            self.welcome_mail_title.setText(welcome_mail_config.get('title', ''))
            self.welcome_mail_sender.setText(welcome_mail_config.get('sender', ''))
            self.welcome_mail_content.setText(welcome_mail_config.get('content', ''))
            # 加载欢迎邮件附件 (Assuming items are directly under welcomeMail)
            items = welcome_mail_config.get('items', [])
            self.welcome_mail_attachments.setRowCount(len(items))
            for row, item in enumerate(items):
                self.welcome_mail_attachments.setItem(row, 0, QTableWidgetItem(str(item.get('itemId', 0))))
                self.welcome_mail_attachments.setItem(row, 1, QTableWidgetItem(str(item.get('itemCount', 0))))

        except Exception as e:
            logger.error(f'加载配置文件失败: {e}')
            QMessageBox.critical(self, '配置错误', f'加载失败: {e}')

    def save_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)

            # 更新文件结构配置
            config['folderStructure'] = {
                "resources": self.resources_path.text(),
                "data": self.data_path.text(),
                "packets": self.packets_path.text(), # Added missing keys
                "scripts": self.scripts_path.text(), # Added missing keys
                "plugins": self.plugins_path.text()  # Added missing keys
            }
            # 更新数据库配置
            config['database'] = { # Corrected key name
                "server": {
                    "connectionUri": self.db_uri.text(),
                    "collection": self.db_collection.text()
                },
                "game": { # Assuming game uses same DB for now
                    "connectionUri": self.db_uri.text(),
                    "collection": self.db_collection.text()
                }
            }
            # 更新服务器配置
            config['server']['http']['bindPort'] = int(self.http_port.text())
            config['server']['game']['bindPort'] = int(self.game_port.text())
            config['server']['game']['enableConsole'] = self.enable_console.isChecked()
            # 新增：更新树脂配置
            config['server']['game']['resinOptions'] = {
                "cap": self.resin_capacity.value(),
                "rechargeTime": self.resin_recovery_time.value()
            }
            # 新增：更新背包限制配置
            config['server']['game']['inventory'] = {
                "weaponLimit": self.weapon_limit.value(),
                "reliquaryLimit": self.reliquary_limit.value(),
                "materialLimit": self.material_limit.value(),
                "furnitureLimit": self.furniture_limit.value()
            }
            # 新增：更新角色限制配置
            config['server']['game']['character'] = {
                "singleCharacterLimit": self.single_char_limit.value(),
                "partyLimit": self.party_limit.value()
            }
            # 新增：更新游戏功能开关
            config['server']['game']['enableFishing'] = self.enable_fishing.isChecked()
            config['server']['game']['enableHousing'] = self.enable_housing.isChecked()
            config['server']['game']['enableGacha'] = self.enable_gacha.isChecked()
            # 新增：更新视觉设置配置
            config['server']['game']['visionOptions'] = [] # Corrected path
            for row in range(self.view_distance_table.rowCount()):
                name = self.view_distance_table.item(row, 0).text()
                vision_range = int(self.view_distance_table.item(row, 1).text())
                grid_width = int(self.view_distance_table.item(row, 2).text())
                config['server']['game']['visionOptions'].append({"name": name, "visionRange": vision_range, "gridWidth": grid_width})
            # 新增：更新调试模式配置
            config['server']['debug'] = {
                "logLevel": self.log_level.currentText(),
                "showPacketContent": self.show_packet_content.isChecked()
            }

            # 更新调度服务器配置
            # Aligning save structure with load structure (assuming single region)
            config['dispatch'] = config.get('dispatch', {}) # Preserve other dispatch keys if any
            config['dispatch']['regions'] = config['dispatch'].get('regions', [{}])
            if not config['dispatch']['regions']: # Ensure there's at least one region dict
                config['dispatch']['regions'].append({})
            region_config = config['dispatch']['regions'][0]
            region_config['name'] = region_config.get('name', 'os_usa') # Preserve or set default name
            region_config['title'] = self.default_area_name.text()
            region_config['dispatchUrl'] = self.dispatch_url.text()
            region_config['secretKey'] = self.automatic_register_key.text()
            region_config['encryptionKey'] = self.encryption_key.text()
            region_config['servers'] = []
            for row in range(self.area_servers_table.rowCount()):
                name = self.area_servers_table.item(row, 0).text()
                display_name = self.area_servers_table.item(row, 1).text()
                ip = self.area_servers_table.item(row, 2).text()
                port = int(self.area_servers_table.item(row, 3).text())
                region_config['servers'].append({"name": name, "displayName": display_name, "ip": ip, "port": port})

            # 更新语言设置配置
            config['language'] = {
                "primary": self.primary_language.currentText(),
                "secondary": self.secondary_language.currentText(),
                "documentLanguage": self.document_language.currentText()
            }

            # 更新账户系统配置
            config['account'] = {
                "autoCreate": self.auto_create_account.isChecked(),
                # "initialUid": self.initial_uid.value(), # Removed as UI element doesn't exist
                "default": {
                    "avatarId": self.avatar_id.value(),
                    "nameCardId": self.name_card_id.value(),
                    "nickname": self.nickname.text(),
                    "signature": self.signature.text(),
                    "worldLevel": self.world_level.value()
                },
                "permissions": []
            }
            for row in range(self.permission_table.rowCount()):
                name = self.permission_table.item(row, 0).text()
                description = self.permission_table.item(row, 1).text()
                config['account']['permissions'].append({"name": name, "description": description})

            # 更新欢迎邮件配置
            config['welcomeMail'] = {
                "title": self.welcome_mail_title.text(),
                "sender": self.welcome_mail_sender.text(),
                "content": self.welcome_mail_content.text(),
                "items": [] # Corrected key name based on load logic assumption
            }
            # 更新欢迎邮件附件
            for row in range(self.welcome_mail_attachments.rowCount()):
                item_id = int(self.welcome_mail_attachments.item(row, 0).text())
                count = int(self.welcome_mail_attachments.item(row, 1).text())
                config['welcomeMail']['items'].append({"itemId": item_id, "itemCount": count, "itemLevel": 1})

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.success('配置保存成功')
            self.accept()
        except Exception as e:
            logger.error(f'保存配置失败: {e}')
            QMessageBox.critical(self, '保存错误', f'保存失败: {e}')

    def add_area_server(self):
        row = self.area_servers_table.rowCount()
        self.area_servers_table.insertRow(row)
        self.area_servers_table.setItem(row, 0, QTableWidgetItem(''))
        self.area_servers_table.setItem(row, 1, QTableWidgetItem(''))
        self.area_servers_table.setItem(row, 2, QTableWidgetItem(''))
        self.area_servers_table.setItem(row, 3, QTableWidgetItem(''))

    def delete_area_server(self):
        selected_rows = self.area_servers_table.selectionModel().selectedRows()
        for row in selected_rows:
            self.area_servers_table.removeRow(row.row())

    def add_view_distance(self):
        row = self.view_distance_table.rowCount()
        self.view_distance_table.insertRow(row)
        self.view_distance_table.setItem(row, 0, QTableWidgetItem(''))
        self.view_distance_table.setItem(row, 1, QTableWidgetItem(''))
        self.view_distance_table.setItem(row, 2, QTableWidgetItem(''))

    def delete_view_distance(self):
        selected_rows = self.view_distance_table.selectionModel().selectedRows()
        for row in selected_rows:
            self.view_distance_table.removeRow(row.row())