"""
主窗口模块
管理应用的主窗口，包括窗口设置、事件处理、数据更新等
"""
import platform
import json
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QUrl, QThread
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtGui import QMouseEvent

from ..core.config import AppConfig
from ..core.data_fetcher import GoldDataFetcher
from ..workers.fetch_worker import FetchWorker
from .menu import MenuManager


class GoldWindow(QMainWindow):
    """市场行情浮动窗口主类"""
    
    # 定义信号：请求数据抓取
    request_fetch = Signal()
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 初始化状态变量
        self.fetcher = GoldDataFetcher()
        self.old_pos = None  # 用于窗口拖动
        self.is_loaded = False  # WebView是否加载完成
        self.is_always_on_top = False  # 默认不置顶
        
        # 初始化菜单管理器
        self.menu_manager = MenuManager(self)
        
        # 设置窗口
        self._setup_window()
        
        # 设置WebView
        self._setup_webview()
        
        # 设置异步数据抓取
        self._setup_worker_thread()
        
        # 设置定时器
        self._setup_timers()
        
        # 设置初始尺寸
        self.resize(AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)
    
    def _setup_window(self):
        """设置窗口属性"""
        self.update_window_flags()
        self.setAttribute(Qt.WA_TranslucentBackground)  # 背景透明
    
    def _setup_webview(self):
        """设置WebView组件"""
        # 创建Web视图
        self.browser = QWebEngineView(self)
        self.browser.setContextMenuPolicy(Qt.NoContextMenu)  # 禁用右键菜单
        
        # 配置WebEngine设置
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        
        # 设置为中央控件
        self.setCentralWidget(self.browser)
        
        # 配置渲染属性
        self.browser.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.browser.page().setBackgroundColor(Qt.transparent)
        # 开启鼠标事件穿透，让Python处理所有鼠标事件
        self.browser.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # 监听加载完成
        self.browser.loadFinished.connect(self.on_load_finished)
        
        # 加载HTML文件
        html_path = AppConfig.get_html_path()
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
    
    def _setup_worker_thread(self):
        """设置异步工作线程"""
        # 创建工作线程
        self.worker_thread = QThread()
        self.worker = FetchWorker(self.fetcher)
        self.worker.moveToThread(self.worker_thread)
        
        # 连接信号：触发任务 -> 执行任务 -> 更新面板
        self.request_fetch.connect(self.worker.do_fetch)
        self.worker.data_fetched.connect(self.handle_data)
        
        # 启动线程
        self.worker_thread.start()
    
    def _setup_timers(self):
        """设置各种定时器"""
        # 数据更新定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.request_fetch.emit())
        self.timer.start(AppConfig.UPDATE_INTERVAL_MS)
    
    def on_load_finished(self, success):
        """
        WebView加载完成回调
        
        Args:
            success: 是否加载成功
        """
        if success:
            self.is_loaded = True
            self.update_data()
            
            # 同步初始置顶状态到UI
            self.browser.page().runJavaScript(
                f"if(typeof setPinState === 'function') setPinState({str(self.is_always_on_top).lower()});"
            )
            
            # 启动置顶状态轮询
            self.pin_poll_timer = QTimer(self)
            self.pin_poll_timer.timeout.connect(self.check_pin_state)
            self.pin_poll_timer.start(AppConfig.PIN_POLL_INTERVAL_MS)
            
            # 启动拖动状态轮询
            self.drag_poll_timer = QTimer(self)
            self.drag_poll_timer.timeout.connect(self.check_drag_state)
            self.drag_poll_timer.start(AppConfig.DRAG_POLL_INTERVAL_MS)
            
            # 启动右键菜单轮询
            self.menu_poll_timer = QTimer(self)
            self.menu_poll_timer.timeout.connect(self.check_context_menu)
            self.menu_poll_timer.start(AppConfig.MENU_POLL_INTERVAL_MS)
        else:
            pass  # 加载失败，静默处理
    
    def check_pin_state(self):
        """轮询检查JavaScript中的置顶状态"""
        if not self.is_loaded:
            return
        self.browser.page().runJavaScript("window.pinState;", self.handle_pin_state)
    
    def handle_pin_state(self, result):
        """
        处理从JavaScript返回的置顶状态
        
        Args:
            result: JavaScript返回的置顶状态值
        """
        if result is not None and isinstance(result, bool):
            if result != self.is_always_on_top:
                self.is_always_on_top = result
                self.update_window_flags()
    
    def check_drag_state(self):
        """轮询检查JavaScript中的拖动状态"""
        if not self.is_loaded:
            return
        self.browser.page().runJavaScript("window.dragState;", self.handle_drag_state)
    
    def handle_drag_state(self, result):
        """
        处理从JavaScript返回的拖动状态
        
        Args:
            result: JavaScript返回的拖动状态字典
        """
        if result and isinstance(result, dict):
            action = result.get('action')
            if action == 'move':
                deltaX = result.get('deltaX', 0)
                deltaY = result.get('deltaY', 0)
                if deltaX != 0 or deltaY != 0:
                    # 移动窗口
                    new_x = self.x() + deltaX
                    new_y = self.y() + deltaY
                    self.move(new_x, new_y)
            # 清除已处理的状态
            self.browser.page().runJavaScript("window.dragState = null;")
    
    def check_context_menu(self):
        """轮询检查JavaScript中的右键菜单请求"""
        if not self.is_loaded:
            return
        self.browser.page().runJavaScript("window.contextMenuRequest;", self.handle_context_menu)
    
    def handle_context_menu(self, result):
        """
        处理从JavaScript返回的右键菜单请求
        
        Args:
            result: JavaScript返回的菜单请求字典
        """
        if result and isinstance(result, dict):
            x = result.get('x', 0)
            y = result.get('y', 0)
            self.show_context_menu(QPoint(int(x), int(y)))
            # 清除已处理的请求
            self.browser.page().runJavaScript("window.contextMenuRequest = null;")
    
    def handle_data(self, data):
        """
        主线程槽函数：将获取到的数据渲染至Web界面
        
        Args:
            data: 抓取到的数据字典
        """
        if not self.is_loaded:
            return
        data_json = json.dumps(data)
        self.browser.page().runJavaScript(
            f"if(typeof updateUI === 'function') updateUI({data_json});"
        )
    
    def update_data(self):
        """手动触发数据更新"""
        self.request_fetch.emit()
    
    def update_window_flags(self):
        """更新窗口标志（置顶/不置顶）"""
        if platform.system() == 'Darwin':
            # macOS
            flags = Qt.FramelessWindowHint
            if self.is_always_on_top:
                flags |= Qt.WindowStaysOnTopHint
            self.setWindowFlags(flags)
        else:
            # Windows/Linux
            flags = Qt.FramelessWindowHint | Qt.Tool
            if self.is_always_on_top:
                flags |= Qt.WindowStaysOnTopHint
            self.setWindowFlags(flags)
        
        # setWindowFlags会隐藏窗口，需要重新显示并激活
        self.show()
        self.raise_()  # 确保窗口在最前面
        self.activateWindow()  # 激活窗口获得焦点
    
    def toggle_always_on_top(self):
        """
        切换置顶状态
        
        Returns:
            bool: 新的置顶状态
        """
        self.is_always_on_top = not self.is_always_on_top
        self.update_window_flags()
        # 同步状态到WebView UI
        self.browser.page().runJavaScript(
            f"if(typeof setPinState === 'function') setPinState({str(self.is_always_on_top).lower()});"
        )
        return self.is_always_on_top
    
    def show_context_menu(self, pos):
        """
        显示右键上下文菜单
        
        Args:
            pos: 菜单显示位置（全局坐标）
        """
        self.menu_manager.create_context_menu(pos)
    
    def mousePressEvent(self, event: QMouseEvent):
        """
        处理鼠标按下事件
        
        Args:
            event: 鼠标事件对象
        """
        if event.button() == Qt.LeftButton:
            # 左键任意位置开始拖动
            try:
                self.old_pos = event.globalPosition().toPoint()
            except AttributeError:
                self.old_pos = event.globalPos()
        elif event.button() == Qt.RightButton:
            # 右键打开菜单
            try:
                global_pos = event.globalPosition().toPoint()
            except AttributeError:
                global_pos = event.globalPos()
            self.show_context_menu(global_pos)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """
        处理鼠标移动事件 - 拖动窗口
        
        Args:
            event: 鼠标事件对象
        """
        if self.old_pos:
            try:
                curr_pos = event.globalPosition().toPoint()
            except AttributeError:
                curr_pos = event.globalPos()
            delta = curr_pos - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = curr_pos
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        处理鼠标释放事件
        
        Args:
            event: 鼠标事件对象
        """
        self.old_pos = None
    
    def closeEvent(self, event):
        """
        窗口关闭事件：安全终止后台线程
        
        Args:
            event: 关闭事件对象
        """
        self.worker_thread.quit()
        self.worker_thread.wait()
        super().closeEvent(event)
