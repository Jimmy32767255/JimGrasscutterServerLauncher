#!/bin/bash

# JimGrasscutterServerLauncher AppImage 构建脚本 (使用 appimagetool)
# 用法: ./Build.sh

set -e

echo "=========================================="
echo "JimGrasscutterServerLauncher AppImage 构建工具"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 创建构建目录
BUILD_DIR="$SCRIPT_DIR/build-appimage"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 检查依赖
echo "[检查依赖...]"

# 检查 appimagetool
if [[ ! -f "appimagetool-x86_64.AppImage" ]]; then
    echo "[下载 appimagetool...]"
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x appimagetool-x86_64.AppImage
fi

# 检查 runtime
if [[ ! -f "runtime-x86_64" ]]; then
    echo "[下载 AppImage runtime...]"
    wget -q "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
fi

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python3"
    exit 1
fi

# 检查图标 PNG 是否存在，若不存在则尝试从 ICO 转换
ICON_PNG="$SCRIPT_DIR/Assets/JGSL-Logo.png"
if [[ ! -f "$ICON_PNG" ]]; then
    if command -v convert &> /dev/null; then
        echo "[从 ICO 转换图标...]"
        convert "$SCRIPT_DIR/Assets/JGSL-Logo.ico" -resize 256x256 "$ICON_PNG"
    else
        echo "[警告] 未检测到 ImageMagick convert，无法生成 PNG 图标，请手动准备 Assets/JGSL-Logo.png"
    fi
fi

echo "[依赖检查完成]"

# 创建 AppDir 结构
echo "[创建 AppDir 结构...]"
APPDIR="$BUILD_DIR/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/share/jimgrasscutterserverlauncher"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/pixmaps"
mkdir -p "$APPDIR/usr/lib"

# 复制程序文件
echo "[复制程序文件...]"
cp -r "$SCRIPT_DIR/Src" "$APPDIR/usr/share/jimgrasscutterserverlauncher/"
cp -r "$SCRIPT_DIR/Assets" "$APPDIR/usr/share/jimgrasscutterserverlauncher/"
cp -r "$SCRIPT_DIR/Themes" "$APPDIR/usr/share/jimgrasscutterserverlauncher/"
cp -r "$SCRIPT_DIR/Translations" "$APPDIR/usr/share/jimgrasscutterserverlauncher/"

# 安装 Python 依赖到 AppDir
echo "[安装 Python 依赖...]"
pip3 install --prefix="$APPDIR/usr" --ignore-installed -r "$SCRIPT_DIR/requirements.txt"

# 复制图标
if [[ -f "$ICON_PNG" ]]; then
    cp "$ICON_PNG" "$APPDIR/usr/share/icons/hicolor/256x256/apps/jimgrasscutterserverlauncher.png"
    cp "$ICON_PNG" "$APPDIR/usr/share/pixmaps/jimgrasscutterserverlauncher.png"
fi

# 创建桌面文件
cat > "$APPDIR/usr/share/applications/jimgrasscutterserverlauncher.desktop" << 'EOF'
[Desktop Entry]
Name=JimGrasscutterServerLauncher
Comment=Grasscutter 服务端管理器
Exec=jimgrasscutterserverlauncher
Icon=jimgrasscutterserverlauncher
Terminal=false
Type=Application
Categories=Utility
StartupNotify=true
EOF

# 创建启动脚本
cat > "$APPDIR/usr/bin/jimgrasscutterserverlauncher" << 'EOF'
#!/bin/bash
# JimGrasscutterServerLauncher 启动脚本

HERE="$(dirname "$(readlink -f "${0}")")"
APPDIR="$(dirname "$(dirname "$HERE")")"

# AppImage 内程序目录为只读，将用户数据目录指向 HOME 下的可写位置
export JGSL_APPDATA_DIR="${HOME}/.config/JimGrasscutterServerLauncher"
mkdir -p "$JGSL_APPDATA_DIR"

# 查找 Python site-packages 目录
PYTHON_VERSION=$(python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')
export PYTHONPATH="$APPDIR/usr/share/jimgrasscutterserverlauncher:$APPDIR/usr/lib/$PYTHON_VERSION/site-packages:$PYTHONPATH"

exec python3 "$APPDIR/usr/share/jimgrasscutterserverlauncher/Src/main.py" "$@"
EOF
chmod +x "$APPDIR/usr/bin/jimgrasscutterserverlauncher"

# 创建 AppRun 脚本
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
# AppImage 入口点

# 获取 AppDir 路径
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

# AppImage 内程序目录为只读，将用户数据目录指向 HOME 下的可写位置
export JGSL_APPDATA_DIR="${HOME}/.config/JimGrasscutterServerLauncher"
mkdir -p "$JGSL_APPDATA_DIR"

# 设置环境变量
export PATH="$HERE/usr/bin:$PATH"

# 查找 Python site-packages 目录
PYTHON_VERSION=$(python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')
export PYTHONPATH="$HERE/usr/share/jimgrasscutterserverlauncher:$HERE/usr/lib/$PYTHON_VERSION/site-packages:$PYTHONPATH"

# 启动程序
exec python3 "$HERE/usr/share/jimgrasscutterserverlauncher/Src/main.py" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# 复制 .desktop 到根目录
cp "$APPDIR/usr/share/applications/jimgrasscutterserverlauncher.desktop" "$APPDIR/jimgrasscutterserverlauncher.desktop"

# 复制图标到根目录
if [[ -f "$ICON_PNG" ]]; then
    cp "$ICON_PNG" "$APPDIR/jimgrasscutterserverlauncher.png"
fi

# 使用 appimagetool 打包
echo "[使用 appimagetool 打包...]"
ARCH=x86_64 APPIMAGELAUNCHER_DISABLE=1 ./appimagetool-x86_64.AppImage "$APPDIR" --runtime-file runtime-x86_64

# 检查并提示
cd "$SCRIPT_DIR"
if [[ -f "$BUILD_DIR/JimGrasscutterServerLauncher-x86_64.AppImage" ]]; then
    mkdir -p "$SCRIPT_DIR/dist"
    mv "$BUILD_DIR/JimGrasscutterServerLauncher-x86_64.AppImage" "$SCRIPT_DIR/dist/GNU-Linux-amd64.AppImage"
    echo ""
    echo "=========================================="
    echo "构建成功!"
    echo "输出文件: $SCRIPT_DIR/dist/GNU-Linux-amd64.AppImage"
    echo "=========================================="
else
    echo "[错误] 构建失败，未找到输出文件"
    exit 1
fi
