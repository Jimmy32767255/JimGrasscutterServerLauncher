# 开发者须知：
## 如何制作主题？
在[主题文件夹](Translations)中创建一个新文件夹，文件夹名即为主题名。
主题文件夹中必须包含一个`theme.json`文件，用于描述主题的信息。
`theme.json`文件的内容如下：
```json
{
    "name": "主题名",
    "font_color": "HEX颜色代码",
    "background_color": "同上",
    "background_image": 布尔值，是否启用背景图片，如果为真，您还必须添加`background.png`或`background.jpg`,
    "enable_blur": 布尔值，是否启用模糊效果，如果为真，这将会覆盖`background_image`
}
```
JimGrasscutterServerLauncher也提供了一些自带主题供您参考。
另请参阅：[目录说明](DirInfo.md)
## 如何更新/制作翻译？
- 确保需要翻译的字符串已用self.tr()包裹。
- 确保代码文件在[pro](Translations/JimGrasscutterServerLauncher.pro)的SOURCES =列表中。
- 确保目标语言在[pro](Translations/JimGrasscutterServerLauncher.pro)的TRANSLATIONS =列表中。
- 确保已安装lupdate和lrelease工具。
- 在项目根目录运行"lupdate .\Translations\JimGrasscutterServerLauncher.pro"命令，这将自动更新.tr翻译文件。
- 手动翻译生成的.tr翻译文件。
- 在项目根目录运行"lrelease .\JimGrasscutterServerLauncher\Translations\JimGrasscutterServerLauncher_语言_地区.ts"命令，这将自动生成.qm文件。
- 测试并提交你的修改。