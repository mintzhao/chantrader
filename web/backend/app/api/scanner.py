"""
批量扫描 WebSocket API
"""
import asyncio
import json
from typing import Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import pandas as pd

from app.models.schemas import KLineType, ScannerProgress
from app.services.chan_service import ChanAnalysisService

router = APIRouter(prefix="/scanner", tags=["批量扫描"])


async def get_tradable_stocks() -> pd.DataFrame:
    """获取可交易股票列表"""
    import akshare as ak

    try:
        df = ak.stock_zh_a_spot_em()

        # 过滤条件
        df = df[~df["名称"].str.contains("ST", case=False, na=False)]
        df = df[~df["代码"].str.startswith("688")]  # 科创板
        df = df[~df["代码"].str.startswith("8")]  # 北交所
        df = df[~df["代码"].str.startswith("43")]
        df = df[~df["代码"].str.startswith("200")]  # B股
        df = df[~df["代码"].str.startswith("900")]
        df = df[~df["代码"].str.startswith("920")]  # CDR
        df = df[df["成交量"] > 0]  # 剔除停牌
        df = df[df["最新价"] > 0]

        return df[["代码", "名称", "最新价", "涨跌幅"]].reset_index(drop=True)
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return pd.DataFrame()


@router.websocket("/ws")
async def scanner_websocket(websocket: WebSocket):
    """
    批量扫描 WebSocket

    客户端发送:
        { "action": "start", "config": {...} }
        { "action": "stop" }

    服务端响应:
        { "type": "progress", "current": 100, "total": 5000, "stock_info": "..." }
        { "type": "found", "data": {...} }
        { "type": "finished", "data": {"success": 4800, "failed": 200} }
    """
    await websocket.accept()
    is_scanning = False

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")

            if action == "start" and not is_scanning:
                is_scanning = True
                config = message.get("config", {})

                # 发送状态
                await websocket.send_json(
                    {"type": "status", "message": "正在获取股票列表..."}
                )

                # 获取股票列表
                stock_list = await get_tradable_stocks()
                if stock_list.empty:
                    await websocket.send_json(
                        {"type": "error", "message": "获取股票列表失败"}
                    )
                    is_scanning = False
                    continue

                total = len(stock_list)
                await websocket.send_json(
                    {"type": "status", "message": f"开始扫描 {total} 只股票"}
                )

                success_count = 0
                fail_count = 0
                found_count = 0

                for idx, row in stock_list.iterrows():
                    if not is_scanning:
                        break

                    code = row["代码"]
                    name = row["名称"]

                    # 发送进度
                    await websocket.send_json(
                        {
                            "type": "progress",
                            "current": idx + 1,
                            "total": total,
                            "stock_info": f"{code} {name}",
                        }
                    )

                    try:
                        # 分析股票
                        result = ChanAnalysisService.analyze_single(
                            code=code,
                            kl_type=KLineType.K_DAY,
                            periods=365,
                        )

                        # 检查最近3天内是否有买点
                        cutoff_idx = len(result.klines) - 3
                        recent_buy_points = [
                            bsp
                            for bsp in result.bsp_list
                            if bsp.is_buy and bsp.x >= cutoff_idx
                        ]

                        if recent_buy_points:
                            latest_bsp = recent_buy_points[-1]
                            found_count += 1
                            await websocket.send_json(
                                {
                                    "type": "found",
                                    "data": {
                                        "code": code,
                                        "name": name,
                                        "price": float(row["最新价"]),
                                        "change_pct": float(row["涨跌幅"]),
                                        "bsp_type": latest_bsp.type,
                                        "bsp_idx": latest_bsp.idx,
                                    },
                                }
                            )

                        success_count += 1

                    except Exception as e:
                        fail_count += 1
                        print(f"扫描 {code} 失败: {e}")

                    # 适当延时，避免请求过快
                    await asyncio.sleep(0.1)

                # 扫描完成
                await websocket.send_json(
                    {
                        "type": "finished",
                        "data": {
                            "success": success_count,
                            "failed": fail_count,
                            "found": found_count,
                        },
                    }
                )
                is_scanning = False

            elif action == "stop":
                is_scanning = False
                await websocket.send_json(
                    {"type": "stopped", "message": "扫描已停止"}
                )

    except WebSocketDisconnect:
        print("WebSocket 连接断开")
    except Exception as e:
        print(f"WebSocket 错误: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
