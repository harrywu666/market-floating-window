import sys
import os
import json
if sys.platform == 'darwin':
    os.environ["QT_MAC_WANTS_LAYER"] = "1"
from PySide6.QtCore import Qt, QTimer, QPoint, QObject, Signal, Slot, QUrl, QThread
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtGui import QIcon, QAction, QMouseEvent
from PySide6.QtWidgets import QWidgetAction, QSlider, QHBoxLayout, QWidget, QLabel
from data_fetcher import GoldDataFetcher
import requests # 确保导入以支持 worker

class OpacitySliderAction(QWidgetAction):
    """自定义带磁吸效果的透明度调节滑块"""
    def __init__(self, parent, initial_value, callback):
        super().__init__(parent)
        self.callback = callback
        
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # 滑块主体
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(20) # 最低保留 20% 以防窗口完全看不见
        self.slider.setMaximum(100)
        self.slider.setValue(int(initial_value * 100))
        self.slider.setFixedWidth(140)
        
        # 样式美化
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 6px;
                background: #222;
                margin: 2px 0;
                border_radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #26d38e;
                border: 1px solid #26d38e;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)
        
        self.label = QLabel(f"{self.slider.value()}%")
        self.label.setStyleSheet("color: #26d38e; font-weight: bold; min-width: 40px;")
        
        self.slider.valueChanged.connect(self._handle_value_changed)
        
        title_label = QLabel("不透明度")
        title_label.setStyleSheet("color: #ccc; font-size: 11px;")
        
        layout.addWidget(title_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.label)
        
        self.setDefaultWidget(container)

    def _handle_value_changed(self, value):
        # 磁吸逻辑：靠近整十数进行锁定
        snap_points = [20, 50, 80, 100]
        for point in snap_points:
            if abs(value - point) <= 4: # 4% 的感应范围
                value = point
                self.slider.blockSignals(True)
                self.slider.setValue(value)
                self.slider.blockSignals(False)
                break
        
        self.label.setText(f"{value}%")
        self.callback(value / 100.0)
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

class ClickOverlay(QWidget):
    """专门捕获点击的透明遮罩层，解决 Mac 系统点击穿透和拦截问题"""
    def __init__(self, parent, window):
        super().__init__(parent)
        self.window = window
        self.setAttribute(Qt.WA_TranslucentBackground)
        
    def mousePressEvent(self, event):
        self.window.mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        self.window.mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.window.mouseReleaseEvent(event)
        
    def contextMenuEvent(self, event):
        self.window.contextMenuEvent(event)

class GoldWindow(QMainWindow):
    # 定义任务触发信号
    request_fetch = Signal()
    def __init__(self):
        super().__init__()
        self.fetcher = GoldDataFetcher()
        self.old_pos = None
        self.is_loaded = False
        
        # 窗口基本设置
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
        
        # 配置 WebEngine 渲染属性
        self.browser.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.browser.page().setBackgroundColor(Qt.transparent)
        # 移除 WA_TransparentForMouseEvents，由 Overlay 接管交互
        
        # 监听加载完成
        self.browser.loadFinished.connect(self.on_load_finished)
        
        # 初始化遮罩层 (最关键的一步，确保它在浏览器上方)
        self.overlay = ClickOverlay(self, self)
        self.overlay.setGeometry(0, 0, 320, 480)
        self.overlay.show()
        self.overlay.raise_() # 强制提升到最顶层
        
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
        self.resize(320, 480)
        
        # 优化启动：立即发射一次请求，不等定时器
        QTimer.singleShot(0, lambda: self.request_fetch.emit())

    def resizeEvent(self, event):
        """确保遮罩层始终覆盖整个窗口"""
        if hasattr(self, 'overlay'):
            self.overlay.setGeometry(self.rect())
        super().resizeEvent(event)

    def on_load_finished(self, success):
        if success:
            self.is_loaded = True
            # 默认设置为 100% 不透明并应用实色背景
            self.set_window_opacity(1.0)
            self.update_data()
        else:
            print("Failed to load local index.html")

    def handle_data(self, data):
        """主线程槽函数：将获取到的数据渲染至 Web 界面"""
        if not self.is_loaded:
            return
        data_json = json.dumps(data)
        self.browser.page().runJavaScript(f"if(typeof updateUI === 'function') updateUI({data_json});")

    def set_window_opacity(self, value):
        """设置窗口不透明度，并处理 100% 时的全实填充逻辑"""
        self.setWindowOpacity(value)
        # 只有在 100% 时切换为实色，避免玻璃通透感
        is_solid = "true" if value >= 0.99 else "false"
        self.browser.page().runJavaScript(f"if(typeof setSolidMode === 'function') setSolidMode({is_solid});")

    def update_data(self):
        """兼容保留，供手动调用"""
        self.request_fetch.emit()

    def closeEvent(self, event):
        """窗口关闭时安全终止后台线程"""
        self.worker_thread.quit()
        self.worker_thread.wait()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        # 调试日志：如果右键没反应，请观察黑窗口是否有此输出
        print(f">>> 窗口点击: {event.button()}") 
        
        if event.button() == Qt.LeftButton:
            try:
                self.old_pos = event.globalPosition().toPoint()
            except AttributeError:
                self.old_pos = event.globalPos()
        elif event.button() == Qt.RightButton:
            gp = event.globalPos()
            print(f">>> [!] 右键按下 - 捕获全局坐标: ({gp.x()}, {gp.y()})")
            self.show_context_menu(gp)
            event.accept()

    def mouseReleaseEvent(self, event):
        # 调试日志
        if event.button() == Qt.RightButton:
             print(">>> 检测到右键释放...")
        self.old_pos = None
        event.accept()

    def contextMenuEvent(self, event):
        """标准右键菜单事件回调"""
        print(">>> 触发系统级 ContextMenuEvent...")
        self.show_context_menu(event.globalPos())
        event.accept()

    def show_context_menu(self, pos):
        # 调试：打印弹出坐标
        print(f">>> [!] 正在尝试弹出菜单...")
        
        # 创建一个完全独立的菜单，不带父对象，避免继承窗口的透明度
        menu = QMenu() 
        menu.setAttribute(Qt.WA_DeleteOnClose) # 关闭即销毁
        # 增加 WindowStaysOnTopHint | FramelessWindowHint
        menu.setWindowFlags(Qt.Popup | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground, False) # 显式禁用菜单背景透明
        
        # 强制设置菜单样式
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 30, 0.95);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 25px;
                background-color: transparent;
                border-radius: 6px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #26d38e;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 4px 10px;
            }
            QMenu::right-arrow {
                image: none;
                width: 0px;
            }
        """)
        
        # 1. 版块切换 (子菜单)
        toggle_menu = menu.addMenu("版块显示切换")
        
        gold_action = QAction("黄金版块", self)
        gold_action.triggered.connect(lambda: self.browser.page().runJavaScript("toggleSection('gold')"))
        toggle_menu.addAction(gold_action)
        
        silver_action = QAction("白银版块", self)
        silver_action.triggered.connect(lambda: self.browser.page().runJavaScript("toggleSection('silver')"))
        toggle_menu.addAction(silver_action)
        
        crypto_all_action = QAction("加密版块", self)
        crypto_all_action.triggered.connect(lambda: self.browser.page().runJavaScript("toggleSection('crypto')"))
        toggle_menu.addAction(crypto_all_action)

        # 2. 加密货币细分筛选 (直接在主菜单显示)
        crypto_filter_menu = menu.addMenu("加密货币细分筛选")
        for name in ["BTC", "ETH", "BNB", "SOL"]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked=False, s=name: self.browser.page().runJavaScript(f"toggleSection('{s}')"))
            crypto_filter_menu.addAction(action)

        menu.addSeparator()

        # 3. 个性化设置 (仅保留不透明度)
        settings_menu = menu.addMenu("个性化设置")
        
        # 三级菜单：不透明度
        opacity_submenu = settings_menu.addMenu("调节窗口不透明度")
        slider_action = OpacitySliderAction(opacity_submenu, self.windowOpacity(), self.set_window_opacity)
        opacity_submenu.addAction(slider_action)

        menu.addSeparator()

        refresh_action = QAction("立即刷新数据", self)
        refresh_action.triggered.connect(self.update_data)
        menu.addAction(refresh_action)
        
        menu.addSeparator()
        
        exit_action = QAction("退出程序", self)
        exit_action.triggered.connect(QApplication.instance().quit)
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

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # 即使窗口关闭也不退出进程
    
    window = GoldWindow()
    
    # 设置应用及窗口图标
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "app_icon.png"))
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    window.setWindowIcon(app_icon)
    app.setApplicationDisplayName("行情悬浮窗")
    
    window.show()
    
    # 系统托盘
    tray = QSystemTrayIcon(app)
    tray.setIcon(app_icon) 
    
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
