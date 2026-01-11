"""
系统配置 API
"""
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.models.schemas import SystemConfig, ChanConfig

router = APIRouter(prefix="/config", tags=["系统配置"])

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "system_config.json"


def ensure_data_dir():
    """确保数据目录存在"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> SystemConfig:
    """加载配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return SystemConfig(**data)
        except Exception as e:
            print(f"加载配置失败: {e}")
    return SystemConfig()


def save_config(config: SystemConfig):
    """保存配置"""
    ensure_data_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)


@router.get("", response_model=SystemConfig)
async def get_config():
    """
    获取系统配置
    """
    return load_config()


@router.put("", response_model=SystemConfig)
async def update_config(config: SystemConfig):
    """
    更新系统配置
    """
    try:
        save_config(config)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.get("/chan", response_model=ChanConfig)
async def get_chan_config():
    """
    获取缠论配置
    """
    config = load_config()
    return config.chan_config


@router.put("/chan", response_model=ChanConfig)
async def update_chan_config(chan_config: ChanConfig):
    """
    更新缠论配置
    """
    try:
        config = load_config()
        config.chan_config = chan_config
        save_config(config)
        return chan_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.post("/reset")
async def reset_config():
    """
    重置为默认配置
    """
    try:
        config = SystemConfig()
        save_config(config)
        return {"message": "配置已重置", "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")
