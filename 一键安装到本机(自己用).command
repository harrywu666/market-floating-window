#!/bin/bash
cd "$(dirname "$0")"

# 目标文件定义
APP_NAME="行情悬浮窗"
APP_DIR="$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

INSTALL_DIR="/Applications"
TARGET_PATH="$INSTALL_DIR/$APP_NAME.app"

echo "========================================"
echo "    正在执行本机一键安装 (Auto Install)    "
echo "========================================"

# --- 阶段1：构建 App (内嵌逻辑) ---
echo "[1/4] 正在编译最新版本..."

# 清理现有的
rm -rf "$APP_DIR"

# 创建目录
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

# 拷贝源码
cp main.py data_fetcher.py "$RESOURCES_DIR/"
cp -r ui "$RESOURCES_DIR/"

# 创建启动器
LAUNCHER="$MACOS_DIR/launcher"
cat > "$LAUNCHER" <<EOF
#!/bin/bash
DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
# 切换到资源目录运行
cd "\$DIR/../Resources"
# 使用 exec 接管进程
exec python3 main.py
EOF
chmod +x "$LAUNCHER"

# 创建 Info.plist
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
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# 处理图标
if [ -f "ui/app_icon.png" ]; then
    cp "ui/app_icon.png" "$RESOURCES_DIR/app_icon.icns"
fi

# 签名
codesign --force --deep --sign - "$APP_DIR"
# -----------------------------------

# --- 阶段2：安装 ---
echo "[2/4] 正在安装到系统应用程序目录..."

if [ -d "$TARGET_PATH" ]; then
    echo "发现旧版本，正在覆盖..."
    rm -rf "$TARGET_PATH"
    
    # 再次检查是否删除成功 (权限检查)
    if [ -d "$TARGET_PATH" ]; then
         echo "⚠️ 需要管理员权限来覆盖旧版本，请输入密码(屏幕不会显示)："
         sudo rm -rf "$TARGET_PATH"
    fi
fi

# 移动
mv "$APP_DIR" "$INSTALL_DIR/"

# 二次检查移动结果
if [ -d "$TARGET_PATH" ]; then
    echo "✅ 安装成功！"
else
    echo "⚠️ 正在尝试使用管理员权限安装..."
    sudo mv "$APP_DIR" "$INSTALL_DIR/"
fi

# 清理残留
rm -f "$APP_NAME.dmg"

echo "========================================"
echo "🎉 恭喜！安装完成！"
echo "您现在可以在【启动台】或【应用程序】中找到它。"
echo "如果不想要了，直接去应用程序里删掉即可。"
echo "========================================"

open -R "$TARGET_PATH"
read -p "按回车键退出..."
