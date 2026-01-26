#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "        行情悬浮窗 - 强制卸载工具        "
echo "========================================"

# 1. 强制杀掉所有相关进程
echo "[1/3] 正在检测并终止残留进程..."
pkill -9 "行情悬浮窗"
pkill -9 "main"
# 有时候打包的应用进程名可能是这些

# 2. 尝试卸载已安装的应用
echo "[2/3] 正在清理残留文件..."
TARGET_APP="/Applications/行情悬浮窗.app"

if [ -d "$TARGET_APP" ]; then
    echo "发现已安装版本: $TARGET_APP"
    rm -rf "$TARGET_APP"
    echo "✅ 已删除 /Applications 下的旧版本"
else
    echo "未在 /Applications 下发现旧版本"
fi

# 3. 清理当前目录的 dist（如果存在）
if [ -d "dist/行情悬浮窗.app" ]; then
    echo "清理构建目录中的临时版本..."
    rm -rf "dist"
fi

echo "========================================"
echo "✅ 清理完成！您现在可以重新打包或安装了。"
echo "========================================"
read -p "按回车键退出..."
