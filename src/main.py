"""
市场行情浮动窗口应用 - 主入口
显示实时黄金、白银和加密货币价格
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from .core.config import AppConfig
from .ui.window import GoldWindow
from .ui.tray import TrayManager


def main():
    """应用主函数"""
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 即使窗口关闭也不退出进程
    
    # 设置应用图标
    icon_path = AppConfig.get_icon_path()
    icon = QIcon(icon_path)
    app.setWindowIcon(icon)
    
    # 创建主窗口
    window = GoldWindow()
    window.show()
    
    # 创建系统托盘
    tray_manager = TrayManager(icon_path, window)
    tray_manager.show()
    
    # 启动应用循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
