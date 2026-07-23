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
  
- [待办清单](TODO.md)
  
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

Windows 在项目根目录执行：

```bat
.\Start.bat
```

GNU/Linux 在项目根目录执行：

```bash
python ./Src/main.py
```

## 构建/编译

###### 不建议，除非需要在没有python的环境中使用，spec文件目前有问题，而且会产生更大的空间占用

### Windows

在项目根目录执行：

```bat
.\build.bat
```

完成后，在 `.\dist` 文件夹中找到产物。

### GNU/Linux (AppImage)

需要先安装 `python3`、`pip`、`wget` 以及 `convert` (ImageMagick，用于图标转换)，然后在项目根目录执行：

```bash
chmod +x Build.sh
./Build.sh
```

完成后，在 `./dist/GNU-Linux-amd64.AppImage` 找到产物。

也可以使用 `appimage-builder`：

```bash
appimage-builder --recipe AppImageBuilder.yml
```

AppImage 运行时，用户数据会写入 `~/.config/JimGrasscutterServerLauncher`。

## 社交媒体

- QQ群:985349267
  
- [H.H.T.C.](https://t.me/Jimmy32767255_Community_recover)

## 已知问题

1. 打开监控面板有可能会导致服务端日志中多出几百万行的EOF的问题，该问题是Grasscutter.java的341行导致，为偶发性故障且原因不明，如果遇到请在配置文件中禁用控制台(game.enableConsole)并使用opencommand。

2. 第一次运行时可能会遇到资源占用不高但是非常卡顿的问题，原因不明，多次重启和长时间使用可能能解决此问题。