#!/usr/bin/env python3
"""
创建带有标准边距的 macOS 应用图标
macOS 图标通常需要一定的边距，内容不应该撑满整个画布
"""
from PIL import Image
import os

def create_icon_with_padding(input_path, output_path, padding_percent=0.1):
    """
    为图标添加边距，使内容不撑满整个画布
    padding_percent: 边距百分比（0.1 = 10%）
    """
    img = Image.open(input_path).convert("RGBA")
    
    # 创建新图像（透明背景）
    size = img.size[0]
    new_size = int(size / (1 - padding_percent * 2))
    
    # 确保是 1024x1024（macOS 图标标准尺寸）
    if new_size < 1024:
        new_size = 1024
    
    new_img = Image.new("RGBA", (new_size, new_size), (0, 0, 0, 0))
    
    # 计算居中位置
    offset = (new_size - size) // 2
    
    # 粘贴原图
    new_img.paste(img, (offset, offset), img)
    
    # 保存
    new_img.save(output_path, "PNG")
    print(f"Created icon with padding: {output_path}")
    return output_path

if __name__ == "__main__":
    input_file = "/Users/harry/@dev/market-floating-window/ui/app_icon.png"
    output_file = "/Users/harry/@dev/market-floating-window/ui/app_icon_padded.png"
    
    create_icon_with_padding(input_file, output_file, padding_percent=0.08)
