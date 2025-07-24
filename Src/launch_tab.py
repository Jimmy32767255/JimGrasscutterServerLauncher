import json
import psutil
import os, json, time, locale
from pathlib import Path
from loguru import logger
from port_checker import check_ports
from PyQt5.QtCore import QProcess, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QMessageBox

class LaunchTab(QWidget):
    instance_started = pyqtSignal(str, int)
    instance_stopped = pyqtSignal(str)
    # 新增信号:进程创建时发射 (PID, QProcess 对象)
    process_created = pyqtSignal(int, QProcess)
    # 新增信号:进程结束或错误时发射 (PID)
    process_finished_signal = pyqtSignal(int) # 避免与内建 finished 冲突

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")  # 设置背景透明
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.running_instances = {} # 存储所有正在运行的实例 {instance_name: {'process': QProcess, 'pid': int, 'instance_dir': Path}}
        self.db_process = QProcess()
        self.instance_counter = 0
        self.db_heartbeat_timer = QTimer()
        self.db_heartbeat_timer.setInterval(5000)
        self.db_heartbeat_timer.timeout.connect(self.check_db_health)

        self.server_list = QListWidget()
        self.start_btn = QPushButton(self.tr('启动选定的实例'))

        layout = QVBoxLayout()
        layout.addWidget(self.server_list)
        layout.addWidget(self.start_btn)

        self.setLayout(layout)
        self.refresh_server_list()

        self.start_btn.clicked.connect(self.start_selected_server)

    def refresh_server_list(self):
        self.server_list.clear()
        logger.debug(self.tr(f'当前项目根目录: {self.root_dir}'))
        instances_dir = Path(self.root_dir) / 'Servers'
        if instances_dir.exists() and instances_dir.is_dir():
            for instance_dir in instances_dir.iterdir():
                if instance_dir.is_dir() and (instance_dir / 'JGSL/Config.json').exists():
                    self.server_list.addItem(str(instance_dir.name))

    def start_selected_server(self):
        selected_items = self.server_list.selectedItems()
        if not selected_items:
            logger.warning(self.tr('请选择一个服务器实例'))
            return

        instance_name = selected_items[0].text()
        instance_dir = Path(self.root_dir) / 'Servers' / instance_name
        lock_file = instance_dir / 'Running.lock'

        if lock_file.exists():
            try:
                with open(lock_file, 'r') as f:
                    lock_info = json.load(f)
                pid = lock_info.get('pid')
                if pid and psutil.pid_exists(pid):
                    logger.warning(self.tr(f'实例 {instance_name} 正在运行中，无法启动'))
                    return
                else:
                    logger.warning(self.tr(f'检测到残留的锁文件，尝试移除'))
                    self.remove_lock_file(instance_dir)
            except json.JSONDecodeError:
                logger.warning(self.tr(f'锁文件读取失败，尝试移除'))
                self.remove_lock_file(instance_dir)
            except FileNotFoundError:
                logger.warning(self.tr(f'锁文件已不存在'))
            except Exception as e:
                logger.error(self.tr(f'检查锁文件时发生错误: {e}'))
                return

        try:
            with open(instance_dir / 'JGSL/Config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            java_path = config.get('java_path', 'java')
            # 检查 grasscutter_path 是否为绝对路径，如果不是则拼接
            raw_grasscutter_path = config.get("grasscutter_path", "grasscutter.jar")
            if Path(raw_grasscutter_path).is_absolute():
                grasscutter_path = Path(raw_grasscutter_path)
            else:
                grasscutter_path = instance_dir / raw_grasscutter_path
            
            # 检查 grasscutter_path 指向的文件是否存在
            if not grasscutter_path.exists():
                logger.error(self.tr(f'Grasscutter JAR 文件不存在: {grasscutter_path}'))
                QMessageBox.critical(self, self.tr('启动失败'), self.tr(f'Grasscutter JAR 文件不存在: {grasscutter_path}'), QMessageBox.Ok)
                self.remove_lock_file(instance_dir)
                return

            jvm_pre_args = config.get('jvm_pre_args', [])
            if isinstance(jvm_pre_args, str):
                jvm_pre_args = jvm_pre_args.split()
            jvm_post_args = config.get('jvm_post_args', [])
            if isinstance(jvm_post_args, str):
                jvm_post_args = jvm_post_args.split()
            
            config_path = instance_dir / 'config.json'
            dispatch_port = None
            game_port = None
            run_mode = None # 新增run_mode变量
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        gc_config = json.load(f)
                    dispatch_port = gc_config.get('server', {}).get('http', {}).get('bindPort')
                    game_port = gc_config.get('server', {}).get('game', {}).get('bindPort')
                    run_mode = gc_config.get('server', {}).get('runMode') # 读取runMode
                    if not all([dispatch_port, game_port]):
                        logger.warning(self.tr('Grasscutter配置文件缺少端口配置，将尝试使用默认端口或跳过端口检查。'))
                except Exception as e:
                    logger.error(self.tr(f'读取Grasscutter配置文件失败: {e}，将尝试在无配置状态下启动。'))
            else:
                logger.warning(self.tr(f'Grasscutter配置文件 {config_path} 不存在，将尝试在无配置状态下启动。'))

            # 如果端口未从配置文件中获取到，则使用默认值或跳过检查
            if dispatch_port is None:
                dispatch_port = 443
                logger.info(self.tr(f'未找到Dispatch端口配置，使用默认值: {dispatch_port}'))
            if game_port is None:
                game_port = 22102
                logger.info(self.tr(f'未找到Game端口配置，使用默认值: {game_port}'))

            # 只有当端口有效时才进行端口检查
            if dispatch_port and game_port:
                port_results = check_ports([(27017, 'tcp'), (dispatch_port, 'tcp'), (game_port, 'udp')], run_mode=run_mode, dispatch_port=dispatch_port)
                for port, proto, occupied, info in port_results:
                    if occupied:
                        logger.error(self.tr(f'端口 {port}/{proto} 被进程占用: {info}'))
                        QMessageBox.critical(self, self.tr('端口冲突'), self.tr(f'端口 {port}/{proto} 被进程占用\n进程ID: {info["pid"]}\n进程名称: {info["process_name"]}'), QMessageBox.Ok)
                        self.remove_lock_file(instance_dir)
                        return
                logger.info(self.tr('所有必要端口可用'))
            else:
                logger.warning(self.tr('由于端口配置缺失，跳过端口可用性检查。'))

            # 检查是否已经有实例在运行，如果没有，则启动数据库服务
            if not self.running_instances:
                self.start_database_service()
                self.db_heartbeat_timer.start()

            # 检查当前实例是否已经在运行
            if instance_name in self.running_instances:
                logger.warning(self.tr(f'实例 {instance_name} 已经在运行中，无法重复启动。'))
                QMessageBox.warning(self, self.tr('重复启动'), self.tr(f'实例 {instance_name} 已经在运行中。'), QMessageBox.Ok)
                return

            self.instance_counter += 1
            # 启动按钮不再禁用，允许同时启动多个实例
            # 检查Java路径和Grasscutter路径是否有效
            if not java_path or not grasscutter_path:
                logger.error(self.tr(f'Java路径或Grasscutter路径无效: java_path={java_path}, grasscutter_path={grasscutter_path}'))
                QMessageBox.critical(self, self.tr('启动失败'), self.tr(f'Java路径或Grasscutter路径无效\nJava路径: {java_path}\nGrasscutter路径: {grasscutter_path}'), QMessageBox.Ok)
                self.start_btn.setEnabled(True)
                self.instance_counter -= 1
                return
                
            process = QProcess(self)
            process.setWorkingDirectory(str(instance_dir))
            process.setProgram(java_path)
            process.setArguments([*(str(arg) for arg in jvm_pre_args), '-jar', str(grasscutter_path), *(str(arg) for arg in jvm_post_args)])
            process.errorOccurred.connect(lambda error, p=process, inst_name=instance_name, inst_dir=instance_dir: self.on_process_error(error, p, inst_name, inst_dir))
            process.finished.connect(lambda exitCode, exitStatus, p=process, inst_name=instance_name, inst_dir=instance_dir: self.on_process_finished(exitCode, exitStatus, p, inst_name, inst_dir))
            process.readyReadStandardOutput.connect(lambda p=process: self.handle_stdout(p))
            process.readyReadStandardError.connect(lambda p=process: self.handle_stderr(p))
            logger.debug(self.tr(f'执行命令: {java_path} {" ".join([*jvm_pre_args, "-jar", str(grasscutter_path), *jvm_post_args])}'))
            try:
                process.start()
                if not process.waitForStarted(3000):  # 等待最多3秒
                    logger.error(f'进程启动超时: {process.errorString()}')
                    QMessageBox.critical(self, '启动失败', f'进程启动超时\n错误信息: {process.errorString()}', QMessageBox.Ok)
                    self.instance_counter -= 1
                    return
                    
                # 进程成功启动后的处理
                if process and process.state() == QProcess.Running:
                    pid = process.processId()
                    # 将新启动的实例添加到字典中
                    self.running_instances[instance_name] = {'process': process, 'pid': pid, 'instance_dir': instance_dir}
                    # 发射 process_created 信号
                    self.process_created.emit(pid, process)
                    lock_file = instance_dir / 'Running.lock'
                    logger.debug(self.tr(f'创建锁文件: {lock_file} PID={pid}'))
                    try:
                        with open(lock_file, 'w') as f:
                            json.dump({
                                'pid': pid,
                                'start_time': time.time(),
                                'program': __file__,
                                'process_path': os.path.abspath(__file__)
                            }, f, indent=2)
                        logger.info(self.tr(f'成功写入锁文件 PID={pid}'))
                        if psutil.pid_exists(pid) and psutil.Process(pid).name() == 'java.exe':
                            logger.debug(self.tr(f'进程验证成功: PID={pid}'))
                        else:
                            logger.warning(self.tr(f'进程验证失败: PID={pid}'))
                    except Exception as e:
                        logger.error(self.tr(f'写入锁文件失败: {e}'))
                    self.instance_started.emit(instance_name, pid)
                logger.info(self.tr(f'启动实例 {instance_name}'))
            except Exception as e:
                logger.error(self.tr(f'启动进程时发生错误: {e}'))
                if process:
                    logger.error(self.tr(f'进程启动错误: {process.errorString()}'))
                self.instance_counter -= 1
                return
        except Exception as e:
            logger.error(self.tr(f'启动实例 {instance_name} 时发生错误: {e}'))
            logger.error(self.tr(f'读取配置文件失败或启动进程时发生错误: {e}'))
            if process:
                logger.error(self.tr(f'进程启动错误: {process.errorString()}'))
            self.instance_counter -= 1
            self.remove_lock_file(instance_dir)
            return

    def start_database_service(self):
        try:
            # 检查进程名是否为mongod.exe
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'mongod.exe':
                        logger.warning(self.tr(f'检测到 mongod.exe 进程，终止进程 {proc.info["pid"]}'))
                        proc.terminate()
                        proc.wait()
                        # 二次检查确保进程已关闭
                        if proc.is_running():
                            logger.warning(self.tr(f'进程 {proc.info["pid"]} 未正确终止，尝试强制终止'))
                            proc.kill()
                            proc.wait()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            # 删除Data目录下的mongod.lock文件
            lock_file = Path(self.root_dir) / 'Database' / 'Data' / 'mongod.lock'
            if lock_file.exists():
                lock_file.unlink()
        except Exception as e:
            logger.error(f'数据库启动前清理失败: {e}')
            return

        self.db_process.setProgram(str(Path(self.root_dir) / 'Database' / 'mongod.exe'))
        self.db_process.setArguments(['--dbpath', str(Path(self.root_dir) / 'Database' / 'Data'), '--logpath', str(Path(self.root_dir) / 'Database' / 'mongod.log'), '--bind_ip', '127.0.0.1', '--port', '27017', '--nojournal'])
        self.db_process.errorOccurred.connect(self.handle_db_error)
        self.db_process.readyReadStandardError.connect(self.handle_stderr)
        logger.debug(f'执行命令: mongod.exe --dbpath {str(Path(self.root_dir) / "Database" / "Data")} --logpath {str(Path(self.root_dir) / "Database" / "mongod.log")} --bind_ip 127.0.0.1 --port 27017 --nojournal')
        self.db_process.start()
        logger.info(f'启动数据库')
        if not self.db_process.waitForStarted(3000):
            logger.error(f'数据库启动失败: {self.db_process.errorString()}')
            self.db_process.kill()
            self.db_process.waitForFinished()

    def create_lock_file(self, instance_dir):
        lock_file = instance_dir / 'Running.lock'
        try:
            if self.current_process is None:
                logger.error('无法创建锁文件: 进程未初始化')
                return
            pid = self.current_process.processId()
            with open(lock_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'pid': pid,
                    'start_time': time.time(),
                    'program': __file__,
                    'process_path': os.path.abspath(__file__)
                }, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f'创建锁文件失败: {e}')

    def remove_lock_file(self, instance_dir):
        lock_file = instance_dir / 'Running.lock'
        if lock_file.exists():
            lock_file.unlink()

    def on_process_finished(self, exitCode, exitStatus, process: QProcess, instance_name: str, instance_dir: Path):
        pid = process.processId() if process else None
        self.remove_lock_file(instance_dir)
        self.instance_stopped.emit(instance_name)
        logger.info(f'实例 {instance_name} 已停止')
        # 从运行实例字典中移除
        if instance_name in self.running_instances:
            del self.running_instances[instance_name]
        # 发射 process_finished_signal 信号
        if pid:
            self.process_finished_signal.emit(pid)
        self.instance_counter -= 1
        if self.instance_counter == 0:
            self.db_process.terminate()
            self.db_process.finished.connect(self.db_process.deleteLater)
            self.db_process.waitForFinished(3000)
            self.db_heartbeat_timer.stop()
            logger.info(f'数据库已停止')

    def on_process_error(self, error, process: QProcess, instance_name: str, instance_dir: Path):
        pid = process.processId() if process else None
        logger.error(f'实例 {instance_name} 启动失败: {process.errorString()}')
        self.remove_lock_file(instance_dir)
        # 从运行实例字典中移除
        if instance_name in self.running_instances:
            del self.running_instances[instance_name]
        # 发射 process_finished_signal 信号
        if pid:
            self.process_finished_signal.emit(pid)
        self.instance_counter -= 1
        if self.instance_counter == 0:
            self.db_process.terminate()
            self.db_process.finished.connect(self.db_process.deleteLater)
            self.db_process.waitForFinished(3000)
            self.db_heartbeat_timer.stop()
            logger.info(f'数据库已停止')

    def handle_stdout(self, process: QProcess):
        text = process.readAllStandardOutput().data().decode(locale.getpreferredencoding(False), errors='replace')
        logger.trace(f'进程输出: {text.strip()}')

    def handle_stderr(self, process: QProcess):
        text = process.readAllStandardError().data().decode(locale.getpreferredencoding(False), errors='replace')
        if process.state() != QProcess.Running:
            logger.error(f'进程错误: {text.strip()}')
        elif self.db_process.state() != QProcess.Running and process == self.db_process:
            if 'waiting for connections on port' in text:
                logger.info(f'数据库已成功启动')
            else:
                logger.error(f'数据库错误: {text.strip()}')

    def handle_db_error(self, error):
        logger.error(f'数据库启动失败: {self.db_process.errorString()}')

    def check_db_health(self):
        if self.db_process.state() != QProcess.Running:
            logger.warning('数据库进程异常，尝试重启...')
            self.start_database_service()

    def cleanup(self):
        # 终止所有运行中的实例进程
        for instance_name, instance_data in list(self.running_instances.items()):
            process = instance_data['process']
            pid = instance_data['pid']
            instance_dir = instance_data['instance_dir']
            if process and process.state() == QProcess.Running:
                logger.info(f'正在终止实例 {instance_name} (PID: {pid})')
                process.terminate()
                process.waitForFinished(3000)
                if process.state() == QProcess.Running:
                    process.kill()
                    process.waitForFinished() # 等待 kill 完成
                # 发射 process_finished_signal 信号
                if pid:
                    self.process_finished_signal.emit(pid)
                self.remove_lock_file(instance_dir)
                del self.running_instances[instance_name]
        # 终止数据库进程
        if self.db_process.state() == QProcess.Running:
            self.db_process.terminate()
            self.db_process.waitForFinished(3000)
            if self.db_process.state() == QProcess.Running:
                self.db_process.kill()
        # 额外检查并终止mongod.exe进程
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == 'mongod.exe':
                    logger.warning(f'检测到残留的mongod.exe进程，终止进程 {proc.info["pid"]}')
                    proc.terminate()
                    proc.wait()
                    if proc.is_running():
                        proc.kill()
                        proc.wait()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        # 停止心跳检测
        self.db_heartbeat_timer.stop()
        # 重置计数器
        self.instance_counter = 0
        logger.info('完成所有资源清理')

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_server_list()