"""
缠论分析服务
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PlotMeta import CChanPlotMeta

from app.core.config import settings
from app.models.schemas import (
    KLineType,
    KLineUnit,
    BiInfo,
    SegInfo,
    ZSInfo,
    BSPInfo,
    MACDInfo,
    ChanAnalysisResult,
    MultiLevelResult,
    ChanConfig,
)
from app.services.stock_service import StockService


# K线类型映射
KL_TYPE_MAP = {
    KLineType.K_1M: KL_TYPE.K_1M,
    KLineType.K_5M: KL_TYPE.K_5M,
    KLineType.K_15M: KL_TYPE.K_15M,
    KLineType.K_30M: KL_TYPE.K_30M,
    KLineType.K_60M: KL_TYPE.K_60M,
    KLineType.K_DAY: KL_TYPE.K_DAY,
    KLineType.K_WEEK: KL_TYPE.K_WEEK,
    KLineType.K_MON: KL_TYPE.K_MON,
}

# 分钟级别使用 AkShare
AKSHARE_KL_TYPES = {
    KL_TYPE.K_1M,
    KL_TYPE.K_5M,
    KL_TYPE.K_15M,
    KL_TYPE.K_30M,
    KL_TYPE.K_60M,
}


class ChanAnalysisService:
    """缠论分析服务"""

    @staticmethod
    def get_chan_config(config: Optional[ChanConfig] = None) -> CChanConfig:
        """获取缠论配置"""
        if config is None:
            return CChanConfig(settings.DEFAULT_CHAN_CONFIG)

        return CChanConfig(
            {
                "bi_strict": config.bi_strict,
                "trigger_step": config.trigger_step,
                "divergence_rate": config.divergence_rate,
                "bsp2_follow_1": config.bsp2_follow_1,
                "bsp3_follow_1": config.bsp3_follow_1,
                "min_zs_cnt": config.min_zs_cnt,
                "bs1_peak": config.bs1_peak,
                "macd_algo": config.macd_algo,
                "bs_type": config.bs_type,
                "print_warning": False,
                "zs_algo": config.zs_algo,
            }
        )

    @staticmethod
    def calc_days_from_periods(periods: int, kl_type: KL_TYPE) -> int:
        """根据周期数和K线类型计算需要的天数"""
        if kl_type == KL_TYPE.K_1M:
            return min(max(periods // 240 + 1, 1), 5)
        elif kl_type == KL_TYPE.K_5M:
            return max(periods // 48 + 5, 5)
        elif kl_type == KL_TYPE.K_15M:
            return max(periods // 16 + 5, 8)
        elif kl_type == KL_TYPE.K_30M:
            return max(periods // 8 + 5, 10)
        elif kl_type == KL_TYPE.K_60M:
            return max(periods // 4 + 5, 15)
        elif kl_type == KL_TYPE.K_DAY:
            return periods
        elif kl_type == KL_TYPE.K_WEEK:
            return periods * 7
        elif kl_type == KL_TYPE.K_MON:
            return periods * 30
        return periods

    @classmethod
    def analyze_single(
        cls,
        code: str,
        kl_type: KLineType,
        periods: int = 300,
        config: Optional[ChanConfig] = None,
    ) -> ChanAnalysisResult:
        """单级别分析"""
        kl_type_enum = KL_TYPE_MAP.get(kl_type, KL_TYPE.K_DAY)
        days = cls.calc_days_from_periods(periods, kl_type_enum)
        begin_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # 选择数据源
        if kl_type_enum in AKSHARE_KL_TYPES:
            data_src = DATA_SRC.AKSHARE
        else:
            data_src = DATA_SRC.BAO_STOCK

        # 创建 CChan 对象
        chan = CChan(
            code=code,
            begin_time=begin_time,
            end_time=None,
            data_src=data_src,
            lv_list=[kl_type_enum],
            config=cls.get_chan_config(config),
            autype=AUTYPE.QFQ,
        )

        # 使用 PlotMeta 提取数据
        return cls._extract_analysis_result(chan, code, kl_type.value)

    @classmethod
    def analyze_multi_level(
        cls,
        code: str,
        levels: List[KLineType],
        periods: int = 300,
        config: Optional[ChanConfig] = None,
    ) -> MultiLevelResult:
        """多级别分析"""
        results = {}

        for kl_type in levels:
            try:
                result = cls.analyze_single(code, kl_type, periods, config)
                results[kl_type.value] = result
            except Exception as e:
                print(f"分析 {kl_type.value} 失败: {e}")
                continue

        stock_name = StockService.get_stock_name(code)
        return MultiLevelResult(code=code, name=stock_name, levels=results)

    @classmethod
    def _extract_analysis_result(
        cls, chan: CChan, code: str, kl_type_name: str
    ) -> ChanAnalysisResult:
        """从 CChan 对象提取分析结果"""
        kl_data = chan[0]
        meta = CChanPlotMeta(kl_data)

        # 提取 K线数据
        klines = []
        for klu in meta.klu_iter():
            klines.append(
                KLineUnit(
                    idx=klu.idx,
                    time=str(klu.time),
                    open=klu.open,
                    high=klu.high,
                    low=klu.low,
                    close=klu.close,
                    volume=getattr(klu, "volume", 0),
                )
            )

        # 提取笔数据
        bi_list = []
        for bi in meta.bi_list:
            bi_list.append(
                BiInfo(
                    idx=bi.idx,
                    begin_idx=bi.begin_x,
                    end_idx=bi.end_x,
                    begin_x=bi.begin_x,
                    end_x=bi.end_x,
                    begin_y=bi.begin_y,
                    end_y=bi.end_y,
                    is_sure=bi.is_sure,
                    direction="up" if bi.begin_y < bi.end_y else "down",
                )
            )

        # 提取线段数据
        seg_list = []
        for seg in meta.seg_list:
            seg_list.append(
                SegInfo(
                    idx=seg.idx,
                    begin_idx=seg.begin_x,
                    end_idx=seg.end_x,
                    begin_x=seg.begin_x,
                    end_x=seg.end_x,
                    begin_y=seg.begin_y,
                    end_y=seg.end_y,
                    is_sure=seg.is_sure,
                    direction="up" if seg.begin_y < seg.end_y else "down",
                )
            )

        # 提取中枢数据
        zs_list = []
        for zs in meta.zs_lst:
            zs_list.append(
                ZSInfo(
                    idx=zs.idx,
                    begin=zs.begin,
                    end=zs.begin + zs.w,
                    low=zs.low,
                    high=zs.low + zs.h,
                    is_sure=zs.is_sure,
                )
            )

        # 提取买卖点数据
        bsp_list = []
        for bsp in meta.bs_point_lst:
            bsp_list.append(
                BSPInfo(
                    idx=bsp.idx,
                    x=bsp.x,
                    y=bsp.y,
                    is_buy=bsp.is_buy,
                    type=bsp.desc(),
                    is_sure=bsp.is_sure,
                )
            )

        # 提取 MACD 数据
        macd_list = []
        for klu in meta.klu_iter():
            if klu.macd is not None:
                macd_list.append(
                    MACDInfo(
                        idx=klu.idx,
                        dif=klu.macd.DIF,
                        dea=klu.macd.DEA,
                        macd=klu.macd.macd,
                    )
                )

        stock_name = StockService.get_stock_name(code)

        return ChanAnalysisResult(
            code=code,
            name=stock_name,
            kl_type=kl_type_name,
            klines=klines,
            bi_list=bi_list,
            seg_list=seg_list,
            zs_list=zs_list,
            bsp_list=bsp_list,
            macd_list=macd_list,
            dateticks=meta.datetick,
        )
