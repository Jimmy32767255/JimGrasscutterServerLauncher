import os
import json
import requests
from loguru import logger
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QSizePolicy, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime

class GitHubActivityThread(QThread):
    activity_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    github_token = None

    def __init__(self, repo_owner=None, repo_name=None, is_all_repos=False, all_repos_list=None):
        super().__init__()
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.is_all_repos = is_all_repos
        self.all_repos_list = all_repos_list if all_repos_list is not None else []

    def run(self):
        try:
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if GitHubActivityThread.github_token:
                headers['Authorization'] = f'token {GitHubActivityThread.github_token}'

            all_activities = []

            if self.is_all_repos:
                for repo in self.all_repos_list:
                    owner = repo['owner']
                    name = repo['name']
                    events_url = f'https://api.github.com/repos/{owner}/{name}/events'
                    response = requests.get(events_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    events = response.json()
                    all_activities.extend(self._process_events(events, f"{owner}/{name}"))
            else:
                events_url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/events'
                response = requests.get(events_url, headers=headers, timeout=10)
                response.raise_for_status()
                events = response.json()
                all_activities.extend(self._process_events(events, f"{self.repo_owner}/{self.repo_name}"))

            self.activity_fetched.emit(all_activities)
        except requests.exceptions.RequestException as e:
            logger.error(self.tr(f"获取GitHub活动时网络错误: {e}"))
            self.error_occurred.emit(self.tr(f"获取GitHub活动时网络错误: {e}"))
        except json.JSONDecodeError:
            logger.error(self.tr("GitHub API返回了无效的JSON"))
            self.error_occurred.emit(self.tr("GitHub API返回了无效的JSON"))
        except Exception as e:
            logger.error(self.tr(f"获取GitHub活动时发生未知错误: {e}"))
            self.error_occurred.emit(self.tr(f"获取GitHub活动时发生未知错误: {e}"))

    def _process_events(self, events, repo_full_name):
        activities = []
        for event in events:
            event_type = event.get('type')
            created_at = QDateTime.fromString(event.get('created_at'), Qt.ISODate).toString("yyyy-MM-dd hh:mm:ss")
            actor = event.get('actor', {}).get('display_login', 'Unknown')

            summary = f"[{created_at}] {actor} 在 {repo_full_name} 上 "
            if event_type == 'PushEvent':
                commits = event.get('payload', {}).get('commits', [])
                if commits:
                    summary += f"推送了提交: {commits[0].get('message', '').splitlines()[0]}"
            elif event_type == 'PullRequestEvent':
                action = event.get('payload', {}).get('action')
                pr_number = event.get('payload', {}).get('number')
                pr_title = event.get('payload', {}).get('pull_request', {}).get('title', '无标题')
                summary += f"{action} 了拉取请求 #{pr_number}: {pr_title}"
            elif event_type == 'IssuesEvent':
                action = event.get('payload', {}).get('action')
                issue_number = event.get('payload', {}).get('issue', {}).get('number')
                issue_title = event.get('payload', {}).get('issue', {}).get('title', '无标题')
                summary += f"{action} 了问题 #{issue_number}: {issue_title}"
            elif event_type == 'ReleaseEvent':
                action = event.get('payload', {}).get('action')
                release_name = event.get('payload', {}).get('release', {}).get('name', '无名称')
                summary += f"{action} 了发布: {release_name}"
            elif event_type == 'CreateEvent':
                ref_type = event.get('payload', {}).get('ref_type')
                ref = event.get('payload', {}).get('ref')
                summary += f"创建了 {ref_type}: {ref}"
            elif event_type == 'ForkEvent':
                summary += f"Fork 了仓库"
            else:
                summary += f"执行了 {event_type} 事件"
            activities.append(summary)
        return activities

class ActivityTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.01);")
        self.repo_owner = "Jimmy32767255"
        self.repo_name = "JimGrasscutterServerLauncher"
        self.repo_list = []

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        repo_selection_layout = QHBoxLayout()
        self.repo_combo_box = QComboBox()
        self.repo_combo_box.currentIndexChanged.connect(self.on_repo_selected)
        repo_selection_layout.addWidget(self.repo_combo_box)
        self.select_all_checkbox = QCheckBox(self.tr("全部"))
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)
        repo_selection_layout.addWidget(self.select_all_checkbox)
        main_layout.addLayout(repo_selection_layout)
        self.info_label = QLabel(self.tr("GitHub仓库最近活动"))
        self.info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.info_label)
        self.activity_list_widget = QListWidget()
        self.activity_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.activity_list_widget)
        self.status_label = QLabel(self.tr("正在加载活动..."))
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        self.setLayout(main_layout)

    def load_repo_list(self):
        repo_list_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Config', 'repo-list.json')
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Config', 'config.json')
        try:
            if os.path.exists(repo_list_file):
                with open(repo_list_file, 'r', encoding='utf-8') as f:
                    self.repo_list = json.load(f)
                logger.info(self.tr(f"从 {repo_list_file} 加载仓库列表成功。"))
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                github_token = config_data.get('GitHubToken')
                if github_token:
                    GitHubActivityThread.github_token = github_token
            self.repo_combo_box.clear()
            if self.repo_list:
                for repo in self.repo_list:
                    self.repo_combo_box.addItem(f"{repo['owner']}/{repo['name']}")
                self.repo_combo_box.setCurrentIndex(0)
                self.repo_owner = self.repo_list[0]['owner']
                self.repo_name = self.repo_list[0]['name']
            else:
                self.repo_combo_box.addItem(self.tr("无可用仓库"))
                self.repo_combo_box.setEnabled(False)
                self.select_all_checkbox.setEnabled(False)
        except Exception as e:
            logger.warning(self.tr(f"加载仓库列表或配置时出错: {e}，使用默认值"))
            self.repo_combo_box.addItem(self.tr("加载失败"))
            self.repo_combo_box.setEnabled(False)
            self.select_all_checkbox.setEnabled(False)

    def fetch_activity(self):
        self.status_label.setText(self.tr("正在加载活动..."))
        self.activity_list_widget.clear()
        # 确保之前的线程已终止
        if hasattr(self, '_current_thread') and self._current_thread.isRunning():
            self._current_thread.quit()
            self._current_thread.wait()
        if self.select_all_checkbox.isChecked():
            self._current_thread = GitHubActivityThread(is_all_repos=True, all_repos_list=self.repo_list)
        else:
            self._current_thread = GitHubActivityThread(self.repo_owner, self.repo_name)
        self._current_thread.activity_fetched.connect(self.on_activity_fetched)
        self._current_thread.error_occurred.connect(self.on_error_occurred)
        self._current_thread.finished.connect(self._current_thread.deleteLater)
        self._current_thread.start()

    def on_repo_selected(self, index):
        if self.repo_list and not self.select_all_checkbox.isChecked():
            self.repo_owner = self.repo_list[index]['owner']
            self.repo_name = self.repo_list[index]['name']
            logger.info(self.tr(f"选择了仓库: {self.repo_owner}/{self.repo_name}"))
            self.fetch_activity()

    def on_select_all_changed(self, state):
        if state == Qt.Checked:
            self.repo_combo_box.setEnabled(False)
            logger.info(self.tr("选择了显示所有仓库活动"))
        else:
            self.repo_combo_box.setEnabled(True)
            logger.info(self.tr("取消了显示所有仓库活动"))
        self.fetch_activity()

    def on_activity_fetched(self, activities):
        if activities:
            for activity in activities:
                item = QListWidgetItem(activity)
                self.activity_list_widget.addItem(item)
            self.status_label.setText(self.tr("活动加载完成。"))
            logger.info(self.tr("GitHub活动加载完成。"))
        else:
            self.status_label.setText(self.tr("没有找到最近的GitHub活动。"))
            logger.info(self.tr("没有找到最近的GitHub活动。"))

    def on_error_occurred(self, message):
        self.status_label.setText(self.tr(f"加载活动失败: {message}"))
        logger.error(self.tr(f"加载GitHub活动失败: {message}"))

    def on_tab_selected(self):
        logger.info(self.tr("活动选项卡被选中，开始加载活动。"))
        self.load_repo_list()
        # 确保之前的线程已终止
        if hasattr(self, '_current_thread') and self._current_thread.isRunning():
            self._current_thread.quit()
            self._current_thread.wait()
        self.fetch_activity()