"""
应用配置模块
管理应用的全局配置，包括窗口设置、API配置等
"""
import os


class AppConfig:
    """应用配置类"""
    
    # 窗口默认配置
    WINDOW_WIDTH = 360
    WINDOW_HEIGHT = 700
    DEFAULT_OPACITY = 1.0  # 默认透明度
    
    # 数据更新间隔（毫秒）
    UPDATE_INTERVAL_MS = 1000
    
    # 线程轮询间隔（毫秒）
    PIN_POLL_INTERVAL_MS = 100  # 置顶状态轮询
    DRAG_POLL_INTERVAL_MS = 16  # 拖动状态轮询（约60fps）
    MENU_POLL_INTERVAL_MS = 100  # 右键菜单轮询
    
    # UI资源路径（相对于项目根目录）
    @staticmethod
    def get_ui_path():
        """获取UI资源目录路径"""
        # 获取项目根目录（src的父目录）
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root_dir, "resources", "ui")
    
    @staticmethod
    def get_icon_path():
        """获取应用图标路径"""
        ui_path = AppConfig.get_ui_path()
        return os.path.join(ui_path, "assets", "app_icon.png")
    
    @staticmethod
    def get_html_path():
        """获取HTML文件路径"""
        ui_path = AppConfig.get_ui_path()
        return os.path.join(ui_path, "index.html")
    
    # 加密货币配置
    CRYPTO_SYMBOLS = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT", 
        "BNB": "BNBUSDT",
        "SOL": "SOLUSDT",
        "HYPE": "HYPEUSDT"
    }
    
    # 加密货币显示顺序
    CRYPTO_ORDER = ['BTC', 'ETH', 'BNB', 'SOL', 'HYPE']
    
    # 数据源配置
    SINA_URL = "https://hq.sinajs.cn/list=hf_XAU,hf_SI,fx_susdcny"
    
    # 初始溢价值（用于休市期间推演）
    INITIAL_PREMIUM_GOLD = 9.5
    INITIAL_PREMIUM_SILVER = 0.15
    
    # 单位转换常数
    OZ_TO_GRAM = 31.1034768  # 1盎司 = 31.1034768克
