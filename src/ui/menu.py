"""
右键菜单管理模块
管理应用的右键上下文菜单，包括版块切换、透明度调节等功能
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QWidgetAction, QSlider, QLabel, QHBoxLayout, QWidget
from PySide6.QtGui import QAction


class MenuManager:
    """右键菜单管理器"""
    
    # 菜单样式（与主界面UI一致的毛玻璃风格）
    MENU_STYLE = """
        QMenu {
            background-color: rgba(20, 20, 20, 0.7);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 28px;
            padding: 16px;
        }
        QMenu::item {
            padding: 8px 20px;
            background-color: transparent;
            border-radius: 8px;
            margin: 2px 4px;
            font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", sans-serif;
            font-size: 11px;
            font-weight: 800;
            color: rgba(255, 255, 255, 0.9);
        }
        QMenu::item:selected {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 8px 12px;
        }
    """
    
    # 滑块样式
    SLIDER_STYLE = """
        QSlider::groove:horizontal {
            border: 1px solid #999999;
            height: 4px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
            margin: 2px 0;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
            border: 1px solid #5c5c5c;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
    """
    
    def __init__(self, window):
        """
        初始化菜单管理器
        
        Args:
            window: 主窗口实例，用于调用窗口方法和访问browser对象
        """
        self.window = window
    
    def create_context_menu(self, pos):
        """
        创建并显示右键上下文菜单
        
        Args:
            pos: 菜单显示位置（全局坐标）
        """
        # 创建菜单
        menu = QMenu()
        menu.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground, True)
        menu.setStyleSheet(self.MENU_STYLE)
        
        # 1. 大类切换子菜单
        toggle_menu = menu.addMenu("显示/隐藏版块")
        self._add_section_toggles(toggle_menu)
        menu.addSeparator()
        
        # 2. 加密货币筛选子菜单
        crypto_menu = menu.addMenu("加密货币筛选")
        self._add_crypto_filters(crypto_menu)
        menu.addSeparator()
        
        # 3. 立即刷新数据
        refresh_action = QAction("立即刷新数据", menu)
        refresh_action.triggered.connect(self.window.update_data)
        menu.addAction(refresh_action)
        
        # 4. 透明度调节
        menu.addSeparator()
        self._add_opacity_slider(menu)
        
        # 5. 完全退出程序
        menu.addSeparator()
        exit_action = QAction("完全退出程序", menu)
        exit_action.triggered.connect(self._exit_application)
        menu.addAction(exit_action)
        
        # 显示菜单
        menu.exec(pos)
    
    def _add_section_toggles(self, menu):
        """
        添加版块显示/隐藏切换选项
        
        Args:
            menu: 父菜单对象
        """
        # 黄金版块
        gold_action = QAction("黄金版块", menu)
        gold_action.triggered.connect(
            lambda: self.window.browser.page().runJavaScript("toggleSection('gold')")
        )
        menu.addAction(gold_action)
        
        # 白银版块
        silver_action = QAction("白银版块", menu)
        silver_action.triggered.connect(
            lambda: self.window.browser.page().runJavaScript("toggleSection('silver')")
        )
        menu.addAction(silver_action)
        
        # 加密货币版块（全部）
        crypto_all_action = QAction("加密版块", menu)
        crypto_all_action.triggered.connect(
            lambda: self.window.browser.page().runJavaScript("toggleSection('crypto')")
        )
        menu.addAction(crypto_all_action)
    
    def _add_crypto_filters(self, menu):
        """
        添加单个加密货币筛选选项
        
        Args:
            menu: 父菜单对象
        """
        crypto_names = ["BTC", "ETH", "BNB", "SOL", "HYPE"]
        
        for name in crypto_names:
            action = QAction(name, menu)
            # 使用lambda的默认参数来捕获当前值
            action.triggered.connect(
                lambda checked=False, symbol=name: 
                self.window.browser.page().runJavaScript(f"toggleSection('{symbol}')")
            )
            menu.addAction(action)
    
    def _add_opacity_slider(self, menu):
        """
        添加透明度调节滑块
        
        Args:
            menu: 父菜单对象
        """
        # 创建自定义Widget容器
        opacity_widget = QWidget()
        opacity_layout = QHBoxLayout(opacity_widget)
        opacity_layout.setContentsMargins(10, 5, 10, 5)
        
        # 标签
        opacity_label = QLabel("透明度:")
        opacity_label.setStyleSheet(
            "color: white; font-weight: bold; "
            "font-family: 'Microsoft YaHei'; font-size: 11px;"
        )
        
        # 滑块
        opacity_slider = QSlider(Qt.Horizontal)
        opacity_slider.setRange(20, 100)  # 20% - 100%
        
        # 获取当前窗口透明度并设置
        current_opacity = int(self.window.windowOpacity() * 100)
        opacity_slider.setValue(current_opacity if current_opacity > 0 else 100)
        opacity_slider.setFixedWidth(120)
        opacity_slider.setStyleSheet(self.SLIDER_STYLE)
        
        # 连接透明度变化事件
        opacity_slider.valueChanged.connect(
            lambda val: self.window.setWindowOpacity(val / 100.0)
        )
        
        # 添加到布局
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(opacity_slider)
        
        # 添加到菜单
        opacity_action = QWidgetAction(menu)
        opacity_action.setDefaultWidget(opacity_widget)
        menu.addAction(opacity_action)
    
    def _exit_application(self):
        """退出应用程序"""
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
