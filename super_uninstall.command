#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "      行情悬浮窗 - 超强力卸载工具       "
echo "========================================"

echo "[1/4] 强制终止所有相关进程..."
# 尝试杀掉各种可能的名字
pkill -9 "行情悬浮窗"
pkill -9 "market_window"
pkill -9 "main"
pkill -f "行情悬浮窗"

echo "[2/4] 搜寻并粉碎所有旧版应用..."
# 1. 删除 /Applications 下的
if [ -d "/Applications/行情悬浮窗.app" ]; then
    echo "删除系统应用目录下的版本..."
    rm -rf "/Applications/行情悬浮窗.app"
fi

# 2. 删除用户目录下的 Applications
if [ -d "$HOME/Applications/行情悬浮窗.app" ]; then
    echo "删除用户应用目录下的版本..."
    rm -rf "$HOME/Applications/行情悬浮窗.app"
fi

# 3. 删除桌面上可能的残留
if [ -d "$HOME/Desktop/行情悬浮窗.app" ]; then
    echo "删除桌面上的残留..."
    rm -rf "$HOME/Desktop/行情悬浮窗.app"
fi

echo "[3/4] 刷新图标缓存 (解决删了图还在的问题)..."
# 强制刷新 Launchpad (启动台) 数据库
defaults write com.apple.dock ResetLaunchPad -bool true
killall Dock

echo "[4/4] 清理构建垃圾..."
rm -rf dist build
rm -rf *.spec

echo "========================================"
echo "✅ 清理完毕！"
echo "Launchpad (启动台) 正在重建图标索引..."
echo "屏幕可能会闪烁一下，这是正常的。"
echo "那个删不掉的图标现在应该彻底消失了。"
echo "========================================"
