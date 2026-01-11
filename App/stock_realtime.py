"""
实时股票数据获取模块

功能：
    - 获取单只股票的实时行情数据
    - 支持缓存机制，避免频繁请求
    - 提供格式化的数据展示

数据来源：
    - AkShare: stock_individual_info_em + stock_bid_ask_em (东方财富)
    - 使用单只股票接口，速度快（约2秒），而非全量接口（60+秒）
"""
import threading
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class StockRealtimeData:
    """实时股票数据"""
    code: str                      # 股票代码
    name: str                      # 股票名称
    latest_price: float            # 最新价
    change_pct: float              # 涨跌幅(%)
    change_amount: float           # 涨跌额
    volume: float                  # 成交量(手)
    turnover: float                # 成交额(元)
    high: float                    # 最高价
    low: float                     # 最低价
    open_price: float              # 开盘价
    prev_close: float              # 昨收价
    volume_ratio: float            # 量比
    turnover_rate: float           # 换手率(%)
    total_shares: float            # 总股本
    circulating_shares: float      # 流通股
    total_market_cap: float        # 总市值(元)
    circulating_market_cap: float  # 流通市值(元)
    avg_price: float               # 均价
    limit_up: float                # 涨停价
    limit_down: float              # 跌停价
    industry: str                  # 所属行业
    update_time: datetime          # 更新时间

    def format_market_cap(self, value: float) -> str:
        """格式化市值显示"""
        if value >= 1e12:
            return f"{value / 1e12:.2f}万亿"
        elif value >= 1e8:
            return f"{value / 1e8:.2f}亿"
        elif value >= 1e4:
            return f"{value / 1e4:.2f}万"
        else:
            return f"{value:.2f}"

    def format_volume(self, value: float) -> str:
        """格式化成交量显示（输入为手）"""
        shares = value * 100  # 转为股
        if shares >= 1e8:
            return f"{shares / 1e8:.2f}亿股"
        elif shares >= 1e4:
            return f"{shares / 1e4:.2f}万股"
        else:
            return f"{shares:.0f}股"

    def format_turnover(self, value: float) -> str:
        """格式化成交额显示"""
        if value >= 1e12:
            return f"{value / 1e12:.2f}万亿"
        elif value >= 1e8:
            return f"{value / 1e8:.2f}亿"
        elif value >= 1e4:
            return f"{value / 1e4:.2f}万"
        else:
            return f"{value:.2f}"

    def get_display_dict(self) -> Dict[str, str]:
        """获取格式化的显示字典"""
        return {
            "最新价": f"{self.latest_price:.2f}",
            "涨跌幅": f"{self.change_pct:+.2f}%",
            "涨跌额": f"{self.change_amount:+.2f}",
            "今开": f"{self.open_price:.2f}",
            "昨收": f"{self.prev_close:.2f}",
            "最高": f"{self.high:.2f}",
            "最低": f"{self.low:.2f}",
            "均价": f"{self.avg_price:.2f}",
            "成交量": self.format_volume(self.volume),
            "成交额": self.format_turnover(self.turnover),
            "换手率": f"{self.turnover_rate:.2f}%",
            "量比": f"{self.volume_ratio:.2f}",
            "总市值": self.format_market_cap(self.total_market_cap),
            "流通市值": self.format_market_cap(self.circulating_market_cap),
            "涨停价": f"{self.limit_up:.2f}",
            "跌停价": f"{self.limit_down:.2f}",
            "行业": self.industry,
        }


class StockRealtimeService:
    """实时股票数据服务"""

    # 缓存有效期（秒）
    CACHE_TTL = 30

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # {code: (data, timestamp)}
        self._lock = threading.Lock()

    def _normalize_code(self, code: str) -> str:
        """标准化股票代码，返回纯数字代码"""
        code = code.strip()
        if code.startswith('sh.') or code.startswith('sz.'):
            return code[3:]
        elif code.startswith('sh') or code.startswith('sz'):
            return code[2:]
        return code

    def get_stock_data(self, code: str) -> Optional[StockRealtimeData]:
        """
        获取单只股票的实时数据（快速接口，约2秒）

        Args:
            code: 股票代码，支持格式: sz.000001, sh.600000, 000001, 600000

        Returns:
            StockRealtimeData 对象，获取失败返回 None
        """
        import akshare as ak

        code_num = self._normalize_code(code)

        with self._lock:
            # 检查缓存
            if code_num in self._cache:
                data, cache_time = self._cache[code_num]
                if (datetime.now() - cache_time).total_seconds() < self.CACHE_TTL:
                    return data

            try:
                # 获取个股基本信息（市值、股本等）
                info_df = ak.stock_individual_info_em(symbol=code_num)
                info_dict = dict(zip(info_df['item'], info_df['value']))

                # 获取盘口数据（价格、换手率、量比等）
                bid_df = ak.stock_bid_ask_em(symbol=code_num)
                bid_dict = dict(zip(bid_df['item'], bid_df['value']))

                # 安全获取数值
                def safe_float(val, default=0.0):
                    try:
                        if val is None or (isinstance(val, float) and val != val):
                            return default
                        return float(val)
                    except:
                        return default

                def safe_str(val, default=""):
                    try:
                        return str(val) if val else default
                    except:
                        return default

                data = StockRealtimeData(
                    code=code_num,
                    name=safe_str(info_dict.get('股票简称', '')),
                    latest_price=safe_float(bid_dict.get('最新')),
                    change_pct=safe_float(bid_dict.get('涨幅')),
                    change_amount=safe_float(bid_dict.get('涨跌')),
                    volume=safe_float(bid_dict.get('总手')),
                    turnover=safe_float(bid_dict.get('金额')),
                    high=safe_float(bid_dict.get('最高')),
                    low=safe_float(bid_dict.get('最低')),
                    open_price=safe_float(bid_dict.get('今开')),
                    prev_close=safe_float(bid_dict.get('昨收')),
                    volume_ratio=safe_float(bid_dict.get('量比')),
                    turnover_rate=safe_float(bid_dict.get('换手')),
                    total_shares=safe_float(info_dict.get('总股本')),
                    circulating_shares=safe_float(info_dict.get('流通股')),
                    total_market_cap=safe_float(info_dict.get('总市值')),
                    circulating_market_cap=safe_float(info_dict.get('流通市值')),
                    avg_price=safe_float(bid_dict.get('均价')),
                    limit_up=safe_float(bid_dict.get('涨停')),
                    limit_down=safe_float(bid_dict.get('跌停')),
                    industry=safe_str(info_dict.get('行业', '')),
                    update_time=datetime.now()
                )

                # 更新缓存
                self._cache[code_num] = (data, datetime.now())

                return data

            except Exception as e:
                print(f"[实时数据] 获取 {code} 数据失败: {e}")
                return None

    def clear_cache(self):
        """清除缓存"""
        with self._lock:
            self._cache.clear()


# 全局单例
_realtime_service: Optional[StockRealtimeService] = None


def get_realtime_service() -> StockRealtimeService:
    """获取实时数据服务单例"""
    global _realtime_service
    if _realtime_service is None:
        _realtime_service = StockRealtimeService()
    return _realtime_service


def get_stock_realtime_data(code: str) -> Optional[StockRealtimeData]:
    """
    便捷函数：获取单只股票的实时数据

    Args:
        code: 股票代码

    Returns:
        StockRealtimeData 对象
    """
    return get_realtime_service().get_stock_data(code)


# 测试代码
if __name__ == "__main__":
    import time

    print("测试实时数据获取（快速接口）...")

    start = time.time()
    data = get_stock_realtime_data("sz.002639")
    elapsed = time.time() - start

    if data:
        print(f"\n获取耗时: {elapsed:.2f}秒")
        print(f"\n{data.name}({data.code}):")
        display = data.get_display_dict()
        for key, value in display.items():
            print(f"  {key}: {value}")
    else:
        print("获取失败")
