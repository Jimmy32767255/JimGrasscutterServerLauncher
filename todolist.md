# ToDoList

## 添加

- [X] config_editor.py：开发图形化配置编辑器（一般 | 集成多语言支持）
- [X] region_manager.py：实现多地区服务器管理（计划 | 含版本兼容检测）
- [X] resource_downloader.py：扩展资源下载功能（一般 | 支持插件/卡池/核心）
- [ ] Language\*：添加中英文翻译文件（一般）
- [ ] update_manager.py：实现自动更新功能（一般）
- [ ] plugin_manager.py：插件生命周期管理（一般）
- [ ] download_tab.py：自动解压压缩包
- [ ] download_tab.py：分卷压缩包支持
- [ ] 启动/停止集群
- [ ] 克隆实例

## 修复

- [ ]  download_tab.py：修复下载过程中提示权限不足的问题（紧急 | 此问题需要与微软合作，暂时忽略）
- [ ]  monitor_tab.py: 修复打开监控面板会导致服务端日志中多出几百万行的EOF的问题（紧急 | Grasscutter.java的341行导致，偶发性故障且原因不明，如果遇到请在配置文件中禁用控制台并使用opencommand）
- [X]  monitor_tab.py：解决监控面板打开崩溃（紧急）

## 修改

暂无

## 删除

暂无