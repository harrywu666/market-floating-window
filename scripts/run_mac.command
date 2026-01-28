#!/bin/bash
# 切换到项目根目录（scripts的父目录）
cd "$(dirname "$0")/.."
# 使用模块方式运行程序
python3 -m src.main
