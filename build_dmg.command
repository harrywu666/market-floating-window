#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "    正在构建 Mac 应用程序 (DMG 打包)    "
echo "========================================"

# 1. 安装打工具 PyInstaller
echo "[1/4] 安装/更新打包工具..."
pip3 install --upgrade pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 清理旧的构建文件
echo "[2/4] 清理旧文件..."
rm -rf build dist *.spec

# 3. 生成 .app 应用
echo "[3/4] 正在生成 .app 应用程序..."
# --windowed: 不显示黑窗口
# --onedir: 生成文件夹形式（启动更快，便于调试）
# --add-data: 打包 ui 资源文件夹
# --icon: 设置图标
# --name: 应用名称
pyinstaller --noconfirm --onedir --windowed \
    --icon "ui/app_icon.png" \
    --add-data "ui:ui" \
    --name "行情悬浮窗" \
    --clean \
    main.py

if [ ! -d "dist/行情悬浮窗.app" ]; then
    echo "❌ 打包失败！未找到应用程序文件。"
    read -p "按回车键退出..."
    exit 1
fi

# 4. 制作 .dmg 安装包
echo "[4/4] 正在制作 DMG 安装包..."
# 如果已有旧的dmg则删除
rm -f "行情悬浮窗.dmg"

# 使用 hdiutil 创建 dmg
# -srcfolder: 指定要把哪个文件夹（.app）放进去
# -volname: 打开dmg后显示的卷标名
hdiutil create -volname "行情悬浮窗" -srcfolder "dist/行情悬浮窗.app" -ov -format UDZO "行情悬浮窗.dmg"

echo "========================================"
echo "✅ 打包完成！"
echo "您可以在当前目录下找到: 行情悬浮窗.dmg"
echo "========================================"
open .
read -p "按回车键退出..."
