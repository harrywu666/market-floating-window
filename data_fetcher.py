import requests
import re
import json
from concurrent.futures import ThreadPoolExecutor

class GoldDataFetcher:
    def __init__(self):
        # 建立持久化会话连接池
        self.session = requests.Session()
        self.session.headers.update({
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        # 使用新浪财经接口：
        # hf_XAU - 国际黄金现货, hf_SI - 国际白银现货
        # fx_susdcny - 美元人民币汇率
        # SGE_AUTD, SGE_AGTD 已移除，改用东方财富接口
        self.sina_url = "https://hq.sinajs.cn/list=hf_XAU,hf_SI,fx_susdcny"

        # 记录国内外溢价（Premium），用于在休市期间进行"无缝推演"
        self.last_premium_gold = 9.5  # 初始经验值
        self.last_premium_silver = 0.15 # 初始经验值（白银国内相比国际通常有固定溢价）

        # API 配置：币安优先，OKX备用
        self.crypto_apis = ['binance', 'okx']
        self.current_api_index = 0  # 当前使用的API索引

    def _safe_float(self, value, default=0.0):
        if not value: return default
        try:
            val = str(value).split(',')[0].strip()
            return float(val) if val != '-' else default
        except: return default

    def _fetch_eastmoney_spot(self, secid):
        """从东方财富获取国内现货数据"""
        try:
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "fields": "f43,f60,f57,f58"  # f43:最新价, f60:昨收, f57:代码, f58:名称
            }
            # 使用独立请求头，避免新浪的 Referer 导致反爬
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://quote.eastmoney.com/",
                "Host": "push2.eastmoney.com"
            }
            # 不使用 self.session 及其默认头部，而是直接使用 requests.get 或创建新 session
            # 为简单起见，这里直接用 requests.get (非持久化连接对于低频请求可接受，或清除 header)
            resp = requests.get(url, params=params, headers=headers, timeout=2.0).json()
            
            if resp and resp.get("data"):
                data = resp["data"]
                return {
                    "price": self._safe_float(data.get("f43")),
                    "prev_close": self._safe_float(data.get("f60"))
                }
        except Exception as e:
            print(f"东方财富 API 获取 {secid} 失败: {e}")
        return None



    def _fetch_crypto_from_okx(self, name, sym):
        """从OKX获取单个加密货币现货数据"""
        try:
            # OKX 使用不同的交易对格式，如 BTC-USDT
            okx_sym = sym.replace('USDT', '-USDT')
            url = f"https://www.okx.com/api/v5/market/ticker?instId={okx_sym}"
            resp = self.session.get(url, timeout=2.0).json()
            if isinstance(resp, dict) and resp.get('code') == '0' and resp.get('data'):
                ticker = resp['data'][0]
                last = self._safe_float(ticker.get('last'))
                open24 = self._safe_float(ticker.get('open24h'))
                
                change = 0.0
                if open24 > 0:
                    change = (last - open24) / open24 * 100

                return name, {
                    "price": last,
                    "change": change
                }
        except Exception as e:
            print(f"OKX API 获取 {name} 失败: {e}")
        return name, None

    def _fetch_contract_from_okx(self, name, sym):
        """从OKX获取合约数据（用于只有合约无现货的币种）"""
        try:
            # OKX 合约使用不同的交易对格式，如 BTC-USDT-SWAP
            okx_sym = sym.replace('USDT', '-USDT-SWAP')
            url = f"https://www.okx.com/api/v5/market/ticker?instId={okx_sym}"
            resp = self.session.get(url, timeout=2.0).json()
            if isinstance(resp, dict) and resp.get('code') == '0' and resp.get('data'):
                ticker = resp['data'][0]
                last = self._safe_float(ticker.get('last'))
                open24 = self._safe_float(ticker.get('open24h'))
                
                change = 0.0
                if open24 > 0:
                    change = (last - open24) / open24 * 100

                return name, {
                    "price": last,
                    "change": change
                }
        except Exception as e:
            print(f"OKX 合约 API 获取 {name} 失败: {e}")
        return name, None

    def _fetch_single_crypto(self, name, sym):
        """获取单个加密货币数据，仅使用OKX"""
        
        # 1. 尝试 OKX 现货
        result = self._fetch_crypto_from_okx(name, sym)
        if result[1] is not None:
            return result
            
        # 2. 现货失败，尝试 OKX 合约 (主要针对 HYPE 等可能只在合约上线的币种)
        print(f"OKX 现货获取 {name} 失败，尝试 OKX 合约...")
        result = self._fetch_contract_from_okx(name, sym)
        if result[1] is not None:
            return result
            
        # 3. 都失败
        print(f"OKX 所有渠道获取 {name} 失败")
        return name, None

    def fetch_all(self):
        """全时段无缝跳动引擎：国内休市期间自动对标国际盘面推演价格"""
        data = {
            "gold": {"intl": 0.0, "intl_change": 0.0, "dom": 0.0, "dom_change": 0.0},
            "silver": {"intl": 0.0, "intl_change": 0.0, "dom": 0.0, "dom_change": 0.0},
            "crypto": {},
            "exchange_rate": 0.0,
            "market_status": {"gold": "open", "silver": "open"},  # open/closed
            "error": None
        }

        try:
            # 恢复 SGE_AUTD 和 SGE_AGTD 到新浪 URL
            # 注意：确保 headers 中 Referer 正确 (已在 __init__ 中设置)
            full_sina_url = self.sina_url + ",SGE_AUTD,SGE_AGTD"
            
            def fetch_sina():
                try:
                    resp = self.session.get(full_sina_url, timeout=2.0)
                    return resp.content.decode('gb18030', errors='ignore')
                except: return ""
            
            # 并行获取新浪数据（国际+汇率+国内现货）和加密货币数据
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_sina = executor.submit(fetch_sina)
                
                crypto_map = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "BNB": "BNBUSDT", "SOL": "SOLUSDT", "HYPE": "HYPEUSDT"}
                crypto_futures = [executor.submit(self._fetch_single_crypto, n, s) for n, s in crypto_map.items()]

                # 1. 解析新浪数据
                html = future_sina.result()
                if html:
                    def parse_sina(key):
                        m = re.search(f'{key}="([^"]+)"', html)
                        return m.group(1).split(',') if m else []

                    # 抓取汇率与国际盘（永不休市，作为基准）
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

                    # 2. 抓取国内现货（恢复新浪数据源）
                    # SGE_AUTD: [代码, 名称, 简拼, 最新价, 昨收, 开盘, 最高, 最低, 买价, 卖价, 昨结, ..., 时间]
                    # 注意新浪数据格式: index 3 是最新价, index 4 是昨收
                    au_spot = parse_sina("SGE_AUTD")
                    ag_spot = parse_sina("SGE_AGTD")

                    #单位转换常数: 1 盎司 = 31.1034768 克
                    oz_to_g = 31.1034768

                    # --- 黄金逻辑：无缝推演 ---
                    if data["gold"]["intl"] > 0 and data["exchange_rate"] > 0:
                        theoretical_dom = data["gold"]["intl"] * data["exchange_rate"] / oz_to_g
                        
                        actual_dom = self._safe_float(au_spot[3]) if len(au_spot) > 3 else 0
                        yesterday_close = self._safe_float(au_spot[4]) if len(au_spot) > 4 else 0

                        # SGE_AUTD 特定判断：如果有 latest_price 且 > 0，则为开市
                        is_market_closed = len(au_spot) < 4 or actual_dom <= 0
                        
                        if actual_dom > 0 and not is_market_closed:
                            # 正常交易时段：记录最新溢价
                            self.last_premium_gold = actual_dom - theoretical_dom
                            data["gold"]["dom"] = actual_dom
                            data["market_status"]["gold"] = "open"
                            # 正常交易时段：使用昨收价计算涨跌幅
                            if yesterday_close > 0:
                                data["gold"]["dom_change"] = round((actual_dom - yesterday_close) / yesterday_close * 100, 2)
                        else:
                            # 休市期间：基于国际走势 + 最后记录的溢价进行"动态推演"
                            data["gold"]["dom"] = round(theoretical_dom + self.last_premium_gold, 2)
                            data["market_status"]["gold"] = "closed"
                            # 休市期间：使用国际盘涨跌幅作为国内涨跌幅
                            data["gold"]["dom_change"] = data["gold"]["intl_change"]

                    # --- 白银逻辑：无缝推演 ---
                    if data["silver"]["intl"] > 0 and data["exchange_rate"] > 0:
                        # 国际盎司到国内克的理论换算
                        theoretical_dom = data["silver"]["intl"] * data["exchange_rate"] / oz_to_g
                        
                        # AGTD 是 元/千克
                        actual_dom_kg = self._safe_float(ag_spot[3]) if len(ag_spot) > 3 else 0
                        actual_dom = actual_dom_kg / 1000
                        yesterday_close_kg = self._safe_float(ag_spot[4]) if len(ag_spot) > 4 else 0
                        yesterday_close = yesterday_close_kg / 1000
                        
                        is_market_closed = len(ag_spot) < 4 or actual_dom <= 0

                        if actual_dom > 0 and not is_market_closed:
                            self.last_premium_silver = actual_dom - theoretical_dom
                            data["silver"]["dom"] = round(actual_dom, 3)
                            data["market_status"]["silver"] = "open"
                            # 正常交易时段：使用昨收价计算涨跌幅
                            if yesterday_close > 0:
                                data["silver"]["dom_change"] = round((actual_dom - yesterday_close) / yesterday_close * 100, 2)
                        else:
                            # 溢价推演
                            data["silver"]["dom"] = round(theoretical_dom + self.last_premium_silver, 3)
                            data["market_status"]["silver"] = "closed"
                            # 休市期间：使用国际盘涨跌幅作为国内涨跌幅
                            data["silver"]["dom_change"] = data["silver"]["intl_change"]

                # 3. 收集加密货币结果
                for f in crypto_futures:
                    res = f.result()
                    if res[1]: data["crypto"][res[0]] = res[1]

        except Exception as e:
            data["error"] = str(e)

        return data

if __name__ == "__main__":
    # 测试代码
    fetcher = GoldDataFetcher()
    print(fetcher.fetch_all())
