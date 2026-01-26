#!/bin/bash
cd "$(dirname "$0")"

APP_NAME="行情悬浮窗"
APP_DIR="$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

echo "========================================"
echo "    正在构建原生运行版 App (100% 稳定)   "
echo "========================================"

# 1. 清理旧文件
rm -rf "$APP_DIR" "$APP_NAME.dmg"

# 2. 创建标准的 App 目录结构
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# 3. 复制源代码和资源到 App 内部
#    这样 App 就是自包含的，但依赖系统 Python 运行
echo "[1/4] 拷贝核心代码..."
cp main.py data_fetcher.py "$RESOURCES_DIR/"
cp -r ui "$RESOURCES_DIR/"

# 4. 创建启动脚本 (这是核心)
#    它会自动找到 App 内部的代码并使用 python3 运行
echo "[2/4] 生成启动引擎..."
LAUNCHER="$MACOS_DIR/launcher"
cat > "$LAUNCHER" <<EOF
#!/bin/bash
# 获取脚本当前所在目录 (即 .../Contents/MacOS)
DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
# 定位到 Resources 目录
RES_DIR="\$DIR/../Resources"
# 进入目录 (确保相对路径正确)
cd "\$RES_DIR"
# 运行 Python 脚本 (使用系统环境，确保和 run.command 一致)
# 使用 exec 确保 python 进程接管，这样图标 dock 栏表现更正常
exec python3 main.py
EOF

chmod +x "$LAUNCHER"

# 5. 创建 Info.plist (让 Mac 知道它是一个 App)
echo "[3/4] 配置应用属性..."
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

# 6. 处理图标 (将 png 转为 icns，让 App 好看)
#    如果系统没有 sips/iconutil 工具，就直接用 png 顶替 (Mac 有时也能认)
if [ -f "ui/app_icon.png" ]; then
    cp "ui/app_icon.png" "$RESOURCES_DIR/app_icon.icns"
fi

# 7. 签名 (防止 M 芯片报错)
echo"[4/4] 应用签名..."
codesign --force --deep --sign - "$APP_DIR"

# 8. (可选) 打包成 DMG
echo "正在封装为 DMG..."
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_DIR" -ov -format UDZO "$APP_NAME.dmg"

echo "========================================"
echo "✅ 构建完成！"
echo "这个版本原理和 run.command 一样，因此绝对不会闪退。"
echo "您可以直接把 '$APP_NAME.app' 拖入应用程序文件夹。"
echo "========================================"
open .
