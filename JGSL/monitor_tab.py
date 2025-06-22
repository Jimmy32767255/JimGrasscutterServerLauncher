from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QMessageBox, QTextEdit, QLineEdit, QHBoxLayout, QDialog
from PyQt5.QtCore import Qt, QTimer, QRect, QPropertyAnimation, pyqtProperty, QEasingCurve, QThread, pyqtSignal, QProcess
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QTextCursor
import psutil
import os
import json
import time
import datetime
import threading
from loguru import logger
import random # 导入 random 用于生成模拟数据
import qdarkstyle # 导入主题库


class CircleProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_value = 0  # 目标值
        self._current_value = 0 # 动画当前值
        self._animation = QPropertyAnimation(self, b'current_value', self) # 动画作用于 current_value
        self._animation.setDuration(500)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.setFixedSize(50, 50)

    # --- Public Method to Set Target --- 
    def set_value(self, target_value):
        # 限制 value 在 0-100
        target_value = max(0, min(100, int(target_value)))

        # 如果目标值与当前目标值相同，则不执行任何操作
        if self._target_value == target_value:
            return

        self._target_value = target_value

        # 如果动画正在运行，先停止
        if self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()

        # 设置动画的起始值和结束值
        self._animation.setStartValue(self._current_value) # 从当前动画值开始
        self._animation.setEndValue(target_value)

        # 启动动画
        try:
            self._animation.start()
        except Exception as e:
            logger.exception(f'CircleProgress - Failed to start animation: {e}')

    # --- Property for Animation --- 
    @pyqtProperty(int)
    def current_value(self):
        return self._current_value

    @current_value.setter
    def current_value(self, value):
        # 这个 setter 由 QPropertyAnimation 调用
        self._current_value = value
        self.update() # 触发重绘

    # --- Paint Event --- 
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制背景圆
            painter.setPen(Qt.NoPen) # 无边框
            painter.setBrush(QColor(230, 230, 230)) # 浅灰色背景
            painter.drawEllipse(0, 0, 50, 50)

            # 绘制进度条弧形
            painter.setPen(QPen(QColor(76, 175, 80), 3)) # 绿色，线宽3
            # painter.setBrush(Qt.NoBrush) # 不填充
            rect = QRect(2, 2, 46, 46) # 稍微内缩以适应边框
            start_angle = 90 * 16 # 12点钟方向
            span_angle = int(-self._current_value * 3.6 * 16) # 逆时针绘制
            painter.drawArc(rect, start_angle, span_angle)

            # 绘制中心文本
            painter.setPen(QColor(255, 255, 255)) # 白色文字
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(QRect(0, 0, 50, 50), Qt.AlignCenter, f"{int(self._current_value)}%")
        except Exception as e:
            logger.exception(f'CircleProgress - Error during paintEvent: {e}')


class MonitorPanel(QDialog):
    instance_closed_signal = pyqtSignal(str) # 实例关闭信号，参数为 instance_name
    process_disappeared_signal = pyqtSignal(str) # 进程消失信号，参数为 instance_name

    def __init__(self, instance_name, pid, log_path, process: QProcess | None = None, debug_mode=False):
        try:
            # 在日志中记录 process 对象
            logger.debug('初始化监控面板 实例:{} PID:{} 日志路径:{} 进程对象:{} 调试模式:{}', instance_name, pid, log_path, process, debug_mode)
            super().__init__()
            self.instance_name = instance_name
            self.pid = pid
            self.log_path = log_path
            self.process = process # 存储 QProcess 对象
            self.debug_mode = debug_mode # 保存调试模式状态
            
            # 应用主题设置
            config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Config', 'config.json')
            try:
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    theme = config_data.get('Theme', 'dark')
                    if theme == 'dark':
                        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
                    else:
                        self.setStyleSheet('')
            except Exception as e:
                logger.error(f'加载主题设置失败: {e}')
                self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            
            # 设置窗口大小和标题
            self.resize(800, 600)  # 设置一个合适的初始大小
            
            # --- 创建控件 ---
            self.cpu_usage = CircleProgress()
            self.mem_usage = CircleProgress()
            self.cpu_label = QLabel("CPU")
            self.mem_label = QLabel("MEM")
            self.uptime_label = QLabel("UpTime: 00h00m00s")
            self.log_text = QTextEdit()
            self.command_input = QLineEdit()
            self.command_button = QPushButton('发送')
            self.clear_button = QPushButton('清屏')
            self.stop_button = QPushButton('关闭实例')
            self.stop_button.setStyleSheet("QPushButton { background-color: red; color: white; }")
            
            # --- 设置控件属性 ---
            self.cpu_label.setAlignment(Qt.AlignCenter)
            self.mem_label.setAlignment(Qt.AlignCenter)
            self.uptime_label.setAlignment(Qt.AlignCenter)
            self.log_text.setReadOnly(True)
            self.log_text.setLineWrapMode(QTextEdit.WidgetWidth) # 自动换行
            self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.command_input.setPlaceholderText("在这里输入指令...")
            
            # 根据调试模式设置控件和连接信号
            if self.debug_mode:
                self.setWindowTitle(f"监控面板: {self.instance_name} (调试模式)")
                self.command_input.setPlaceholderText("调试模式下无法发送命令")
                self.command_input.setEnabled(False)
                self.command_button.setEnabled(False)
                self.stop_button.setText("关闭调试面板")
                self.stop_button.clicked.connect(self.close) # 调试模式下关闭按钮直接关闭窗口
                self.log_text.setPlainText("logs logs logs logs logs logs logs logs logs logs logs logs logs\n" * 20)
                self.clear_button.clicked.connect(self.clear_log)
            else:
                self.setWindowTitle(f"监控面板: {self.instance_name}")
                self.command_button.clicked.connect(self.send_command)
                self.stop_button.clicked.connect(self.stop_instance)
                self.command_input.returnPressed.connect(self.send_command)
                self.clear_button.clicked.connect(self.clear_log)

            # --- 定时器和变量初始化 ---
            self.log_timer = QTimer()
            self.log_timer.timeout.connect(self.update_log)
            self.resource_timer = QTimer()
            self.resource_timer.timeout.connect(self.update_resource_usage)
            self.resource_timer.start(1000)
            self.current_log = ""
            self.last_log_size = 0
            self.command_history = []
            self._is_closing = False

            # 调试模式下不需要计算启动时间或读取真实日志
            if not self.debug_mode:
                # 使用延迟初始化，避免在构造函数中进行耗时操作
                self.start_time = None
                try:
                    # 只有在非调试模式且 PID 有效时才计算启动时间
                    if self.pid and self.pid != -1 and psutil.pid_exists(self.pid):
                        # 使用非阻塞方式获取进程创建时间
                        proc = psutil.Process(self.pid)
                        self.start_time = datetime.datetime.now() - datetime.timedelta(seconds=time.time() - proc.create_time())
                    else:
                        logger.warning("无法获取进程启动时间，PID无效或进程不存在")
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.error(f"获取进程创建时间失败: {e}")
                except Exception as e:
                    logger.error(f"计算进程启动时间时发生未知错误: {e}")
                
                # 创建日志读取线程，但延迟启动
                self.log_reader_thread = LogReaderThread(self.log_path)
                self.log_reader_thread.log_data_ready.connect(self.append_log)
                self.log_reader_thread.log_error.connect(self.handle_log_error)
                # 使用QTimer延迟启动线程，避免在构造函数中启动
                QTimer.singleShot(100, self.log_reader_thread.start)
                self.log_timer.start(1000)
                self.update_log() # 非调试模式才需要立即更新日志
            else:
                self.start_time = datetime.datetime.now() # 调试模式给个假的启动时间

            # --- 创建布局 ---
            # 右侧面板布局
            right_panel = QVBoxLayout()
            right_panel.addWidget(self.cpu_usage, alignment=Qt.AlignCenter)
            right_panel.addWidget(self.cpu_label)
            right_panel.addSpacing(10)
            right_panel.addWidget(self.mem_usage, alignment=Qt.AlignCenter)
            right_panel.addWidget(self.mem_label)
            right_panel.addSpacing(10)
            right_panel.addWidget(self.uptime_label)
            right_panel.addStretch(1)
            right_panel.addWidget(self.stop_button)
            right_panel.addWidget(self.clear_button)
            
            # 右侧面板容器
            right_widget = QWidget()
            right_widget.setLayout(right_panel)
            right_widget.setFixedWidth(100)  # 固定右侧面板宽度
            
            # 底部命令输入区域布局
            command_layout = QHBoxLayout()
            command_layout.addWidget(self.command_input)
            command_layout.addWidget(self.command_button)
            
            # 主布局
            main_layout = QHBoxLayout()
            main_layout.addWidget(self.log_text, 1)  # 日志区域占据更多空间
            main_layout.addWidget(right_widget)
            
            # 整体布局
            layout = QVBoxLayout(self)
            layout.addLayout(main_layout, 1)  # 主布局占据更多空间
            layout.addLayout(command_layout)
            self.setLayout(layout)
            
            # 首次更新资源和运行时间
            self.update_resource_usage()
            self.update_uptime()
            
            logger.info('监控面板初始化成功完成 实例:{} PID:{} 调试模式:{}', instance_name, pid, debug_mode)
        except Exception as e:
            logger.exception('监控面板初始化失败')
            # 即使初始化失败也要尝试显示错误信息
            QMessageBox.critical(self, "错误", f"监控面板初始化失败: {e}")
            # raise # 不再抛出异常，避免程序崩溃

    def update_resource_usage(self):
        try:
            # 调试模式下使用模拟数据
            if self.debug_mode:
                try:
                    # 使用较小范围的随机值，避免大幅度变化
                    if hasattr(self, '_last_cpu_val'):
                        # 在上次值的基础上小幅变化，模拟真实情况
                        cpu_val = max(10, min(70, self._last_cpu_val + random.randint(-5, 5)))
                    else:
                        cpu_val = random.randint(20, 50)
                    self._last_cpu_val = cpu_val
                    self.cpu_usage.set_value(cpu_val)
                except Exception as e:
                    logger.warning(f'调试模式 - 设置 CPU 模拟值失败: {e}')
                    # 使用exception级别太高，改为warning

                try:
                    # 模拟内存使用，改为百分比，同样小幅度变化
                    if hasattr(self, '_last_mem_val'):
                        mem_val = max(20, min(80, self._last_mem_val + random.randint(-3, 3)))
                    else:
                        mem_val = random.randint(30, 60)
                    self._last_mem_val = mem_val
                    self.mem_usage.set_value(mem_val)
                except Exception as e:
                    logger.warning(f'调试模式 - 设置内存模拟值失败: {e}')

                self.update_uptime() # 调试模式也更新假的运行时间
            elif self.pid and self.pid != -1:
                # 先检查进程是否存在，避免不必要的异常
                if not psutil.pid_exists(self.pid):
                    if not hasattr(self, '_pid_warning_shown') or not self._pid_warning_shown:
                        logger.warning(f'进程 {self.pid} 不存在，无法获取资源使用情况')
                        self._pid_warning_shown = True
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
                    return
                
                # 进程存在，获取资源使用情况
                try:
                    proc = psutil.Process(self.pid)
                    # 使用非阻塞方式获取CPU使用率
                    cpu_percent = int(proc.cpu_percent(interval=None))
                    self.cpu_usage.set_value(cpu_percent)
                    
                    # 获取内存使用率
                    mem_percent = int(proc.memory_percent())
                    self.mem_usage.set_value(mem_percent)
                    
                    # 重置警告标志
                    self._pid_warning_shown = False
                    
                    # 更新运行时间
                    self.update_uptime()
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    # 进程消失或无权限访问
                    if not hasattr(self, '_resource_error_shown') or not self._resource_error_shown:
                        logger.warning(f"访问进程 {self.pid} 信息失败: {e}")
                        self._resource_error_shown = True
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
                except Exception as e:
                    # 其他错误
                    if not hasattr(self, '_resource_error_shown') or not self._resource_error_shown:
                        logger.error(f"获取资源使用情况时发生错误: {e}")
                        self._resource_error_shown = True
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
            else:
                # PID无效
                self.cpu_usage.set_value(0)
                self.mem_usage.set_value(0)
                # 只在非调试模式下记录警告，且只记录一次
                if not self.debug_mode and (not hasattr(self, '_invalid_pid_warning_shown') or not self._invalid_pid_warning_shown):
                    logger.warning('无效PID:{} 进程状态:{}', self.pid, psutil.pid_exists(self.pid) if self.pid and self.pid != -1 else 'N/A')
                    self._invalid_pid_warning_shown = True
        except Exception as e:
            # 捕获所有未处理的异常
            logger.error(f"更新资源使用情况时发生未知错误: {e}")
            try:
                self.cpu_usage.set_value(0)
                self.mem_usage.set_value(0)
            except Exception:
                # 忽略二次错误，避免日志过多
                pass

    def update_uptime(self):
        if self.start_time:
            uptime = datetime.datetime.now() - self.start_time
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            # 调试模式标题加上提示
            title_prefix = f"{self.instance_name} (调试模式)" if self.debug_mode else self.instance_name
            self.uptime_label.setText(f"UpTime:\n{int(hours):02d}h{int(minutes):02d}m{int(seconds):02d}s")
        else:
            self.uptime_label.setText("UpTime:\nN/A") # Also add newline here for consistency

    # 添加处理日志读取线程信号的方法
    def append_log(self, log_content):
        try:
            # 使用QTimer.singleShot将UI更新操作放到主线程事件循环中执行
                # 这样可以避免在非主线程中直接操作UI元素导致的问题
                if not hasattr(self, '_log_buffer'):
                    self._log_buffer = ""
                    self._log_buffer_timer = QTimer()
                    self._log_buffer_timer.timeout.connect(self._flush_log_buffer)
                    self._log_buffer_timer.start(100)  # 每100ms刷新一次日志缓冲区
                
                # 将日志内容添加到缓冲区
                self._log_buffer += log_content
                
                # 如果缓冲区过大，立即刷新
                if len(self._log_buffer) > 5000:
                    QTimer.singleShot(0, self._flush_log_buffer)
        except Exception as e:
            logger.error(f"添加日志内容时发生错误: {e}")
    
    # 添加一个方法来刷新日志缓冲区
    def _flush_log_buffer(self):
        try:
            if hasattr(self, '_log_buffer') and self._log_buffer:
                # 获取当前滚动条位置
                scrollbar = self.log_text.verticalScrollBar()
                at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
                
                # 更新文本
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(self._log_buffer)
                self._log_buffer = ""
                
                # 如果之前在底部，则保持在底部
                if at_bottom:
                    scrollbar.setValue(scrollbar.maximum())
                
                # 检查是否需要裁剪日志
                # 从配置文件中读取最大日志行数，如果读取失败则使用默认值1000
                max_log_lines = 1000  # 默认值
                config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Config', 'config.json')
                try:
                    if os.path.exists(config_file):
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        max_log_lines = config_data.get('MaxLogLines', 1000)
                except Exception as e:
                    logger.error(f'读取配置文件中的MaxLogLines失败: {e}，将使用默认值1000')

                if self.log_text.document().lineCount() > max_log_lines:
                    QTimer.singleShot(0, self.trim_log_text)
        except Exception as e:
            logger.error(f"刷新日志缓冲区时发生错误: {e}")
            self._log_buffer = ""  # 出错时清空缓冲区

    def handle_log_error(self, error_message):
        try:
            logger.error(f"日志读取错误: {error_message}")
            # 使用QTimer.singleShot确保在主线程中更新UI
            QTimer.singleShot(0, lambda: self.log_text.append(f"<font color='red'>日志读取错误: {error_message}</font>"))
        except Exception as e:
            logger.error(f"处理日志错误时发生异常: {e}")
            
    def clear_log(self):
        """清空日志显示区域"""
        try:
            self.log_text.clear()
            logger.info(f"已清空监控面板日志显示 实例:{self.instance_name}")
        except Exception as e:
            logger.error(f"清空日志显示时发生错误: {e}")
            QMessageBox.warning(self, "警告", f"清空日志显示失败: {e}")

    def closeEvent(self, event):
        """处理窗口关闭事件，确保资源得到释放"""
        logger.info(f"监控面板关闭事件触发: {self.instance_name}")
        # 检查 _is_closing 标志，防止重复关闭逻辑
        if hasattr(self, '_is_closing') and self._is_closing:
            event.accept()
            return

        if hasattr(self, '_is_closing'):
            self._is_closing = True

        # 停止定时器
        try:
            if hasattr(self, 'log_timer') and self.log_timer.isActive():
                self.log_timer.stop()
                logger.debug(f"日志定时器已为实例 {self.instance_name} 停止")
        except Exception as e:
            logger.error(f"停止日志定时器时出错 ({self.instance_name}): {e}")
        
        try:
            if hasattr(self, 'resource_timer') and self.resource_timer.isActive():
                self.resource_timer.stop()
                logger.debug(f"资源定时器已为实例 {self.instance_name} 停止")
        except Exception as e:
            logger.error(f"停止资源定时器时出错 ({self.instance_name}): {e}")

        # 停止日志读取线程 (仅在非调试模式下)
        try:
            if not self.debug_mode and hasattr(self, 'log_reader_thread') and self.log_reader_thread.isRunning():
                logger.debug(f"正在停止实例 {self.instance_name} 的日志读取线程...")
                self.log_reader_thread.stop() # stop() 内部调用了 wait()
                logger.debug(f"实例 {self.instance_name} 的日志读取线程已请求停止")
        except Exception as e:
            logger.error(f"停止日志读取线程时出错 ({self.instance_name}): {e}")

        logger.info(f"监控面板 {self.instance_name} 清理操作完成，准备关闭。")
        super().closeEvent(event) # 调用父类的closeEvent以完成关闭过程


    # send_command 和 stop_instance 在调试模式下不应该被调用，但保留以防万一
    def send_command(self):
        if self.debug_mode:
            logger.warning("尝试在调试模式下发送命令")
            QMessageBox.warning(self, "提示", "调试模式下无法发送命令")
            return
        command = self.command_input.text()
        if not command:
            return

        logger.info(f'向实例 {self.instance_name} (PID: {self.pid}) 发送命令: {command}')

        # 使用 self.process (QProcess 对象) 发送命令
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            try:
                # 确保命令以换行符结束
                full_command = (command + '\n').encode('utf-8')
                bytes_written = self.process.write(full_command)
                
                # 检查写入是否成功
                if bytes_written == -1:
                    error_string = self.process.errorString()
                    logger.error(f"写入命令到进程 {self.pid} 失败. QProcess 错误: {error_string}")
                    QMessageBox.critical(self, "错误", f"发送命令失败: {error_string}")
                elif bytes_written < len(full_command):
                    logger.warning(f"命令可能未完全写入进程 {self.pid}. 写入 {bytes_written}/{len(full_command)} 字节.")
                    QMessageBox.warning(self, "警告", "命令可能未完全发送")
                    # 即使部分写入，也可能需要记录历史和清空输入
                    QMessageBox.information(self, "提示", f"命令 '{command}' 已发送 (可能不完整)")
                    self.command_history.append(command)
                    self.command_input.clear()
                else:
                    logger.success(f'命令成功发送到进程 {self.pid} (通过 QProcess)')
                    self.command_history.append(command) # 仅在成功或部分写入时添加到历史记录
                    self.command_input.clear()

            except Exception as e:
                logger.error(f'通过 QProcess 发送命令时出错: {e}')
                QMessageBox.critical(self, "错误", f"发送命令时发生意外错误: {e}")
                # 出错时不清除输入或添加到历史记录
        else:
            process_state = self.process.state() if self.process else "N/A"
            logger.error(f'无法发送命令:进程对象无效或进程未运行 (PID: {self.pid}, Process: {self.process}, State: {process_state})')
            QMessageBox.warning(self, "错误", "目标进程无效或未运行，无法发送命令")
            # 不清除输入或添加到历史记录

    def stop_instance(self):
        if self._is_closing: # 如果正在关闭，则不执行任何操作
            return
        self._is_closing = True # 设置正在关闭标志

        if self.debug_mode:
            logger.warning("尝试在调试模式下停止实例")
            self.instance_closed_signal.emit(self.instance_name)
            self.close() # 调试模式下直接关闭窗口
            return
        reply = QMessageBox.question(self, '确认', f'确定要关闭实例 {self.instance_name} (PID: {self.pid}) 吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            logger.info(f'正在尝试关闭实例 {self.instance_name} (PID: {self.pid})')
            try:
                if self.pid and psutil.pid_exists(self.pid):
                    proc = psutil.Process(self.pid)
                    proc.terminate() # 尝试友好终止
                    try:
                        proc.wait(timeout=5) # 等待5秒
                        logger.success(f'实例 {self.instance_name} (PID: {self.pid}) 已成功终止')
                    except psutil.TimeoutExpired:
                        logger.warning(f'实例 {self.instance_name} (PID: {self.pid}) 未能在5秒内终止，尝试强制结束')
                        proc.kill() # 强制结束
                        proc.wait()
                        logger.success(f'实例 {self.instance_name} (PID: {self.pid}) 已强制结束')
                    self.instance_closed_signal.emit(self.instance_name)
                    self.close() # 关闭监控面板
                else:
                    logger.warning(f'实例 {self.instance_name} (PID: {self.pid}) 进程不存在或无效')
                    QMessageBox.warning(self, '错误', '进程不存在或无效')
                    self.process_disappeared_signal.emit(self.instance_name) # 进程不存在，也认为消失了
                    self.instance_closed_signal.emit(self.instance_name)
                    self.close() # 进程不在了也关闭面板
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.error(f'关闭实例 {self.instance_name} (PID: {self.pid}) 时出错: {e}')
                QMessageBox.critical(self, '错误', f'关闭进程时出错: {e}')
                self.instance_closed_signal.emit(self.instance_name)
                self.close() # 出错了也关闭面板
            except Exception as e:
                logger.exception(f'关闭实例时发生未知错误: {e}')
                QMessageBox.critical(self, '错误', f'关闭进程时发生未知错误: {e}')
                self.instance_closed_signal.emit(self.instance_name)
                self.close()
        else:
            self._is_closing = False # 用户取消关闭，重置标志

    def update_resource_usage(self):
        if self.debug_mode:
            try:
                # 调试模式下使用模拟数据
                if self.debug_mode:
                    try:
                        # 使用较小范围的随机值，避免大幅度变化
                        if hasattr(self, '_last_cpu_val'):
                            # 在上次值的基础上小幅变化，模拟真实情况
                            cpu_val = max(10, min(70, self._last_cpu_val + random.randint(-5, 5)))
                        else:
                            cpu_val = random.randint(20, 50)
                        self._last_cpu_val = cpu_val
                        self.cpu_usage.set_value(cpu_val)
                    except Exception as e:
                        logger.warning(f'调试模式 - 设置 CPU 模拟值失败: {e}')
                        # 使用exception级别太高，改为warning

                    try:
                        # 模拟内存使用，改为百分比，同样小幅度变化
                        if hasattr(self, '_last_mem_val'):
                            mem_val = max(20, min(80, self._last_mem_val + random.randint(-3, 3)))
                        else:
                            mem_val = random.randint(30, 60)
                        self._last_mem_val = mem_val
                        self.mem_usage.set_value(mem_val)
                    except Exception as e:
                        logger.warning(f'调试模式 - 设置内存模拟值失败: {e}')

                    self.update_uptime() # 调试模式也更新假的运行时间
                elif self.pid and self.pid != -1:
                    # 先检查进程是否存在，避免不必要的异常
                    if not psutil.pid_exists(self.pid):
                        if not hasattr(self, '_pid_warning_shown') or not self._pid_warning_shown:
                            logger.warning(f'进程 {self.pid} 不存在，无法获取资源使用情况')
                            self._pid_warning_shown = True
                        self.cpu_usage.set_value(0)
                        self.mem_usage.set_value(0)
                        return
                    
                    # 进程存在，获取资源使用情况
                    try:
                        proc = psutil.Process(self.pid)
                        # 使用非阻塞方式获取CPU使用率
                        cpu_percent = int(proc.cpu_percent(interval=None))
                        self.cpu_usage.set_value(cpu_percent)
                        
                        # 获取内存使用率
                        mem_percent = int(proc.memory_percent())
                        self.mem_usage.set_value(mem_percent)
                        
                        # 重置警告标志
                        self._pid_warning_shown = False
                        
                        # 更新运行时间
                        self.update_uptime()
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        # 进程消失或无权限访问
                        if not hasattr(self, '_resource_error_shown') or not self._resource_error_shown:
                            logger.warning(f"访问进程 {self.pid} 信息失败: {e}")
                            self._resource_error_shown = True
                        self.cpu_usage.set_value(0)
                        self.mem_usage.set_value(0)
                    except Exception as e:
                        # 其他错误
                        if not hasattr(self, '_resource_error_shown') or not self._resource_error_shown:
                            logger.error(f"获取资源使用情况时发生错误: {e}")
                            self._resource_error_shown = True
                        self.cpu_usage.set_value(0)
                        self.mem_usage.set_value(0)
                else:
                    # PID无效
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
                    # 只在非调试模式下记录警告，且只记录一次
                    if not self.debug_mode and (not hasattr(self, '_invalid_pid_warning_shown') or not self._invalid_pid_warning_shown):
                        logger.warning('无效PID:{} 进程状态:{}', self.pid, psutil.pid_exists(self.pid) if self.pid and self.pid != -1 else 'N/A')
                        self._invalid_pid_warning_shown = True
            except Exception as e:
                # 捕获所有未处理的异常
                logger.error(f"更新资源使用情况时发生未知错误: {e}")
                try:
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
                except Exception:
                    # 忽略二次错误，避免日志过多
                    pass

            # 调试模式下使用模拟数据
            if self.debug_mode:
                try:
                    # 使用较小范围的随机值，避免大幅度变化
                    if hasattr(self, '_last_cpu_val'):
                        # 在上次值的基础上小幅变化，模拟真实情况
                        cpu_val = max(10, min(70, self._last_cpu_val + random.randint(-5, 5)))
                    else:
                        cpu_val = random.randint(20, 50)
                    self._last_cpu_val = cpu_val
                    self.cpu_usage.set_value(cpu_val)
                except Exception as e:
                    logger.warning(f'调试模式 - 设置 CPU 模拟值失败: {e}')
                    # 使用exception级别太高，改为warning

                try:
                    # 模拟内存使用，改为百分比，同样小幅度变化
                    if hasattr(self, '_last_mem_val'):
                        mem_val = max(20, min(80, self._last_mem_val + random.randint(-3, 3)))
                    else:
                        mem_val = random.randint(30, 60)
                    self._last_mem_val = mem_val
                    self.mem_usage.set_value(mem_val)
                except Exception as e:
                    logger.warning(f'调试模式 - 设置内存模拟值失败: {e}')

                self.update_uptime() # 调试模式也更新假的运行时间
            elif self.pid and self.pid != -1:
                # 先检查进程是否存在，避免不必要的异常
                if not psutil.pid_exists(self.pid):
                    if not hasattr(self, '_pid_warning_shown') or not self._pid_warning_shown:
                        logger.warning(f'进程 {self.pid} 不存在，无法获取资源使用情况')
                        self._pid_warning_shown = True
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
                    return
                
                # 进程存在，获取资源使用情况
                try:
                    proc = psutil.Process(self.pid)
                    # 使用非阻塞方式获取CPU使用率
                    cpu_percent = int(proc.cpu_percent(interval=None))
                    self.cpu_usage.set_value(cpu_percent)
                    
                    # 获取内存使用率
                    mem_percent = int(proc.memory_percent())
                    self.mem_usage.set_value(mem_percent)
                    
                    # 重置警告标志
                    self._pid_warning_shown = False
                    
                    # 更新运行时间
                    self.update_uptime()
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    # 进程消失或无权限访问
                    if not hasattr(self, '_resource_error_shown') or not self._resource_error_shown:
                        logger.warning(f"访问进程 {self.pid} 信息失败: {e}")
                        self._resource_error_shown = True
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
                except Exception as e:
                    # 其他错误
                    if not hasattr(self, '_resource_error_shown') or not self._resource_error_shown:
                        logger.error(f"获取资源使用情况时发生错误: {e}")
                        self._resource_error_shown = True
                    self.cpu_usage.set_value(0)
                    self.mem_usage.set_value(0)
            else:
                # PID无效
                self.cpu_usage.set_value(0)
                self.mem_usage.set_value(0)
                # 只在非调试模式下记录警告，且只记录一次
                if not self.debug_mode and (not hasattr(self, '_invalid_pid_warning_shown') or not self._invalid_pid_warning_shown):
                    logger.warning('无效PID:{} 进程状态:{}', self.pid, psutil.pid_exists(self.pid) if self.pid and self.pid != -1 else 'N/A')
                    self._invalid_pid_warning_shown = True

    def update_uptime(self):
        if self.start_time:
            uptime = datetime.datetime.now() - self.start_time
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            # 调试模式标题加上提示
            title_prefix = f"{self.instance_name} (调试模式)" if self.debug_mode else self.instance_name
            self.uptime_label.setText(f"UpTime:\n{int(hours):02d}h{int(minutes):02d}m{int(seconds):02d}s")
        else:
            self.uptime_label.setText("UpTime:\nN/A") # Also add newline here for consistency

    # 添加处理日志读取线程信号的方法
    def append_log(self, log_content):
        try:
            # 使用QTimer.singleShot将UI更新操作放到主线程事件循环中执行
            # 这样可以避免在非主线程中直接操作UI元素导致的问题
            if not hasattr(self, '_log_buffer'):
                self._log_buffer = ""
                self._log_buffer_timer = QTimer()
                self._log_buffer_timer.timeout.connect(self._flush_log_buffer)
                self._log_buffer_timer.start(100)  # 每100ms刷新一次日志缓冲区
            
            # 将日志内容添加到缓冲区
            self._log_buffer += log_content
            
            # 如果缓冲区过大，立即刷新
            if len(self._log_buffer) > 5000:
                QTimer.singleShot(0, self._flush_log_buffer)
        except Exception as e:
            logger.error(f"添加日志内容时发生错误: {e}")
    
    # 添加一个方法来刷新日志缓冲区
    def _flush_log_buffer(self):
        try:
            if hasattr(self, '_log_buffer') and self._log_buffer:
                # 获取当前滚动条位置
                scrollbar = self.log_text.verticalScrollBar()
                at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
                
                # 更新文本
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(self._log_buffer)
                self._log_buffer = ""
                
                # 如果之前在底部，则保持在底部
                if at_bottom:
                    scrollbar.setValue(scrollbar.maximum())
                
                # 检查是否需要裁剪日志
                if self.log_text.document().lineCount() > 1000:
                    QTimer.singleShot(0, self.trim_log_text)
        except Exception as e:
            logger.error(f"刷新日志缓冲区时发生错误: {e}")
            self._log_buffer = ""  # 出错时清空缓冲区

    def handle_log_error(self, error_message):
        try:
            logger.error(f"日志读取错误: {error_message}")
            # 使用QTimer.singleShot确保在主线程中更新UI
            QTimer.singleShot(0, lambda: self.log_text.append(f"<font color='red'>日志读取错误: {error_message}</font>"))
        except Exception as e:
            logger.error(f"处理日志错误时发生异常: {e}")
            
    def clear_log(self):
        """清空日志显示区域"""
        try:
            self.log_text.clear()
            logger.info(f"已清空监控面板日志显示 实例:{self.instance_name}")
        except Exception as e:
            logger.error(f"清空日志显示时发生错误: {e}")
            QMessageBox.warning(self, "警告", f"清空日志显示失败: {e}")

    def closeEvent(self, event):
        """处理窗口关闭事件，确保资源得到释放"""
        logger.info(f"监控面板关闭事件触发: {self.instance_name}")
        # 检查 _is_closing 标志，防止重复关闭逻辑
        if hasattr(self, '_is_closing') and self._is_closing:
            event.accept()
            return

        if hasattr(self, '_is_closing'):
            self._is_closing = True

        # 停止定时器
        try:
            if hasattr(self, 'log_timer') and self.log_timer.isActive():
                self.log_timer.stop()
                logger.debug(f"日志定时器已为实例 {self.instance_name} 停止")
        except Exception as e:
            logger.error(f"停止日志定时器时出错 ({self.instance_name}): {e}")
        
        try:
            if hasattr(self, 'resource_timer') and self.resource_timer.isActive():
                self.resource_timer.stop()
                logger.debug(f"资源定时器已为实例 {self.instance_name} 停止")
        except Exception as e:
            logger.error(f"停止资源定时器时出错 ({self.instance_name}): {e}")

        # 停止日志读取线程 (仅在非调试模式下)
        try:
            if not self.debug_mode and hasattr(self, 'log_reader_thread') and self.log_reader_thread.isRunning():
                logger.debug(f"正在停止实例 {self.instance_name} 的日志读取线程...")
                self.log_reader_thread.stop() # stop() 内部调用了 wait()
                logger.debug(f"实例 {self.instance_name} 的日志读取线程已请求停止")
        except Exception as e:
            logger.error(f"停止日志读取线程时出错 ({self.instance_name}): {e}")

        logger.info(f"监控面板 {self.instance_name} 清理操作完成，准备关闭。")
        super().closeEvent(event) # 调用父类的closeEvent以完成关闭过程


    # send_command 和 stop_instance 在调试模式下不应该被调用，但保留以防万一
    def send_command(self):
        if self.debug_mode:
            logger.warning("尝试在调试模式下发送命令")
            QMessageBox.warning(self, "提示", "调试模式下无法发送命令")
            return
        command = self.command_input.text()
        if not command:
            return

        logger.info(f'向实例 {self.instance_name} (PID: {self.pid}) 发送命令: {command}')

        # 使用 self.process (QProcess 对象) 发送命令
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            try:
                # 确保命令以换行符结束
                full_command = (command + '\n').encode('utf-8')
                bytes_written = self.process.write(full_command)
                
                # 检查写入是否成功
                if bytes_written == -1:
                    error_string = self.process.errorString()
                    logger.error(f"写入命令到进程 {self.pid} 失败. QProcess 错误: {error_string}")
                    QMessageBox.critical(self, "错误", f"发送命令失败: {error_string}")
                elif bytes_written < len(full_command):
                    logger.warning(f"命令可能未完全写入进程 {self.pid}. 写入 {bytes_written}/{len(full_command)} 字节.")
                    QMessageBox.warning(self, "警告", "命令可能未完全发送")
                    # 即使部分写入，也可能需要记录历史和清空输入
                    QMessageBox.information(self, "提示", f"命令 '{command}' 已发送 (可能不完整)")
                    self.command_history.append(command)
                    self.command_input.clear()
                else:
                    logger.success(f'命令成功发送到进程 {self.pid} (通过 QProcess)')
                    self.command_history.append(command) # 仅在成功或部分写入时添加到历史记录
                    self.command_input.clear()

            except Exception as e:
                logger.error(f'通过 QProcess 发送命令时出错: {e}')
                QMessageBox.critical(self, "错误", f"发送命令时发生意外错误: {e}")
                # 出错时不清除输入或添加到历史记录
        else:
            process_state = self.process.state() if self.process else "N/A"
            logger.error(f'无法发送命令:进程对象无效或进程未运行 (PID: {self.pid}, Process: {self.process}, State: {process_state})')
            QMessageBox.warning(self, "错误", "目标进程无效或未运行，无法发送命令")
            # 不清除输入或添加到历史记录

    def stop_instance(self):
        if self.debug_mode:
            logger.warning("尝试在调试模式下停止实例")
            self.close() # 调试模式下直接关闭窗口
            return
        reply = QMessageBox.question(self, '确认', f'确定要关闭实例 {self.instance_name} (PID: {self.pid}) 吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            logger.info(f'正在尝试关闭实例 {self.instance_name} (PID: {self.pid})')
            try:
                if self.pid and psutil.pid_exists(self.pid):
                    # 优先尝试发送STOP命令安全关闭
                    try:
                        self.command_input.setText("STOP")
                        self.send_command()
                        logger.info(f'已向实例 {self.instance_name} 发送STOP命令，等待安全关闭...')
                        
                        # 等待最多30秒让进程自行退出
                        proc = psutil.Process(self.pid)
                        for _ in range(30):
                            if not proc.is_running():
                                break
                            time.sleep(1)
                        else:
                            raise psutil.TimeoutExpired(30, "等待安全关闭超时")
                        
                        logger.success(f'实例 {self.instance_name} (PID: {self.pid}) 已安全关闭')
                        self.instance_closed_signal.emit(self.instance_name)
                        self.close()
                        return
                    except Exception as e:
                        if isinstance(e, psutil.TimeoutExpired):
                            logger.warning(f'安全关闭失败，等待超时 {e.timeout} 秒，将尝试终止进程。')
                        else:
                            logger.warning(f'安全关闭失败，将尝试终止进程: {e}')
                        
                    # 安全关闭失败后回退到原终止逻辑
                    proc = psutil.Process(self.pid)
                    proc.terminate() # 尝试友好终止
                    try:
                        proc.wait(timeout=5) # 等待5秒
                        logger.success(f'实例 {self.instance_name} (PID: {self.pid}) 已成功终止')
                    except psutil.TimeoutExpired:
                        logger.warning(f'实例 {self.instance_name} (PID: {self.pid}) 未能在5秒内终止，尝试强制结束')
                        proc.kill() # 强制结束
                        proc.wait()
                        logger.success(f'实例 {self.instance_name} (PID: {self.pid}) 已强制结束')
                    self.instance_closed_signal.emit(self.instance_name)
                    self.close() # 关闭监控面板
                else:
                    logger.warning(f'实例 {self.instance_name} (PID: {self.pid}) 进程不存在或无效')
                    QMessageBox.warning(self, '错误', '进程不存在或无效')
                    self.close() # 进程不在了也关闭面板
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.error(f'关闭实例 {self.instance_name} (PID: {self.pid}) 时出错: {e}')
                QMessageBox.critical(self, '错误', f'关闭进程时出错: {e}')
                self.instance_closed_signal.emit(self.instance_name)
                self.close() # 出错了也关闭面板
            except Exception as e:
                logger.exception(f'关闭实例时发生未知错误: {e}')
                QMessageBox.critical(self, '错误', f'关闭进程时发生未知错误: {e}')
                self.instance_closed_signal.emit(self.instance_name)
                self.close()

    # 重写 closeEvent，确保在关闭窗口时停止定时器和线程
    def closeEvent(self, event):
        try:
            # 先停止所有定时器
            if hasattr(self, 'resource_timer') and self.resource_timer.isActive():
                self.resource_timer.stop()
            if hasattr(self, 'log_timer') and self.log_timer.isActive():
                self.log_timer.stop()
            # 停止日志缓冲区定时器
            if hasattr(self, '_log_buffer_timer') and self._log_buffer_timer.isActive():
                self._log_buffer_timer.stop()
            
            # 只有非调试模式才有日志读取线程
            if not self.debug_mode and hasattr(self, 'log_reader_thread'):
                if self.log_reader_thread.isRunning():
                    logger.debug(f'正在停止日志读取线程: {self.log_path}')
                    # 使用QTimer延迟停止线程，避免阻塞UI
                    self.log_reader_thread.stop()
                    # 不等待线程结束，避免阻塞UI
            
            # 清空日志缓冲区
            if hasattr(self, '_log_buffer'):
                self._log_buffer = ""
            
            logger.debug(f'监控面板已关闭: {self.instance_name}')
        except Exception as e:
            logger.error(f'关闭监控面板时发生错误: {e}')
        
        # 调用父类方法完成关闭
        super().closeEvent(event)

    # update_log 在调试模式下模拟日志更新，非调试模式下由LogReaderThread处理
    def update_log(self):
        try:
            if self.debug_mode:
                # 调试模式下可以模拟一些日志更新
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                # 使用随机值模拟不同类型的日志
                log_types = ["INFO", "DEBUG", "WARN"]
                log_type = random.choice(log_types)
                cpu_val = getattr(self.cpu_usage, 'current_value', 0)
                mem_val = getattr(self.mem_usage, 'current_value', 0)
                
                # 随机生成一些模拟日志内容
                log_contents = [
                    f"模拟日志条目 CPU: {cpu_val}%, Mem: {mem_val}MB",
                    "处理客户端请求...",
                    "加载资源完成",
                    "等待连接..."
                ]
                log_content = random.choice(log_contents)
                
                # 格式化日志行
                log_line = f"[{current_time}] [{log_type}] {log_content}\n"
                
                # 使用QTimer延迟执行UI更新，避免阻塞
                QTimer.singleShot(0, lambda: self.append_log(log_line))
                
                # 限制日志行数，防止过多卡顿
                # 使用QTimer延迟执行，避免阻塞UI
                if self.log_text.document().lineCount() > 100:
                    QTimer.singleShot(0, self.trim_log_text)
                return
            
            # 非调试模式下，日志更新由LogReaderThread处理
            # 这个方法仅作为定时器回调存在，实际上不需要做任何事情
            pass
        except Exception as e:
            logger.error(f"更新日志时发生错误: {e}")
    
    # 添加一个方法来裁剪日志文本，保持在合理的行数范围内
    def trim_log_text(self):
        try:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 
                               self.log_text.document().lineCount() - 100)
            cursor.removeSelectedText()
            # 不需要移动光标到末尾，保持用户当前的滚动位置
        except Exception as e:
            logger.error(f"裁剪日志文本时发生错误: {e}") # 非调试模式的日志更新由 LogReaderThread 负责


class LogReaderThread(QThread):
    log_data_ready = pyqtSignal(str)
    log_error = pyqtSignal(str)
    
    def __init__(self, log_path):
        super().__init__()
        self.log_path = log_path
        self.last_log_size = 0
        self.running = True
        self.mutex = threading.Lock()  # 添加互斥锁保护共享数据
        
    def run(self):
        logger.info(f"启动日志读取线程: {self.log_path}")
        while self.running:
            try:
                # 检查文件是否存在
                if not os.path.exists(self.log_path):
                    # 日志文件不存在是正常情况(例如实例刚启动还没生成日志)，不需要报错
                    time.sleep(1)  # 等待一下再检查
                    continue
                
                # 获取文件大小
                try:
                    current_size = os.path.getsize(self.log_path)
                except (FileNotFoundError, PermissionError) as e:
                    # 文件可能在检查存在性和获取大小之间被删除或无权限访问
                    logger.warning(f"获取日志文件大小失败: {e}")
                    time.sleep(1)
                    continue
                except Exception as e:
                    # 其他错误
                    logger.error(f"获取日志文件大小时发生未知错误: {e}")
                    self.log_error.emit(f'检查日志文件大小时发生错误: {str(e)}')
                    time.sleep(1)
                    continue
                
                # 使用互斥锁保护共享数据访问
                with self.mutex:
                    last_size = self.last_log_size
                
                # 文件没有变化，跳过本次读取
                if current_size == last_size:
                    time.sleep(0.2)  # 短暂休眠，降低CPU使用率
                    continue
                
                # 文件变大了，读取新增内容
                try:
                    new_content = ""
                    with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_size)  # 定位到上次读取的位置
                        new_content = f.read(min(current_size - last_size, 1024*1024))  # 限制单次读取大小，防止内存溢出
                    
                    # 更新最后读取位置
                    if new_content:
                        with self.mutex:
                            self.last_log_size = last_size + len(new_content.encode('utf-8', errors='replace'))
                        self.log_data_ready.emit(new_content)
                except UnicodeDecodeError as ude:
                    logger.warning(f'日志文件编码错误: {ude}')
                    self.log_error.emit(f'日志文件编码错误，请检查文件编码')
                    time.sleep(1)  # 减少错误频率
                except (PermissionError, IOError) as e:
                    logger.warning(f'无法访问日志文件: {e}')
                    self.log_error.emit(f'无法访问日志文件: {str(e)}')
                    time.sleep(1)
                except Exception as e:
                    logger.error(f'读取日志文件时发生未知错误: {e}')
                    self.log_error.emit(f'读取日志文件时发生错误: {str(e)}')
                    time.sleep(1)
            
            except Exception as e:
                # 捕获所有未处理的异常
                logger.exception(f"日志读取线程发生严重错误: {e}")
                self.log_error.emit(f'日志读取线程发生严重错误: {str(e)}')
                time.sleep(2)  # 发生严重错误时，暂停一段时间再继续
            
            # 每次循环后短暂休眠
            time.sleep(0.1)
        
        logger.info(f"日志读取线程停止: {self.log_path}")
    
    def stop(self):
        logger.debug(f"请求停止日志读取线程: {self.log_path}")
        self.running = False
        # 等待线程结束，但设置超时防止阻塞
        self.wait(1000)  # 等待最多1秒


# MonitorTab 类保持不变，因为它只负责启动 MonitorPanel 
class MonitorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.instance_list = QListWidget()
        self.db_status = QLabel("数据库状态:未连接")
        self.instance_status = QLabel("运行实例数:0")
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
        # 使用相对路径获取根目录
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.refresh_btn.clicked.connect(self.on_manual_refresh)

    def open_monitor_panel(self):
        try:
            # 检查是否选择了实例
            if not self.instance_list.currentItem():
                QMessageBox.warning(self, '警告', '请先选择一个运行实例')
                return
            
            instance_name = self.instance_list.currentItem().text()
            logger.debug(f'尝试打开实例监控面板: {instance_name}')
            
            # 从 running_instances 中查找选定实例的信息
            selected_instance_info = None
            for pid, path in self.running_instances:
                if os.path.basename(path) == instance_name:
                    selected_instance_info = (pid, path)
                    break
            
            if not selected_instance_info:
                logger.warning(f'找不到实例信息: {instance_name}')
                QMessageBox.warning(self, '错误', '选择的实例信息丢失或已停止运行，请刷新列表')
                return

            pid, instance_path = selected_instance_info
            log_file_path = os.path.join(instance_path, "logs", "latest.log")
            
            # 使用非阻塞方式检查进程是否存在
            if not pid or not psutil.pid_exists(pid):
                logger.warning(f'进程不存在: PID={pid}')
                QMessageBox.warning(self, '错误', '选择的实例未运行或进程已消失')
                # 使用QTimer延迟执行刷新，避免阻塞UI
                QTimer.singleShot(0, self.scan_running_instances)
                return
            
            # 获取 MainWindow 实例
            main_window = self.window()
            
            # 检查 main_window 是否有 running_processes 属性
            if not hasattr(main_window, 'running_processes'):
                logger.error("无法获取 MainWindow 实例或其不包含 running_processes 字典")
                QMessageBox.critical(self, '错误', '内部错误:无法访问主窗口的进程列表，无法打开监控面板。')
                return

            # 获取进程对象
            process_obj = main_window.running_processes.get(pid)
            if not process_obj:
                logger.warning(f"无法找到 PID {pid} 对应的 QProcess 对象，监控面板将以只读模式打开")
                QMessageBox.warning(self, '警告', f'无法找到与实例关联的进程对象。\n监控面板将以只读模式打开，无法发送命令。')
            
            # 使用QTimer延迟创建监控面板，避免在当前函数中进行耗时操作
            def create_monitor_panel():
                try:
                    # 再次检查进程是否存在，因为可能在延迟期间进程已经结束
                    if not psutil.pid_exists(pid):
                        logger.warning(f'延迟创建监控面板时发现进程已不存在: PID={pid}')
                        QMessageBox.warning(self, '错误', '选择的实例未运行或进程已消失')
                        QTimer.singleShot(0, self.scan_running_instances)
                        return
                    
                    # 检查进程类型
                    try:
                        proc_psutil = psutil.Process(pid)
                        if not proc_psutil.name().lower().startswith("java"):
                            logger.warning(f'进程类型异常 PID:{pid} 名称:{proc_psutil.name()} 期望:java*')
                            QMessageBox.warning(self, '错误', '选择的实例似乎不是Java进程')
                            QTimer.singleShot(0, self.scan_running_instances)
                            return
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.error(f"访问进程 {pid} 信息失败: {e}")
                        QMessageBox.critical(self, '错误', f'无法访问进程信息: {e}')
                        QTimer.singleShot(0, self.scan_running_instances)
                        return
                    
                    # 创建并显示监控面板
                    self.monitor_panel = MonitorPanel(instance_name, pid, log_file_path, process=process_obj)
                    self.monitor_panel.show()
                    logger.info(f'成功打开监控面板: {instance_name} (PID: {pid})')
                except Exception as e:
                    logger.error(f"创建监控面板时发生错误: {e}")
                    QMessageBox.critical(self, '错误', f'打开监控面板失败: {e}')
            
            # 使用短延迟启动监控面板创建，避免阻塞UI
            QTimer.singleShot(50, create_monitor_panel)
            
        except Exception as e:
            logger.exception(f"打开监控面板过程中发生未捕获的错误: {e}")
            QMessageBox.critical(self, '错误', f'打开监控面板时发生未知错误: {e}')

    def update_resource_usage(self):
        try:
            db_status = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                if proc.info['name'] == "mongod.exe" and any('dbpath' in part for part in proc.info['cmdline']):
                    db_status = True
            if db_status:
                self.db_status.setText("数据库状态:已连接")
            else:
                self.db_status.setText("数据库状态:未连接")
        except Exception as e:
            logger.error(f"更新资源使用情况时发生错误: {e}")

    def scan_running_instances(self):
        new_running_instances = []
        servers_path = os.path.join(self.root_dir, 'Servers')
        if not os.path.exists(servers_path):
            # 目录不存在就不扫描了
            logger.warning(f'服务器目录 {servers_path} 不存在，无法扫描实例')
            self.running_instances = []
            self.update_instance_display()
            return

        for instance_name in os.listdir(servers_path):
            instance_path = os.path.join(servers_path, instance_name)
            if os.path.isdir(instance_path):
                lock_path = os.path.join(instance_path, "Running.lock")
                if os.path.exists(lock_path):
                    try:
                        with open(lock_path, 'r', encoding='utf-8') as f:
                            lock_data = json.load(f)
                        pid = lock_data.get("pid")
                        if not pid:
                            logger.warning(f'Lock 文件 {lock_path} 中缺少 PID')
                            continue
                        # 检查 PID 是否有效且进程名是否正确
                        if psutil.pid_exists(pid):
                            try:
                                proc = psutil.Process(pid)
                                # 检查进程名是否是 java.exe (Windows) 或 java (Linux/macOS) 
                                if proc.name().lower().startswith("java"):
                                    new_running_instances.append((pid, instance_path))
                                else:
                                    logger.warning(f'PID {pid} 进程名称不符: {proc.name()} (来自 {instance_name})，清理 lock 文件')
                                    os.remove(lock_path) # 清理无效的 lock 文件
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                logger.warning(f'无法访问 PID {pid} (来自 {instance_name})，可能已退出，清理 lock 文件')
                                os.remove(lock_path) # 清理无效的 lock 文件
                        else:
                            logger.warning(f'PID {pid} (来自 {instance_name}) 不存在，清理 lock 文件')
                            os.remove(lock_path) # 清理无效的 lock 文件
                    except json.JSONDecodeError:
                        logger.error(f"Lock 文件 {lock_path} 内容不合法，已忽略")
                        # 可以考虑删除或重命名损坏的 lock 文件
                    except Exception as e:
                        logger.error(f"处理实例 {instance_name} 时发生错误: {e}")
        
        # 比较新旧列表，只在有变化时更新显示
        if set(new_running_instances) != set(self.running_instances):
            logger.info(f"运行实例列表已更新，当前数量: {len(new_running_instances)}")
            self.running_instances = new_running_instances
            self.update_instance_display()
        current_item = self.instance_list.currentItem()
        current_selected = current_item.text() if current_item else None
        
        self.instance_list.clear()
        instance_names = sorted([os.path.basename(path) for pid, path in self.running_instances])
        self.instance_list.addItems(instance_names)
        self.instance_status.setText(f"运行实例数:{len(self.running_instances)}")
        
        # 尝试恢复之前的选中项
        if current_selected:
            items = self.instance_list.findItems(current_selected, Qt.MatchExactly)
            if items:
                self.instance_list.setCurrentItem(items[0])

    def update_instance_display(self):
        """更新实例列表显示"""
        current_item = self.instance_list.currentItem()
        current_selected = current_item.text() if current_item else None
        
        self.instance_list.clear()
        instance_names = sorted([os.path.basename(path) for pid, path in self.running_instances])
        self.instance_list.addItems(instance_names)
        self.instance_status.setText(f"运行实例数:{len(self.running_instances)}")
        
        # 尝试恢复之前的选中项
        if current_selected:
            items = self.instance_list.findItems(current_selected, Qt.MatchExactly)
            if items:
                self.instance_list.setCurrentItem(items[0])
                
    def on_manual_refresh(self):
        logger.info("手动刷新实例列表")
        self.scan_running_instances() # 手动刷新直接调用扫描函数