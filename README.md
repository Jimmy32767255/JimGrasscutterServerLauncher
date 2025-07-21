# Jim割草机服务器启动器

[English](README-en_US.md)

![JGSL Logo](/Assets/JGSL-Logo.ico)

[介绍视频](https://www.bilibili.com/video/BV1C2EkzoEqd)

## 功能特性

- 多实例服务器管理，独创集群功能，快速多地区，让服务器管理不再困难。(正在完善)
  
- 图形化配置文件编辑器，方便、快捷、简单、易懂，再也不用手动编辑json。
  
- 丰富的资源下载，数据库、JDK、卡池、插件、核心，一应俱全。
  
- 完善的监控功能，UpTime、CPU、内存占用、日志，一目了然，还能发送控制台指令。(未来还可能加入群控和异常指令处理！)
  
- 方便快捷的数据库管理，支持导入导出，可一键清空，还支持图形化编辑，实现指令无法做到的事情(如改名、改UID)
  
- 多语言国际化支持(目前支持：中文、英文)
  
- 自动更新检查机制

## 文档导航

- [目录说明](DirInfo.md)
  
- [开源协议](LICENSE)
  
- [待办清单](todolist.md)
  
- [行为准则](CODE_OF_CONDUCT.md)

- [开发文档](DevDoc.md)

## 如何使用？

我们建议普通用户直接下载[Releases](https://github.com/Jimmy32767255/JimGrasscutterServerLauncher/releases)中的打包版本，无需安装依赖，解压缩后即可直接运行。

###### 但是注意：Releases中的打包版本可能不是最新的！

或者，克隆仓库后使用代码:

#### 安装依赖:

```bash
pip install -r requirements.txt
```

#### 运行JGSL:

在项目根目录执行：

```bash
.\Start.bat
```

## 构建/编译

###### 不建议，除非需要在没有python的环境中使用，spec文件目前有问题，而且会产生更大的空间占用

在项目根目录执行：

```bash
.\build.bat
```

完成后，在.\dist文件夹中找到产物

## 社交媒体

- QQ群:985349267
  
- [H.H.T.C.](https://t.me/Jimmy32767255_Community_recover)

## 已知问题

1. 打开监控面板有可能会导致服务端日志中多出几百万行的EOF的问题，该问题是Grasscutter.java的341行导致，为偶发性故障且原因不明，如果遇到请在配置文件中禁用控制台(game.enableConsole)并使用opencommand。

2. 第一次运行时可能会遇到资源占用不高但是非常卡顿的问题，原因不明，多次重启和长时间使用可能能解决此问题。

3. [FE-Core](https://github.com/Jimmy32767255/FE-Core)在Windows11 Insider Preview Canary上高斯模糊效果失效，这个是微软的问题我无法修复，正式版Windows11上没有此问题。