"""
股票数据服务
"""
import csv
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.models.schemas import StockInfo


class StockService:
    """股票服务"""

    _stock_list_cache: List[Tuple[str, str]] = []

    @classmethod
    def load_stock_list(cls) -> List[Tuple[str, str]]:
        """加载股票列表"""
        if cls._stock_list_cache:
            return cls._stock_list_cache

        csv_path = Path(settings.STOCK_LIST_PATH)
        if csv_path.exists():
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    cls._stock_list_cache = [
                        (row["code"], row["name"]) for row in reader
                    ]
                print(f"已加载 {len(cls._stock_list_cache)} 只股票")
                return cls._stock_list_cache
            except Exception as e:
                print(f"加载股票列表失败: {e}")

        # 默认列表
        cls._stock_list_cache = [
            ("sz.000001", "平安银行"),
            ("sh.600000", "浦发银行"),
            ("sz.002639", "雪人股份"),
            ("sh.600519", "贵州茅台"),
            ("sh.000300", "沪深300"),
        ]
        return cls._stock_list_cache

    @classmethod
    def search_stocks(cls, keyword: str, limit: int = 50) -> List[StockInfo]:
        """搜索股票"""
        if not cls._stock_list_cache:
            cls.load_stock_list()

        keyword = keyword.strip().lower()
        if not keyword:
            return []

        results = []
        for code, name in cls._stock_list_cache:
            code_num = code.replace("sz.", "").replace("sh.", "")
            if keyword in code.lower() or keyword in code_num or keyword in name.lower():
                results.append(StockInfo(code=code, name=name))
                if len(results) >= limit:
                    break

        return results

    @classmethod
    def get_stock_name(cls, code: str) -> str:
        """根据代码获取股票名称"""
        if not cls._stock_list_cache:
            cls.load_stock_list()

        for c, name in cls._stock_list_cache:
            if c == code:
                return name
        return ""


class RealtimeService:
    """实时行情服务"""

    CACHE_TTL = 30  # 缓存有效期（秒）
    _cache: dict = {}

    @classmethod
    def normalize_code(cls, code: str) -> str:
        """标准化股票代码"""
        code = code.strip()
        if code.startswith("sh.") or code.startswith("sz."):
            return code[3:]
        elif code.startswith("sh") or code.startswith("sz"):
            return code[2:]
        return code

    @classmethod
    def get_realtime_data(cls, code: str) -> Optional[dict]:
        """获取实时行情数据"""
        import akshare as ak

        code_num = cls.normalize_code(code)

        # 检查缓存
        if code_num in cls._cache:
            data, cache_time = cls._cache[code_num]
            if (datetime.now() - cache_time).total_seconds() < cls.CACHE_TTL:
                return data

        try:
            # 获取个股基本信息
            info_df = ak.stock_individual_info_em(symbol=code_num)
            info_dict = dict(zip(info_df["item"], info_df["value"]))

            # 获取盘口数据
            bid_df = ak.stock_bid_ask_em(symbol=code_num)
            bid_dict = dict(zip(bid_df["item"], bid_df["value"]))

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

            def format_market_cap(value: float) -> str:
                if value >= 1e12:
                    return f"{value / 1e12:.2f}万亿"
                elif value >= 1e8:
                    return f"{value / 1e8:.2f}亿"
                elif value >= 1e4:
                    return f"{value / 1e4:.2f}万"
                else:
                    return f"{value:.2f}"

            def format_volume(value: float) -> str:
                shares = value * 100
                if shares >= 1e8:
                    return f"{shares / 1e8:.2f}亿股"
                elif shares >= 1e4:
                    return f"{shares / 1e4:.2f}万股"
                else:
                    return f"{shares:.0f}股"

            def format_turnover(value: float) -> str:
                if value >= 1e12:
                    return f"{value / 1e12:.2f}万亿"
                elif value >= 1e8:
                    return f"{value / 1e8:.2f}亿"
                elif value >= 1e4:
                    return f"{value / 1e4:.2f}万"
                else:
                    return f"{value:.2f}"

            total_market_cap = safe_float(info_dict.get("总市值"))
            circulating_market_cap = safe_float(info_dict.get("流通市值"))
            volume = safe_float(bid_dict.get("总手"))
            turnover = safe_float(bid_dict.get("金额"))

            data = {
                "code": code_num,
                "name": safe_str(info_dict.get("股票简称", "")),
                "latest_price": safe_float(bid_dict.get("最新")),
                "change_pct": safe_float(bid_dict.get("涨幅")),
                "change_amount": safe_float(bid_dict.get("涨跌")),
                "volume": format_volume(volume),
                "turnover": format_turnover(turnover),
                "high": safe_float(bid_dict.get("最高")),
                "low": safe_float(bid_dict.get("最低")),
                "open_price": safe_float(bid_dict.get("今开")),
                "prev_close": safe_float(bid_dict.get("昨收")),
                "volume_ratio": safe_float(bid_dict.get("量比")),
                "turnover_rate": safe_float(bid_dict.get("换手")),
                "total_market_cap": format_market_cap(total_market_cap),
                "circulating_market_cap": format_market_cap(circulating_market_cap),
                "avg_price": safe_float(bid_dict.get("均价")),
                "limit_up": safe_float(bid_dict.get("涨停")),
                "limit_down": safe_float(bid_dict.get("跌停")),
                "industry": safe_str(info_dict.get("行业", "")),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # 更新缓存
            cls._cache[code_num] = (data, datetime.now())
            return data

        except Exception as e:
            print(f"获取实时数据失败 {code}: {e}")
            return None
