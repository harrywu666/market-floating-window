#!/bin/bash
cd "$(dirname "$0")"

# 定义安装路径
APP_NAME="行情悬浮窗"
SOURCE_APP="$APP_NAME.app"
INSTALL_DIR="/Applications"
TARGET_PATH="$INSTALL_DIR/$APP_NAME.app"

echo "========================================"
echo "      正在执行一键安装程序 (Auto Install)      "
echo "========================================"

# 1. 先构建最新的 App (确保是最新版)
echo "[1/3] 正在编译最新版本..."
./build_local_app.command > /dev/null 2>&1
# 这里静默运行构建脚本，利用之前的成果

if [ ! -d "$SOURCE_APP" ]; then
    echo "❌ 错误：构建失败，未找到源程序。"
    exit 1
fi

# 2. 检测并覆盖旧版本
echo "[2/3] 正在安装到系统应用程序目录..."

if [ -d "$TARGET_PATH" ]; then
    echo "发现旧版本，正在覆盖..."
    # 需要 sudo 权限才能操作 Applications 目录，如果只是用户目录不需要，但标准的是系统目录
    # 为了避免输入密码，尝试安装到用户目录下的 Applications (如果有的话)，或者提示输入密码
    
    # 尝试直接删除 (如果用户由权限)
    rm -rf "$TARGET_PATH"
    
    # 如果删除失败(权限不够)，则使用 sudo
    if [ -d "$TARGET_PATH" ]; then
         echo "⚠️ 需要管理员权限来覆盖旧版本，请输入密码："
         sudo rm -rf "$TARGET_PATH"
    fi
fi

# 3. 移动文件到 Applications
mv "$SOURCE_APP" "$INSTALL_DIR/"

# 检查移动是否成功
if [ -d "$TARGET_PATH" ]; then
    echo "✅ 安装成功！"
else
    # 可能是权限问题，尝试用 sudo 移动
    echo "⚠️ 正在尝试使用管理员权限安装..."
    sudo mv "$SOURCE_APP" "$INSTALL_DIR/"
fi

# 4. 清理残留
rm -f "$APP_NAME.dmg"

echo "========================================"
echo "🎉 恭喜！软件已成功安装！"
echo "您现在可以在【启动台 (Launchpad)】或【应用程序】文件夹中找到它。"
echo "如果不想要了，直接去应用程序里把它删了就行。"
echo "========================================"

# 5. 自动打开应用程序文件夹给用户看一眼
open -R "$TARGET_PATH"

read -p "按回车键退出..."
