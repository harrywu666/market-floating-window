#!/bin/bash
cd "$(dirname "$0")"

APP_NAME="行情悬浮窗"
APP_BUNDLE="$APP_NAME.app"
DMG_NAME="${APP_NAME}_安装包"
STAGING_DIR="dist_staging"

# 定义 App 内部结构
CONTENTS_DIR="$STAGING_DIR/$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
LIB_DIR="$RESOURCES_DIR/lib"

echo "========================================"
echo "   正在构建标准安装版 (Full Installer)   "
echo "========================================"

# 1. 环境清理
rm -rf "$STAGING_DIR" "$DMG_NAME.dmg"
mkdir -p "$MACOS_DIR"
mkdir -p "$LIB_DIR"

# 2. 拷贝核心文件 (完整的应用内容)
echo "[1/6] 组装应用文件..."
cp main.py data_fetcher.py "$RESOURCES_DIR/"
cp -r ui "$RESOURCES_DIR/"

# 3. 下载全量依赖 (确保只要有基础Python就能跑)
echo "[2/6] 内置运行库 (下载中)..."
# 使用 pip 下载依赖到 App 内部，使其独立于系统库
python3 -m pip install -r requirements.txt --target "$LIB_DIR" -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade --no-user > /dev/null 2>&1

# 清理缓存减重
find "$LIB_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find "$LIB_DIR" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null

# 4. 创建智能启动器
echo "[3/6] 配置启动引擎..."
LAUNCHER="$MACOS_DIR/launcher"
cat > "$LAUNCHER" <<EOF
#!/bin/bash
DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
RES_DIR="\$DIR/../Resources"
LIB_DIR="\$RES_DIR/lib"

# 优先使用内置库
export PYTHONPATH="\$LIB_DIR:\$PYTHONPATH"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    # 尝试寻找系统默认 python3 (Xcode Tools)
    if [ -f "/usr/bin/python3" ]; then
        PY_CMD="/usr/bin/python3"
    else
        osascript -e 'display alert "环境缺失" message "此程序需依赖 Python3。MacOS 通常自带，或者请安装 Xcode Command Line Tools。"'
        exit 1
    fi
else
    PY_CMD="python3"
fi

cd "\$RES_DIR"
exec "\$PY_CMD" main.py
EOF
chmod +x "$LAUNCHER"

# 5. 配置 Info.plist
cat > "$CONTENTS_DIR/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>app_icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.harry.marketwidget</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# 图标
if [ -f "ui/app_icon.png" ]; then
    cp "ui/app_icon.png" "$RESOURCES_DIR/app_icon.icns"
fi

# 签名
echo "[4/6] 应用数字签名..."
codesign --force --deep --sign - "$STAGING_DIR/$APP_BUNDLE"

# 6. 制作标准安装盘 (关键步骤)
echo "[5/6] 制作安装盘布局..."
# 在 DMG 根目录下创建一个指向 /Applications 的快捷方式
# 这样用户打开 DMG 就能看到 "App -> Applications" 的拖拽引导
ln -s /Applications "$STAGING_DIR/Applications"

echo "[6/6] 封装 DMG 文件..."
hdiutil create -volname "${APP_NAME}_安装盘" -srcfolder "$STAGING_DIR" -ov -format UDZO "${DMG_NAME}.dmg" > /dev/null

# 清理临时目录
rm -rf "$STAGING_DIR"

echo "========================================"
echo "✅ 完整安装包构建完成！"
echo "文件位置: $(pwd)/${DMG_NAME}.dmg"
echo "使用方法: 打开 DMG -> 将图标拖入 Applications 文件夹 (标准 Mac 流程)"
echo "========================================"
open .
read -p "按回车键退出..."
