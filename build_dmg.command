#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "    正在构建 Mac 应用程序 (安全模式)    "
echo "========================================"

# 安全模式：将项目拷贝到临时目录进行打包
# 这样可以避开路径中的中文、空格、特殊符号(@)导致的 PyInstaller 错误
TEMP_BUILD_DIR="/tmp/market_window_build_$(date +%s)"
CURRENT_DIR=$(pwd)

echo "[1/5] 创建纯英文路径的构建环境..."
mkdir -p "$TEMP_BUILD_DIR"
cp -r . "$TEMP_BUILD_DIR"
cd "$TEMP_BUILD_DIR"

echo "[2/5] 安装/更新打包依赖..."
# 确保安装 wheel 包，有时候缺少它会导致依赖分析出错
python3 -m pip install --upgrade pip wheel pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "[3/5] 开始编译 (在临时目录中)..."
# 使用 clean 清理缓存
python3 -m PyInstaller --noconfirm --onedir --windowed \
    --collect-all PySide6 \
    --icon "ui/app_icon.png" \
    --add-data "ui:ui" \
    --name "行情悬浮窗" \
    --clean \
    main.py

if [ ! -d "dist/行情悬浮窗.app" ]; then
    echo "❌ 打包失败！请检查上方报错信息。"
    # 清理残局
    rm -rf "$TEMP_BUILD_DIR"
    exit 1
fi

echo "[4/5] 进行应用签名 (Self-Sign)..."
codesign --force --deep --sign - "dist/行情悬浮窗.app"

echo "[5/5] 制作 DMG 并移回原目录..."
# 删除原目录下可能存在的旧 dmg
rm -f "$CURRENT_DIR/行情悬浮窗.dmg"

# 制作 DMG
hdiutil create -volname "行情悬浮窗" -srcfolder "dist/行情悬浮窗.app" -ov -format UDZO "market_window.dmg"

# 将结果移回用户的桌面文件夹
mv "market_window.dmg" "$CURRENT_DIR/行情悬浮窗.dmg"

# 清理临时目录
cd "$CURRENT_DIR"
rm -rf "$TEMP_BUILD_DIR"

echo "========================================"
echo "✅ 恭喜！打包成功！"
echo "DMG 文件已生成在当前目录下: 行情悬浮窗.dmg"
echo "========================================"
open .
read -p "按回车键退出..."
