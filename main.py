import sys
import os
import json
import platform
from PySide6.QtCore import Qt, QTimer, QPoint, QObject, Signal, Slot, QUrl, QThread
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu, QWidgetAction, QSlider, QLabel, QHBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtGui import QIcon, QAction, QMouseEvent
from data_fetcher import GoldDataFetcher
import requests # 确保导入以支持 worker

class FetchWorker(QObject):
    """异步抓取执行者，独立于并运行在后台线程"""
    data_fetched = Signal(dict)
    
    def __init__(self, fetcher):
        super().__init__()
        self.fetcher = fetcher
        
    @Slot()
    def do_fetch(self):
        try:
            data = self.fetcher.fetch_all()
            self.data_fetched.emit(data)
        except Exception as e:
            self.data_fetched.emit({"error": str(e)})

class GoldWindow(QMainWindow):
    # 定义任务触发信号
    request_fetch = Signal()
    def __init__(self):
        super().__init__()
        self.fetcher = GoldDataFetcher()
        self.old_pos = None
        self.is_loaded = False
        
        # 窗口基本设置
        if platform.system() == 'Darwin':
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint
            )
        else:
            self.setWindowFlags(
                Qt.FramelessWindowHint |        # 无边框
                Qt.WindowStaysOnTopHint |       # 始终置顶
                Qt.Tool                         # 不在任务栏显示
            )
        self.setAttribute(Qt.WA_TranslucentBackground) # 背景透明
        
        # Web 视图设置
        self.browser = QWebEngineView(self)
        self.browser.setContextMenuPolicy(Qt.NoContextMenu) # 禁用右键菜单
        
        # 配置 WebEngine
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        
        self.setCentralWidget(self.browser)
        
        # 配置 WebEngine 渲染属性（开启穿透以便主窗口捕获拖动）
        self.browser.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.browser.page().setBackgroundColor(Qt.transparent)
        self.browser.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # 监听加载完成
        self.browser.loadFinished.connect(self.on_load_finished)
        
        # 加载 UI (Windows 路径兼容性处理)
        ui_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "index.html"))
        self.browser.setUrl(QUrl.fromLocalFile(ui_path))
        
        # 初始化异步线程
        self.worker_thread = QThread()
        self.worker = FetchWorker(self.fetcher)
        self.worker.moveToThread(self.worker_thread)
        
        # 信号连接：触发任务 -> 执行任务 -> 更新面板
        self.request_fetch.connect(self.worker.do_fetch)
        self.worker.data_fetched.connect(self.handle_data)
        
        self.worker_thread.start()

        # 定时器触发信号发射 (非阻塞调用)
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.request_fetch.emit())
        self.timer.start(1000) 
        
        # 初始尺寸 (紧凑布局优化)
        self.resize(360, 700)

    def on_load_finished(self, success):
        if success:
            self.is_loaded = True
            self.update_data()
        else:
            print("Failed to load local index.html")

    def handle_data(self, data):
        """主线程槽函数：将获取到的数据渲染至 Web 界面"""
        if not self.is_loaded:
            return
        data_json = json.dumps(data)
        self.browser.page().runJavaScript(f"if(typeof updateUI === 'function') updateUI({data_json});")

    def update_data(self):
        """兼容保留，供手动调用"""
        self.request_fetch.emit()

    def closeEvent(self, event):
        """窗口关闭时安全终止后台线程"""
        self.worker_thread.quit()
        self.worker_thread.wait()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 兼容性处理坐标获取
            try:
                self.old_pos = event.globalPosition().toPoint()
            except AttributeError:
                self.old_pos = event.globalPos()
        elif event.button() == Qt.RightButton:
            # 右键点击悬浮窗弹出退出菜单
            self.show_context_menu(event.globalPosition().toPoint())

    def show_context_menu(self, pos):
        # 创建右键菜单，使用与主界面一致的视觉风格
        menu = QMenu()
        menu.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground, True)

        # 设置与主界面UI完全一致的样式
        menu.setStyleSheet("""
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
        """)
        
        # 1. 大类切换
        toggle_menu = menu.addMenu("显示/隐藏版块")
        menu.addSeparator()

        # 2. 单独加密货币切换
        crypto_menu = menu.addMenu("加密货币筛选")
        
        for name in ["BTC", "ETH", "BNB", "SOL", "HYPE"]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked=False, s=name: self.browser.page().runJavaScript(f"toggleSection('{s}')"))
            crypto_menu.addAction(action)

        gold_action = QAction("黄金版块", self)
        gold_action.triggered.connect(lambda: self.browser.page().runJavaScript("toggleSection('gold')"))
        toggle_menu.addAction(gold_action)
        
        silver_action = QAction("白银版块", self)
        silver_action.triggered.connect(lambda: self.browser.page().runJavaScript("toggleSection('silver')"))
        toggle_menu.addAction(silver_action)
        
        crypto_all_action = QAction("加密版块", self)
        crypto_all_action.triggered.connect(lambda: self.browser.page().runJavaScript("toggleSection('crypto')"))
        toggle_menu.addAction(crypto_all_action)
        
        menu.addSeparator()
        
        refresh_action = QAction("立即刷新数据", self)
        refresh_action.triggered.connect(self.update_data)
        exit_action = QAction("完全退出程序", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        
        menu.addAction(refresh_action)
        
        # 透明度调节
        menu.addSeparator()
        
        # 创建一个自定义 Widget 作为 Action
        opacity_widget = QWidget()
        opacity_layout = QHBoxLayout(opacity_widget)
        opacity_layout.setContentsMargins(10, 5, 10, 5)
        
        opacity_label = QLabel("透明度:")
        opacity_label.setStyleSheet("color: white; font-weight: bold; font-family: 'Microsoft YaHei'; font-size: 11px;")
        
        opacity_slider = QSlider(Qt.Horizontal)
        opacity_slider.setRange(20, 100) # 20% - 100%
        # 获取当前窗口透明度并设置
        current_opacity = int(self.windowOpacity() * 100)
        opacity_slider.setValue(current_opacity if current_opacity > 0 else 100) 
        opacity_slider.setFixedWidth(120)
        
        # Slider 样式
        opacity_slider.setStyleSheet("""
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
        """)

        opacity_slider.valueChanged.connect(lambda val: self.setWindowOpacity(val / 100.0))

        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(opacity_slider)
        
        opacity_action = QWidgetAction(menu)
        opacity_action.setDefaultWidget(opacity_widget)
        menu.addAction(opacity_action)

        menu.addSeparator()
        menu.addAction(exit_action)
        
        menu.exec(pos)

    def mouseMoveEvent(self, event):
        if self.old_pos:
            try:
                curr_pos = event.globalPosition().toPoint()
            except AttributeError:
                curr_pos = event.globalPos()
                
            delta = QPoint(curr_pos - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = curr_pos

    def mouseReleaseEvent(self, event):
        self.old_pos = None

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # 即使窗口关闭也不退出进程
    
    window = GoldWindow()
    window.show()
    
    # 系统托盘
    tray = QSystemTrayIcon(app)
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "gold.png"))
    
    icon = QIcon(icon_path)
    app.setWindowIcon(icon) # 设置应用程序图标
    tray.setIcon(icon)
    
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is NOT available on this system.")
    
    menu = QMenu()
    
    show_action = QAction("显示/隐藏", menu)
    show_action.triggered.connect(lambda: window.setVisible(not window.isVisible()))
    
    refresh_action = QAction("立即刷新", menu)
    refresh_action.triggered.connect(window.update_data)
    
    exit_action = QAction("退出", menu)
    exit_action.triggered.connect(app.quit)
    
    menu.addAction(show_action)
    menu.addAction(refresh_action)
    menu.addSeparator()
    menu.addAction(exit_action)
    
    tray.setContextMenu(menu)
    tray.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
