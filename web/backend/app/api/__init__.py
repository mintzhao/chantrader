"""
API module
"""
from fastapi import APIRouter

from .stocks import router as stocks_router
from .analysis import router as analysis_router
from .config import router as config_router
from .scanner import router as scanner_router

api_router = APIRouter()

api_router.include_router(stocks_router)
api_router.include_router(analysis_router)
api_router.include_router(config_router)
api_router.include_router(scanner_router)

__all__ = ["api_router"]
