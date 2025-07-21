# Developer Notes:
## How to create a theme?
Create a new folder in the [Themes folder](Translations), the folder name will be the theme name.
The theme folder must contain a `theme.json` file to describe the theme's information.
The content of the `theme.json` file is as follows:
```json
{
    "name": "Theme Name",
    "font_color": "HEX Color Code",
    "background_color": "Same as above",
    "background_image": "Boolean, whether to enable background image, if true, you must also add `background.png` or `background.jpg`",
    "enable_blur": "Boolean, whether to enable blur effect, if true, this will override `background_image`"
}
```
JimGrasscutterServerLauncher also provides some built-in themes for your reference.
See also: [Directory Info](DirInfo.md)
## How to update/create translations?
- Ensure that the string to be translated is wrapped with self.tr().
- Ensure that the code file is in the SOURCES = list of [pro](Translations/JimGrasscutterServerLauncher.pro).
- Ensure that the target language is in the TRANSLATIONS = list of [pro](Translations/JimGrasscutterServerLauncher.pro).
- Ensure that lupdate and lrelease tools are installed.
- Run the "lupdate .\Translations\JimGrasscutterServerLauncher.pro" command in the project root directory, which will automatically update the .tr translation file.
- Manually translate the generated .tr translation file.
- Run the "lrelease .\JimGrasscutterServerLauncher\Translations\JimGrasscutterServerLauncher_language_region.ts" command in the project root directory, which will automatically generate the .qm file.
- Test and submit your changes.