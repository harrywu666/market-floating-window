import requests
import re
import json
import urllib3
import certifi
from concurrent.futures import ThreadPoolExecutor

# 禁用安全请求警告 (针对旧系统 SSL 兼容性)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 代理配置 (Proxy Configuration) ---
# 根据您的 Clash 截图：混合端口 7897，HTTP 端口 7899
PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897"
}

class GoldDataFetcher:
    def __init__(self):
        # 建立持久化会话连接池
        self.session = requests.Session()
        
        # 配置代理 (直接应用到会话，确保所有请求走代理)
        self.session.proxies.update(PROXIES)
        
        self.session.headers.update({
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self.sina_url = "https://hq.sinajs.cn/list=hf_XAU,hf_SI,nf_AU0,nf_AG0,fx_susdcny"
        
        # 记录国内外溢价（Premium），用于在休市期间进行“无缝推演”
        self.last_premium_gold = 9.5  # 初始经验值
        self.last_premium_silver = 3.35 # 初始经验值（白银国内相比国际通常有固定溢价）
        self.last_exchange_rate = 7.2  # 初始汇率

    def _safe_float(self, value, default=0.0):
        if not value: return default
        try:
            val = str(value).split(',')[0].strip()
            return float(val)
        except: return default

    def _fetch_crypto_batch(self):
        """
        全量欧易 (OKX) 唯一数据源
        仅使用 OKX API 抓取数据，报错则直接输出
        """
        targets = [
            {"symbol": "BTC", "okx": "BTC-USDT"},
            {"symbol": "ETH", "okx": "ETH-USDT"},
            {"symbol": "BNB", "okx": "BNB-USDT"},
            {"symbol": "SOL", "okx": "SOL-USDT"}
        ]
        
        try:
            url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
            response = self.session.get(url, timeout=5, verify=certifi.where())
            content = response.json()
            
            if content.get("code") == "0" and "data" in content:
                res = {}
                data_map = {item['instId']: item for item in content['data']}
                for t in targets:
                    item = data_map.get(t["okx"])
                    if item:
                        last_price = float(item['last'])
                        open_price = float(item['open24h'])
                        change_percent = ((last_price - open_price) / open_price * 100) if open_price > 0 else 0.0
                        res[t["symbol"]] = {
                            "price": last_price,
                            "change": change_percent
                        }
                return res
            else:
                print(f"OKX API Error: {content.get('msg', 'Unknown Error')}")
                return {}
        except Exception as e:
            print(f"OKX Fetch Exception (请检查代理配置): {e}")
            return {}

    def fetch_all(self):
        """全时段无缝跳动引擎：国内休市期间自动对标国际盘面推演价格"""
        data = {
            "gold": {"intl": 0.0, "intl_change": 0.0, "dom": 0.0, "dom_change": 0.0},
            "silver": {"intl": 0.0, "intl_change": 0.0, "dom": 0.0, "dom_change": 0.0},
            "crypto": {},
            "exchange_rate": 0.0,
            "error": None
        }

        try:
            def fetch_sina():
                try:
                    resp = self.session.get(self.sina_url, timeout=2.0)
                    return resp.content.decode('gb18030', errors='ignore')
                except: return ""

            with ThreadPoolExecutor(max_workers=3) as executor:
                future_sina = executor.submit(fetch_sina)
                future_crypto = executor.submit(self._fetch_crypto_batch)
                
                html = future_sina.result()
                if html:
                    def parse_sina(key):
                        m = re.search(f'{key}="([^"]+)"', html)
                        return m.group(1).split(',') if m else []

                    # 1. 抓取汇率与国际盘（永不休市，作为基准）
                    ex = parse_sina("fx_susdcny")
                    if ex: data["exchange_rate"] = self._safe_float(ex[1])
                    
                    xau = parse_sina("hf_XAU")
                    if xau:
                        data["gold"]["intl"] = self._safe_float(xau[0])
                        pc = self._safe_float(xau[1])
                        if pc > 0: data["gold"]["intl_change"] = round((data["gold"]["intl"] - pc) / pc * 100, 2)
                    
                    si = parse_sina("hf_SI")
                    if si:
                        data["silver"]["intl"] = self._safe_float(si[0])
                        pc = self._safe_float(si[1]) or self._safe_float(si[7])
                        if pc > 0: data["silver"]["intl_change"] = round((data["silver"]["intl"] - pc) / pc * 100, 2)

                    # 2. 抓取国内上海盘（11:30-13:30 午休）
                    au0 = parse_sina("nf_AU0")
                    ag0 = parse_sina("nf_AG0")

                    #单位转换常数: 1 盎司 = 31.1034768 克
                    oz_to_g = 31.1034768

                    # --- 黄金逻辑：无缝推演 ---
                    if data["gold"]["intl"] > 0 and data["exchange_rate"] > 0:
                        theoretical_dom = data["gold"]["intl"] * data["exchange_rate"] / oz_to_g
                        actual_dom = self._safe_float(au0[8]) if au0 else 0
                        
                        # 检测国内市场是否更新：如果此时是午休或收盘，Sina 数据的时间戳会固定在 113000
                        is_market_closed = au0[1] == "113000" if (au0 and len(au0)>1) else True
                        
                        if actual_dom > 0 and not is_market_closed:
                            # 正常交易时段：记录最新溢价
                            self.last_premium_gold = actual_dom - theoretical_dom
                            data["gold"]["dom"] = actual_dom
                        else:
                            # 休市期间：基于国际走势 + 最后记录的溢价进行“动态推演”
                            data["gold"]["dom"] = round(theoretical_dom + self.last_premium_gold, 2)
                            
                        # 计算涨跌幅
                        pc = self._safe_float(au0[2]) if au0 else 0
                        if pc > 0: data["gold"]["dom_change"] = round((data["gold"]["dom"] - pc) / pc * 100, 2)

                    # --- 白银逻辑：无缝推演（回滚为“克”单位） ---
                    if data["silver"]["intl"] > 0 and data["exchange_rate"] > 0:
                        # 国际盎司到国内克的理论换算
                        theoretical_dom = data["silver"]["intl"] * data["exchange_rate"] / oz_to_g
                        actual_dom = (self._safe_float(ag0[8]) / 1000.0) if ag0 else 0
                        is_market_closed = ag0[1] == "113000" if (ag0 and len(ag0)>1) else True

                        if actual_dom > 0 and not is_market_closed:
                            self.last_premium_silver = actual_dom - theoretical_dom
                            data["silver"]["dom"] = actual_dom
                        else:
                            # 溢价推演 (加回偏差值)
                            data["silver"]["dom"] = round(theoretical_dom + self.last_premium_silver, 3)

                        pc = (self._safe_float(ag0[2]) / 1000.0) if ag0 else 0
                        if pc > 0: data["silver"]["dom_change"] = round((data["silver"]["dom"] - pc) / pc * 100, 2)

                # 3. 收集加密货币结果
                crypto_res = future_crypto.result()
                if crypto_res:
                    data["crypto"] = crypto_res

        except Exception as e:
            data["error"] = str(e)

        return data

if __name__ == "__main__":
    # 测试代码
    fetcher = GoldDataFetcher()
    print(fetcher.fetch_all())
