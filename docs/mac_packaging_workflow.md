# macOS 应用程序构建与自动部署最佳实践 (SOP)

> **核心原则**：对于 Python 开发的 Mac 应用，优先使用 **“Native Shell Wrapper (原生壳封装)”** 方案，而非 PyInstaller 的二进制冻结方案。这种方式能完美避开 M 系列芯片的签名闪退问题，且体积更小、更稳定。

## 1. 目录结构规范
构建前，确保项目根目录包含以下基础结构：
- `main.py` (入口文件)
- `ui/` (包含 index.html, css 及 `app_icon.png` 资源)
- `requirements.txt` (依赖列表)

## 2. 构建核心：build_local_app.command
创建一个脚本，不进行编译，而是生成标准的 macOS `.app` 目录结构，并内置一个调用系统 Python 的启动器。

### 脚本模板
```bash
#!/bin/bash
cd "$(dirname "$0")"

APP_NAME="您的应用名称"
APP_DIR="$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# 1. 创建目录
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

# 2. 拷贝源码 (原封不动)
cp main.py data_fetcher.py "$RESOURCES_DIR/"
cp -r ui "$RESOURCES_DIR/"

# 3. 创建启动器 (核心逻辑)
LAUNCHER="$MACOS_DIR/launcher"
cat > "$LAUNCHER" <<EOF
#!/bin/bash
DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
# 切换到资源目录运行，确保相对路径正确
cd "\$DIR/../Resources"
# 使用 exec 接管进程
exec python3 main.py
EOF
chmod +x "$LAUNCHER"

# 4. 创建 Info.plist (声明应用身份)
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
    <string>com.yourname.appname</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# 5. 图标处理 (PNG -> ICNS)
if [ -f "ui/app_icon.png" ]; then
    # 简单拷贝
    cp "ui/app_icon.png" "$RESOURCES_DIR/app_icon.icns"
fi

# 6. Ad-Hoc 签名 (修复 M 芯片闪退)
codesign --force --deep --sign - "$APP_DIR"
```

## 3. 部署核心：install.command
不要让用户手动拖拽，提供一键安装脚本。

### 脚本模板
```bash
#!/bin/bash
cd "$(dirname "$0")"
APP_NAME="您的应用名称"
SOURCE_APP="$APP_NAME.app"
INSTALL_DIR="/Applications"

# 1. 触发构建
./build_local_app.command > /dev/null 2>&1

# 2. 检测并移除旧版本
if [ -d "$INSTALL_DIR/$SOURCE_APP" ]; then
    rm -rf "$INSTALL_DIR/$SOURCE_APP" || sudo rm -rf "$INSTALL_DIR/$SOURCE_APP"
fi

# 3. 移动新版本
mv "$SOURCE_APP" "$INSTALL_DIR/" || sudo mv "$SOURCE_APP" "$INSTALL_DIR/"

# 4. 自动打开
echo "安装完成！"
open -R "$INSTALL_DIR/$SOURCE_APP"
```

## 4. 应急处理：Ghost Icon 清理
如果遇到图标删不掉的情况，严禁直接重置 Launchpad 数据库。应优先使用 **“同名覆盖法”**：
1. 在 `/Applications` 创建一个同名的空 App。
2. 再次执行删除操作。
