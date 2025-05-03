from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QFileDialog, QMessageBox, QTextEdit, QLineEdit, QHBoxLayout, QDialog, QFormLayout, QDialogButtonBox
from PyQt5.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QObject, pyqtProperty, QEasingCurve, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen, QLinearGradient
import psutil
import os
import json
import sys
import time
import datetime
import threading
from loguru import logger


class CircleProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._animation = QPropertyAnimation(self, b'value', self)
        self._animation.setDuration(1000)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.setFixedSize(50, 50)

    def set_value(self, value):
        self._animation.setEndValue(value)
        self._animation.start()

    def get_value(self):
        return self._value

    value = pyqtProperty(int, get_value, set_value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(0, 0, 50, 50)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        gradient = QLinearGradient(0, 0, 50, 50)
        gradient.setColorAt(0, QColor(0, 255, 0))
        gradient.setColorAt(1, QColor(0, 128, 0))
        painter.setBrush(gradient)
        painter.drawPie(QRect(2, 2, 46, 46), 90 * 16, int(-self.value * 16 * 3.6))
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(QRect(0, 0, 50, 50), Qt.AlignCenter, f"{self.value}%")


class MonitorPanel(QDialog):
    def __init__(self, instance_name, pid, log_path):
        try:
            logger.debug('初始化监控面板 实例:{} PID:{} 日志路径:{}', instance_name, pid, log_path)
            super().__init__()
            self.instance_name = instance_name
            self.pid = pid
            self.log_path = log_path
            self.cpu_usage = CircleProgress()
            self.mem_usage = CircleProgress()
            self.log_text = QTextEdit()
            self.command_input = QLineEdit()
            self.command_button = QPushButton('发送')
            self.command_button.clicked.connect(self.send_command)
            self.stop_button = QPushButton('关闭实例')
            self.stop_button.clicked.connect(self.stop_instance)
            self.stop_button.setStyleSheet("QPushButton { background-color: red; color: white; }")
            self.log_timer = QTimer()
            self.log_timer.timeout.connect(self.update_log)
            self.resource_timer = QTimer()
            self.resource_timer.timeout.connect(self.update_resource_usage)
            self.resource_timer.start(1000)
            self.current_log = ""
            self.start_time = datetime.datetime.now() - datetime.timedelta(seconds=time.time() - psutil.Process(self.pid).create_time())
            self.last_log_size = 0
            self.layout = QVBoxLayout()
            self.layout.addWidget(self.cpu_usage)
            self.layout.addWidget(self.mem_usage)
            self.layout.addWidget(self.stop_button)
            self.layout.addWidget(self.log_text)
            self.layout.addWidget(self.command_input)
            self.layout.addWidget(self.command_button)
            self.setLayout(self.layout)
            self.log_text.setReadOnly(True)
            self.log_text.setLineWrapMode(QTextEdit.NoWrap)
            self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.command_input.returnPressed.connect(self.send_command)
            self.command_history = []
            self.log_timer.start(1000)
            self.update_log()
            self.update_resource_usage()
        except Exception as e:
            logger.exception('监控面板初始化失败')
            raise

    def update_resource_usage(self):
        try:
            if self.pid and psutil.pid_exists(self.pid):
                proc = psutil.Process(self.pid)
                self.cpu_usage.value = proc.cpu_percent(interval=1)
                self.mem_usage.value = proc.memory_info().rss / 1024 / 1024
                self.update_uptime()
            else:
                self.cpu_usage.value = 0
                self.mem_usage.value = 0
                logger.warning('无效PID:{} 进程状态:{}', self.pid, psutil.pid_exists(self.pid))
        except Exception as e:
            logger.error(f"更新资源使用情况时发生错误: {e}")

    def update_uptime(self):
        if self.start_time:
            uptime = datetime.datetime.now() - self.start_time
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.setWindowTitle(f"{self.instance_name} 运行时间：{int(hours)} 小时 {int(minutes)} 分钟 {int(seconds)} 秒")

class LogReaderThread(QThread):
    log_data_ready = pyqtSignal(str)
    log_error = pyqtSignal(str)
    
    def __init__(self, log_path):
        super().__init__()
        self.log_path = log_path
        self.last_log_size = 0
        self.running = True
        
    def run(self):
        while self.running:
            try:
                if not os.path.exists(self.log_path):
                    self.log_error.emit(f'日志文件不存在: {self.log_path}')
                    time.sleep(1)
                    continue
                    
                try:
                    file_size = os.path.getsize(self.log_path)
                    if file_size != self.last_log_size:
                        try:
                            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                                # 先尝试定位到文件末尾附近
                                f.seek(max(0, file_size - 50 * 100))  # 从文件末尾前50KB开始读取
                                # 丢弃第一行，因为可能是不完整的行
                                f.readline()
                                # 读取剩余行
                                lines = f.readlines()
                                if len(lines) > 100:
                                    lines = lines[-100:]
                                new_log = ''.join(lines)
                            
                            self.log_data_ready.emit(new_log)
                            self.last_log_size = file_size
                        except UnicodeDecodeError as ude:
                            logger.warning('日志文件编码错误: {}', str(ude))
                            self.log_error.emit(f'日志文件编码错误，尝试使用替代编码读取')
                            # 尝试使用替代编码
                            try:
                                with open(self.log_path, 'r', encoding='gbk', errors='replace') as f:
                                    lines = f.readlines()
                                    if len(lines) > 100:
                                        lines = lines[-100:]
                                    new_log = ''.join(lines)
                                self.log_data_ready.emit(new_log)
                                self.last_log_size = file_size
                            except Exception as e2:
                                self.log_error.emit(f'使用替代编码读取日志失败: {str(e2)}')
                        except Exception as e:
                            self.log_error.emit(f'读取日志文件时发生错误: {str(e)}')
                except Exception as e:
                    self.log_error.emit(f'获取文件大小时发生错误: {str(e)}')
                
                time.sleep(0.5)
            except Exception as e:
                self.log_error.emit(f'日志读取线程发生错误: {str(e)}')
                time.sleep(1)
    
    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class MonitorPanel(QDialog):
    def __init__(self, instance_name, pid, log_path):
        try:
            logger.debug('初始化监控面板 实例:{} PID:{} 日志路径:{}', instance_name, pid, log_path)
            super().__init__()
            self.instance_name = instance_name
            self.pid = pid
            self.log_path = log_path
            self.cpu_usage = CircleProgress()
            self.mem_usage = CircleProgress()
            self.log_text = QTextEdit()
            self.command_input = QLineEdit()
            self.command_button = QPushButton('发送')
            self.command_button.clicked.connect(self.send_command)
            self.stop_button = QPushButton('关闭实例')
            self.stop_button.clicked.connect(self.stop_instance)
            self.stop_button.setStyleSheet("QPushButton { background-color: red; color: white; }")
            self.log_timer = QTimer()
            self.log_timer.timeout.connect(self.update_log)
            self.resource_timer = QTimer()
            self.resource_timer.timeout.connect(self.update_resource_usage)
            self.resource_timer.start(1000)
            self.current_log = ""
            self.start_time = datetime.datetime.now() - datetime.timedelta(seconds=time.time() - psutil.Process(self.pid).create_time())
            self.last_log_size = 0
            self.layout = QVBoxLayout()
            self.layout.addWidget(self.cpu_usage)
            self.layout.addWidget(self.mem_usage)
            self.layout.addWidget(self.stop_button)
            self.layout.addWidget(self.log_text)
            self.layout.addWidget(self.command_input)
            self.layout.addWidget(self.command_button)
            self.setLayout(self.layout)
            self.log_text.setReadOnly(True)
            self.log_text.setLineWrapMode(QTextEdit.NoWrap)
            self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.command_input.returnPressed.connect(self.send_command)
            self.command_history = []
            self.log_timer.start(1000)
            self.update_log()
            self.update_resource_usage()
        except Exception as e:
            logger.exception('监控面板初始化失败')
            raise

    def update_resource_usage(self):
        try:
            if self.pid and psutil.pid_exists(self.pid):
                proc = psutil.Process(self.pid)
                self.cpu_usage.value = proc.cpu_percent(interval=1)
                self.mem_usage.value = proc.memory_info().rss / 1024 / 1024
                self.update_uptime()
            else:
                self.cpu_usage.value = 0
                self.mem_usage.value = 0
                logger.warning('无效PID:{} 进程状态:{}', self.pid, psutil.pid_exists(self.pid))
        except Exception as e:
            logger.error(f"更新资源使用情况时发生错误: {e}")

    def update_uptime(self):
        if self.start_time:
            uptime = datetime.datetime.now() - self.start_time
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.setWindowTitle(f"{self.instance_name} 运行时间：{int(hours)} 小时 {int(minutes)} 分钟 {int(seconds)} 秒")
            
    def update_log(self):
        # 使用单一的日志读取线程实例
        if not hasattr(self, 'log_reader'):
            logger.debug('创建日志读取线程: {}', self.log_path)
            self.log_reader = LogReaderThread(self.log_path)
            self.log_reader.log_data_ready.connect(self.update_log_text)
            self.log_reader.log_error.connect(lambda msg: logger.warning(msg))
            self.log_reader.last_log_size = self.last_log_size  # 传递当前已知的日志大小
        
        # 每次调用时启动线程进行一次读取
        if not self.log_reader.isRunning():
            self.log_reader.start()
    
    def update_log_text(self, log_text):
        self.log_text.setText(log_text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def send_command(self):
        command = self.command_input.text()
        if self.pid and command:
            try:
                proc = psutil.Process(self.pid)
                stdin_fd = proc.stdin
                stdin_fd.write(command + '\n')
                stdin_fd.flush()
                self.command_history.append(command)
                self.command_input.clear()
            except Exception as e:
                print(f"发送命令时发生错误: {e}")
                
    def stop_instance(self):
        reply = QMessageBox.question(self, '确认', '你确定要关闭这个实例吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.pid:
                try:
                    proc = psutil.Process(self.pid)
                    proc.terminate()
                    self.log_timer.stop()
                    # 停止日志读取线程
                    if hasattr(self, 'log_reader'):
                        logger.debug('停止日志读取线程')
                        self.log_reader.stop()
                    self.pid = None
                    self.close()
                except Exception as e:
                    logger.error(f"终止进程时发生错误: {e}")

    def closeEvent(self, event):
        self.log_timer.stop()
        self.resource_timer.stop()
        # 停止日志读取线程
        if hasattr(self, 'log_reader'):
            logger.debug('停止日志读取线程')
            self.log_reader.stop()
        event.accept()

    def stop_instance(self):
        reply = QMessageBox.question(self, '确认', '你确定要关闭这个实例吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.pid:
                try:
                    proc = psutil.Process(self.pid)
                    proc.terminate()
                    self.log_timer.stop()
                    # 停止日志读取线程
                    if hasattr(self, 'log_reader'):
                        logger.debug('停止日志读取线程')
                        self.log_reader.stop()
                    self.pid = None
                    self.close()
                except Exception as e:
                    logger.error(f"终止进程时发生错误: {e}")

    def closeEvent(self, event):
        self.log_timer.stop()
        self.resource_timer.stop()
        # 停止日志读取线程
        if hasattr(self, 'log_reader'):
            logger.debug('停止日志读取线程')
            self.log_reader.stop()
        event.accept()


class MonitorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.instance_list = QListWidget()
        self.db_status = QLabel("数据库状态：未连接")
        self.instance_status = QLabel("运行实例数：0")
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.instance_status)
        self.layout.addWidget(QLabel("运行实例:"))
        self.layout.addWidget(self.instance_list)
        self.layout.addWidget(self.db_status)
        self.start_btn = QPushButton('打开监控面板')
        self.start_btn.clicked.connect(self.open_monitor_panel)
        self.refresh_btn = QPushButton('手动刷新')
        self.btn_layout = QHBoxLayout()
        self.btn_layout.addWidget(self.start_btn)
        self.btn_layout.addWidget(self.refresh_btn)
        self.layout.addLayout(self.btn_layout)
        self.setLayout(self.layout)
        self.resource_timer = QTimer()
        self.resource_timer.timeout.connect(self.update_resource_usage)
        self.resource_timer.start(1000)
        self.running_instances = []
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.refresh_btn.clicked.connect(self.on_manual_refresh)

    def open_monitor_panel(self):
        if not self.instance_list.currentItem():
            QMessageBox.warning(self, '警告', '请先选择一个运行实例')
            return
        self.instance_name = self.instance_list.currentItem().text()
        self.instance_path = os.path.join(self.root_dir, "Servers", self.instance_name)
        self.log_file_path = os.path.join(self.instance_path, "logs", "latest.log")
        lock_path = os.path.join(self.instance_path, "Running.lock")
        if not os.path.exists(lock_path):
            QMessageBox.warning(self, '错误', '选择的实例未运行')
            return
        try:
            logger.info(f"正在加载配置文件 {lock_path}")
            with open(lock_path, 'r') as f:
                lock_data = json.load(f)
            logger.debug('加载lock文件内容: {}', lock_data)
            self.pid = lock_data.get("pid")
            if not self.pid or not psutil.pid_exists(self.pid):
                QMessageBox.warning(self, '错误', '选择的实例未运行')
                return
            proc = psutil.Process(self.pid)
            if proc.name() != "java.exe":
                logger.warning('进程类型异常 PID:{} 名称:{} 期望:java.exe', self.pid, proc.name())
                QMessageBox.warning(self, '错误', '选择的实例未运行')
                return
            monitor_panel = MonitorPanel(self.instance_name, self.pid, self.log_file_path)
            monitor_panel.exec_()
        except json.JSONDecodeError:
            logger.error(f"配置文件 {lock_path} 内容不合法")
            QMessageBox.critical(self, '配置错误', '配置文件内容不合法')
        except Exception as e:
            logger.error(f"加载配置文件时发生错误: {e}")
            QMessageBox.critical(self, '配置错误', '配置文件读取失败')

    def update_resource_usage(self):
        try:
            db_status = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                if proc.info['name'] == "mongod.exe" and any('dbpath' in part for part in proc.info['cmdline']):
                    db_status = True
            if db_status:
                self.db_status.setText("数据库状态：已连接")
            else:
                self.db_status.setText("数据库状态：未连接")
        except Exception as e:
            logger.error(f"更新资源使用情况时发生错误: {e}")

    def scan_running_instances(self):
        self.running_instances.clear()
        servers_path = os.path.join(self.root_dir, 'Servers')
        logger.debug(f'当前Servers路径: {servers_path}')
        if not os.path.exists(servers_path):
            os.makedirs(servers_path, exist_ok=True)
            logger.success(f'目录已成功创建: {os.path.abspath(servers_path)}')
            logger.debug(f'绝对路径验证: {os.path.exists(servers_path)}')
        logger.success(f'服务器目录准备就绪: {servers_path}')
        for instance_name in os.listdir(servers_path):
            instance_path = os.path.join(servers_path, instance_name)
            if os.path.isdir(instance_path):
                lock_path = os.path.join(instance_path, "Running.lock")
                if os.path.exists(lock_path):
                    try:
                        logger.info(f"正在加载配置文件 {lock_path}")
                        with open(lock_path, 'r') as f:
                            lock_data = json.load(f)
                        pid = lock_data.get("pid")
                        if not pid or not psutil.pid_exists(pid):
                            logger.warning(f'PID {pid} 不存在')
                            continue
                        proc = psutil.Process(pid)
                        if proc.name() != "java.exe":
                            logger.warning(f'PID {pid} 进程名称不符: {proc.name()}')
                            continue
                        logger.debug(f'发现运行实例: {instance_name} PID={pid}')
                        self.running_instances.append((pid, instance_path))
                    except json.JSONDecodeError:
                        logger.error(f"配置文件 {lock_path} 内容不合法")
                    except Exception as e:
                        logger.error(f"加载配置文件时发生错误: {e}")
                        QMessageBox.critical(self, '配置错误', '配置文件读取失败')
        self.update_instance_display()

    def update_instance_display(self):
        valid_instances = []
        for pid, instance_path in self.running_instances:
            try:
                if psutil.pid_exists(pid) and psutil.Process(pid).name() == 'java.exe':
                    valid_instances.append((pid, instance_path))
                else:
                    logger.warning(f'进程 {pid} 已终止或不是Java进程')
            except psutil.NoSuchProcess:
                logger.warning(f'进程 {pid} 不存在')
        
        self.running_instances = valid_instances
        self.instance_status.setText(f"运行实例数：{len(self.running_instances)}")
        self.instance_list.clear()
        for pid, instance_path in self.running_instances:
            instance_name = os.path.basename(instance_path)
            self.instance_list.addItem(instance_name)
            logger.debug(f'更新实例显示: {instance_name}')

    def on_manual_refresh(self):
        current_item = self.instance_list.currentItem()
        current_selected = current_item.text() if current_item else None
        self.scan_running_instances()
        if current_selected:
            items = self.instance_list.findItems(current_selected, Qt.MatchExactly)
            if items:
                self.instance_list.setCurrentItem(items[0])