"""
股票历史记录管理模块

功能：
    - 记录用户分析过的股票代码
    - 持久化存储到本地 JSON 文件
    - 支持最近访问排序
    - 支持最大记录数限制
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def get_history_file_path() -> Path:
    """
    获取历史记录文件路径
    - 普通运行：存储在 App 目录下
    - PyInstaller 打包：存储在用户目录下
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，存储在用户目录
        if os.name == 'nt':  # Windows
            base_dir = Path(os.environ.get('APPDATA', Path.home())) / 'ChanTrader'
        else:  # Linux/Mac
            base_dir = Path.home() / '.chantrader'
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / 'stock_history.json'
    else:
        # 普通 Python 运行，存储在 App 目录
        return Path(__file__).parent / 'stock_history.json'


class StockHistory:
    """股票历史记录管理器"""

    MAX_HISTORY = 50  # 最大保存记录数

    def __init__(self):
        self.history_file = get_history_file_path()
        self._history: List[Dict] = []
        self._load()

    def _load(self):
        """从文件加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = data.get('history', [])
            except Exception as e:
                print(f"加载历史记录失败: {e}")
                self._history = []

    def _save(self):
        """保存历史记录到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({'history': self._history}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def add(self, code: str, name: str):
        """
        添加股票到历史记录
        - 如果已存在，更新访问时间并移到最前
        - 如果不存在，添加到最前
        """
        # 标准化代码格式
        code = code.strip()
        name = name.strip()

        if not code:
            return

        # 查找是否已存在
        existing_idx = None
        for i, item in enumerate(self._history):
            if item.get('code') == code:
                existing_idx = i
                break

        # 构建新记录
        record = {
            'code': code,
            'name': name,
            'last_access': datetime.now().isoformat()
        }

        if existing_idx is not None:
            # 已存在，移到最前
            self._history.pop(existing_idx)

        # 添加到最前
        self._history.insert(0, record)

        # 限制最大数量
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[:self.MAX_HISTORY]

        # 保存
        self._save()

    def get_all(self) -> List[Dict]:
        """获取所有历史记录"""
        return self._history.copy()

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """获取最近的 N 条记录"""
        return self._history[:limit]

    def remove(self, code: str):
        """删除指定股票的历史记录"""
        self._history = [h for h in self._history if h.get('code') != code]
        self._save()

    def clear(self):
        """清空所有历史记录"""
        self._history = []
        self._save()

    def get_display_list(self, limit: int = 10) -> List[str]:
        """
        获取用于显示的格式化列表
        Returns: ["sz.000001  平安银行", ...]
        """
        result = []
        for item in self._history[:limit]:
            code = item.get('code', '')
            name = item.get('name', '')
            result.append(f"{code}  {name}")
        return result


# 全局单例
_stock_history: Optional[StockHistory] = None


def get_stock_history() -> StockHistory:
    """获取股票历史记录管理器单例"""
    global _stock_history
    if _stock_history is None:
        _stock_history = StockHistory()
    return _stock_history
