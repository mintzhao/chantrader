"""
Chan.py Web Backend - 核心配置
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    APP_NAME: str = "Chan.py Web API"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # 数据路径
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    STOCK_LIST_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "App", "stock_list.csv"
    )

    # 缓存配置
    CACHE_TTL: int = 30  # 缓存有效期（秒）

    # 缠论默认配置
    DEFAULT_CHAN_CONFIG: dict = {
        "bi_strict": True,
        "trigger_step": False,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": "1,1p,2,2s,3a,3b",
        "print_warning": False,
        "zs_algo": "normal",
    }

    class Config:
        env_file = ".env"


settings = Settings()
