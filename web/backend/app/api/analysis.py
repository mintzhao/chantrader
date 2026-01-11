"""
缠论分析 API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from app.models.schemas import (
    KLineType,
    SingleAnalysisRequest,
    MultiLevelRequest,
    ChanAnalysisResult,
    MultiLevelResult,
    ChanConfig,
)
from app.services.chan_service import ChanAnalysisService

router = APIRouter(prefix="/analysis", tags=["缠论分析"])


@router.post("/single", response_model=ChanAnalysisResult)
async def analyze_single(request: SingleAnalysisRequest):
    """
    单级别缠论分析

    返回 K线、笔、线段、中枢、买卖点、MACD 等数据
    """
    try:
        result = ChanAnalysisService.analyze_single(
            code=request.code,
            kl_type=request.kl_type,
            periods=request.periods,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/multilevel", response_model=MultiLevelResult)
async def analyze_multilevel(request: MultiLevelRequest):
    """
    多级别缠论分析（区间套）

    同时分析多个级别，用于区间套买卖点定位
    """
    try:
        result = ChanAnalysisService.analyze_multi_level(
            code=request.code,
            levels=request.levels,
            periods=request.periods,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/kl-types")
async def get_kl_types():
    """
    获取支持的 K线类型列表
    """
    return [
        {"value": kt.value, "label": kt.value}
        for kt in KLineType
    ]


@router.get("/preset-levels")
async def get_preset_levels():
    """
    获取预设的级别组合
    """
    return [
        {
            "name": "日线 + 60分钟",
            "levels": [KLineType.K_DAY.value, KLineType.K_60M.value],
        },
        {
            "name": "日线 + 60分钟 + 15分钟",
            "levels": [
                KLineType.K_DAY.value,
                KLineType.K_60M.value,
                KLineType.K_15M.value,
            ],
        },
        {
            "name": "日线 + 30分钟 + 5分钟",
            "levels": [
                KLineType.K_DAY.value,
                KLineType.K_30M.value,
                KLineType.K_5M.value,
            ],
        },
        {
            "name": "周线 + 日线",
            "levels": [KLineType.K_WEEK.value, KLineType.K_DAY.value],
        },
        {
            "name": "周线 + 日线 + 60分钟",
            "levels": [
                KLineType.K_WEEK.value,
                KLineType.K_DAY.value,
                KLineType.K_60M.value,
            ],
        },
        {
            "name": "60分钟 + 15分钟 + 5分钟",
            "levels": [
                KLineType.K_60M.value,
                KLineType.K_15M.value,
                KLineType.K_5M.value,
            ],
        },
    ]
