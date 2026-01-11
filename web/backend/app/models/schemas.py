"""
Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class KLineType(str, Enum):
    """K线类型"""

    K_1M = "1分钟"
    K_5M = "5分钟"
    K_15M = "15分钟"
    K_30M = "30分钟"
    K_60M = "60分钟"
    K_DAY = "日线"
    K_WEEK = "周线"
    K_MON = "月线"


class StockInfo(BaseModel):
    """股票基本信息"""

    code: str
    name: str


class KLineUnit(BaseModel):
    """K线单元"""

    idx: int
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class BiInfo(BaseModel):
    """笔信息"""

    idx: int
    begin_idx: int
    end_idx: int
    begin_x: float
    end_x: float
    begin_y: float
    end_y: float
    is_sure: bool
    direction: str  # "up" or "down"


class SegInfo(BaseModel):
    """线段信息"""

    idx: int
    begin_idx: int
    end_idx: int
    begin_x: float
    end_x: float
    begin_y: float
    end_y: float
    is_sure: bool
    direction: str


class ZSInfo(BaseModel):
    """中枢信息"""

    idx: int
    begin: float
    end: float
    low: float
    high: float
    is_sure: bool


class BSPInfo(BaseModel):
    """买卖点信息"""

    idx: int
    x: float
    y: float
    is_buy: bool
    type: str  # "1", "2", "3a", "3b", "1p", "2s"
    is_sure: bool


class MACDInfo(BaseModel):
    """MACD 信息"""

    idx: int
    dif: float
    dea: float
    macd: float


class ChanAnalysisResult(BaseModel):
    """缠论分析结果"""

    code: str
    name: str
    kl_type: str
    klines: List[KLineUnit]
    bi_list: List[BiInfo]
    seg_list: List[SegInfo]
    zs_list: List[ZSInfo]
    bsp_list: List[BSPInfo]
    macd_list: List[MACDInfo]
    dateticks: List[str]


class MultiLevelResult(BaseModel):
    """多级别分析结果"""

    code: str
    name: str
    levels: Dict[str, ChanAnalysisResult]


class SingleAnalysisRequest(BaseModel):
    """单级别分析请求"""

    code: str = Field(..., description="股票代码，如 sz.000001")
    kl_type: KLineType = Field(default=KLineType.K_DAY, description="K线类型")
    periods: int = Field(default=300, ge=50, le=2000, description="周期数")


class MultiLevelRequest(BaseModel):
    """多级别分析请求"""

    code: str = Field(..., description="股票代码")
    levels: List[KLineType] = Field(
        default=[KLineType.K_DAY, KLineType.K_60M, KLineType.K_15M],
        description="级别列表",
    )
    periods: int = Field(default=300, ge=50, le=500, description="周期数")


class RealtimeData(BaseModel):
    """实时行情数据"""

    code: str
    name: str
    latest_price: float
    change_pct: float
    change_amount: float
    volume: str
    turnover: str
    high: float
    low: float
    open_price: float
    prev_close: float
    volume_ratio: float
    turnover_rate: float
    total_market_cap: str
    circulating_market_cap: str
    avg_price: float
    limit_up: float
    limit_down: float
    industry: str
    update_time: str


class ChanConfig(BaseModel):
    """缠论配置"""

    bi_strict: bool = True
    trigger_step: bool = False
    divergence_rate: float = float("inf")
    bsp2_follow_1: bool = False
    bsp3_follow_1: bool = False
    min_zs_cnt: int = 0
    bs1_peak: bool = False
    macd_algo: str = "peak"
    bs_type: str = "1,1p,2,2s,3a,3b"
    zs_algo: str = "normal"


class SystemConfig(BaseModel):
    """系统配置"""

    chan_config: ChanConfig = Field(default_factory=ChanConfig)
    default_kl_type: KLineType = KLineType.K_DAY
    default_periods: int = 300
    auto_refresh_interval: int = 60
    theme: str = "light"


class ScannerProgress(BaseModel):
    """扫描进度"""

    type: str  # "progress", "found", "finished", "error"
    current: Optional[int] = None
    total: Optional[int] = None
    stock_info: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
