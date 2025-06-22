import requests
from loguru import logger
from PyQt5.QtCore import QThread, pyqtSignal

# GitHub 仓库信息
REPO_OWNER = "Jimmy32767255"
REPO_NAME = "JimGrasscutterServerLauncher"
GITHUB_API_URL_LATEST_RELEASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

# 当前版本号
VERSION = "V0.2.1R-FESE"

class UpdateCheckThread(QThread):
    # 定义一个信号，用来发送检查结果 (是否可用更新, 最新版本号)
    update_check_result = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("UpdateCheckThread 初始化")

    def run(self):
        logger.info("开始检查最新发行版...")
        update_available, latest_version = self.check_for_latest_release()
        logger.info(f"检查完成，是否有更新: {update_available}, 最新版本: {latest_version}")
        self.update_check_result.emit(update_available, latest_version)

    def check_for_latest_release(self):
        """ 检查 GitHub 最新发行版"""
        try:
            response = requests.get(GITHUB_API_URL_LATEST_RELEASE, timeout=10) # 设置10秒超时
            response.raise_for_status() # 如果请求失败就抛出异常
            latest_release_data = response.json()
            latest_version = latest_release_data.get('tag_name', 'N/A')
            logger.debug(f"获取到最新发行版标签: {latest_version}")
            
            # 简单的版本比较逻辑，假设版本号格式类似 v1.2.3 或 1.2.3
            current_v = VERSION.lstrip('V')
            latest_v = latest_version.lstrip('V')
            
            # 使用分割后的版本号进行比较
            current_parts = list(map(int, current_v.split('.')))
            latest_parts = list(map(int, latest_v.split('.')))
            
            # 补齐版本号长度以便比较
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            if latest_parts > current_parts:
                logger.info(f"发现新版本！当前版本: {VERSION}, 最新版本: {latest_version}")
                return True, latest_version
            else:
                logger.info(f"当前已是最新版本 ({VERSION})")
                return False, VERSION
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"GitHub仓库不存在或没有发行版: {REPO_OWNER}/{REPO_NAME}")
            else:
                logger.error(f"检查最新发行版时HTTP错误({e.response.status_code}): {e}")
            return False, VERSION
        except requests.exceptions.RequestException as e:
            logger.error(f"检查最新发行版时网络错误: {e}")
            return False, VERSION
        except Exception as e:
            logger.error(f"检查最新发行版时发生未知错误: {e}")
            return False, VERSION