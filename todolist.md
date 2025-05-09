# ToDoList

## 添加

 - [X] config_editor.py:开发图形化配置编辑器

 - [X] cluster_tab.py:实现多地区服务器管理

 - [X] download_tab.py:扩展资源下载功能

 - [X] manage_tab.py:克隆实例

 - [X] update_manager.py:实现检查更新功能

 - [X] database_tab:数据库标签页

 - [X] monitor_tab.py:关闭实例时自动刷新

 - [X] monitor_tab.py:实例进程消失后自动关闭监控面板

 - [x] plugin_manager.py:插件生命周期管理

 - [X] download_tab.py:自动解压压缩包

 - [ ] download_tab.py:分卷压缩包支持(计划)

 - [ ] cluster_tab.py:启动/停止集群(一般)

 - [ ] Language\*:添加中英文翻译文件(一般 | 暂时忽略)

 - [ ] building_tab:构建标签页(可能 | 用于构建割草机，非常简单而且不太实用所以优先级低)

 - [ ] data_manager:可视化json编辑，如Banners、Shop、ActivityConfig、Announcement等等(一般)

 - [ ] resources_manager:可视化编辑TextMap中的游戏文本(一般)

 - [ ] download_tab.py&download-list.json:添加不可自动下载的资源的支持(一般)

## 修复

 - [X] monitor_tab.py:解决监控面板打开崩溃

 - [X] dispatch.py:修复在集群界面中选中其复选框时崩溃的问题(一般)

 - [X] download_tab.py:修复下载过程中提示权限不足的问题

 - [ ] monitor_tab.py:修复打开监控面板会导致服务端日志中多出几百万行的EOF的问题(紧急 | 偶发性问题且原因不明，暂时忽略)

## 修改

 - [X] monitor_tab.py:关闭实例应优先通过对服务器发送"STOP"命令来进行安全的关闭

 - [X] download_tab.py&download-list.json:在json中指定文件名、目标位置、是否可自动下载等

 - [ ] dispatch.py:地区列表应该从配置文件中读取(一般)

 - [ ] cluster_tab.py:应该遵循[多服务器配置教程](https://www.bilibili.com/video/BV1L5CXY4Eaj)，适当复用资源，减少空间浪费(一般)

## 删除

暂无
