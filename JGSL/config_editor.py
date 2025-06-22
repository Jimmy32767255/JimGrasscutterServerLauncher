from PyQt5.QtWidgets import QDialog, QTabWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHBoxLayout, QComboBox, QSpinBox, QGroupBox, QTextEdit, QFileDialog, QScrollArea, QHeaderView
from PyQt5.QtCore import Qt
import json
from loguru import logger


class ConfigEditorDialog(QDialog):
    def __init__(self, parent=None, config_path=None):
        super().__init__(parent)
        self.setWindowTitle('服务器配置编辑器')
        self.setGeometry(100, 100, 800, 600)
        self.setWindowModality(Qt.ApplicationModal)
        self.config_path = config_path

        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建标签页容器
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 初始化各配置模块
        self.init_ui()
        self.load_config()
        
        # 保存按钮
        self.save_btn = QPushButton('保存配置')
        self.save_btn.clicked.connect(self.save_config)
        main_layout.addWidget(self.save_btn)

    def create_scrollable_tab(self, content_widget):
        """创建带有滚动区域的选项卡"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        return scroll_area

    def init_ui(self):
        # 文件结构标签页
        self.structure_tab = QWidget()
        structure_layout = QFormLayout(self.structure_tab)
        self.resources_path = QLineEdit()
        # 初始化所有路径输入框
        self.resources_path = QLineEdit()
        self.data_path = QLineEdit()
        self.packets_path = QLineEdit()
        self.scripts_path = QLineEdit()
        self.plugins_path = QLineEdit()
        self.cache_path = QLineEdit() # 缓存目录
        
        # 路径选择行
        structure_layout.addRow('资源目录:', self.resources_path)
        structure_layout.addRow('数据目录:', self.data_path)
        structure_layout.addRow('包目录:', self.packets_path)
        structure_layout.addRow('脚本目录:', self.scripts_path)
        structure_layout.addRow('插件目录:', self.plugins_path)
        structure_layout.addRow('缓存目录:', self.cache_path) # 缓存目录行
        self.structure_tab.setLayout(structure_layout)
        self.tab_widget.addTab(self.create_scrollable_tab(self.structure_tab), "文件结构")

        # 数据库标签页
        self.database_tab = QWidget()
        database_layout = QFormLayout()
        self.db_uri = QLineEdit()
        database_layout.addRow('数据库URI:', self.db_uri)
        self.db_collection = QLineEdit()
        database_layout.addRow('集合名称:', self.db_collection)

        # 游戏数据库配置 (与服务器库分开)
        self.game_db_uri = QLineEdit()
        database_layout.addRow('游戏数据库URI:', self.game_db_uri)
        self.game_db_collection = QLineEdit()
        database_layout.addRow('游戏集合名称:', self.game_db_collection)

        self.database_tab.setLayout(database_layout)
        self.tab_widget.addTab(self.create_scrollable_tab(self.database_tab), "数据库")

        # 服务器设置标签页
        self.server_tab = QWidget()
        server_layout = QFormLayout()
        self.http_bind_address = QLineEdit() # HTTP绑定地址
        server_layout.addRow('调度绑定地址(HTTP):', self.http_bind_address)
        self.http_port = QLineEdit()
        server_layout.addRow('调度端口(HTTP):', self.http_port)
        self.http_access_address = QLineEdit() # HTTP访问地址
        server_layout.addRow('调度访问地址(HTTP):', self.http_access_address)
        self.http_access_port = QLineEdit() # HTTP访问端口
        server_layout.addRow('调度访问端口(HTTP):', self.http_access_port)

        self.game_bind_address = QLineEdit() # Game绑定地址
        server_layout.addRow('游戏绑定地址(UDP):', self.game_bind_address)
        self.game_port = QLineEdit()
        server_layout.addRow('游戏端口(UDP):', self.game_port)
        self.game_access_address = QLineEdit() # Game访问地址
        server_layout.addRow('游戏访问地址(UDP):', self.game_access_address)
        self.game_access_port = QLineEdit() # Game访问端口
        server_layout.addRow('游戏访问端口(UDP):', self.game_access_port)

        self.enable_console = QCheckBox('启用控制台')
        server_layout.addRow(self.enable_console)
        self.fast_require = QCheckBox('快速加载Lua脚本')

        # 调度服务器地区配置
        self.regions_group = QGroupBox('调度服务器地区配置')
        self.regions_layout = QVBoxLayout()
        self.regions_table = QTableWidget(0, 6)
        self.regions_table.setMinimumHeight(200) # 最小高度
        self.regions_table.setMaximumHeight(400) # 最大高度
        self.regions_table.setHorizontalHeaderLabels([
            '地区名', '标题', '调度URL', '加密密钥', '地区密钥', '操作'
        ])
        self.regions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.add_region_btn = QPushButton('添加地区')
        self.add_region_btn.clicked.connect(self.add_region_row)
        self.regions_layout.addWidget(self.regions_table)
        self.regions_layout.addWidget(self.add_region_btn)
        self.regions_group.setLayout(self.regions_layout)
        server_layout.addRow(self.regions_group)
        server_layout.addRow(self.fast_require)
        self.start_immediately = QCheckBox('立即启动HTTP服务器')
        server_layout.addRow(self.start_immediately)
        self.use_unique_packet_key = QCheckBox('使用唯一数据包密钥')
        server_layout.addRow(self.use_unique_packet_key)
        self.log_commands = QCheckBox('记录命令日志')
        server_layout.addRow(self.log_commands)
        self.run_mode = QComboBox()
        self.run_mode.addItems(['HYBRID', 'DISPATCH_ONLY', 'GAME_ONLY'])
        server_layout.addRow('运行模式:', self.run_mode)
        # 树脂容量
        self.resin_capacity = QSpinBox()
        self.resin_capacity.setRange(0, 9999)
        server_layout.addRow('树脂容量:', self.resin_capacity)
        # 树脂恢复时间
        self.resin_recovery_time = QSpinBox()
        self.resin_recovery_time.setRange(0, 9999)
        server_layout.addRow('树脂恢复时间:', self.resin_recovery_time)
        # 背包限制配置
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
        # 角色限制配置
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

        # 更多游戏功能开关
        self.game_options_switch_group = QGroupBox('游戏功能开关')
        self.game_options_switch_layout = QFormLayout()
        self.enable_avatar_events = QCheckBox('启用头像事件')
        self.game_options_switch_layout.addRow(self.enable_avatar_events)
        self.enable_shop_items = QCheckBox('启用商店物品')
        self.game_options_switch_layout.addRow(self.enable_shop_items)
        self.enable_costumes = QCheckBox('启用衣装')
        self.game_options_switch_layout.addRow(self.enable_costumes)
        self.costume_strategy = QComboBox()
        self.costume_strategy.addItems(['DEFAULT', 'DISABLE', 'ENABLE'])
        self.game_options_switch_layout.addRow('衣装策略:', self.costume_strategy)
        self.trial_costumes = QCheckBox('启用试用衣装')
        self.game_options_switch_layout.addRow(self.trial_costumes)
        self.enable_fishing = QCheckBox('启用钓鱼')
        self.game_options_switch_layout.addRow(self.enable_fishing)
        self.enable_housing = QCheckBox('启用家园')
        self.game_options_switch_layout.addRow(self.enable_housing)
        self.enable_gacha = QCheckBox('启用祈愿')
        self.game_options_switch_layout.addRow(self.enable_gacha)
        self.game_options_switch_group.setLayout(self.game_options_switch_layout)
        server_layout.addRow(self.game_options_switch_group)

        # 任务选项配置
        self.quest_options_group = QGroupBox('任务选项')
        self.quest_options_layout = QFormLayout()
        self.enable_quests = QCheckBox('启用任务系统')
        self.quest_options_layout.addRow(self.enable_quests)
        self.enable_main_quests = QCheckBox('启用主线任务')
        self.quest_options_layout.addRow(self.enable_main_quests)
        self.share_quests = QCheckBox('共享任务进度')
        self.quest_options_layout.addRow(self.share_quests)
        self.reward_quests = QCheckBox('奖励任务')
        self.quest_options_layout.addRow(self.reward_quests)
        self.daily_quests = QSpinBox()
        self.daily_quests.setRange(0, 100)
        self.quest_options_layout.addRow('每日任务数量:', self.daily_quests)
        self.random_quests = QSpinBox()
        self.random_quests.setRange(0, 100)
        self.quest_options_layout.addRow('随机任务数量:', self.random_quests)
        self.talk_quests = QSpinBox()
        self.talk_quests.setRange(0, 100)
        self.quest_options_layout.addRow('对话任务数量:', self.talk_quests)
        self.quest_options_group.setLayout(self.quest_options_layout)
        server_layout.addRow(self.quest_options_group)

        # 手册选项配置
        self.handbook_options_group = QGroupBox('手册选项')
        self.handbook_options_layout = QFormLayout()
        self.allow_handbook = QCheckBox('允许手册')
        self.handbook_options_layout.addRow(self.allow_handbook)
        self.handbook_server = QLineEdit()
        self.handbook_options_layout.addRow('手册服务器:', self.handbook_server)
        self.handbook_max_requests = QSpinBox()
        self.handbook_max_requests.setRange(0, 1000)
        self.handbook_options_layout.addRow('最大请求数:', self.handbook_max_requests)
        self.handbook_time_frame = QSpinBox()
        self.handbook_time_frame.setRange(0, 3600)
        self.handbook_options_layout.addRow('时间范围 (秒):', self.handbook_time_frame)
        self.handbook_options_group.setLayout(self.handbook_options_layout)
        server_layout.addRow(self.handbook_options_group)

        # 视觉设置配置
        self.view_settings_group = QGroupBox('视觉设置')
        self.view_settings_layout = QFormLayout()
        self.view_distance_table = QTableWidget(0, 3)
        self.view_distance_table.setHorizontalHeaderLabels(['名称', '可视距离', '网格宽度'])
        self.view_distance_table.setColumnWidth(0, 100)
        self.view_distance_table.setColumnWidth(1, 150)
        self.view_distance_table.setColumnWidth(2, 100)
        view_button_layout = QHBoxLayout()
        add_view_button = QPushButton('添加视觉设置') # 统一按钮文本
        add_view_button.clicked.connect(self.add_view_distance)
        delete_view_button = QPushButton('删除选中设置') # 统一按钮文本
        delete_view_button.clicked.connect(self.delete_view_distance)
        view_button_layout.addWidget(add_view_button)
        view_button_layout.addWidget(delete_view_button)
        self.view_settings_layout.addRow(self.view_distance_table)
        self.view_settings_layout.addRow(view_button_layout)
        self.view_settings_group.setLayout(self.view_settings_layout)
        server_layout.addRow(self.view_settings_group)

        # 调试模式配置
        self.debug_mode_group = QGroupBox('调试模式')
        self.debug_mode_layout = QFormLayout()
        self.log_level = QComboBox()
        self.log_level.addItems(['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'OFF']) # 修正日志级别选项
        self.debug_mode_layout.addRow('服务器日志级别:', self.log_level) # 修正标签
        self.show_packet_content = QCheckBox('显示数据包内容')
        self.debug_mode_layout.addRow(self.show_packet_content)
        self.debug_mode_group.setLayout(self.debug_mode_layout)
        server_layout.addRow(self.debug_mode_group)
        # 调试白名单/黑名单
        self.debug_lists_group = QGroupBox('调试名单')
        self.debug_lists_layout = QFormLayout()
        self.debug_whitelist = QTextEdit() # 使用 QTextEdit 处理多行 ID
        self.debug_whitelist.setPlaceholderText('每行一个玩家 UID')
        self.debug_lists_layout.addRow('白名单:', self.debug_whitelist)
        self.debug_blacklist = QTextEdit() # 使用 QTextEdit 处理多行 ID
        self.debug_blacklist.setPlaceholderText('每行一个玩家 UID')
        self.debug_lists_layout.addRow('黑名单:', self.debug_blacklist)
        self.debug_lists_group.setLayout(self.debug_lists_layout)
        server_layout.addRow(self.debug_lists_group)

        # HTTP 加密配置
        self.http_encryption_group = QGroupBox('HTTP 加密')
        self.http_encryption_layout = QFormLayout()
        self.use_http_encryption = QCheckBox('启用加密')
        self.http_encryption_layout.addRow(self.use_http_encryption)
        self.keystore_path = QLineEdit()
        self.keystore_path_btn = QPushButton('选择 Keystore')
        self.keystore_path_btn.clicked.connect(lambda: self.select_file(self.keystore_path, '选择 Keystore 文件', ''))
        keystore_layout = QHBoxLayout()
        keystore_layout.addWidget(self.keystore_path)
        keystore_layout.addWidget(self.keystore_path_btn)
        self.http_encryption_layout.addRow('Keystore 路径:', keystore_layout)
        self.keystore_password = QLineEdit()
        self.keystore_password.setEchoMode(QLineEdit.Password)
        self.http_encryption_layout.addRow('Keystore 密码:', self.keystore_password)
        self.http_encryption_group.setLayout(self.http_encryption_layout)
        server_layout.addRow(self.http_encryption_group)

        # HTTP 策略配置
        self.http_policies_group = QGroupBox('HTTP 策略')
        self.http_policies_layout = QFormLayout()
        self.enable_cors = QCheckBox('启用 CORS')
        self.http_policies_layout.addRow(self.enable_cors)
        self.allowed_origins = QLineEdit()
        self.allowed_origins.setPlaceholderText('多个源用逗号分隔, * 表示所有')
        self.http_policies_layout.addRow('允许的源:', self.allowed_origins)
        self.http_policies_group.setLayout(self.http_policies_layout)
        server_layout.addRow(self.http_policies_group)

        # HTTP 静态文件配置
        self.http_files_group = QGroupBox('HTTP 静态文件')
        self.http_files_layout = QFormLayout()
        self.index_file = QLineEdit()
        self.http_files_layout.addRow('索引文件:', self.index_file)
        self.error_file = QLineEdit()
        self.http_files_layout.addRow('错误文件:', self.error_file)
        self.http_files_group.setLayout(self.http_files_layout)
        server_layout.addRow(self.http_files_group)

        self.server_tab.setLayout(server_layout)
        self.tab_widget.addTab(self.create_scrollable_tab(self.server_tab), "服务器设置")

        # 语言设置标签页
        self.language_tab = QWidget()
        language_layout = QFormLayout()
        self.primary_language = QComboBox()
        self.primary_language.addItems(['en_US', 'es_ES', 'fr_FR', 'it_IT', 'ja_JP', 'ko_KR', 'pl_PL', 'ro_RO', 'ru_RU', 'zh_CN', 'zh_TW'])
        language_layout.addRow('主语言:', self.primary_language)
        self.secondary_language = QComboBox()
        self.secondary_language.addItems(['en_US', 'es_ES', 'fr_FR', 'it_IT', 'ja_JP', 'ko_KR', 'pl_PL', 'ro_RO', 'ru_RU', 'zh_CN', 'zh_TW'])
        language_layout.addRow('备用语言:', self.secondary_language)
        self.document_language = QComboBox()
        self.document_language.addItems(['CHS', 'CHT', 'DE', 'EN', 'ES', 'FR', 'ID', 'IT', 'JP', 'KR', 'PT', 'RU', 'TH', 'TR', 'VI'])
        language_layout.addRow('文档语言:', self.document_language)
        self.language_tab.setLayout(language_layout)
        self.tab_widget.addTab(self.create_scrollable_tab(self.language_tab), "语言设置")

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
        self.permission_table = QTableWidget(0, 1)
        self.permission_table.setHorizontalHeaderLabels(['权限'])
        account_layout.addRow(self.permission_table)
        # 权限添加/删除按钮
        permission_button_layout = QHBoxLayout()
        add_perm_button = QPushButton('添加权限')
        add_perm_button.clicked.connect(self.add_permission)
        delete_perm_button = QPushButton('删除选中权限') # 统一按钮文本
        delete_perm_button.clicked.connect(self.delete_permission)
        permission_button_layout.addWidget(add_perm_button)
        permission_button_layout.addWidget(delete_perm_button)
        account_layout.addRow(permission_button_layout)
        self.account_tab.setLayout(account_layout)
        self.tab_widget.addTab(self.create_scrollable_tab(self.account_tab), "账户系统")

        # 欢迎邮件标签页
        self.welcome_mail_tab = QWidget()
        welcome_mail_layout = QFormLayout()
        self.welcome_mail_title = QLineEdit()
        welcome_mail_layout.addRow('标题:', self.welcome_mail_title)
        self.welcome_mail_sender = QLineEdit()
        welcome_mail_layout.addRow('发件人:', self.welcome_mail_sender)
        self.welcome_mail_content = QLineEdit()
        welcome_mail_layout.addRow('内容:', self.welcome_mail_content)
        self.welcome_mail_attachments = QTableWidget(0, 3)
        self.welcome_mail_attachments.setHorizontalHeaderLabels(['物品ID', '数量', '等级'])
        welcome_mail_layout.addRow(self.welcome_mail_attachments)
        # 附件添加/删除按钮
        attachment_button_layout = QHBoxLayout()
        add_attach_button = QPushButton('添加附件')
        add_attach_button.clicked.connect(self.add_welcome_item)
        delete_attach_button = QPushButton('删除选中附件') # 统一按钮文本
        delete_attach_button.clicked.connect(self.delete_welcome_item)
        attachment_button_layout.addWidget(add_attach_button)
        attachment_button_layout.addWidget(delete_attach_button)
        welcome_mail_layout.addRow(attachment_button_layout)
        self.welcome_mail_tab.setLayout(welcome_mail_layout)
        self.tab_widget.addTab(self.create_scrollable_tab(self.welcome_mail_tab), "欢迎邮件")

    def add_region_row(self):
        row_count = self.regions_table.rowCount()
        self.regions_table.insertRow(row_count)
        # 默认值
        self.regions_table.setItem(row_count, 0, QTableWidgetItem('New Region'))
        self.regions_table.setItem(row_count, 1, QTableWidgetItem('New Title'))
        self.regions_table.setItem(row_count, 2, QTableWidgetItem('http://localhost:22333'))
        self.regions_table.setItem(row_count, 3, QTableWidgetItem('')) # dispatchKey
        self.regions_table.setItem(row_count, 4, QTableWidgetItem('')) # regionKey

        # 添加删除按钮
        delete_btn = QPushButton('删除')
        delete_btn.clicked.connect(lambda checked, row=row_count: self.delete_region_row(row))
        self.regions_table.setCellWidget(row_count, 5, delete_btn)

    def delete_region_row(self, row):
        self.regions_table.removeRow(row)

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
            self.cache_path.setText(config.get('folderStructure', {}).get('cache', '')) # 加载缓存路径

            # 加载数据库配置
            self.db_uri.setText(config.get('databaseInfo', {}).get('server', {}).get('connectionUri', ''))
            self.db_collection.setText(config.get('databaseInfo', {}).get('server', {}).get('collection', ''))
            
            # 加载游戏数据库配置
            self.game_db_uri.setText(config.get('databaseInfo', {}).get('game', {}).get('connectionUri', ''))
            self.game_db_collection.setText(config.get('databaseInfo', {}).get('game', {}).get('collection', ''))

            # 加载服务器配置
            server_config = config.get('server', {})
            http_config = server_config.get('http', {})
            game_config = server_config.get('game', {})
            debug_config = server_config.get('debugMode', {}) # 修正:debugMode
            dispatch_config = server_config.get('dispatch', {}) # 修正路径
            http_encryption_config = http_config.get('encryption', {}) # 加载 HTTP 加密
            http_policies_config = http_config.get('policies', {}) # 加载 HTTP 策略
            http_files_config = http_config.get('files', {}) # 加载 HTTP 文件

            self.http_bind_address.setText(http_config.get('bindAddress', '0.0.0.0')) # 加载 HTTP 绑定地址
            self.http_port.setText(str(http_config.get('bindPort', ''))) 
            self.http_access_address.setText(http_config.get('accessAddress', '')) # 加载 HTTP 访问地址
            self.http_access_port.setText(str(http_config.get('accessPort', ''))) # 加载 HTTP 访问端口

            self.game_bind_address.setText(game_config.get('bindAddress', '0.0.0.0')) # 加载 Game 绑定地址
            self.game_port.setText(str(game_config.get('bindPort', ''))) 
            self.game_access_address.setText(game_config.get('accessAddress', '')) # 加载 Game 访问地址
            self.game_access_port.setText(str(game_config.get('accessPort', ''))) # 加载 Game 访问端口

            self.enable_console.setChecked(game_config.get('enableConsole', False))
            self.fast_require.setChecked(server_config.get('fastRequire', True)) # 修正:fastRequire 在 server 下
            self.start_immediately.setChecked(http_config.get('startImmediately', True)) # 修正:startImmediately 在 http 下
            self.use_unique_packet_key.setChecked(game_config.get('useUniquePacketKey', False))
            self.log_commands.setChecked(server_config.get('logCommands', False)) # 加载 logCommands
            self.run_mode.setCurrentText(server_config.get('runMode', 'HYBRID')) # 加载 runMode

            # 加载树脂配置
            resin_options = game_config.get('gameOptions', {}).get('resinOptions', {}) # 修正路径
            self.resin_capacity.setValue(resin_options.get('cap', 160))
            self.resin_recovery_time.setValue(resin_options.get('rechargeTime', 8))
            # 加载背包限制配置
            inventory_limits = game_config.get('gameOptions', {}).get('inventoryLimits', {}) # 修正路径和键名
            self.weapon_limit.setValue(inventory_limits.get('weaponLimit', 2000))
            self.reliquary_limit.setValue(inventory_limits.get('reliquaryLimit', 2000))
            self.material_limit.setValue(inventory_limits.get('materialLimit', 2000))
            self.furniture_limit.setValue(inventory_limits.get('furnitureLimit', 2000))
            # 加载角色限制配置
            character_limits = game_config.get('gameOptions', {}).get('characterLimits', {}) # 修正路径和键名
            self.single_char_limit.setValue(character_limits.get('singleCharacterLimit', 10))
            self.party_limit.setValue(character_limits.get('partyLimit', 4))
            # 加载游戏功能开关
            game_options = game_config.get('gameOptions', {}) # 修正路径
            self.enable_avatar_events.setChecked(game_options.get('enableAvatarEvents', False)) # 新增
            self.enable_shop_items.setChecked(game_options.get('enableShopItems', False)) # 新增
            self.enable_costumes.setChecked(game_options.get('enableCostumes', False)) # 新增
            self.costume_strategy.setCurrentText(game_options.get('costumeStrategy', 'DEFAULT')) # 新增
            self.trial_costumes.setChecked(game_options.get('trialCostumes', False)) # 新增
            self.enable_fishing.setChecked(game_options.get('enableFishing', False))
            self.enable_housing.setChecked(game_options.get('enableHousing', False))
            self.enable_gacha.setChecked(game_options.get('enableGacha', False))

            # 加载任务选项配置
            quest_options = game_options.get('questOptions', {}) # 新增
            self.enable_quests.setChecked(quest_options.get('enabled', True))
            self.enable_main_quests.setChecked(quest_options.get('mainQuests', True))
            self.share_quests.setChecked(quest_options.get('shareQuests', True))
            self.reward_quests.setChecked(quest_options.get('rewardQuests', True))
            self.daily_quests.setValue(quest_options.get('dailyQuests', 4))
            self.random_quests.setValue(quest_options.get('randomQuests', 1))
            self.talk_quests.setValue(quest_options.get('talkQuests', 1))

            # 加载手册选项配置
            handbook_options = game_options.get('handbook', {}) # 新增
            self.allow_handbook.setChecked(handbook_options.get('allowHandbook', True))
            server_info = handbook_options.get('server', {})
            if isinstance(server_info, dict):
                # 从字典中提取地址和端口
                address = server_info.get('address', '')
                port = server_info.get('port', '')
                # 组合成 address:port 格式
                server_str = f"{address}:{port}" if address and port else ''
                self.handbook_server.setText(server_str)
            else:
                # 如果已经是字符串，直接使用
                self.handbook_server.setText(server_info)
            handbook_limits = handbook_options.get('limits', {})
            self.handbook_max_requests.setValue(handbook_limits.get('maxRequests', 5))
            self.handbook_time_frame.setValue(handbook_limits.get('timeFrame', 60))

            # 加载视觉设置配置
            vision_options = game_options.get('visionOptions', []) # 修正路径
            self.view_distance_table.setRowCount(0) # 清空表格
            for setting in vision_options:
                try:
                    row_position = self.view_distance_table.rowCount()
                    self.view_distance_table.insertRow(row_position)
                    self.view_distance_table.setItem(row_position, 0, QTableWidgetItem(setting.get('name', '')))
                    self.view_distance_table.setItem(row_position, 1, QTableWidgetItem(str(setting.get('visionRange', 0))))
                    self.view_distance_table.setItem(row_position, 2, QTableWidgetItem(str(setting.get('gridWidth', 0))))
                except Exception as e:
                    logger.error(f'加载视觉设置时出错: {e}')
                    QMessageBox.warning(self, '加载错误', f'加载视觉设置时出错: {e}')
            # 加载调试模式配置
            server_logger = debug_config.get('serverLoggerLevel', {})
            self.log_level.setCurrentText(server_logger.get('levelStr', 'INFO'))
            self.show_packet_content.setChecked(debug_config.get('showPacketContent', False))

            # 加载调试白名单/黑名单
            whitelist_ids = [str(uid) for uid in server_config.get('debugWhitelist', [])]
            self.debug_whitelist.setText('\n'.join(whitelist_ids))
            blacklist_ids = [str(uid) for uid in server_config.get('debugBlacklist', [])]
            self.debug_blacklist.setText('\n'.join(blacklist_ids))

            # 加载调度服务器配置 (多地区)
            self.regions_table.setRowCount(0) # 清空表格
            for region in dispatch_config.get('regions', []):
                try:
                    row_position = self.regions_table.rowCount()
                    self.regions_table.insertRow(row_position)
                    self.regions_table.setItem(row_position, 0, QTableWidgetItem(region.get('name', '')))
                    self.regions_table.setItem(row_position, 1, QTableWidgetItem(region.get('title', '')))
                    self.regions_table.setItem(row_position, 2, QTableWidgetItem(region.get('dispatchUrl', '')))
                    self.regions_table.setItem(row_position, 3, QTableWidgetItem(region.get('secretKey', '')))
                    self.regions_table.setItem(row_position, 4, QTableWidgetItem(region.get('encryptionKey', '')))
                    # 添加删除按钮
                    delete_btn = QPushButton('删除')
                    delete_btn.clicked.connect(lambda checked, row=row_position: self.delete_region_row(row))
                    self.regions_table.setCellWidget(row_position, 5, delete_btn)
                except Exception as e:
                    logger.error(f'加载地区配置时出错: {e}')
                    QMessageBox.warning(self, '加载错误', f'加载地区配置时出错: {e}')

            # 加载语言设置配置
            self.primary_language.setCurrentText(config.get('language', {}).get('primary', 'zh_CN'))
            self.secondary_language.setCurrentText(config.get('language', {}).get('secondary', 'en_US'))
            self.document_language.setCurrentText(config.get('language', {}).get('documentLanguage', 'CHS'))

            # 加载账户系统配置
            account_config = config.get('account', {})
            self.auto_create_account.setChecked(account_config.get('autoCreate', False))

            default_account_config = account_config.get('default', {})
            self.avatar_id.setValue(default_account_config.get('avatarId', 10000000))
            self.name_card_id.setValue(default_account_config.get('nameCardId', 0))
            self.nickname.setText(default_account_config.get('nickname', ''))
            self.signature.setText(default_account_config.get('signature', ''))
            self.world_level.setValue(default_account_config.get('worldLevel', 0))

            # 修改权限加载逻辑
            permissions = account_config.get('defaultPermissions', [])
            self.permission_table.setRowCount(0)
            for perm in permissions:
                try:
                    row_position = self.permission_table.rowCount()
                    self.permission_table.insertRow(row_position)
                    self.permission_table.setItem(row_position, 0, QTableWidgetItem(perm))
                except Exception as e:
                    logger.error(f'加载权限时出错: {e}')
                    QMessageBox.warning(self, '加载错误', f'加载权限时出错: {e}')

            # 加载欢迎邮件配置
            welcome_mail_config = config.get('welcomeMail', {})
            self.welcome_mail_title.setText(welcome_mail_config.get('title', ''))
            self.welcome_mail_sender.setText(welcome_mail_config.get('sender', ''))
            self.welcome_mail_content.setText(welcome_mail_config.get('content', ''))
            # 加载欢迎邮件附件 (Assuming items are directly under welcomeMail)
            items = welcome_mail_config.get('items', []) # 修正:从 welcome_mail_config 获取 items
            self.welcome_mail_attachments.setRowCount(0) # 清空表格
            for item in items:
                row_position = self.welcome_mail_attachments.rowCount()
                self.welcome_mail_attachments.insertRow(row_position)
                self.welcome_mail_attachments.setItem(row_position, 0, QTableWidgetItem(str(item.get('itemId', 0))))
                self.welcome_mail_attachments.setItem(row_position, 1, QTableWidgetItem(str(item.get('itemCount', 0))))
                self.welcome_mail_attachments.setItem(row_position, 2, QTableWidgetItem(str(item.get('itemLevel', 1))))

        except FileNotFoundError:
            logger.warning(f'配置文件 {self.config_path} 未找到，将使用默认值或留空。')
            # 可以选择性地填充默认值或让用户知道
            pass # 允许程序继续，但某些字段可能为空
        except json.JSONDecodeError as e:
            logger.error(f'配置文件 {self.config_path} 格式错误: {e}')
            QMessageBox.critical(self, '配置错误', f'配置文件格式错误，请检查或删除后重试。\n错误: {e}')
        except Exception as e:
            logger.error(f'加载配置文件时发生未知错误: {e}')
            QMessageBox.critical(self, '加载错误', f'加载配置文件时发生未知错误: {e}')

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
                "plugins": self.plugins_path.text(),  # Added missing keys
                "cache": self.cache_path.text() # 保存缓存路径
            }
            # 更新数据库配置
            config['databaseInfo'] = {
                "server": {
                    "connectionUri": self.db_uri.text(),
                    "collection": self.db_collection.text()
                },
                "game": {
                    "connectionUri": self.game_db_uri.text(),
                    "collection": self.game_db_collection.text()
                }
            }
            # 更新服务器配置
            config['server'] = config.get('server', {}) # 确保 server 字典存在
            config['server']['http'] = config['server'].get('http', {}) # 确保 http 字典存在
            config['server']['game'] = config['server'].get('game', {}) # 确保 game 字典存在
            config['server']['debugMode'] = config['server'].get('debugMode', {}) # 确保 debugMode 字典存在
            config['server']['dispatch'] = config['server'].get('dispatch', {}) # 确保 dispatch 字典存在

            config['server']['http']['bindAddress'] = self.http_bind_address.text()
            config['server']['http']['bindPort'] = int(self.http_port.text())
            config['server']['http']['accessAddress'] = self.http_access_address.text()
            config['server']['http']['accessPort'] = int(self.http_access_port.text())
            config['server']['http']['startImmediately'] = self.start_immediately.isChecked()

            config['server']['game']['bindAddress'] = self.game_bind_address.text()
            config['server']['game']['bindPort'] = int(self.game_port.text())
            config['server']['game']['accessAddress'] = self.game_access_address.text()
            config['server']['game']['accessPort'] = int(self.game_access_port.text())
            config['server']['game']['enableConsole'] = self.enable_console.isChecked()
            config['server']['game']['useUniquePacketKey'] = self.use_unique_packet_key.isChecked()

            config['server']['fastRequire'] = self.fast_require.isChecked()
            config['server']['logCommands'] = self.log_commands.isChecked()
            config['server']['runMode'] = self.run_mode.currentText()

            # 确报 gameOptions 字典存在
            config['server']['game']['gameOptions'] = config['server']['game'].get('gameOptions', {})

            # 更新树脂配置
            config['server']['game']['gameOptions']['resinOptions'] = {
                "cap": self.resin_capacity.value(),
                "rechargeTime": self.resin_recovery_time.value()
            }
            # 更新背包限制配置
            config['server']['game']['gameOptions']['inventoryLimits'] = { # 修正键名
                "weaponLimit": self.weapon_limit.value(),
                "reliquaryLimit": self.reliquary_limit.value(),
                "materialLimit": self.material_limit.value(),
                "furnitureLimit": self.furniture_limit.value()
            }
            # 更新角色限制配置
            config['server']['game']['gameOptions']['characterLimits'] = { # 修正键名
                "singleCharacterLimit": self.single_char_limit.value(),
                "partyLimit": self.party_limit.value()
            }
            # 更新游戏功能开关
            config['server']['game']['gameOptions']['enableAvatarEvents'] = self.enable_avatar_events.isChecked() # 新增
            config['server']['game']['gameOptions']['enableShopItems'] = self.enable_shop_items.isChecked() # 新增
            config['server']['game']['gameOptions']['enableCostumes'] = self.enable_costumes.isChecked() # 新增
            config['server']['game']['gameOptions']['costumeStrategy'] = self.costume_strategy.currentText() # 新增
            config['server']['game']['gameOptions']['trialCostumes'] = self.trial_costumes.isChecked() # 新增
            config['server']['game']['gameOptions']['enableFishing'] = self.enable_fishing.isChecked()
            config['server']['game']['gameOptions']['enableHousing'] = self.enable_housing.isChecked()
            config['server']['game']['gameOptions']['enableGacha'] = self.enable_gacha.isChecked()

            # 更新任务选项配置
            config['server']['game']['gameOptions']['questOptions'] = { # 新增
                "enabled": self.enable_quests.isChecked(),
                "mainQuests": self.enable_main_quests.isChecked(),
                "shareQuests": self.share_quests.isChecked(),
                "rewardQuests": self.reward_quests.isChecked(),
                "dailyQuests": self.daily_quests.value(),
                "randomQuests": self.random_quests.value(),
                "talkQuests": self.talk_quests.value()
            }

            # 更新手册选项配置
            # 解析handbook服务器配置
            server_text = self.handbook_server.text()
            server_dict = {}
            if ':' in server_text:
                address, port = server_text.split(':', 1)
                server_dict = {"address": address, "port": int(port)}
            else:
                server_dict = {"address": server_text, "port": 443}  # 默认端口

            # 保留原始配置中的额外字段
            original_server = config['server']['game']['gameOptions'].get('handbook', {}).get('server', {})

            if isinstance(original_server, dict):
                server_dict.update({
                    "enforced": original_server.get('enforced', False),
                    "canChange": original_server.get('canChange', False)
                })

            # 更新handbook配置
            config['server']['game']['gameOptions']['handbook'] = {
                "allowHandbook": self.allow_handbook.isChecked(),
                "server": server_dict,  # 使用解析后的字典
                "limits": {
                    "maxRequests": self.handbook_max_requests.value(),
                    "timeFrame": self.handbook_time_frame.value()
                }
            }

            # 更新视觉设置配置
            config['server']['game']['gameOptions']['visionOptions'] = []
            for row in range(self.view_distance_table.rowCount()):
                try:
                    name_item = self.view_distance_table.item(row, 0)
                    range_item = self.view_distance_table.item(row, 1)
                    width_item = self.view_distance_table.item(row, 2)
                    # 检查单元格是否存在且内容不为空
                    if name_item and name_item.text() and range_item and range_item.text() and width_item and width_item.text():
                        name = name_item.text()
                        vision_range = int(range_item.text())
                        grid_width = int(width_item.text())
                        config['server']['game']['gameOptions']['visionOptions'].append({"name": name, "visionRange": vision_range, "gridWidth": grid_width})
                    else:
                        logger.warning(f'视觉设置表格第 {row+1} 行数据不完整或为空，已跳过')
                except ValueError:
                    QMessageBox.warning(self, '保存警告', f'视觉设置表格第 {row+1} 行包含无效数字，该行未保存')
                    continue # 跳过此行，继续处理下一行
                except Exception as e:
                    QMessageBox.critical(self, '保存错误', f'处理视觉设置表格第 {row+1} 行时出错: {e}')
                    return # 出现意外错误则停止保存
            # 更新调试模式配置
            config['server']['debugMode'] = {
            "serverLoggerLevel": {"levelStr": self.log_level.currentText()},
            "showPacketContent": self.show_packet_content.isChecked()
            }
            # 更新调试白名单/黑名单
            try:
                whitelist_ids = [int(uid.strip()) for uid in self.debug_whitelist.toPlainText().split('\n') if uid.strip().isdigit()]
            except ValueError:
                QMessageBox.warning(self, '警告', '调试白名单包含无效的 UID')
                return
            config['server']['debugWhitelist'] = whitelist_ids
            try:
                blacklist_ids = [int(uid.strip()) for uid in self.debug_blacklist.toPlainText().split('\n') if uid.strip().isdigit()]
            except ValueError:
                QMessageBox.warning(self, '警告', '调试黑名单包含无效的 UID')
                return
            config['server']['debugBlacklist'] = blacklist_ids

            # 更新调度服务器地区配置
            regions_data = []
            for row in range(self.regions_table.rowCount()):
                name = self.regions_table.item(row, 0).text() if self.regions_table.item(row, 0) else ''
                title = self.regions_table.item(row, 1).text() if self.regions_table.item(row, 1) else ''
                dispatch_url = self.regions_table.item(row, 2).text() if self.regions_table.item(row, 2) else ''
                secret_key = self.regions_table.item(row, 3).text() if self.regions_table.item(row, 3) else ''
                encryption_key = self.regions_table.item(row, 4).text() if self.regions_table.item(row, 4) else ''
                regions_data.append({
                    'name': name,
                    'title': title,
                    'dispatchUrl': dispatch_url,
                    'secretKey': secret_key,
                    'encryptionKey': encryption_key,
                    'dispatchKey': 'HK4E_Dispatch_Key',
                    'logRequests': False
                })
            config['server']['dispatch']['regions'] = regions_data

            # 更新语言设置配置
            config['language'] = {
                "primary": self.primary_language.currentText(),
                "secondary": self.secondary_language.currentText(),
                "documentLanguage": self.document_language.currentText()
            }

            # 更新账户系统配置，保留其他字段
            if 'account' not in config:
                config['account'] = {}
            account_config = config['account']
            account_config['autoCreate'] = self.auto_create_account.isChecked()

            # 更新default字段
            if 'default' not in account_config:
                account_config['default'] = {}
            default_account = account_config['default']
            default_account['avatarId'] = self.avatar_id.value()
            default_account['nameCardId'] = self.name_card_id.value()
            default_account['nickname'] = self.nickname.text()
            default_account['signature'] = self.signature.text()
            default_account['worldLevel'] = self.world_level.value()

            # 修改权限保存逻辑
            permissions_list = []
            for row in range(self.permission_table.rowCount()):
                try:
                    name_item = self.permission_table.item(row, 0)
                    if name_item and name_item.text():
                        permissions_list.append(name_item.text())
                except Exception as e:
                    QMessageBox.critical(self, '保存错误', f'处理权限表格第 {row+1} 行时出错: {e}')
                    return
            account_config['defaultPermissions'] = permissions_list

            # 更新欢迎邮件配置
            config['welcomeMail'] = {
                "title": self.welcome_mail_title.text(),
                "sender": self.welcome_mail_sender.text(),
                "content": self.welcome_mail_content.text(),
                "items": [] # Corrected key name based on load logic assumption
            }
            # 更新欢迎邮件附件
            for row in range(self.welcome_mail_attachments.rowCount()):
                id_item = self.welcome_mail_attachments.item(row, 0)
                count_item = self.welcome_mail_attachments.item(row, 1)
                level_item = self.welcome_mail_attachments.item(row, 2)  # 新增
                
                if id_item and id_item.text() and count_item and count_item.text():
                    item_id = int(id_item.text())
                    count = int(count_item.text())
                    level = int(level_item.text()) if level_item and level_item.text() else 1
                    if count > 0:
                        config['welcomeMail']['items'].append({
                            "itemId": item_id, 
                            "itemCount": count, 
                            "itemLevel": level
                        })

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.success('配置保存成功')
            self.accept()
        except ValueError as e:
            logger.error(f'保存配置时遇到无效的数值: {e}')
            QMessageBox.critical(self, '保存错误', f'保存失败: 无效的数值，请检查输入。\n错误: {e}')
        except Exception as e:
            logger.error(f'保存配置时发生未知错误: {e}')
            QMessageBox.critical(self, '保存错误', f'保存失败: {e}')

    # --- 通用表格操作方法 ---
    def _add_table_row(self, table: QTableWidget):
        """向指定表格添加一个空行"""
        row_position = table.rowCount()
        table.insertRow(row_position)
        # 为新行添加默认空 QTableWidgetItem，防止保存时因 item 为 None 出错
        for col in range(table.columnCount()):
            table.setItem(row_position, col, QTableWidgetItem(''))

    def _remove_selected_table_rows(self, table: QTableWidget):
        """删除指定表格中选中的行"""
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, '提示', '请先选择要删除的行')
            return
        # 从后往前删除，避免索引变化导致错误
        for index in sorted([r.row() for r in selected_rows], reverse=True):
            table.removeRow(index)

    # --- 特定表格操作方法 (调用通用方法) ---
    def add_view_distance(self):
        self._add_table_row(self.view_distance_table)

    def delete_view_distance(self):
        self._remove_selected_table_rows(self.view_distance_table)

    def add_area_server(self):
        self._add_table_row(self.area_servers_table)

    def delete_area_server(self):
        self._remove_selected_table_rows(self.area_servers_table)

    def add_permission(self):
        self._add_table_row(self.permission_table)

    def delete_permission(self):
        self._remove_selected_table_rows(self.permission_table)

    def add_welcome_item(self):
        self._add_table_row(self.welcome_mail_attachments)

    def delete_welcome_item(self):
        self._remove_selected_table_rows(self.welcome_mail_attachments)

    def select_file(self, line_edit, caption, filter_str):
        file_name, _ = QFileDialog.getOpenFileName(self, caption, '', filter_str)