import os
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from utils import BASE_PATH


class AboutTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 20, 20, 20)

        # 项目标题
        title = QLabel(self.tr('JimGrasscutterServerLauncher'))
        title.setFont(QFont('', 24))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 项目中文名
        title = QLabel(self.tr('Jim割草机服务器启动器'))
        title.setFont(QFont('', 24))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 项目链接
        layout.addStretch(1)
        self.add_link(layout,
                    QIcon(os.path.join(BASE_PATH, 'Assets', 'JGSL-Logo.ico')),
                    self.tr('本项目GitHub仓库'),
                    'https://github.com/Jimmy32767255/JimGrasscutterServerLauncher')

        # Grasscutter链接
        self.add_link(layout,
                    QIcon(os.path.join(BASE_PATH, 'Assets', 'Grasscutter-Logo.ico')),
                    self.tr('Grasscutter项目'),
                    'https://github.com/Grasscutters/Grasscutter')

        # 官网链接
        self.add_link(layout,
                    QIcon('Assets/Grasscutter-Logo.ico'),
                    self.tr('Grasscutter官网'),
                    'https://grasscutter.io')
        layout.addStretch(1)

        self.setLayout(layout)

    def add_link(self, layout, icon, text, url):
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)
        h_layout.setAlignment(Qt.AlignCenter)
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(32, 32))
        icon_label.setContentsMargins(0, 0, 10, 0)
        h_layout.addWidget(icon_label)

        link_label = QLabel()
        link_label.setText(f'<html><a href="{url}">{text}</a></html>')
        link_label.setOpenExternalLinks(True)
        link_label.linkActivated.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        link_label.setStyleSheet('color: #2a82da; text-decoration: underline; font-size: 24px;')
        link_label.setContentsMargins(10, 0, 0, 0)
        h_layout.addWidget(link_label)

        layout.addLayout(h_layout)