"""
A股买点扫描器 - Powered by chan.py (tkinter版本)

功能说明:
    - 批量扫描A股市场，自动识别近期出现买点的股票
    - 支持单只股票的技术分析和图表展示
    - 可视化显示K线、笔、线段、中枢、买卖点、MACD等
    - 支持多级别区间套共振确认
    - 买卖点风险系数评级

数据来源:
    - 使用 akshare 获取A股实时行情和历史K线数据

过滤规则:
    - 可配置股票范围（主板/创业板/科创板/北交所）
    - 剔除ST股票、B股
    - 剔除停牌股票和新股
    - 支持价格区间过滤

依赖:
    - tkinter: GUI框架
    - matplotlib: 图表绑定
    - akshare: A股数据接口
    - chan.py: 技术分析核心库

使用方法:
    python App/ashare_bsp_scanner_tk.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# 将项目根目录加入路径（兼容 PyInstaller 打包）
def _setup_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = str(Path(__file__).resolve().parent.parent)
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
_setup_path()

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import akshare as ak
import pandas as pd

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE


# 买卖点风险系数（5星制，星越多风险越低/确定性越高）
BSP_RISK_RATING = {
    "1": 5,    # 一类买卖点 - 趋势背驰，最可靠
    "1p": 4,   # 盘整一类 - 盘整背驰，较可靠
    "2": 4,    # 二类买卖点 - 回调不破，较可靠
    "2s": 3,   # 类二买卖点 - 类似二类，一般
    "3a": 3,   # 三类买卖点(中枢后) - 中枢突破，一般
    "3b": 2,   # 三类买卖点(中枢前) - 中枢进入，风险较高
}

# 风险系数说明
BSP_RISK_DESC = {
    "1": "趋势背驰，最经典可靠的买卖点",
    "1p": "盘整背驰，盘整走势结束信号",
    "2": "回调/反弹不破前低/高，确认趋势延续",
    "2s": "类二买卖点，类似二类但条件略宽松",
    "3a": "中枢之后的买卖机会，需确认突破有效",
    "3b": "中枢之前的买卖机会，风险相对较高",
}


# 筛选逻辑说明文档
FILTER_LOGIC_DOC = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         A股买点扫描器 - 筛选逻辑说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【第一层：股票池过滤】
━━━━━━━━━━━━━━━━━━━
可配置的股票范围：

  ☑ 主板(60/00)  - 沪深主板，流动性最好
  ☐ 创业板(300)  - 创业板，成长性高但波动大
  ☐ 科创板(688)  - 科创板，门槛高波动大
  ☐ 北交所(8/43) - 北交所，流动性较差

固定剔除：
  ✗ ST股票      - 名称包含ST，有退市风险
  ✗ B股(200/900)- 外币计价，普通投资者难参与
  ✗ CDR(920)    - 存托凭证，交易规则特殊
  ✗ 停牌股票    - 成交量为0，无法交易
  ✗ 异常股票    - 最新价<=0，数据异常

【第二层：价格区间过滤】
━━━━━━━━━━━━━━━━━━━━━━
可配置股价范围，例如：
  • 最低价: 5元 （过滤低价股）
  • 最高价: 100元（过滤高价股）

【第三层：技术分析】
━━━━━━━━━━━━━━━━━━
使用chan.py进行技术分析计算：

  • 数据周期: 日线级别 (K_DAY)
  • K线数据: 获取往前N天的历史数据
  • 复权方式: 前复权 (QFQ)

  计算内容:
  ├─ 笔 (Bi)      - K线合并后的上下走势
  ├─ 线段 (Seg)   - 笔的更高级别走势
  ├─ 中枢 (ZS)    - 走势的震荡区间
  └─ 买卖点 (BSP) - 基于背驰的交易信号

【第四层：买点筛选】
━━━━━━━━━━━━━━━━━━
从技术分析结果中筛选有效买点：

  条件1: bsp.is_buy = True
         → 只筛选买点，不要卖点

  条件2: 买点时间 >= (今天 - N天)
         → 只要近期出现的买点

【买卖点风险系数】★★★★★
━━━━━━━━━━━━━━━━━━━━━━
  类型  评级  说明
  ────────────────────────────────
  1    ★★★★★  趋势背驰，最经典可靠
  1p   ★★★★☆  盘整背驰，盘整结束信号
  2    ★★★★☆  回调不破，趋势延续确认
  2s   ★★★☆☆  类二买卖，条件略宽松
  3a   ★★★☆☆  中枢后买卖，需确认突破
  3b   ★★☆☆☆  中枢前买卖，风险较高

【区间套共振加成】
━━━━━━━━━━━━━━━━━━
勾选"区间套共振"后，使用三级别联合分析：

  级别组合: 日线 + 30分钟 + 5分钟

  • 日线买点:   近N天内出现
  • 30分钟买点: 近5天内出现
  • 5分钟买点:  近3天内出现

共振加成规则：
  • 仅日线买点:     基础评级
  • 日线+30分共振:  评级+1星
  • 三级别共振:     评级+2星（最高5星）

注意：开启区间套会增加扫描时间（约3倍）

【参数说明】
━━━━━━━━━━━━
  • 近N天买点: 筛选最近N天内出现的买点
  • K线数据:   获取往前N天的历史K线
  • 笔严格模式: 开启后对笔的划分更严格
  • 价格区间:  过滤指定价格范围的股票

【设计思想】
━━━━━━━━━━━━
本扫描器的核心思想是：

  用技术分析理论在全市场范围内
  自动发现近期出现买入机会的股票
  并通过风险评级帮助投资者筛选

注意：技术分析仅供参考，不构成投资建议。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def get_tradable_stocks(include_main: bool = True,
                        include_gem: bool = False,
                        include_star: bool = False,
                        include_bse: bool = False,
                        min_price: float = 0,
                        max_price: float = float('inf')) -> pd.DataFrame:
    """
    获取可交易的A股股票列表

    Args:
        include_main: 包含主板 (60/00开头)
        include_gem: 包含创业板 (300开头)
        include_star: 包含科创板 (688开头)
        include_bse: 包含北交所 (8/43开头)
        min_price: 最低价格
        max_price: 最高价格

    Returns:
        pd.DataFrame: 包含 ['代码', '名称', '最新价', '涨跌幅'] 列的股票列表
    """
    try:
        # 获取A股实时行情
        df = ak.stock_zh_a_spot_em()

        # 1. 剔除ST股票（名称包含ST）
        df = df[~df['名称'].str.contains('ST', case=False, na=False)]

        # 2. 剔除B股（200开头深圳B股，900开头上海B股）
        df = df[~df['代码'].str.startswith('200')]
        df = df[~df['代码'].str.startswith('900')]

        # 3. 剔除存托凭证CDR（920开头）
        df = df[~df['代码'].str.startswith('920')]

        # 4. 剔除停牌股票（成交量为0）
        df = df[df['成交量'] > 0]

        # 5. 剔除异常股票（最新价<=0）
        df = df[df['最新价'] > 0]

        # 6. 根据配置过滤板块
        conditions = []

        if include_main:
            # 主板：沪市60开头，深市00开头（排除创业板300）
            conditions.append(df['代码'].str.startswith('60'))
            conditions.append(df['代码'].str.startswith('00') & ~df['代码'].str.startswith('003'))

        if include_gem:
            # 创业板：300开头
            conditions.append(df['代码'].str.startswith('300') | df['代码'].str.startswith('301'))

        if include_star:
            # 科创板：688开头
            conditions.append(df['代码'].str.startswith('688'))

        if include_bse:
            # 北交所：8开头、43开头
            conditions.append(df['代码'].str.startswith('8'))
            conditions.append(df['代码'].str.startswith('43'))

        if conditions:
            combined_condition = conditions[0]
            for cond in conditions[1:]:
                combined_condition = combined_condition | cond
            df = df[combined_condition]

        # 7. 价格区间过滤
        df = df[(df['最新价'] >= min_price) & (df['最新价'] <= max_price)]

        return df[['代码', '名称', '最新价', '涨跌幅']].reset_index(drop=True)
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return pd.DataFrame()


def get_bsp_risk_rating(bsp_type: str) -> int:
    """获取买卖点风险系数（1-5星）"""
    # 提取基础类型（去掉前缀b/s）
    base_type = bsp_type.lower().replace('b', '').replace('s', '')
    return BSP_RISK_RATING.get(base_type, 3)


def get_risk_stars(rating: int) -> str:
    """将评级转换为星星显示"""
    return "★" * rating + "☆" * (5 - rating)


class BspScannerWindow(tk.Toplevel):
    """
    A股买点扫描器窗口
    """

    window_count = 0
    instances: List['BspScannerWindow'] = []

    def __init__(self, master=None):
        super().__init__(master)

        BspScannerWindow.window_count += 1
        BspScannerWindow.instances.append(self)

        self.chan: Optional[CChan] = None
        self.scan_thread: Optional[threading.Thread] = None
        self.analysis_thread: Optional[threading.Thread] = None
        self.stock_cache: Dict[str, CChan] = {}
        self.stock_data: List[Dict] = []  # 存储完整的股票数据用于排序
        self.is_scanning = False
        self.is_analyzing = False
        self.scan_queue = queue.Queue()

        # 排序状态
        self.sort_column = None
        self.sort_reverse = False

        self.init_ui()

        # 启动队列轮询
        self._poll_scan_queue()

        offset = (BspScannerWindow.window_count - 1) * 30
        self.geometry(f"1600x950+{100 + offset}+{50 + offset}")
        self.minsize(1200, 750)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def init_ui(self):
        """初始化用户界面"""
        self.title(f'A股买点扫描器 #{BspScannerWindow.window_count}')

        # 配置 grid 权重
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # === 顶部控制栏 ===
        control_frame = ttk.Frame(self, padding="5")
        control_frame.grid(row=0, column=0, sticky="ew")

        # 扫描控制区
        scan_group = ttk.LabelFrame(control_frame, text="扫描控制", padding="5")
        scan_group.pack(side=tk.LEFT, padx=(0, 10))

        self.bi_strict_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(scan_group, text="笔严格模式",
                       variable=self.bi_strict_var).pack(side=tk.LEFT, padx=5)

        self.nesting_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(scan_group, text="区间套共振",
                       variable=self.nesting_var).pack(side=tk.LEFT, padx=5)

        self.scan_btn = ttk.Button(scan_group, text="开始扫描", command=self.toggle_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        # 股票范围配置区
        range_group = ttk.LabelFrame(control_frame, text="股票范围", padding="5")
        range_group.pack(side=tk.LEFT, padx=(0, 10))

        self.include_main_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(range_group, text="主板",
                       variable=self.include_main_var).pack(side=tk.LEFT, padx=2)

        self.include_gem_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(range_group, text="创业板",
                       variable=self.include_gem_var).pack(side=tk.LEFT, padx=2)

        self.include_star_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(range_group, text="科创板",
                       variable=self.include_star_var).pack(side=tk.LEFT, padx=2)

        self.include_bse_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(range_group, text="北交所",
                       variable=self.include_bse_var).pack(side=tk.LEFT, padx=2)

        # 筛选参数区
        filter_group = ttk.LabelFrame(control_frame, text="筛选参数", padding="5")
        filter_group.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(filter_group, text="近N天买点:").pack(side=tk.LEFT, padx=(0, 2))
        self.bsp_days_var = tk.IntVar(value=3)
        ttk.Spinbox(filter_group, from_=1, to=30,
                   textvariable=self.bsp_days_var, width=4).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(filter_group, text="K线数据:").pack(side=tk.LEFT, padx=(0, 2))
        self.history_days_var = tk.IntVar(value=365)
        ttk.Spinbox(filter_group, from_=60, to=730,
                   textvariable=self.history_days_var, width=4).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Label(filter_group, text="天").pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(filter_group, text="并行数:").pack(side=tk.LEFT, padx=(0, 2))
        self.workers_var = tk.IntVar(value=4)
        ttk.Spinbox(filter_group, from_=1, to=16,
                   textvariable=self.workers_var, width=3).pack(side=tk.LEFT, padx=(0, 5))

        # 价格区间
        price_group = ttk.LabelFrame(control_frame, text="价格区间", padding="5")
        price_group.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(price_group, text="最低:").pack(side=tk.LEFT, padx=(0, 2))
        self.min_price_var = tk.DoubleVar(value=0)
        ttk.Spinbox(price_group, from_=0, to=9999,
                   textvariable=self.min_price_var, width=5).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(price_group, text="最高:").pack(side=tk.LEFT, padx=(0, 2))
        self.max_price_var = tk.DoubleVar(value=9999)
        ttk.Spinbox(price_group, from_=0, to=9999,
                   textvariable=self.max_price_var, width=5).pack(side=tk.LEFT, padx=(0, 5))

        # 单股分析区
        single_group = ttk.LabelFrame(control_frame, text="单只股票分析", padding="5")
        single_group.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(single_group, text="代码:").pack(side=tk.LEFT, padx=(0, 5))
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(single_group, textvariable=self.code_var, width=10)
        self.code_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.code_entry.insert(0, "000001")
        self.code_entry.bind('<Return>', lambda e: self.analyze_single())

        self.analyze_btn = ttk.Button(single_group, text="分析", command=self.analyze_single)
        self.analyze_btn.pack(side=tk.LEFT, padx=5)

        # === 主内容区域 ===
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # 左侧面板
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # 左侧使用 Notebook 组织
        left_notebook = ttk.Notebook(left_frame)
        left_notebook.pack(fill=tk.BOTH, expand=True)

        # === 标签页1: 扫描结果 ===
        scan_tab = ttk.Frame(left_notebook, padding="5")
        left_notebook.add(scan_tab, text="扫描结果")

        scan_paned = ttk.PanedWindow(scan_tab, orient=tk.VERTICAL)
        scan_paned.pack(fill=tk.BOTH, expand=True)

        # 进度和股票列表
        list_frame = ttk.LabelFrame(scan_paned, text="买点股票列表（点击表头排序）", padding="5")
        scan_paned.add(list_frame, weight=3)

        # 进度条
        progress_frame = ttk.Frame(list_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 5))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 5))

        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack(side=tk.LEFT)

        # 使用Frame包装Treeview和滚动条
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # 股票列表 - 增加风险系数列和共振列
        columns = ('code', 'name', 'price', 'change', 'risk', 'resonance', 'bsp')
        self.stock_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        self.stock_tree.heading('code', text='代码', command=lambda: self.sort_by_column('code'))
        self.stock_tree.heading('name', text='名称', command=lambda: self.sort_by_column('name'))
        self.stock_tree.heading('price', text='现价', command=lambda: self.sort_by_column('price'))
        self.stock_tree.heading('change', text='涨跌%', command=lambda: self.sort_by_column('change'))
        self.stock_tree.heading('risk', text='风险系数', command=lambda: self.sort_by_column('risk'))
        self.stock_tree.heading('resonance', text='共振', command=lambda: self.sort_by_column('resonance'))
        self.stock_tree.heading('bsp', text='买点类型')

        self.stock_tree.column('code', width=70, anchor='center')
        self.stock_tree.column('name', width=80, anchor='center')
        self.stock_tree.column('price', width=60, anchor='e')
        self.stock_tree.column('change', width=60, anchor='e')
        self.stock_tree.column('risk', width=80, anchor='center')
        self.stock_tree.column('resonance', width=90, anchor='center')
        self.stock_tree.column('bsp', width=80, anchor='center')

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=tree_scroll.set)

        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.stock_tree.bind('<<TreeviewSelect>>', self.on_stock_selected)

        # 按钮区 - 放在列表下方
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="导出TXT", command=self.export_to_txt).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="清空列表", command=self.clear_stock_list).pack(side=tk.LEFT, padx=(5, 0))

        # 日志区域
        log_frame = ttk.LabelFrame(scan_paned, text="扫描日志", padding="5")
        scan_paned.add(log_frame, weight=1)

        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, height=8, font=("Consolas", 9),
                                bg="#1e1e1e", fg="#d4d4d4", wrap=tk.WORD,
                                yscrollcommand=log_scroll.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

        self.log_text.tag_configure("info", foreground="#4fc3f7")
        self.log_text.tag_configure("success", foreground="#66bb6a")
        self.log_text.tag_configure("warning", foreground="#ffca28")
        self.log_text.tag_configure("error", foreground="#ef5350")
        self.log_text.tag_configure("skip", foreground="#9e9e9e")

        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(log_btn_frame, text="清空日志", command=lambda: self.log_text.delete(1.0, tk.END)).pack(side=tk.LEFT)

        # === 标签页2: 筛选逻辑说明 ===
        doc_tab = ttk.Frame(left_notebook, padding="5")
        left_notebook.add(doc_tab, text="筛选逻辑说明")

        doc_scroll = ttk.Scrollbar(doc_tab)
        doc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.doc_text = tk.Text(doc_tab, font=("Consolas", 10),
                                 bg="#2d2d2d", fg="#e0e0e0", wrap=tk.WORD,
                                 yscrollcommand=doc_scroll.set, padx=10, pady=10)
        self.doc_text.pack(fill=tk.BOTH, expand=True)
        doc_scroll.config(command=self.doc_text.yview)

        self.doc_text.insert(tk.END, FILTER_LOGIC_DOC)
        self.doc_text.config(state=tk.DISABLED)

        # 右侧面板 - 使用 Notebook
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)

        right_notebook = ttk.Notebook(right_frame)
        right_notebook.pack(fill=tk.BOTH, expand=True)

        # K线图表标签页
        chart_tab = ttk.Frame(right_notebook, padding="5")
        right_notebook.add(chart_tab, text="K线图表")

        # 图表显示选项
        plot_options = ttk.Frame(chart_tab)
        plot_options.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(plot_options, text="显示:").pack(side=tk.LEFT)

        self.plot_kline_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options, text="K线", variable=self.plot_kline_var).pack(side=tk.LEFT, padx=2)

        self.plot_bi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options, text="笔", variable=self.plot_bi_var).pack(side=tk.LEFT, padx=2)

        self.plot_seg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options, text="线段", variable=self.plot_seg_var).pack(side=tk.LEFT, padx=2)

        self.plot_zs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options, text="中枢", variable=self.plot_zs_var).pack(side=tk.LEFT, padx=2)

        self.plot_bsp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options, text="买卖点", variable=self.plot_bsp_var).pack(side=tk.LEFT, padx=2)

        self.plot_macd_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options, text="MACD", variable=self.plot_macd_var).pack(side=tk.LEFT, padx=2)

        ttk.Button(plot_options, text="刷新图表", command=self.refresh_chart).pack(side=tk.LEFT, padx=(10, 0))

        # 分隔线
        ttk.Separator(plot_options, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # 快捷分析入口
        ttk.Button(plot_options, text="单级别分析", command=self.open_single_level_viewer).pack(side=tk.LEFT, padx=2)
        ttk.Button(plot_options, text="多级别分析", command=self.open_multi_level_viewer).pack(side=tk.LEFT, padx=2)

        # matplotlib 画布
        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(chart_tab)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        # === 状态栏 ===
        status_frame = ttk.Frame(self)
        status_frame.grid(row=2, column=0, sticky="ew")

        self.status_var = tk.StringVar(value='就绪 - 点击"开始扫描"分析所有股票')
        self.status_bar = ttk.Label(status_frame, textvariable=self.status_var,
                                    relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X)

    def sort_by_column(self, column: str):
        """按列排序"""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        # 根据列类型选择排序键
        if column == 'price':
            self.stock_data.sort(key=lambda x: x['price'], reverse=self.sort_reverse)
        elif column == 'change':
            self.stock_data.sort(key=lambda x: x['change'], reverse=self.sort_reverse)
        elif column == 'risk':
            self.stock_data.sort(key=lambda x: x['risk_rating'], reverse=self.sort_reverse)
        elif column == 'resonance':
            self.stock_data.sort(key=lambda x: x['resonance_count'], reverse=self.sort_reverse)
        elif column == 'code':
            self.stock_data.sort(key=lambda x: x['code'], reverse=self.sort_reverse)
        elif column == 'name':
            self.stock_data.sort(key=lambda x: x['name'], reverse=self.sort_reverse)

        # 刷新表格
        self._refresh_stock_tree()

    def _refresh_stock_tree(self):
        """刷新股票列表显示"""
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)

        for data in self.stock_data:
            # 共振显示：有共振显示级别，无共振显示"-"
            resonance_display = data.get('resonance_str', '-') if data.get('resonance_count', 1) >= 2 else '-'
            self.stock_tree.insert('', tk.END, values=(
                data['code'],
                data['name'],
                f"{data['price']:.2f}",
                f"{data['change']:+.2f}%",
                get_risk_stars(data['risk_rating']),
                resonance_display,
                data['bsp_type'].split('(')[0]  # 只显示买点类型，不含共振信息
            ))

    def export_to_txt(self):
        """导出股票列表到TXT文件"""
        if not self.stock_data:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"买点股票_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"A股买点扫描结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")

                f.write(f"{'代码':<10}{'名称':<12}{'现价':<10}{'涨跌%':<10}{'风险系数':<12}{'买点类型'}\n")
                f.write("-" * 70 + "\n")

                for data in self.stock_data:
                    f.write(f"{data['code']:<10}"
                           f"{data['name']:<12}"
                           f"{data['price']:<10.2f}"
                           f"{data['change']:+.2f}%".ljust(10) +
                           f"{get_risk_stars(data['risk_rating']):<12}"
                           f"{data['bsp_type']}\n")

                f.write("\n" + "-" * 70 + "\n")
                f.write(f"共 {len(self.stock_data)} 只股票\n")
                f.write("\n风险系数说明:\n")
                f.write("★★★★★ (5星) - 最可靠\n")
                f.write("★★★★☆ (4星) - 较可靠\n")
                f.write("★★★☆☆ (3星) - 一般\n")
                f.write("★★☆☆☆ (2星) - 风险较高\n")

            self.status_var.set(f'已导出到: {filename}')
            messagebox.showinfo("导出成功", f"已导出 {len(self.stock_data)} 只股票到:\n{filename}")

        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _poll_scan_queue(self):
        """轮询扫描结果队列"""
        try:
            # 每次最多处理50条消息，避免阻塞UI
            for _ in range(50):
                try:
                    msg_type, data = self.scan_queue.get_nowait()
                    if msg_type == 'log':
                        self._append_log(data['text'], data.get('tag', 'info'))
                    elif msg_type == 'progress':
                        self.progress_var.set(data['value'])
                        self.progress_label.config(text=data['text'])
                    elif msg_type == 'found':
                        self._add_stock_to_list(data)
                    elif msg_type == 'finished':
                        self._on_scan_finished(data['success'], data['fail'], data['found'])
                    elif msg_type == 'analysis_done':
                        self._on_analysis_done(data['chan'], data['code'])
                    elif msg_type == 'analysis_error':
                        self._on_analysis_error(data['error'])
                except queue.Empty:
                    break
            # 强制更新UI
            self.update_idletasks()
        except Exception:
            pass
        self.after(50, self._poll_scan_queue)  # 加快轮询频率

    def _append_log(self, text: str, tag: str = "info"):
        """追加日志"""
        self.log_text.insert(tk.END, f"{text}\n", tag)
        self.log_text.see(tk.END)

    def get_chan_config(self) -> CChanConfig:
        """获取技术分析配置"""
        return CChanConfig({
            "bi_strict": self.bi_strict_var.get(),
            "trigger_step": False,
            "skip_step": 0,
            "divergence_rate": float("inf"),
            "bsp2_follow_1": False,
            "bsp3_follow_1": False,
            "min_zs_cnt": 0,
            "bs1_peak": False,
            "macd_algo": "peak",
            "bs_type": "1,1p,2,2s,3a,3b",
            "print_warning": False,
            "zs_algo": "normal",
        })

    def get_plot_config(self) -> dict:
        """获取图表绑定配置"""
        return {
            "plot_kline": self.plot_kline_var.get(),
            "plot_kline_combine": True,
            "plot_bi": self.plot_bi_var.get(),
            "plot_seg": self.plot_seg_var.get(),
            "plot_zs": self.plot_zs_var.get(),
            "plot_macd": self.plot_macd_var.get(),
            "plot_bsp": self.plot_bsp_var.get(),
        }

    def toggle_scan(self):
        """切换扫描状态"""
        if self.is_scanning:
            self.stop_scan()
        else:
            self.start_scan()

    def start_scan(self):
        """开始批量扫描"""
        if self.is_scanning:
            return

        self.is_scanning = True
        self.scan_btn.config(text="停止扫描")
        self.stock_cache.clear()
        self.stock_data.clear()
        self.progress_var.set(0)

        # 清空表格
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)

        self.status_var.set('正在获取股票列表...')
        self.update()

        # 在主线程中获取所有 tkinter 变量的值，避免在后台线程中访问
        scan_params = {
            'bsp_days': self.bsp_days_var.get(),
            'history_days': self.history_days_var.get(),
            'min_price': self.min_price_var.get(),
            'max_price': self.max_price_var.get(),
            'use_nesting': self.nesting_var.get(),
            'max_workers': self.workers_var.get(),
            'include_main': self.include_main_var.get(),
            'include_gem': self.include_gem_var.get(),
            'include_star': self.include_star_var.get(),
            'include_bse': self.include_bse_var.get(),
            'config': self.get_chan_config(),
        }

        self.scan_thread = threading.Thread(target=self._scan_thread, args=(scan_params,), daemon=True)
        self.scan_thread.start()

    def stop_scan(self):
        """停止扫描"""
        self.is_scanning = False
        self.scan_btn.config(text="开始扫描")
        self.status_var.set('扫描已停止')

    def _analyze_single_stock(self, code: str, name: str, price: float, change: float,
                               bsp_days: int, history_days: int, use_nesting: bool,
                               config: CChanConfig) -> Optional[Dict]:
        """
        分析单只股票（用于并行处理）
        返回: 买点信息字典 或 None（无买点/失败）
        """
        if not self.is_scanning:
            return None

        try:
            begin_time = (datetime.now() - timedelta(days=history_days)).strftime("%Y-%m-%d")
            end_time = datetime.now().strftime("%Y-%m-%d")

            # 日线分析
            chan_day = CChan(
                code=code,
                begin_time=begin_time,
                end_time=end_time,
                data_src=DATA_SRC.AKSHARE,
                lv_list=[KL_TYPE.K_DAY],
                config=config,
                autype=AUTYPE.QFQ,
            )

            # 检查数据有效性
            if len(chan_day[0]) == 0:
                return {'status': 'skip', 'reason': '无K线数据'}

            # 检查日线买点
            bsp_list = chan_day.get_latest_bsp(number=0)
            cutoff_date = datetime.now() - timedelta(days=bsp_days)
            day_buy_points = [
                bsp for bsp in bsp_list
                if bsp.is_buy and datetime(bsp.klu.time.year, bsp.klu.time.month, bsp.klu.time.day) >= cutoff_date
            ]

            if not day_buy_points:
                return {'status': 'skip', 'reason': '无近期买点'}

            latest_buy = day_buy_points[0]
            bsp_type = latest_buy.type2str()
            base_rating = get_bsp_risk_rating(bsp_type)
            resonance_count = 1
            resonance_levels = ["日线"]

            # 区间套共振检查
            if use_nesting:
                # 30分钟级别
                try:
                    min30_days = max(history_days // 10, 30)
                    min30_begin = (datetime.now() - timedelta(days=min30_days)).strftime("%Y-%m-%d")

                    chan_30m = CChan(
                        code=code,
                        begin_time=min30_begin,
                        end_time=end_time,
                        data_src=DATA_SRC.AKSHARE,
                        lv_list=[KL_TYPE.K_30M],
                        config=config,
                        autype=AUTYPE.QFQ,
                    )

                    if len(chan_30m[0]) > 0:
                        bsp_30m = chan_30m.get_latest_bsp(number=0)
                        cutoff_30m = datetime.now() - timedelta(days=5)
                        buy_30m = [
                            bsp for bsp in bsp_30m
                            if bsp.is_buy and datetime(bsp.klu.time.year, bsp.klu.time.month, bsp.klu.time.day) >= cutoff_30m
                        ]
                        if buy_30m:
                            resonance_count += 1
                            resonance_levels.append("30分")
                except Exception:
                    pass

                # 5分钟级别
                try:
                    min5_days = min(5, max(history_days // 30, 3))
                    min5_begin = (datetime.now() - timedelta(days=min5_days)).strftime("%Y-%m-%d")

                    chan_5m = CChan(
                        code=code,
                        begin_time=min5_begin,
                        end_time=end_time,
                        data_src=DATA_SRC.AKSHARE,
                        lv_list=[KL_TYPE.K_5M],
                        config=config,
                        autype=AUTYPE.QFQ,
                    )

                    if len(chan_5m[0]) > 0:
                        bsp_5m = chan_5m.get_latest_bsp(number=0)
                        cutoff_5m = datetime.now() - timedelta(days=3)
                        buy_5m = [
                            bsp for bsp in bsp_5m
                            if bsp.is_buy and datetime(bsp.klu.time.year, bsp.klu.time.month, bsp.klu.time.day) >= cutoff_5m
                        ]
                        if buy_5m:
                            resonance_count += 1
                            resonance_levels.append("5分")
                except Exception:
                    pass

            # 计算最终风险评级
            bonus = resonance_count - 1
            final_rating = min(5, base_rating + bonus)
            resonance_str = "+".join(resonance_levels)

            return {
                'status': 'found',
                'code': code,
                'name': name,
                'price': price,
                'change': change,
                'bsp_type': f"{bsp_type}({resonance_str})" if resonance_count >= 2 else bsp_type,
                'bsp_time': str(latest_buy.klu.time),
                'risk_rating': final_rating,
                'resonance_count': resonance_count,
                'resonance_str': resonance_str,
                'chan': chan_day,
            }

        except Exception as e:
            return {'status': 'error', 'reason': str(e)[:50]}

    def _scan_thread(self, params: dict):
        """扫描线程（使用线程池并行处理）

        Args:
            params: 包含所有扫描参数的字典，在主线程中预先获取
        """
        try:
            # 使用预先获取的参数（避免在后台线程访问 tkinter 变量）
            bsp_days = params['bsp_days']
            history_days = params['history_days']
            min_price = params['min_price']
            max_price = params['max_price']
            use_nesting = params['use_nesting']
            max_workers = params['max_workers']
            config = params['config']

            # 获取股票列表
            stock_list = get_tradable_stocks(
                include_main=params['include_main'],
                include_gem=params['include_gem'],
                include_star=params['include_star'],
                include_bse=params['include_bse'],
                min_price=min_price,
                max_price=max_price
            )

            if stock_list.empty:
                self.scan_queue.put(('log', {'text': '获取股票列表失败或无符合条件的股票', 'tag': 'error'}))
                self.scan_queue.put(('finished', {'success': 0, 'fail': 0, 'found': 0}))
                return

            total = len(stock_list)
            nesting_str = "日线+30分+5分" if use_nesting else "仅日线"
            self.scan_queue.put(('log', {'text': f'获取到 {total} 只可交易股票，使用 {max_workers} 线程并行扫描...', 'tag': 'info'}))
            self.scan_queue.put(('log', {'text': f'筛选参数: 近{bsp_days}天买点, {history_days}天K线, 价格{min_price}-{max_price}元, {nesting_str}', 'tag': 'info'}))

            success_count = 0
            fail_count = 0
            found_count = 0
            completed = 0

            # 使用线程池并行处理
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_stock = {}
                for idx, row in stock_list.iterrows():
                    if not self.is_scanning:
                        break
                    future = executor.submit(
                        self._analyze_single_stock,
                        row['代码'], row['名称'], row['最新价'], row['涨跌幅'],
                        bsp_days, history_days, use_nesting, config
                    )
                    future_to_stock[future] = (row['代码'], row['名称'])

                # 处理完成的任务
                for future in as_completed(future_to_stock):
                    if not self.is_scanning:
                        # 取消剩余任务
                        for f in future_to_stock:
                            f.cancel()
                        break

                    code, name = future_to_stock[future]
                    completed += 1
                    progress = completed / total * 100
                    self.scan_queue.put(('progress', {'value': progress, 'text': f'{completed}/{total}'}))

                    try:
                        result = future.result()
                        if result is None:
                            continue

                        if result['status'] == 'found':
                            found_count += 1
                            success_count += 1
                            risk_str = get_risk_stars(result['risk_rating'])

                            if result['resonance_count'] >= 2:
                                self.scan_queue.put(('log', {'text': f'🎯 {code} {name}: {result["resonance_str"]}共振! {result["bsp_type"].split("(")[0]} {risk_str}', 'tag': 'success'}))
                            else:
                                self.scan_queue.put(('log', {'text': f'✅ {code} {name}: 发现买点 {result["bsp_type"]} {risk_str}', 'tag': 'success'}))

                            self.scan_queue.put(('found', result))

                        elif result['status'] == 'skip':
                            success_count += 1
                            # 跳过的不记录日志，减少噪音

                        elif result['status'] == 'error':
                            fail_count += 1
                            self.scan_queue.put(('log', {'text': f'❌ {code} {name}: {result["reason"]}', 'tag': 'error'}))

                    except Exception as e:
                        fail_count += 1
                        self.scan_queue.put(('log', {'text': f'❌ {code} {name}: {str(e)[:50]}', 'tag': 'error'}))

            self.scan_queue.put(('finished', {'success': success_count, 'fail': fail_count, 'found': found_count}))

        except Exception as e:
            self.scan_queue.put(('log', {'text': f'扫描出错: {e}', 'tag': 'error'}))
            self.scan_queue.put(('finished', {'success': 0, 'fail': 0, 'found': 0}))

    def _add_stock_to_list(self, data: dict):
        """添加股票到列表"""
        # 保存数据用于排序
        self.stock_data.append(data)

        # 共振显示：有共振显示级别，无共振显示"-"
        resonance_display = data.get('resonance_str', '-') if data.get('resonance_count', 1) >= 2 else '-'

        # 添加到表格
        self.stock_tree.insert('', tk.END, values=(
            data['code'],
            data['name'],
            f"{data['price']:.2f}",
            f"{data['change']:+.2f}%",
            get_risk_stars(data['risk_rating']),
            resonance_display,
            data['bsp_type'].split('(')[0]  # 只显示买点类型，不含共振信息
        ))

        # 缓存 chan 对象
        self.stock_cache[data['code']] = data['chan']

    def _on_scan_finished(self, success: int, fail: int, found: int):
        """扫描完成"""
        self.is_scanning = False
        self.scan_btn.config(text="开始扫描")
        self.progress_label.config(text=f"完成: 成功{success}, 跳过{fail}, 买点{found}")
        self.status_var.set(f'扫描完成: 成功{success}只, 跳过{fail}只, 发现{found}只买点股票')

    def on_stock_selected(self, event=None):
        """股票列表选择事件"""
        selection = self.stock_tree.selection()
        if not selection:
            return

        item = self.stock_tree.item(selection[0])
        values = item['values']
        if not values or len(values) < 2:
            return

        # 确保 code 是字符串类型，并补齐前导零
        code = str(values[0])
        # 股票代码需要6位，如果不足则补零
        if len(code) < 6:
            code = code.zfill(6)
        name = str(values[1])

        if code in self.stock_cache:
            self.chan = self.stock_cache[code]
            self.plot_chart()
            self.status_var.set(f'显示: {code} {name}')
        else:
            self._analyze_stock(code)

    def analyze_single(self):
        """分析单只股票"""
        code = self.code_var.get().strip()
        if not code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        self._analyze_stock(code)

    def _analyze_stock(self, code: str):
        """分析指定股票"""
        if self.is_analyzing:
            return

        self.is_analyzing = True
        self.analyze_btn.config(state=tk.DISABLED)
        self.status_var.set(f'正在分析 {code}...')

        self.analysis_thread = threading.Thread(
            target=self._analysis_thread,
            args=(code,),
            daemon=True
        )
        self.analysis_thread.start()

    def _analysis_thread(self, code: str):
        """分析线程"""
        try:
            history_days = self.history_days_var.get()
            begin_time = (datetime.now() - timedelta(days=history_days)).strftime("%Y-%m-%d")
            end_time = datetime.now().strftime("%Y-%m-%d")

            chan = CChan(
                code=code,
                begin_time=begin_time,
                end_time=end_time,
                data_src=DATA_SRC.AKSHARE,
                lv_list=[KL_TYPE.K_DAY],
                config=self.get_chan_config(),
                autype=AUTYPE.QFQ,
            )
            self.scan_queue.put(('analysis_done', {'chan': chan, 'code': code}))
        except Exception as e:
            self.scan_queue.put(('analysis_error', {'error': str(e)}))

    def _on_analysis_done(self, chan: CChan, code: str):
        """分析完成"""
        self.chan = chan
        self.is_analyzing = False
        self.analyze_btn.config(state=tk.NORMAL)
        self.plot_chart()
        self.status_var.set(f'分析完成: {code}')

    def _on_analysis_error(self, error: str):
        """分析出错"""
        self.is_analyzing = False
        self.analyze_btn.config(state=tk.NORMAL)
        messagebox.showerror("分析错误", error)
        self.status_var.set('分析失败')

    def plot_chart(self):
        """绑制图表"""
        if not self.chan:
            return

        try:
            from Plot.PlotDriver import CPlotDriver

            plt.close('all')

            plot_config = self.get_plot_config()

            canvas_widget = self.canvas.get_tk_widget()
            canvas_width = canvas_widget.winfo_width()
            canvas_height = canvas_widget.winfo_height()
            dpi = 100
            fig_width = max(canvas_width / dpi, 10)

            if plot_config.get("plot_macd", False):
                macd_h_ratio = 0.3
                fig_height = max(canvas_height / dpi / (1 + macd_h_ratio), 5)
            else:
                fig_height = max(canvas_height / dpi, 6)

            plot_para = {
                "figure": {
                    "x_range": 200,
                    "w": fig_width,
                    "h": fig_height,
                }
            }

            plot_driver = CPlotDriver(self.chan, plot_config=plot_config, plot_para=plot_para)

            self.fig = plot_driver.figure
            self.canvas.figure = self.fig
            self.canvas.draw()
            self.toolbar.update()

        except Exception as e:
            messagebox.showerror("绑图错误", str(e))

    def refresh_chart(self):
        """刷新图表"""
        self.plot_chart()

    def get_selected_stock_code(self) -> str:
        """获取当前选中的股票代码（BaoStock格式）"""
        selection = self.stock_tree.selection()
        if not selection:
            return ""

        item = self.stock_tree.item(selection[0])
        values = item['values']
        if not values or len(values) < 1:
            return ""

        # 获取股票代码并补齐
        code = str(values[0])
        if len(code) < 6:
            code = code.zfill(6)

        # 转换为 BaoStock 格式 (sz.000001 或 sh.600000)
        if code.startswith('6'):
            return f"sh.{code}"
        else:
            return f"sz.{code}"

    def get_selected_stock_name(self) -> str:
        """获取当前选中的股票名称"""
        selection = self.stock_tree.selection()
        if not selection:
            return ""

        item = self.stock_tree.item(selection[0])
        values = item['values']
        if not values or len(values) < 2:
            return ""

        return str(values[1])

    def open_single_level_viewer(self):
        """打开单级别K线分析器"""
        try:
            from chan_viewer_tk import ChanViewerWindow

            # 创建新窗口
            window = ChanViewerWindow(self.master)

            # 如果有选中的股票，同步到新窗口
            code = self.get_selected_stock_code()
            name = self.get_selected_stock_name()
            if code and name:
                window.code_var.set(f"{code}  {name}")
                # 自动开始分析
                window.after(100, window.start_analysis)

            self.status_var.set(f'已打开单级别分析窗口')

        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    def open_multi_level_viewer(self):
        """打开多级别区间套分析器"""
        try:
            from chan_viewer_multilevel_tk import MultiLevelViewerWindow

            # 创建新窗口
            window = MultiLevelViewerWindow(self.master)

            # 如果有选中的股票，同步到新窗口
            code = self.get_selected_stock_code()
            name = self.get_selected_stock_name()
            if code and name:
                window.code_var.set(f"{code}  {name}")
                # 自动开始分析
                window.after(100, window.start_analysis)

            self.status_var.set(f'已打开多级别分析窗口')

        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    def clear_stock_list(self):
        """清空股票列表"""
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        self.stock_cache.clear()
        self.stock_data.clear()
        self.status_var.set('列表已清空')

    def on_close(self):
        """窗口关闭"""
        if self.is_scanning:
            self.stop_scan()

        if self in BspScannerWindow.instances:
            BspScannerWindow.instances.remove(self)

        if len(BspScannerWindow.instances) == 0:
            if isinstance(self.master, BspScannerApp):
                self.master.quit()

        self.destroy()


class BspScannerApp(tk.Tk):
    """独立运行时的主应用"""
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.first_window = BspScannerWindow(self)

    def run(self):
        self.mainloop()


def main():
    """程序入口"""
    print("启动A股买点扫描器...")
    app = BspScannerApp()
    app.run()


if __name__ == '__main__':
    main()
