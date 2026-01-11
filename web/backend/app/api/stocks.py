"""
股票相关 API
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List

from app.models.schemas import StockInfo, RealtimeData
from app.services.stock_service import StockService, RealtimeService

router = APIRouter(prefix="/stocks", tags=["股票"])


@router.get("/search", response_model=List[StockInfo])
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
):
    """
    搜索股票

    支持按代码或名称模糊搜索
    """
    results = StockService.search_stocks(q, limit)
    return results


@router.get("/realtime/{code}", response_model=RealtimeData)
async def get_realtime_data(code: str):
    """
    获取实时行情数据

    - code: 股票代码，如 sz.000001 或 000001
    """
    data = RealtimeService.get_realtime_data(code)
    if data is None:
        raise HTTPException(status_code=404, detail="获取实时数据失败")
    return data


@router.get("/list", response_model=List[StockInfo])
async def get_stock_list(
    limit: int = Query(default=100, ge=1, le=5000, description="返回数量限制"),
):
    """
    获取股票列表
    """
    stock_list = StockService.load_stock_list()
    return [
        StockInfo(code=code, name=name)
        for code, name in stock_list[:limit]
    ]
