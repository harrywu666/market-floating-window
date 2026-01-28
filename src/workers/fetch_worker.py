"""
异步数据抓取工作线程
使用QThread实现非阻塞的数据抓取
"""
from PySide6.QtCore import QObject, Signal, Slot


class FetchWorker(QObject):
    """异步抓取执行者，独立于并运行在后台线程"""
    
    # 信号：数据抓取完成后发出，携带抓取到的数据字典
    data_fetched = Signal(dict)
    
    def __init__(self, fetcher):
        """
        初始化工作线程
        
        Args:
            fetcher: GoldDataFetcher实例，用于执行实际的数据抓取
        """
        super().__init__()
        self.fetcher = fetcher
        
    @Slot()
    def do_fetch(self):
        """
        执行数据抓取任务（槽函数）
        在后台线程中调用，抓取完成后发出data_fetched信号
        """
        try:
            # 调用fetcher获取所有数据
            data = self.fetcher.fetch_all()
            # 发送数据到主线程
            self.data_fetched.emit(data)
        except Exception as e:
            # 发生错误时，返回包含错误信息的字典
            self.data_fetched.emit({"error": str(e)})
