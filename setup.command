#!/bin/bash
cd "$(dirname "$0")"
echo "正在安装必要的运行库 (Installing dependencies)..."
echo "这可能需要几分钟，请耐心等待..."
echo "----------------------------------------"

# 尝试使用 pip3 安装
if command -v pip3 &> /dev/null; then
    pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
else
    echo "Error: 未找到 pip3。请确保您已安装 Python 3。"
    echo "如果您已安装 Python 3，可能需要手动运行: python3 -m pip install -r requirements.txt"
fi

echo "----------------------------------------"
echo "安装完成! 现在您可以双击 run.command 启动程序了。"
read -p "按回车键退出 (Press Enter to exit)..."
