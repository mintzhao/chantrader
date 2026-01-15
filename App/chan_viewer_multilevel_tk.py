"""
多级别区间套分析器 - Powered by chan.py

功能说明:
    - 支持多级别联合分析（如日线+60分钟+15分钟）
    - 区间套买卖点精确定位
    - 多级别图表垂直排列显示
    - 级别间显示范围联动
    - 支持全量A股股票搜索

数据来源:
    - BaoStock: 日/周/月线数据
    - AkShare: 分钟级别数据（盘中实时）

使用方法:
    python App/chan_viewer_multilevel_tk.py
"""
import sys
import io
import queue
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

# 将项目根目录加入路径（兼容 PyInstaller 打包）
def _setup_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后运行，使用 _MEIPASS
        base_path = sys._MEIPASS
    else:
        # 普通 Python 运行
        base_path = str(Path(__file__).resolve().parent.parent)
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
_setup_path()

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from stock_history import get_stock_history
from stock_realtime import get_stock_realtime_data, StockRealtimeData


# K线周期映射
KL_TYPE_MAP = {
    "月线": KL_TYPE.K_MON,
    "周线": KL_TYPE.K_WEEK,
    "日线": KL_TYPE.K_DAY,
    "60分钟": KL_TYPE.K_60M,
    "30分钟": KL_TYPE.K_30M,
    "15分钟": KL_TYPE.K_15M,
    "5分钟": KL_TYPE.K_5M,
    "1分钟": KL_TYPE.K_1M,
}

# 级别顺序（从大到小）
KL_TYPE_ORDER = [
    KL_TYPE.K_MON, KL_TYPE.K_WEEK, KL_TYPE.K_DAY,
    KL_TYPE.K_60M, KL_TYPE.K_30M, KL_TYPE.K_15M,
    KL_TYPE.K_5M, KL_TYPE.K_1M
]

# 分钟级别使用 AkShare
AKSHARE_KL_TYPES = {KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M}

# 英文级别名称（用于图表显示，避免中文字体问题）
KL_TYPE_NAME_EN = {
    KL_TYPE.K_MON: "Monthly",
    KL_TYPE.K_WEEK: "Weekly",
    KL_TYPE.K_DAY: "Daily",
    KL_TYPE.K_60M: "60min",
    KL_TYPE.K_30M: "30min",
    KL_TYPE.K_15M: "15min",
    KL_TYPE.K_5M: "5min",
    KL_TYPE.K_1M: "1min",
}

# 预设级别组合（相邻级别间相差约5根K线）
PRESET_LEVEL_COMBOS = {
    # 4级别组合
    "日线 + 30分钟 + 5分钟 + 1分钟": [KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M, KL_TYPE.K_1M],
    "周线 + 日线 + 30分钟 + 5分钟": [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M],
    # 3级别组合
    "日线 + 30分钟 + 5分钟": [KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M],
    "周线 + 日线 + 30分钟": [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_30M],
    "30分钟 + 5分钟 + 1分钟": [KL_TYPE.K_30M, KL_TYPE.K_5M, KL_TYPE.K_1M],
}

# 区间套说明
INTERVAL_NESTING_INFO = """
区间套原理说明:

区间套是缠论中精确定位买卖点的核心技术，
通过多级别联合分析，逐级缩小买卖区间。

操作流程:
1. 大级别确定方向和区间
   - 找到大级别的中枢和背驰
   - 确定潜在的买卖点区域

2. 次级别细化区间
   - 在大级别信号区域内
   - 观察次级别的走势完成情况

3. 小级别精确入场
   - 等待小级别出现同向买卖点
   - 多级别共振确认后入场

买点区间套示例:
  日线一买区域 → 60分钟一买 → 15分钟一买
  三级别共振，买点确认度最高

卖点区间套示例:
  日线一卖区域 → 60分钟一卖 → 15分钟一卖
  三级别共振，卖点确认度最高

注意事项:
• 大级别定方向，小级别定点位
• 各级别买卖点不必完全对齐
• 关键是趋势方向一致
"""

# 全局股票列表缓存
_stock_list_cache: List[tuple] = []


def load_stock_list() -> List[tuple]:
    """加载股票列表"""
    global _stock_list_cache
    if _stock_list_cache:
        return _stock_list_cache

    # 处理 PyInstaller 打包后的路径
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，从 _MEIPASS 目录读取
        base_path = Path(sys._MEIPASS) / 'App'
    else:
        # 普通 Python 运行
        base_path = Path(__file__).parent

    csv_path = base_path / "stock_list.csv"
    if csv_path.exists():
        try:
            import csv
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                result = [(row['code'], row['name']) for row in reader]
            _stock_list_cache = result
            return result
        except Exception as e:
            print(f"读取股票列表失败: {e}")

    return [
        ("sz.000001", "平安银行"),
        ("sh.600000", "浦发银行"),
        ("sz.002639", "雪人股份"),
        ("sh.600519", "贵州茅台"),
    ]


class StockSearchEntry(ttk.Frame):
    """股票搜索输入框（支持中文，WSL环境可右键粘贴）"""
    def __init__(self, master, textvariable=None, width=25, **kwargs):
        super().__init__(master, **kwargs)

        self.text_var = textvariable or tk.StringVar()
        self.stock_list: List[tuple] = []
        self.filtered_list: List[tuple] = []
        self._search_job = None  # 防抖动定时器

        self.entry = ttk.Entry(self, textvariable=self.text_var, width=width)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.search_btn = ttk.Button(self, text="搜", width=3, command=self.do_search)
        self.search_btn.pack(side=tk.LEFT, padx=(2, 0))

        self.popup = None
        self.listbox = None

        # 使用 trace 监听文本变化（支持中文输入法和粘贴）
        self.text_var.trace_add('write', self._on_text_changed)

        # 绑定键盘事件（用于导航）
        self.entry.bind('<Return>', self.on_enter)
        self.entry.bind('<Escape>', self.hide_popup)
        self.entry.bind('<Down>', self.focus_listbox)

        # 支持右键粘贴菜单
        self.entry.bind('<Button-3>', self._show_paste_menu)

        self.stock_list = load_stock_list()

    def _show_paste_menu(self, event):
        """显示右键粘贴菜单"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="粘贴", command=self._paste_from_clipboard)
        menu.add_command(label="清空", command=lambda: self.text_var.set(""))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _paste_from_clipboard(self):
        """从剪贴板粘贴"""
        try:
            text = self.clipboard_get()
            self.entry.insert(tk.INSERT, text)
        except tk.TclError:
            pass

    def _on_text_changed(self, *args):
        """文本变化时触发搜索（带防抖动）"""
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(200, self._do_search_internal)

    def _do_search_internal(self):
        """实际执行搜索"""
        self._search_job = None
        keyword = self.text_var.get().strip().lower()
        if len(keyword) < 1:
            self.hide_popup()
            return

        self.filtered_list = []
        for code, name in self.stock_list:
            code_num = code.replace('sz.', '').replace('sh.', '')
            if (keyword in code.lower() or
                keyword in code_num or
                keyword in name.lower()):
                self.filtered_list.append((code, name))
                if len(self.filtered_list) >= 50:
                    break

        if self.filtered_list:
            self.show_popup()
        else:
            self.hide_popup()

    def do_search(self):
        self._do_search_internal()

    def show_popup(self):
        if not self.filtered_list:
            return

        if self.popup is None or not self.popup.winfo_exists():
            self.popup = tk.Toplevel(self)
            self.popup.wm_overrideredirect(True)
            self.popup.attributes('-topmost', True)

            frame = ttk.Frame(self.popup)
            frame.pack(fill=tk.BOTH, expand=True)

            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.listbox = tk.Listbox(
                frame, height=min(15, len(self.filtered_list)),
                width=35, yscrollcommand=scrollbar.set,
                font=("Consolas", 10)
            )
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=self.listbox.yview)

            self.listbox.bind('<ButtonRelease-1>', self.on_select)
            self.listbox.bind('<Return>', self.on_select)
            self.listbox.bind('<Double-Button-1>', self.on_select)

        self.listbox.delete(0, tk.END)
        for code, name in self.filtered_list:
            self.listbox.insert(tk.END, f"{code}  {name}")

        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        height = min(300, len(self.filtered_list) * 20 + 10)
        self.popup.geometry(f"280x{height}+{x}+{y}")
        self.popup.deiconify()

    def hide_popup(self, event=None):
        if self.popup and self.popup.winfo_exists():
            self.popup.withdraw()

    def focus_listbox(self, event=None):
        if self.listbox and self.popup and self.popup.winfo_exists():
            self.listbox.focus_set()
            if self.listbox.size() > 0:
                self.listbox.selection_set(0)

    def on_enter(self, event=None):
        if self.listbox and self.listbox.curselection():
            self.on_select()
        self.hide_popup()

    def on_select(self, event=None):
        if self.listbox and self.listbox.curselection():
            selection = self.listbox.get(self.listbox.curselection())
            self.text_var.set(selection)
            self.hide_popup()

    def get(self) -> str:
        return self.text_var.get()

    def set(self, value: str):
        self.text_var.set(value)


class MultiLevelViewerWindow(tk.Toplevel):
    """多级别区间套分析窗口"""

    window_count = 0
    instances: List['MultiLevelViewerWindow'] = []

    def __init__(self, master=None):
        super().__init__(master)

        MultiLevelViewerWindow.window_count += 1
        MultiLevelViewerWindow.instances.append(self)

        self.chan_dict: Dict[KL_TYPE, CChan] = {}  # 各级别的CChan对象
        self.current_levels: List[KL_TYPE] = []
        self.is_analyzing = False
        self.analysis_thread: Optional[threading.Thread] = None
        self.auto_refresh_job = None  # 自动刷新任务

        self.init_ui()

        offset = (MultiLevelViewerWindow.window_count - 1) * 30
        self.geometry(f"1600x1000+{50 + offset}+{50 + offset}")
        self.minsize(1200, 800)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def init_ui(self):
        """初始化界面"""
        self.title(f'多级别区间套分析器 #{MultiLevelViewerWindow.window_count}')

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # === 顶部控制栏 ===
        control_frame = ttk.Frame(self, padding="5")
        control_frame.grid(row=0, column=0, sticky="ew")

        # 股票选择
        ttk.Label(control_frame, text="股票:").pack(side=tk.LEFT, padx=(0, 5))
        self.code_var = tk.StringVar(value="sz.002639  雪人股份")
        self.code_entry = StockSearchEntry(control_frame, textvariable=self.code_var, width=24)
        self.code_entry.pack(side=tk.LEFT, padx=(0, 5))

        # 历史记录下拉框
        self.history_var = tk.StringVar(value="")
        self.history_combo = ttk.Combobox(
            control_frame, textvariable=self.history_var,
            values=[], width=20, state="readonly"
        )
        self.history_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.history_combo.bind('<<ComboboxSelected>>', self.on_history_selected)
        self._update_history_combo()  # 初始化历史记录列表

        # 级别组合选择
        ttk.Label(control_frame, text="级别组合:").pack(side=tk.LEFT, padx=(0, 5))
        self.level_combo_var = tk.StringVar(value="日线 + 30分钟 + 5分钟 + 1分钟")
        self.level_combo = ttk.Combobox(
            control_frame, textvariable=self.level_combo_var,
            values=list(PRESET_LEVEL_COMBOS.keys()), width=25, state="readonly"
        )
        self.level_combo.pack(side=tk.LEFT, padx=(0, 15))

        # 周期数
        ttk.Label(control_frame, text="周期数:").pack(side=tk.LEFT, padx=(0, 5))
        self.periods_var = tk.IntVar(value=300)
        self.periods_spin = ttk.Spinbox(
            control_frame, from_=50, to=500,
            textvariable=self.periods_var, width=6
        )
        self.periods_spin.pack(side=tk.LEFT, padx=(0, 15))

        # 分析按钮
        self.analyze_btn = ttk.Button(
            control_frame, text="开始分析",
            command=self.toggle_analysis
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 分隔
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 自动刷新
        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.auto_refresh_cb = ttk.Checkbutton(
            control_frame, text="自动刷新",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh
        )
        self.auto_refresh_cb.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(control_frame, text="间隔(秒):").pack(side=tk.LEFT, padx=(0, 5))
        self.refresh_interval_var = tk.IntVar(value=60)
        self.refresh_interval_spin = ttk.Spinbox(
            control_frame, from_=10, to=3600,
            textvariable=self.refresh_interval_var, width=5
        )
        self.refresh_interval_spin.pack(side=tk.LEFT, padx=(0, 10))

        # 分隔
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 区间套说明按钮
        ttk.Button(
            control_frame, text="区间套原理",
            command=self.show_interval_nesting_info
        ).pack(side=tk.LEFT, padx=(0, 5))

        # 保存按钮
        ttk.Button(
            control_frame, text="保存图片",
            command=self.save_chart
        ).pack(side=tk.LEFT)

        # 单级别分析按钮
        ttk.Button(
            control_frame, text="单级别分析",
            command=self.open_single_level_viewer
        ).pack(side=tk.LEFT, padx=(10, 0))

        # === 绘图选项 ===
        options_frame = ttk.Frame(self, padding="5")
        options_frame.grid(row=1, column=0, sticky="ew")

        ttk.Label(options_frame, text="显示:").pack(side=tk.LEFT)

        self.plot_kline_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="K线", variable=self.plot_kline_var).pack(side=tk.LEFT, padx=3)

        self.plot_bi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="笔", variable=self.plot_bi_var).pack(side=tk.LEFT, padx=3)

        self.plot_seg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="线段", variable=self.plot_seg_var).pack(side=tk.LEFT, padx=3)

        self.plot_zs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="中枢", variable=self.plot_zs_var).pack(side=tk.LEFT, padx=3)

        self.plot_bsp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="买卖点", variable=self.plot_bsp_var).pack(side=tk.LEFT, padx=3)

        self.plot_macd_var = tk.BooleanVar(value=False)  # 多级别默认不显示MACD节省空间
        ttk.Checkbutton(options_frame, text="MACD", variable=self.plot_macd_var).pack(side=tk.LEFT, padx=3)

        ttk.Separator(options_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(options_frame, text="刷新图表", command=self.plot_charts).pack(side=tk.LEFT)

        # === 主内容区域 ===
        content_frame = ttk.Frame(self)
        content_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # 左侧图表区域
        chart_frame = ttk.Frame(content_frame)
        chart_frame.grid(row=0, column=0, sticky="nsew")
        chart_frame.grid_rowconfigure(0, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)

        # 创建垂直滚动的画布容器
        self.fig = Figure(figsize=(14, 12), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # 右侧信息面板
        info_frame = ttk.Frame(content_frame, width=280)
        info_frame.grid(row=0, column=1, sticky="ns", padx=(5, 0))
        info_frame.grid_propagate(False)

        # 使用 Notebook 组织右侧面板
        right_notebook = ttk.Notebook(info_frame)
        right_notebook.pack(fill=tk.BOTH, expand=True)

        # 实时行情标签页
        realtime_tab = ttk.Frame(right_notebook, padding="5")
        right_notebook.add(realtime_tab, text="实时行情")

        self.realtime_text = tk.Text(realtime_tab, width=30, height=20, font=("Consolas", 9),
                                      bg="#f0f8ff", relief=tk.FLAT, wrap=tk.WORD)
        self.realtime_text.pack(fill=tk.BOTH, expand=True)

        # 配置实时行情标签样式
        self.realtime_text.tag_configure("title", font=("Arial", 11, "bold"), foreground="#333333")
        self.realtime_text.tag_configure("price_up", foreground="#ff4444", font=("Consolas", 10, "bold"))
        self.realtime_text.tag_configure("price_down", foreground="#00aa00", font=("Consolas", 10, "bold"))
        self.realtime_text.tag_configure("price_flat", foreground="#666666", font=("Consolas", 10, "bold"))
        self.realtime_text.tag_configure("label", foreground="#666666")
        self.realtime_text.tag_configure("value", foreground="#333333")
        self.realtime_text.tag_configure("highlight", foreground="#0066cc", font=("Consolas", 9, "bold"))

        ttk.Button(realtime_tab, text="刷新行情", command=self.refresh_realtime_data).pack(pady=(5, 0))

        # 买卖点汇总标签页
        bsp_tab = ttk.Frame(right_notebook, padding="5")
        right_notebook.add(bsp_tab, text="买卖点")

        self.bsp_text = tk.Text(bsp_tab, width=30, height=20, font=("Consolas", 9),
                                 bg="#f8f8f8", relief=tk.FLAT, wrap=tk.WORD)
        self.bsp_text.pack(fill=tk.BOTH, expand=True)

        # 区间套分析标签页
        nesting_tab = ttk.Frame(right_notebook, padding="5")
        right_notebook.add(nesting_tab, text="区间套")

        self.nesting_text = tk.Text(nesting_tab, width=30, height=20, font=("Consolas", 9),
                                     bg="#fff8e8", relief=tk.FLAT, wrap=tk.WORD)
        self.nesting_text.pack(fill=tk.BOTH, expand=True)

        # === 状态栏 ===
        status_frame = ttk.Frame(self)
        status_frame.grid(row=3, column=0, sticky="ew")

        self.status_var = tk.StringVar(value='就绪 - 选择股票和级别组合后点击"开始分析"')
        self.status_bar = ttk.Label(status_frame, textvariable=self.status_var,
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)

    def get_current_code(self) -> str:
        """获取当前股票代码"""
        text = self.code_var.get().strip()
        if '  ' in text:
            return text.split('  ')[0]
        elif ' ' in text:
            return text.split()[0]
        return text

    def get_current_stock_name(self) -> str:
        """获取当前股票名称"""
        text = self.code_var.get().strip()
        if '  ' in text:
            parts = text.split('  ', 1)
            return parts[1] if len(parts) > 1 else ""
        elif ' ' in text:
            parts = text.split(None, 1)
            return parts[1] if len(parts) > 1 else ""
        return ""

    def get_selected_levels(self) -> List[KL_TYPE]:
        """获取选择的级别组合"""
        combo_name = self.level_combo_var.get()
        return PRESET_LEVEL_COMBOS.get(combo_name, [KL_TYPE.K_DAY, KL_TYPE.K_60M])

    def get_chan_config(self) -> CChanConfig:
        """获取缠论配置"""
        return CChanConfig({
            "bi_strict": True,
            "trigger_step": False,
            "divergence_rate": float("inf"),
            "bsp2_follow_1": False,
            "bsp3_follow_1": False,
            "min_zs_cnt": 0,
            "bs1_peak": False,
            "macd_algo": "peak",
            "bs_type": "1,1p,2,2s,3a,3b",
            "print_warning": True,
            "zs_algo": "normal",
        })

    def get_plot_config(self) -> dict:
        """获取绑图配置"""
        return {
            "plot_kline": self.plot_kline_var.get(),
            "plot_kline_combine": True,
            "plot_bi": self.plot_bi_var.get(),
            "plot_seg": self.plot_seg_var.get(),
            "plot_zs": self.plot_zs_var.get(),
            "plot_bsp": self.plot_bsp_var.get(),
            "plot_macd": self.plot_macd_var.get(),
        }

    def calc_days_for_level(self, kl_type: KL_TYPE, periods: int) -> int:
        """根据级别计算需要的天数"""
        if kl_type == KL_TYPE.K_1M:
            # 1分钟K线：每天约240根，至少请求5天数据确保足够
            return max(periods // 240 + 3, 5)
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

    def toggle_analysis(self):
        """切换分析状态"""
        if self.is_analyzing:
            self.stop_analysis()
        else:
            self.start_analysis()

    def stop_analysis(self):
        """停止分析"""
        self.is_analyzing = False
        self.analyze_btn.config(text="开始分析")
        self.status_var.set('分析已停止')

    def start_analysis(self):
        """开始多级别分析"""
        if self.is_analyzing:
            return

        code = self.get_current_code()
        if not code:
            messagebox.showwarning("警告", "请输入股票代码")
            return

        self.current_levels = self.get_selected_levels()
        if not self.current_levels:
            messagebox.showwarning("警告", "请选择级别组合")
            return

        self.is_analyzing = True
        self.analyze_btn.config(text="停止")
        self.chan_dict.clear()

        level_names = [self.get_level_name(lv) for lv in self.current_levels]
        self.status_var.set(f'正在分析 {code} [{" + ".join(level_names)}]...')
        self.update()

        # 在后台线程执行分析
        self.analysis_thread = threading.Thread(
            target=self._do_analysis_thread,
            args=(code,),
            daemon=True
        )
        self.analysis_thread.start()

    def _do_analysis_thread(self, code: str):
        """后台线程执行分析"""
        try:
            periods = self.periods_var.get()
            config = self.get_chan_config()

            for i, kl_type in enumerate(self.current_levels):
                if not self.is_analyzing:
                    return

                level_name = self.get_level_name(kl_type)
                self.after(0, lambda n=level_name, idx=i: self.status_var.set(
                    f'正在分析第 {idx+1}/{len(self.current_levels)} 级别: {n}...'
                ))

                # 计算时间范围
                days = self.calc_days_for_level(kl_type, periods)
                begin_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

                # 选择数据源
                if kl_type in AKSHARE_KL_TYPES:
                    data_src = DATA_SRC.AKSHARE
                else:
                    data_src = DATA_SRC.BAO_STOCK

                try:
                    # 创建 CChan 对象
                    chan = CChan(
                        code=code,
                        begin_time=begin_time,
                        end_time=None,
                        data_src=data_src,
                        lv_list=[kl_type],
                        config=config,
                        autype=AUTYPE.QFQ,
                    )

                    # 检查数据有效性
                    kl_data = chan[0]
                    kl_count = len(list(kl_data))
                    if kl_count < 10:
                        raise Exception(f"{level_name}数据不足(仅{kl_count}根K线)，请检查网络或稍后重试")

                    self.chan_dict[kl_type] = chan

                except Exception as e:
                    error_msg = f"{level_name}分析失败: {str(e)}"
                    raise Exception(error_msg)

            # 在主线程更新UI
            self.after(0, lambda: self._on_analysis_done(code))

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: self._on_analysis_error(msg))

    def _on_analysis_done(self, code: str):
        """分析完成回调"""
        if not self.is_analyzing:
            return

        self.is_analyzing = False
        self.analyze_btn.config(text="开始分析")

        level_names = [self.get_level_name(lv) for lv in self.current_levels]
        self.title(f'{code} [{" + ".join(level_names)}] - 多级别区间套分析器')

        # 添加到历史记录
        stock_name = self.get_current_stock_name()
        self._add_to_history(code, stock_name)

        # 绘制图表
        self.plot_charts()

        # 更新买卖点汇总
        self.update_bsp_summary()

        # 分析区间套
        self.analyze_interval_nesting()

        # 刷新实时行情数据
        self.refresh_realtime_data()

        # 统计信息
        stats = []
        for kl_type in self.current_levels:
            if kl_type in self.chan_dict:
                kl_data = self.chan_dict[kl_type][0]
                name = self.get_level_name(kl_type)
                stats.append(f"{name}:笔{len(kl_data.bi_list)}/买卖点{len(kl_data.bs_point_lst)}")

        self.status_var.set(f'分析完成 | {" | ".join(stats)}')

    def _on_analysis_error(self, error_msg: str):
        """分析出错回调"""
        self.is_analyzing = False
        self.analyze_btn.config(text="开始分析")
        messagebox.showerror("分析错误", f"分析失败:\n{error_msg}")
        self.status_var.set('分析失败')

    def refresh_realtime_data(self):
        """刷新实时行情数据"""
        code = self.get_current_code()
        if not code:
            return

        # 在后台线程获取实时数据
        def fetch_data():
            try:
                data = get_stock_realtime_data(code)
                if data:
                    self.after(0, lambda: self.update_realtime_display(data))
                else:
                    self.after(0, lambda: self._show_realtime_error("无法获取实时数据"))
            except Exception as e:
                self.after(0, lambda msg=str(e): self._show_realtime_error(msg))

        threading.Thread(target=fetch_data, daemon=True).start()

    def _show_realtime_error(self, error_msg: str):
        """显示实时数据获取错误"""
        if not hasattr(self, 'realtime_text'):
            return
        self.realtime_text.config(state=tk.NORMAL)
        self.realtime_text.delete(1.0, tk.END)
        self.realtime_text.insert(tk.END, f"获取实时数据失败:\n{error_msg}\n\n点击\"刷新行情\"重试")
        self.realtime_text.config(state=tk.DISABLED)

    def update_realtime_display(self, data: StockRealtimeData):
        """更新实时行情显示"""
        if not hasattr(self, 'realtime_text'):
            return

        self.realtime_text.config(state=tk.NORMAL)
        self.realtime_text.delete(1.0, tk.END)

        # 标题：股票名称
        self.realtime_text.insert(tk.END, f"{data.name}\n", "title")
        self.realtime_text.insert(tk.END, f"代码: {data.code}\n\n", "label")

        # 当前价格和涨跌
        price_tag = "price_up" if data.change_pct > 0 else ("price_down" if data.change_pct < 0 else "price_flat")
        self.realtime_text.insert(tk.END, f"{data.latest_price:.2f}", price_tag)
        self.realtime_text.insert(tk.END, f"  {data.change_pct:+.2f}%\n\n", price_tag)

        # 关键指标
        self.realtime_text.insert(tk.END, "━━ 核心指标 ━━\n", "highlight")

        display_data = data.get_display_dict()

        key_fields = [
            ("总市值", display_data["总市值"]),
            ("流通市值", display_data["流通市值"]),
            ("今开", display_data["今开"]),
            ("换手率", display_data["换手率"]),
            ("量比", display_data["量比"]),
        ]

        for label, value in key_fields:
            self.realtime_text.insert(tk.END, f"{label}: ", "label")
            self.realtime_text.insert(tk.END, f"{value}\n", "value")

        self.realtime_text.insert(tk.END, "\n━━ 价格信息 ━━\n", "highlight")

        price_fields = [
            ("最高", display_data["最高"]),
            ("最低", display_data["最低"]),
            ("昨收", display_data["昨收"]),
            ("均价", display_data["均价"]),
        ]

        for label, value in price_fields:
            self.realtime_text.insert(tk.END, f"{label}: ", "label")
            self.realtime_text.insert(tk.END, f"{value}\n", "value")

        self.realtime_text.insert(tk.END, "\n━━ 成交信息 ━━\n", "highlight")

        volume_fields = [
            ("成交量", display_data["成交量"]),
            ("成交额", display_data["成交额"]),
        ]

        for label, value in volume_fields:
            self.realtime_text.insert(tk.END, f"{label}: ", "label")
            self.realtime_text.insert(tk.END, f"{value}\n", "value")

        self.realtime_text.insert(tk.END, "\n━━ 涨跌限制 ━━\n", "highlight")

        limit_fields = [
            ("涨停价", display_data["涨停价"]),
            ("跌停价", display_data["跌停价"]),
            ("行业", display_data["行业"]),
        ]

        for label, value in limit_fields:
            self.realtime_text.insert(tk.END, f"{label}: ", "label")
            self.realtime_text.insert(tk.END, f"{value}\n", "value")

        # 更新时间
        self.realtime_text.insert(tk.END, f"\n更新: {data.update_time.strftime('%H:%M:%S')}", "label")

        self.realtime_text.config(state=tk.DISABLED)

    def get_level_name(self, kl_type: KL_TYPE) -> str:
        """获取级别名称"""
        for name, kt in KL_TYPE_MAP.items():
            if kt == kl_type:
                return name
        return str(kl_type)

    def plot_charts(self):
        """绑制多级别图表 - 使用原项目 PlotDriver"""
        if not self.chan_dict:
            return

        try:
            from Plot.PlotDriver import CPlotDriver

            plt.close('all')

            plot_config = self.get_plot_config()
            num_levels = len(self.current_levels)

            # 清除旧图
            self.fig.clear()

            # 获取画布实际大小来计算合适的图表尺寸
            canvas_widget = self.canvas.get_tk_widget()
            canvas_width = canvas_widget.winfo_width()
            canvas_height = canvas_widget.winfo_height()
            dpi = 100

            # 为每个级别单独绑制，然后组合
            # 计算每个级别的高度（4级别时适当压缩）
            min_level_height = 2.5 if num_levels >= 4 else 3
            level_height = max(canvas_height / dpi / num_levels, min_level_height)
            fig_width = max(canvas_width / dpi, 10)

            # 计算子图高度比例
            if plot_config.get("plot_macd", False):
                # 如果显示MACD，每个级别需要额外30%空间
                height_ratios = []
                for _ in range(num_levels):
                    height_ratios.extend([1, 0.3])  # K线图 + MACD
                total_rows = num_levels * 2
            else:
                height_ratios = [1] * num_levels
                total_rows = num_levels

            # 创建子图
            axes = self.fig.subplots(total_rows, 1, gridspec_kw={'height_ratios': height_ratios})
            if total_rows == 1:
                axes = [axes]

            # 为每个级别绘制
            ax_idx = 0
            for i, kl_type in enumerate(self.current_levels):
                if kl_type not in self.chan_dict:
                    ax_idx += 2 if plot_config.get("plot_macd", False) else 1
                    continue

                chan = self.chan_dict[kl_type]
                # 使用英文级别名称，避免中文字体显示问题
                level_name_en = KL_TYPE_NAME_EN.get(kl_type, str(kl_type))

                # 获取当前级别的 axes
                if plot_config.get("plot_macd", False):
                    ax_main = axes[ax_idx]
                    ax_macd = axes[ax_idx + 1]
                    ax_idx += 2
                else:
                    ax_main = axes[ax_idx]
                    ax_macd = None
                    ax_idx += 1

                # 使用原项目的绘图逻辑绘制单个级别
                self._plot_level_with_driver(chan, ax_main, ax_macd, level_name_en, plot_config)

            self.fig.tight_layout()
            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("绑图错误", str(e))
            import traceback
            traceback.print_exc()

    def _plot_level_with_driver(self, chan: CChan, ax, ax_macd, level_name: str, plot_config: dict):
        """使用原项目的绘图逻辑绑制单个级别的图表"""
        from Plot.PlotMeta import CChanPlotMeta
        from matplotlib.patches import Rectangle

        kl_data = chan[0]
        meta = CChanPlotMeta(kl_data)

        if meta.klu_len == 0:
            ax.text(0.5, 0.5, f'{level_name}: 无数据', ha='center', va='center', transform=ax.transAxes)
            return

        # 计算x轴范围（显示最近150个K线）
        x_range = 150
        X_LEN = meta.klu_len
        x_limits = [X_LEN - x_range, X_LEN - 1] if X_LEN > x_range else [0, X_LEN - 1]

        # 设置x轴刻度
        x_tick_num = 8
        ax.set_xlim(x_limits[0], x_limits[1] + 1)
        tick_step = max([1, int((x_limits[1] - x_limits[0]) / float(x_tick_num))])
        ax.set_xticks(range(x_limits[0], x_limits[1], tick_step))
        ax.set_xticklabels([meta.datetick[i] if i < len(meta.datetick) else '' for i in ax.get_xticks()], rotation=20, fontsize=7)

        # 计算y轴范围
        x_begin = ax.get_xlim()[0]
        y_min = float("inf")
        y_max = float("-inf")
        for klc_meta in meta.klc_list:
            if klc_meta.klu_list[-1].idx < x_begin:
                continue
            if klc_meta.high > y_max:
                y_max = klc_meta.high
            if klc_meta.low < y_min:
                y_min = klc_meta.low

        # 绘制K线
        if plot_config.get("plot_kline", False):
            width = 0.4
            for kl in meta.klu_iter():
                i = kl.idx
                if i + width < x_begin:
                    continue
                if kl.close > kl.open:
                    ax.add_patch(Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, fill=False, color='r'))
                    ax.plot([i, i], [kl.low, kl.open], 'r')
                    ax.plot([i, i], [kl.close, kl.high], 'r')
                else:
                    ax.add_patch(Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, color='g'))
                    ax.plot([i, i], [kl.low, kl.high], color='g')

        # 绘制合并K线
        from Common.CEnum import FX_TYPE, KLINE_DIR
        if plot_config.get("plot_kline_combine", True):
            color_type = {FX_TYPE.TOP: 'red', FX_TYPE.BOTTOM: 'blue', KLINE_DIR.UP: 'green', KLINE_DIR.DOWN: 'green'}
            width = 0.4
            for klc_meta in meta.klc_list:
                if klc_meta.klu_list[-1].idx + width < x_begin:
                    continue
                ax.add_patch(
                    Rectangle(
                        (klc_meta.begin_idx - width, klc_meta.low),
                        klc_meta.end_idx - klc_meta.begin_idx + width * 2,
                        klc_meta.high - klc_meta.low,
                        fill=False,
                        color=color_type.get(klc_meta.type, 'gray')))

        # 绘制笔
        if plot_config.get("plot_bi", True):
            for bi in meta.bi_list:
                if bi.end_x < x_begin:
                    continue
                if bi.is_sure:
                    ax.plot([bi.begin_x, bi.end_x], [bi.begin_y, bi.end_y], color='black')
                else:
                    ax.plot([bi.begin_x, bi.end_x], [bi.begin_y, bi.end_y], linestyle='dashed', color='black')

        # 绘制线段
        if plot_config.get("plot_seg", True):
            for seg_meta in meta.seg_list:
                if seg_meta.end_x < x_begin:
                    continue
                if seg_meta.is_sure:
                    ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color='g', linewidth=5)
                else:
                    ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color='g', linewidth=5, linestyle='dashed')

        # 绘制中枢
        if plot_config.get("plot_zs", True):
            for zs_meta in meta.zs_lst:
                if zs_meta.begin + zs_meta.w < x_begin:
                    continue
                line_style = '-' if zs_meta.is_sure else '--'
                ax.add_patch(Rectangle((zs_meta.begin, zs_meta.low), zs_meta.w, zs_meta.h, fill=False, color='orange', linewidth=2, linestyle=line_style))

        # 绘制买卖点
        if plot_config.get("plot_bsp", True):
            y_range = y_max - y_min
            arrow_l = 0.15
            arrow_h = 0.2
            arrow_w = 1
            for bsp in meta.bs_point_lst:
                if bsp.x < x_begin:
                    continue
                color = 'r' if bsp.is_buy else 'g'
                arrow_dir = 1 if bsp.is_buy else -1
                arrow_len = arrow_l * y_range
                arrow_head = arrow_len * arrow_h
                ax.text(bsp.x,
                        bsp.y - arrow_len * arrow_dir,
                        f'{bsp.desc()}',
                        fontsize=10,
                        color=color,
                        verticalalignment='top' if bsp.is_buy else 'bottom',
                        horizontalalignment='center')
                ax.arrow(bsp.x,
                         bsp.y - arrow_len * arrow_dir,
                         0,
                         (arrow_len - arrow_head) * arrow_dir,
                         head_width=arrow_w,
                         head_length=arrow_head,
                         color=color)
                # 更新y范围以包含买卖点标注
                if bsp.y - arrow_len * arrow_dir < y_min:
                    y_min = bsp.y - arrow_len * arrow_dir
                if bsp.y - arrow_len * arrow_dir > y_max:
                    y_max = bsp.y - arrow_len * arrow_dir

        # 绘制MACD
        if plot_config.get("plot_macd", False) and ax_macd is not None:
            macd_lst = [klu.macd for klu in meta.klu_iter()]
            if macd_lst and macd_lst[0] is not None:
                width = 0.4
                x_idx = range(len(macd_lst))[x_limits[0]:]
                dif_line = [macd.DIF for macd in macd_lst[x_limits[0]:]]
                dea_line = [macd.DEA for macd in macd_lst[x_limits[0]:]]
                macd_bar = [macd.macd for macd in macd_lst[x_limits[0]:]]
                macd_y_min = min([min(dif_line), min(dea_line), min(macd_bar)])
                macd_y_max = max([max(dif_line), max(dea_line), max(macd_bar)])
                ax_macd.plot(x_idx, dif_line, "#FFA500")
                ax_macd.plot(x_idx, dea_line, "#0000ff")
                _bar = ax_macd.bar(x_idx, macd_bar, color="r", width=width)
                for idx, macd in enumerate(macd_bar):
                    if macd < 0:
                        _bar[idx].set_color("#006400")
                ax_macd.set_ylim(macd_y_min, macd_y_max)
                ax_macd.set_xlim(x_limits[0], x_limits[1] + 1)

        # 设置标题和标签
        kl_count = meta.klu_len
        bi_count = len(meta.bi_list)
        bsp_count = len(meta.bs_point_lst)
        ax.set_title(f'{level_name} (K:{kl_count} bi:{bi_count} bsp:{bsp_count})',
                    fontsize=10, fontweight='bold', loc='left', color='r')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(y_min, y_max)

    def _plot_single_level(self, ax, chan: CChan, level_name: str, plot_config: dict):
        """绑制单个级别的图表（备用方法）"""
        kl_data = chan[0]

        # 获取K线数据
        # 注意：kl_data 迭代返回的是 CKLine（合并K线），不是 CKLine_Unit
        # CKLine 有 high, low 属性，但没有 close, open
        # 需要通过 kl.lst[-1] 获取最后一根原始K线单元的收盘价
        klines = list(kl_data)
        if not klines:
            ax.text(0.5, 0.5, f'{level_name}: 无数据', ha='center', va='center', transform=ax.transAxes)
            return

        x_data = list(range(len(klines)))
        # CKLine.lst 包含原始 CKLine_Unit，取最后一根的收盘价作为合并K线的收盘价
        close_prices = [kl.lst[-1].close for kl in klines]
        high_prices = [kl.high for kl in klines]
        low_prices = [kl.low for kl in klines]

        # 绘制K线（简化为收盘价折线）
        if plot_config.get("plot_kline", True):
            ax.plot(x_data, close_prices, 'b-', linewidth=0.8, alpha=0.6, label='收盘价')
            ax.fill_between(x_data, low_prices, high_prices, alpha=0.1, color='blue')

        # 绘制笔
        if plot_config.get("plot_bi", True) and kl_data.bi_list:
            bi_x = []
            bi_y = []
            for bi in kl_data.bi_list:
                begin_idx = bi.get_begin_klu().idx
                end_idx = bi.get_end_klu().idx
                if begin_idx < len(klines) and end_idx < len(klines):
                    bi_x.extend([begin_idx, end_idx])
                    bi_y.extend([bi.get_begin_val(), bi.get_end_val()])

            if bi_x:
                # 绘制笔的连线
                for i in range(0, len(bi_x) - 1, 2):
                    ax.plot(bi_x[i:i+2], bi_y[i:i+2], 'r-', linewidth=1.5)

        # 绘制线段
        if plot_config.get("plot_seg", True) and kl_data.seg_list:
            for seg in kl_data.seg_list:
                begin_idx = seg.get_begin_klu().idx
                end_idx = seg.get_end_klu().idx
                if begin_idx < len(klines) and end_idx < len(klines):
                    ax.plot([begin_idx, end_idx],
                           [seg.get_begin_val(), seg.get_end_val()],
                           'g-', linewidth=2.5, alpha=0.8)

        # 绘制中枢
        if plot_config.get("plot_zs", True) and kl_data.zs_list:
            for zs in kl_data.zs_list:
                begin_idx = zs.begin.idx
                end_idx = zs.end.idx
                if begin_idx < len(klines) and end_idx < len(klines):
                    rect = plt.Rectangle(
                        (begin_idx, zs.low),
                        end_idx - begin_idx,
                        zs.high - zs.low,
                        fill=True, facecolor='orange', alpha=0.2,
                        edgecolor='orange', linewidth=1
                    )
                    ax.add_patch(rect)

        # 绘制买卖点
        if plot_config.get("plot_bsp", True) and len(kl_data.bs_point_lst) > 0:
            for bsp in kl_data.bs_point_lst.bsp_iter():
                idx = bsp.klu.idx
                val = bsp.bi.get_end_val()
                if idx < len(klines):
                    is_buy = bsp.is_buy
                    bsp_type = bsp.type2str()

                    color = 'red' if is_buy else 'green'
                    marker = '^' if is_buy else 'v'
                    prefix = 'b' if is_buy else 's'

                    ax.scatter(idx, val, c=color, marker=marker, s=100, zorder=5)
                    ax.annotate(f'{prefix}{bsp_type}', (idx, val),
                               textcoords="offset points",
                               xytext=(0, 10 if is_buy else -15),
                               ha='center', fontsize=8, color=color,
                               fontweight='bold')

        # 设置标题和标签
        kl_count = len(klines)
        bi_count = len(kl_data.bi_list)
        bsp_count = len(kl_data.bs_point_lst)
        ax.set_title(f'{level_name} (K线:{kl_count} 笔:{bi_count} 买卖点:{bsp_count})',
                    fontsize=10, fontweight='bold')
        ax.set_ylabel('价格')
        ax.grid(True, alpha=0.3)

        # 设置x轴范围（只显示最近的数据）
        if len(klines) > 150:
            ax.set_xlim(len(klines) - 150, len(klines))

    def update_bsp_summary(self):
        """更新买卖点汇总"""
        self.bsp_text.delete(1.0, tk.END)

        for kl_type in self.current_levels:
            if kl_type not in self.chan_dict:
                continue

            chan = self.chan_dict[kl_type]
            kl_data = chan[0]
            level_name = self.get_level_name(kl_type)

            self.bsp_text.insert(tk.END, f"【{level_name}】\n", "header")

            if len(kl_data.bs_point_lst) == 0:
                self.bsp_text.insert(tk.END, "  无买卖点\n\n")
                continue

            # 按时间倒序显示最近的买卖点
            bsp_list = list(reversed(kl_data.bs_point_lst.getSortedBspList()))
            for bsp in bsp_list[:5]:  # 只显示最近5个
                bsp_type = bsp.type2str()
                prefix = '买' if bsp.is_buy else '卖'
                price = f"{bsp.bi.get_end_val():.2f}"
                self.bsp_text.insert(tk.END, f"  {prefix}{bsp_type}: {price}\n")

            self.bsp_text.insert(tk.END, "\n")

    def analyze_interval_nesting(self):
        """分析区间套（支持2-4级别共振）"""
        self.nesting_text.delete(1.0, tk.END)

        if len(self.current_levels) < 2:
            self.nesting_text.insert(tk.END, "需要至少2个级别才能进行区间套分析\n")
            return

        # 收集各级别的最近买卖点
        level_bsp_info = {}
        for kl_type in self.current_levels:
            if kl_type not in self.chan_dict:
                continue

            kl_data = self.chan_dict[kl_type][0]
            level_name = self.get_level_name(kl_type)

            if len(kl_data.bs_point_lst) > 0:
                buy_points = [bsp for bsp in kl_data.bs_point_lst.bsp_iter() if bsp.is_buy]
                sell_points = [bsp for bsp in kl_data.bs_point_lst.bsp_iter() if not bsp.is_buy]

                latest_buy = max(buy_points, key=lambda x: x.klu.idx) if buy_points else None
                latest_sell = max(sell_points, key=lambda x: x.klu.idx) if sell_points else None

                level_bsp_info[level_name] = {
                    'buy': latest_buy,
                    'sell': latest_sell,
                    'kl_count': len(list(kl_data))
                }

        if not level_bsp_info:
            self.nesting_text.insert(tk.END, "各级别均无买卖点\n")
            return

        total_levels = len(self.current_levels)
        self.nesting_text.insert(tk.END, f"【{total_levels}级别区间套共振分析】\n\n")

        # 分析买点共振
        buy_resonance = self._collect_resonance(level_bsp_info, is_buy=True)
        self._display_resonance(buy_resonance, is_buy=True, total_levels=total_levels)

        # 分析卖点共振
        sell_resonance = self._collect_resonance(level_bsp_info, is_buy=False)
        self._display_resonance(sell_resonance, is_buy=False, total_levels=total_levels)

    def _collect_resonance(self, level_bsp_info: dict, is_buy: bool) -> list:
        """收集买点或卖点共振信息"""
        resonance = []
        key = 'buy' if is_buy else 'sell'
        for level_name, info in level_bsp_info.items():
            if info[key]:
                bsp = info[key]
                kl_count = info['kl_count']
                recency = (kl_count - bsp.klu.idx) / kl_count
                resonance.append({
                    'level': level_name,
                    'type': bsp.type2str(),
                    'price': bsp.bi.get_end_val(),
                    'recency': recency
                })
        return resonance

    def _display_resonance(self, resonance: list, is_buy: bool, total_levels: int):
        """显示共振分析结果"""
        signal_type = "买点" if is_buy else "卖点"
        action = "做多" if is_buy else "做空/减仓"

        if not resonance:
            self.nesting_text.insert(tk.END, f"{signal_type}信号: 无\n\n")
            return

        self.nesting_text.insert(tk.END, f"{signal_type}信号:\n")
        for r in resonance:
            recent_str = "★近期" if r['recency'] < 0.1 else "较早"
            self.nesting_text.insert(tk.END,
                f"  {r['level']}: {r['type']}类 @{r['price']:.2f} ({recent_str})\n")

        # 计算共振强度
        recent_count = sum(1 for r in resonance if r['recency'] < 0.1)
        total_count = len(resonance)

        # 根据级别数和共振数判断强度
        if recent_count >= 4:
            strength = "★★★★ 极强共振"
            desc = f"4级别{signal_type}共振！强烈{action}信号"
        elif recent_count >= 3:
            strength = "★★★ 强共振"
            desc = f"3级别{signal_type}共振！关注{action}机会"
        elif recent_count >= 2:
            strength = "★★ 中等共振"
            desc = f"2级别{signal_type}共振，可关注{action}"
        elif total_count >= 2:
            strength = "★ 弱共振"
            desc = f"有{signal_type}但时间分散，谨慎操作"
        else:
            strength = ""
            desc = ""

        if strength:
            self.nesting_text.insert(tk.END, f"\n  {strength}\n  {desc}\n")
        self.nesting_text.insert(tk.END, "\n")

    def show_interval_nesting_info(self):
        """显示区间套原理说明"""
        messagebox.showinfo("区间套原理说明", INTERVAL_NESTING_INFO)

    def save_chart(self):
        """保存图表"""
        if not self.chan_dict:
            messagebox.showwarning("警告", "请先分析股票")
            return

        code = self.get_current_code().replace('.', '_')
        levels_str = "_".join([self.get_level_name(lv) for lv in self.current_levels])
        default_name = f"{code}_multilevel_{levels_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")],
            initialfile=default_name
        )

        if filename:
            self.fig.savefig(filename, dpi=150, bbox_inches='tight')
            self.status_var.set(f'图片已保存: {filename}')

    def open_single_level_viewer(self):
        """打开单级别K线分析器"""
        try:
            from chan_viewer_tk import ChanViewerWindow
            # 传递当前股票信息
            window = ChanViewerWindow(self.master)
            # 同步当前股票代码到新窗口
            current_code = self.code_var.get()
            if current_code:
                window.code_var.set(current_code)
        except ImportError:
            # 如果导入失败，使用 subprocess 启动
            import subprocess
            script_path = Path(__file__).parent / "chan_viewer_tk.py"
            subprocess.Popen([sys.executable, str(script_path)])

    def toggle_auto_refresh(self):
        """切换自动刷新"""
        if self.auto_refresh_var.get():
            interval = self.refresh_interval_var.get() * 1000
            self._schedule_refresh(interval)
            self.status_var.set(f'自动刷新已启用 (间隔: {self.refresh_interval_var.get()}秒)')
        else:
            if self.auto_refresh_job:
                self.after_cancel(self.auto_refresh_job)
                self.auto_refresh_job = None
            self.status_var.set('自动刷新已关闭')

    def _schedule_refresh(self, interval: int):
        """调度自动刷新"""
        if self.auto_refresh_var.get():
            self.start_analysis()
            self.auto_refresh_job = self.after(interval, lambda: self._schedule_refresh(interval))

    def _update_history_combo(self):
        """更新历史记录下拉框"""
        history = get_stock_history()
        display_list = history.get_display_list(limit=15)
        if display_list:
            self.history_combo['values'] = ['-- 历史记录 --'] + display_list
            self.history_var.set('-- 历史记录 --')
        else:
            self.history_combo['values'] = ['-- 无历史记录 --']
            self.history_var.set('-- 无历史记录 --')

    def on_history_selected(self, event=None):
        """历史记录选择事件"""
        selected = self.history_var.get()
        if selected and not selected.startswith('--'):
            # 设置到股票输入框
            self.code_var.set(selected)
            # 自动开始分析
            self.start_analysis()

    def _add_to_history(self, code: str, name: str):
        """添加股票到历史记录"""
        history = get_stock_history()
        history.add(code, name)
        self._update_history_combo()

    def on_close(self):
        """窗口关闭"""
        if self.is_analyzing:
            self.stop_analysis()

        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)

        if self in MultiLevelViewerWindow.instances:
            MultiLevelViewerWindow.instances.remove(self)

        # 只有当 master 是 MultiLevelApp（独立运行）时才退出主程序
        # 如果是从 ChanApp 统一入口启动的，不要退出
        if len(MultiLevelViewerWindow.instances) == 0:
            if isinstance(self.master, MultiLevelApp):
                self.master.quit()

        self.destroy()


class MultiLevelApp(tk.Tk):
    """主应用"""
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.first_window = MultiLevelViewerWindow(self)

    def run(self):
        self.mainloop()


def main():
    """程序入口"""
    print("启动多级别区间套分析器...")
    load_stock_list()
    app = MultiLevelApp()
    app.run()


if __name__ == '__main__':
    main()
