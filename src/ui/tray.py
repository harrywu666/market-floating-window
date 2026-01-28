"""
系统托盘管理模块
管理系统托盘图标和托盘菜单
"""
import os
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QApplication


class TrayManager:
    """系统托盘管理器"""
    
    def __init__(self, icon_path, window):
        """
        初始化托盘管理器
        
        Args:
            icon_path: 图标文件路径
            window: 主窗口实例，用于控制窗口显示/隐藏
        """
        self.window = window
        self.icon_path = icon_path
        
        # 创建托盘图标
        self.tray = QSystemTrayIcon()
        icon = QIcon(icon_path)
        self.tray.setIcon(icon)
        
        # 创建托盘菜单
        self._create_menu()
        
        # 设置托盘菜单
        self.tray.setContextMenu(self.menu)
        
    def _create_menu(self):
        """创建托盘右键菜单"""
        self.menu = QMenu()
        
        # 显示/隐藏窗口
        show_action = QAction("显示/隐藏", self.menu)
        show_action.triggered.connect(self._toggle_window_visibility)
        
        # 立即刷新数据
        refresh_action = QAction("立即刷新", self.menu)
        refresh_action.triggered.connect(self.window.update_data)
        
        # 退出应用
        exit_action = QAction("退出", self.menu)
        exit_action.triggered.connect(QApplication.instance().quit)
        
        # 添加到菜单
        self.menu.addAction(show_action)
        self.menu.addAction(refresh_action)
        self.menu.addSeparator()
        self.menu.addAction(exit_action)
    
    def _toggle_window_visibility(self):
        """切换窗口显示/隐藏状态"""
        self.window.setVisible(not self.window.isVisible())
    
    def show(self):
        """显示托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("系统托盘在此系统上不可用")
            return
        self.tray.show()
    
    def hide(self):
        """隐藏托盘图标"""
        self.tray.hide()
