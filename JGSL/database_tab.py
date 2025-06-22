from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt
from loguru import logger
import pymongo
from database_editor_dialog import DatabaseEditorDialog
import os
import shutil
import subprocess
import zipfile
import datetime
import psutil
import time
import sys
from PyQt5.QtWidgets import QApplication

class DatabaseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)

        # 提示标签
        self.info_label = QLabel("在这里管理你的数据库", self)
        self.info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.info_label)

        # 按钮行布局
        button_layout = QHBoxLayout()

        # 清空数据库按钮
        self.clear_db_button = QPushButton("清空数据库", self)
        self.clear_db_button.clicked.connect(self.clear_database)
        button_layout.addWidget(self.clear_db_button)

        # 导出数据库按钮
        self.export_db_button = QPushButton("导出数据库", self)
        self.export_db_button.clicked.connect(self.export_database)
        button_layout.addWidget(self.export_db_button)

        # 导入数据库按钮
        self.import_db_button = QPushButton("导入数据库", self)
        self.import_db_button.clicked.connect(self.import_database)
        button_layout.addWidget(self.import_db_button)

        # 修改数据库按钮
        self.modify_db_button = QPushButton("修改数据库", self)
        self.modify_db_button.clicked.connect(self.edit_database)
        button_layout.addWidget(self.modify_db_button)

        main_layout.addLayout(button_layout)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(main_layout)
        logger.info("数据库管理标签页初始化完成")

    def clear_database(self):
        # 警告用户
        reply = QMessageBox.warning(self, "警告", "此操作将停止数据库服务并删除所有数据，是否继续？", 
                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            logger.info("用户取消了清空数据库操作")
            return
            
        try:
            # 停止数据库服务
            self.stop_database_service()
            
            # 删除 Database/Data 目录
            data_path = os.path.join(os.getcwd(), "Database", "Data")
            if os.path.exists(data_path):
                shutil.rmtree(data_path)
                os.makedirs(data_path)
                logger.info(f"已清空数据库目录: {data_path}")
                
            QMessageBox.information(self, "成功", "数据库已清空")
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            QMessageBox.critical(self, "错误", f"清空数据库失败\n错误信息: {e}")

    def export_database(self):
        # 实现导出数据库的逻辑
        database_path = os.path.join(os.getcwd(), "Database", "Data") # 获取 Database/Data 文件夹的绝对路径
        if not os.path.exists(database_path) or not os.path.isdir(database_path):
            logger.warning(f"数据库文件夹 {database_path} 不存在或不是一个目录")
            QMessageBox.warning(self, "错误", f"数据库文件夹不存在\n路径:{database_path}")
            return

        # 默认保存路径为项目根目录，文件名为 database_backup.zip 
        default_save_path = os.path.join(os.getcwd(), "database_backup.zip")
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "导出数据库", default_save_path, "Zip Files (*.zip);;All Files (*)", options=options)

        if file_path:
            try:
                # 确保目标目录存在，如果用户选择了一个尚不存在的目录中的文件名
                save_dir = os.path.dirname(file_path)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)

                # shutil.make_archive 会自动添加 .zip 后缀，所以如果用户输入的文件名包含 .zip，需要去掉
                archive_name = file_path
                if archive_name.endswith('.zip'):
                    archive_name = archive_name[:-4]

                shutil.make_archive(archive_name, 'zip', database_path)
                logger.info(f"数据库已成功导出到 {file_path} ")
                QMessageBox.information(self, "成功", f"数据库已成功导出到\n路径:{file_path}")
            except Exception as e:
                logger.error(f"导出数据库失败:{e}")
                QMessageBox.critical(self, "错误", f"导出数据库失败\n错误信息:{e}")
        else:
            logger.info("用户取消了导出数据库操作")

    def import_database(self):
        # 实现导入数据库的逻辑
        logger.info("开始导入数据库操作")
        
        # 获取数据库目录路径
        database_path = os.path.join(os.getcwd(), "Database", "Data")
        if not os.path.exists(os.path.dirname(database_path)):
            os.makedirs(os.path.dirname(database_path))
        
        # 选择要导入的zip文件
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "选择数据库备份文件", "", "Zip Files (*.zip);;All Files (*)", options=options)
        
        if not file_path:
            logger.info("用户取消了导入数据库操作")
            return
            
        # 确认是否继续导入（会覆盖现有数据）
        reply = QMessageBox.question(self, "确认导入", "导入操作将覆盖现有数据库，是否继续", 
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            logger.info("用户取消了导入确认")
            return
            
        try:
            # 停止MongoDB服务（如果正在运行）
            self.stop_database_service()
            
            # 备份当前数据库（如果存在）
            if os.path.exists(database_path) and os.path.isdir(database_path) and os.listdir(database_path):
                backup_dir = os.path.join(os.getcwd(), "Database", "Backup_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
                logger.info(f"备份当前数据库到 {backup_dir}")
                shutil.copytree(database_path, backup_dir)
            
            # 清空当前数据库目录
            if os.path.exists(database_path):
                shutil.rmtree(database_path)
            os.makedirs(database_path)
            
            # 解压导入的zip文件
            logger.info(f"从 {file_path} 导入数据库")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(database_path)
                
            logger.info("数据库导入成功")
            QMessageBox.information(self, "成功", f"数据库已成功导入\n源文件:{file_path}")
        except Exception as e:
            logger.error(f"导入数据库失败:{e}")
            QMessageBox.critical(self, "错误", f"导入数据库失败\n错误信息:{e}")
            
    def stop_database_service(self):
        """停止MongoDB数据库服务"""
        logger.info("停止MongoDB服务")
        try:
            # 检查进程名是否为mongod.exe并终止
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'mongod.exe':
                        logger.warning(f'检测到 mongod.exe 进程，终止进程 {proc.info["pid"]}') 
                        proc.terminate()
                        proc.wait(timeout=3)
                        # 二次检查确保进程已关闭
                        if proc.is_running():
                            logger.warning(f'进程 {proc.info["pid"]} 未正确终止，尝试强制终止')
                            proc.kill()
                            proc.wait(timeout=3)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired) as e:
                    logger.error(f"终止进程时出错: {e}")
                    
            # 删除Data目录下的mongod.lock文件
            lock_file = os.path.join(os.getcwd(), "Database", "Data", "mongod.lock")
            if os.path.exists(lock_file):
                os.remove(lock_file)
                logger.info("已删除mongod.lock文件")
                
            logger.info("MongoDB服务已停止")
        except Exception as e:
            logger.error(f"停止数据库服务时出错: {e}")
            QMessageBox.warning(self, "警告", f"停止数据库服务时出错\n错误信息:{e}\n\n请手动确保MongoDB服务已停止后再继续。")

    def is_mongod_running(self):
        """检查 mongod.exe 进程是否正在运行"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'mongod.exe':
                return True
        return False

    def start_mongod(self):
        """启动 mongod.exe 服务"""
        # 获取当前脚本所在的目录 (JGSL)
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        # 获取项目根目录 (JimGrasscutterServerLauncher)
        project_root_dir = os.path.dirname(current_script_dir)
        # 构建 mongod.exe 的相对路径
        mongod_exe_path = os.path.join(project_root_dir, "Database", "mongod.exe")
        # 构建 mongod.conf 的相对路径
        mongod_conf_path = os.path.join(project_root_dir, "Database", "mongod.conf")
        # 构建数据库数据目录的相对路径
        db_path = os.path.join(project_root_dir, "Database", "Data")

        if not os.path.exists(mongod_exe_path):
            logger.error(f"mongod.exe 未找到路径: {mongod_exe_path}")
            QMessageBox.critical(self, "错误", f"启动数据库失败\nmongod.exe 未找到，请检查路径是否正确。\n预期路径: {mongod_exe_path}")
            return False

        # 确保数据目录存在
        if not os.path.exists(db_path):
            try:
                os.makedirs(db_path)
                logger.info(f"已创建数据库目录: {db_path}")
            except Exception as e:
                logger.error(f"创建数据库目录 {db_path} 失败: {e}")
                QMessageBox.critical(self, "错误", f"创建数据库目录失败\n路径: {db_path}\n错误: {e}")
                return False

        try:
            logger.info(f"尝试启动 mongod.exe 从: {mongod_exe_path}")
            # 使用 subprocess.Popen 启动 mongod.exe
            if os.path.exists(mongod_conf_path):
                logger.info(f"使用配置文件: {mongod_conf_path}")
                subprocess.Popen([mongod_exe_path, "--config", mongod_conf_path], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                logger.warning(f"mongod.conf 未找到于: {mongod_conf_path}，尝试无配置文件启动，可能需要手动指定 --dbpath")
                subprocess.Popen([mongod_exe_path, "--dbpath", db_path], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 等待一段时间让 MongoDB 启动
            time.sleep(3) # 等待3秒，可以根据实际情况调整
            if self.is_mongod_running():
                logger.success("mongod.exe 已成功启动")
                return True
            else:
                logger.error("mongod.exe 启动失败或超时")
                QMessageBox.warning(self, "警告", "启动 mongod.exe 失败或超时\n请检查日志或手动启动。")
                return False
        except Exception as e:
            logger.error(f"启动 mongod.exe 失败: {e}")
            QMessageBox.critical(self, "错误", f"启动数据库失败\n错误信息: {e}")
            return False

    def edit_database(self):
        # 实现编辑数据库的逻辑
        if not self.is_mongod_running():
            logger.info("mongod.exe 未运行，尝试启动...")
            if not self.start_mongod():
                logger.error("无法启动 mongod.exe，取消编辑数据库操作")
                return # 如果启动失败，则不继续
        else:
            logger.info("mongod.exe 正在运行")

        mongo_url = "mongodb://127.0.0.1:27017/"
        try:
            client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000) # 设置5秒超时
            client.admin.command('ping') # 检查连接是否成功
            logger.info(f"成功连接到 MongoDB: {mongo_url} ")
            editor_dialog = DatabaseEditorDialog(client, self)
            editor_dialog.exec_() # 使用 exec_() 以模态方式显示对话框
        except pymongo.errors.ServerSelectionTimeoutError as err:
            logger.error(f"连接 MongoDB 超时: {err}")
            QMessageBox.critical(self, "错误", f"连接 MongoDB 超时\nURL: {mongo_url}\n请确保 MongoDB 服务正在运行并且地址正确")
        except Exception as e:
            logger.error(f"连接 MongoDB 失败: {e}")
            QMessageBox.critical(self, "错误", f"连接 MongoDB 失败\nURL: {mongo_url}\n错误信息: {e}")

if __name__ == '__main__':
    # 这个部分是用于独立测试这个模块的
    app = QApplication(sys.argv)
    main_window = QWidget()
    main_layout = QVBoxLayout(main_window)
    database_tab = DatabaseTab(main_window)
    main_layout.addWidget(database_tab)
    main_window.setWindowTitle("数据库管理测试")
    main_window.resize(400, 300)
    main_window.show()
    sys.exit(app.exec_())