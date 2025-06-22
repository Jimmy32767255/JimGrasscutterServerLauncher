#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自定义窗口标题栏
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from loguru import logger

class CustomTitleBar(QWidget):
    """
    自定义标题栏部件
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        """
        初始化UI界面
        """
        self.setFixedHeight(30)  # 设置标题栏高度
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")  # 设置半透明背景颜色

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0) # 左，上，右，下
        layout.setSpacing(0)

        # 窗口图标
        icon_label = QLabel(self)
        icon_pixmap = QIcon("Assets/JGSL-Logo.ico").pixmap(QSize(16, 16))
        icon_label.setPixmap(icon_pixmap)
        layout.addWidget(icon_label)
        layout.addSpacing(5)

        # 窗口标题
        self.title_label = QLabel("JimGrasscutterServerLauncher", self)
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 10pt; font-weight: bold;")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # 最小化按钮
        self.minimize_button = QPushButton("-", self)
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.01);
            }
        """)
        self.minimize_button.clicked.connect(self.minimize_window)
        layout.addWidget(self.minimize_button)

        # 最大化/还原按钮
        self.maximize_button = QPushButton("□", self)
        self.maximize_button.setFixedSize(30, 30)
        self.maximize_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.01);
            }
        """)
        self.maximize_button.clicked.connect(self.maximize_restore_window)
        layout.addWidget(self.maximize_button)

        # 关闭按钮
        self.close_button = QPushButton("×", self)
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.01);
                color: white;
            }
        """)
        self.close_button.clicked.connect(self.close_window)
        layout.addWidget(self.close_button)

    def set_title(self, title):
        """
        设置窗口标题
        """
        self.title_label.setText(title)

    def minimize_window(self):
        """
        最小化窗口
        """
        if self.parent_window:
            self.parent_window.showMinimized()

    def maximize_restore_window(self):
        """
        最大化或还原窗口
        """
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.maximize_button.setText("□") # 还原状态图标
            else:
                self.parent_window.showMaximized()
                self.maximize_button.setText("▣") # 最大化状态图标 (可以用两个方块表示)

    def close_window(self):
        """
        关闭窗口
        """
        if self.parent_window:
            self.parent_window.close()

    def mousePressEvent(self, event):
        """
        鼠标按下事件，用于实现窗口拖动
        """
        # 只在标题栏区域响应拖动
        title_bar_rect = self.rect()
        if event.button() == Qt.LeftButton and self.parent_window and title_bar_rect.contains(event.pos()):
            self.parent_window.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        """
        鼠标移动事件，用于实现窗口拖动
        """
        if hasattr(self.parent_window, 'old_pos') and self.parent_window.old_pos and self.parent_window:
            delta = event.globalPos() - self.parent_window.old_pos
            self.parent_window.move(self.parent_window.x() + delta.x(), self.parent_window.y() + delta.y())
            self.parent_window.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        """
        鼠标释放事件，用于实现窗口拖动
        """
        if event.button() == Qt.LeftButton and self.parent_window:
            self.parent_window.old_pos = None