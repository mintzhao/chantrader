"""
K线形态分析器 - Powered by chan.py

功能说明:
    - 支持全量A股股票搜索（使用 akshare）
    - 支持选择K线周期
    - 支持自动刷新（可配置间隔）
    - 支持多窗口同时查看不同股票
    - 可视化显示K线、笔、线段、中枢、买卖点、MACD等

数据来源:
    - BaoStock: A股历史数据

使用方法:
    python App/chan_viewer_tk.py
"""
import sys
import io
import queue
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading


class StdoutRedirector(io.StringIO):
    """
    重定向 stdout/stderr 到队列，用于在 GUI 中显示日志
    不修改原始项目代码，通过捕获 print 输出实现日志显示
    """
    def __init__(self, log_queue: queue.Queue, original_stream):
        super().__init__()
        self.log_queue = log_queue
        self.original_stream = original_stream

    def write(self, text):
        if text.strip():  # 忽略空行
            self.log_queue.put(text)
        # 同时输出到原始流（终端）
        if self.original_stream:
            self.original_stream.write(text)
            self.original_stream.flush()

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

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


# K线周期映射（按指定顺序）
# 注意：1分钟使用 akshare 数据源，其他使用 BaoStock
KL_TYPE_MAP = {
    "1分钟": KL_TYPE.K_1M,
    "5分钟": KL_TYPE.K_5M,
    "15分钟": KL_TYPE.K_15M,
    "30分钟": KL_TYPE.K_30M,
    "60分钟": KL_TYPE.K_60M,
    "日线": KL_TYPE.K_DAY,
    "周线": KL_TYPE.K_WEEK,
    "月线": KL_TYPE.K_MON,
}

# 分钟级别K线使用 akshare（数据更新更及时，盘中可获取当天数据）
# BaoStock 分钟数据要等到当天 20:30 才更新，akshare 盘中即可获取
AKSHARE_KL_TYPES = {KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M}

# 买卖点图例说明
BSP_LEGEND = """
买卖点说明:
  b1  = 一类买点 (趋势背驰)
  b2  = 二类买点 (回调不破)
  b3a = 三类买点 (中枢后)
  b3b = 三类买点 (中枢前)
  b1p = 盘整一类买点
  b2s = 类二买点

  s1/s2/s3a/s3b/s1p/s2s
  = 对应的卖点

图形说明:
  实线 = 已确认
  虚线 = 未确认
  橙框 = 中枢区间
"""


# 全局股票列表缓存
_stock_list_cache: List[tuple] = []


def load_stock_list() -> List[tuple]:
    """
    从本地 CSV 文件加载股票列表
    Returns: [(baostock_code, name), ...]  如 [("sz.000001", "平安银行"), ...]

    注意：需要先运行 download_stock_list.py 下载股票列表
    """
    global _stock_list_cache
    if _stock_list_cache:
        return _stock_list_cache

    csv_path = Path(__file__).parent / "stock_list.csv"

    if csv_path.exists():
        try:
            import csv
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                result = [(row['code'], row['name']) for row in reader]
            _stock_list_cache = result
            print(f"已从本地文件加载 {len(result)} 只股票")
            return result
        except Exception as e:
            print(f"读取股票列表文件失败: {e}")

    # 如果本地文件不存在，返回预设列表
    print("未找到股票列表文件，请先运行: python App/download_stock_list.py")
    return [
        ("sz.000001", "平安银行"),
        ("sh.600000", "浦发银行"),
        ("sz.002639", "雪人股份"),
        ("sz.002703", "浙江世宝"),
        ("sh.600519", "贵州茅台"),
        ("sz.000858", "五粮液"),
        ("sh.601318", "中国平安"),
        ("sz.300750", "宁德时代"),
        ("sh.000300", "沪深300"),
        ("sh.000001", "上证指数"),
    ]


class StockSearchEntry(ttk.Frame):
    """
    全量A股股票搜索输入框
    - 简单的输入框 + 搜索结果列表
    - 支持代码、名称模糊搜索
    """
    def __init__(self, master, textvariable=None, width=25, **kwargs):
        super().__init__(master, **kwargs)

        self.text_var = textvariable or tk.StringVar()
        self.stock_list: List[tuple] = []  # [(code, name), ...]
        self.filtered_list: List[tuple] = []

        # 输入框
        self.entry = ttk.Entry(self, textvariable=self.text_var, width=width)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 搜索按钮
        self.search_btn = ttk.Button(self, text="搜", width=3, command=self.do_search)
        self.search_btn.pack(side=tk.LEFT, padx=(2, 0))

        # 下拉列表窗口
        self.popup = None
        self.listbox = None

        # 绑定事件
        self.entry.bind('<KeyRelease>', self.on_key_release)
        self.entry.bind('<Return>', self.on_enter)
        self.entry.bind('<Escape>', self.hide_popup)
        self.entry.bind('<Down>', self.focus_listbox)

        # 直接加载股票列表（读本地文件很快）
        self.stock_list = load_stock_list()

    def do_search(self):
        """执行搜索"""
        self.on_key_release(None)

    def on_key_release(self, event):
        """键盘输入时搜索"""
        if event and event.keysym in ('Up', 'Down', 'Return', 'Escape', 'Tab'):
            return

        keyword = self.text_var.get().strip().lower()
        if len(keyword) < 1:
            self.hide_popup()
            return

        # 模糊搜索
        self.filtered_list = []
        for code, name in self.stock_list:
            code_num = code.replace('sz.', '').replace('sh.', '')
            if (keyword in code.lower() or
                keyword in code_num or
                keyword in name.lower()):
                self.filtered_list.append((code, name))
                if len(self.filtered_list) >= 50:  # 限制显示数量
                    break

        if self.filtered_list:
            self.show_popup()
        else:
            self.hide_popup()

    def show_popup(self):
        """显示搜索结果列表"""
        if not self.filtered_list:
            return

        # 创建或更新弹出窗口
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

        # 更新列表内容
        self.listbox.delete(0, tk.END)
        for code, name in self.filtered_list:
            self.listbox.insert(tk.END, f"{code}  {name}")

        # 定位弹出窗口
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        height = min(300, len(self.filtered_list) * 20 + 10)
        self.popup.geometry(f"280x{height}+{x}+{y}")
        self.popup.deiconify()

    def hide_popup(self, event=None):
        """隐藏弹出窗口"""
        if self.popup and self.popup.winfo_exists():
            self.popup.withdraw()

    def focus_listbox(self, event=None):
        """焦点移到列表"""
        if self.listbox and self.popup and self.popup.winfo_exists():
            self.listbox.focus_set()
            if self.listbox.size() > 0:
                self.listbox.selection_set(0)

    def on_enter(self, event=None):
        """回车确认"""
        if self.listbox and self.listbox.curselection():
            self.on_select()
        self.hide_popup()

    def on_select(self, event=None):
        """选择列表项"""
        if self.listbox and self.listbox.curselection():
            selection = self.listbox.get(self.listbox.curselection())
            self.text_var.set(selection)
            self.hide_popup()

    def get(self) -> str:
        return self.text_var.get()

    def set(self, value: str):
        self.text_var.set(value)


class ChanViewerWindow(tk.Toplevel):
    """
    K线形态分析窗口
    """

    window_count = 0
    instances: List['ChanViewerWindow'] = []

    # 全局日志队列和重定向器（所有窗口共享）
    _log_queue: Optional[queue.Queue] = None
    _stdout_redirector: Optional[StdoutRedirector] = None
    _stderr_redirector: Optional[StdoutRedirector] = None

    @classmethod
    def setup_log_redirection(cls):
        """设置全局日志重定向（只执行一次）"""
        if cls._log_queue is None:
            cls._log_queue = queue.Queue()
            cls._stdout_redirector = StdoutRedirector(cls._log_queue, sys.stdout)
            cls._stderr_redirector = StdoutRedirector(cls._log_queue, sys.stderr)
            sys.stdout = cls._stdout_redirector
            sys.stderr = cls._stderr_redirector

    def __init__(self, master=None):
        super().__init__(master)

        ChanViewerWindow.window_count += 1
        ChanViewerWindow.instances.append(self)

        # 设置日志重定向
        ChanViewerWindow.setup_log_redirection()

        self.chan: Optional[CChan] = None
        self.is_analyzing = False
        self.auto_refresh_job = None
        self.current_stock_name = ""
        self.analysis_thread: Optional[threading.Thread] = None

        self.init_ui()

        # 启动日志轮询
        self._poll_log_queue()

        # 设置窗口位置
        offset = (ChanViewerWindow.window_count - 1) * 30
        self.geometry(f"1400x900+{100 + offset}+{100 + offset}")
        self.minsize(1000, 700)

        # 窗口关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 绑定窗口大小改变事件
        self.bind('<Configure>', self.on_window_resize)

    def on_window_resize(self, event):
        """窗口大小改变时重绘图表"""
        # 只处理窗口本身的resize事件
        if event.widget == self and self.chan:
            # 使用 after 避免频繁重绘
            if hasattr(self, '_resize_job'):
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(200, self.plot_chart)

    def init_ui(self):
        """初始化用户界面"""
        self.title(f'K线形态分析 #{ChanViewerWindow.window_count}')

        # 配置 grid 权重，使图表区域可以自适应
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # === 顶部控制栏 ===
        control_frame = ttk.Frame(self, padding="5")
        control_frame.grid(row=0, column=0, sticky="ew")

        # 股票选择（全量搜索）
        ttk.Label(control_frame, text="股票:").pack(side=tk.LEFT, padx=(0, 5))
        self.code_var = tk.StringVar(value="sz.002639  雪人股份")
        self.code_entry = StockSearchEntry(
            control_frame,
            textvariable=self.code_var,
            width=24
        )
        self.code_entry.pack(side=tk.LEFT, padx=(0, 5))

        # 历史记录下拉框
        self.history_var = tk.StringVar(value="")
        self.history_combo = ttk.Combobox(
            control_frame, textvariable=self.history_var,
            values=[], width=20, state="readonly"
        )
        self.history_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.history_combo.bind('<<ComboboxSelected>>', self.on_history_selected)
        self._update_history_combo()  # 初始化历史记录列表

        # K线周期
        ttk.Label(control_frame, text="周期:").pack(side=tk.LEFT, padx=(0, 5))
        self.kl_type_var = tk.StringVar(value="日线")
        self.kl_type_combo = ttk.Combobox(
            control_frame, textvariable=self.kl_type_var,
            values=list(KL_TYPE_MAP.keys()), width=8, state="readonly"
        )
        self.kl_type_combo.pack(side=tk.LEFT, padx=(0, 10))

        # 周期数
        ttk.Label(control_frame, text="周期数:").pack(side=tk.LEFT, padx=(0, 5))
        self.periods_var = tk.IntVar(value=300)
        self.periods_spin = ttk.Spinbox(
            control_frame, from_=50, to=2000,
            textvariable=self.periods_var, width=6
        )
        self.periods_spin.pack(side=tk.LEFT, padx=(0, 10))

        # 分析/停止按钮
        self.analyze_btn = ttk.Button(
            control_frame, text="分析",
            command=self.toggle_analysis
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 5))

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

        # 新窗口按钮
        self.new_window_btn = ttk.Button(
            control_frame, text="新窗口",
            command=self.open_new_window
        )
        self.new_window_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 保存按钮
        self.save_btn = ttk.Button(
            control_frame, text="保存图片",
            command=self.save_chart
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 多级别分析按钮
        ttk.Button(
            control_frame, text="多级别分析",
            command=self.open_multilevel_viewer
        ).pack(side=tk.LEFT)

        # === 绘图选项 ===
        plot_options_frame = ttk.Frame(self, padding="5")
        plot_options_frame.grid(row=1, column=0, sticky="ew")

        ttk.Label(plot_options_frame, text="显示:").pack(side=tk.LEFT)

        self.plot_kline_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options_frame, text="K线",
                        variable=self.plot_kline_var).pack(side=tk.LEFT, padx=3)

        self.plot_combine_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options_frame, text="合并K线",
                        variable=self.plot_combine_var).pack(side=tk.LEFT, padx=3)

        self.plot_bi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options_frame, text="笔",
                        variable=self.plot_bi_var).pack(side=tk.LEFT, padx=3)

        self.plot_seg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options_frame, text="线段",
                        variable=self.plot_seg_var).pack(side=tk.LEFT, padx=3)

        self.plot_zs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options_frame, text="中枢",
                        variable=self.plot_zs_var).pack(side=tk.LEFT, padx=3)

        self.plot_bsp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options_frame, text="买卖点",
                        variable=self.plot_bsp_var).pack(side=tk.LEFT, padx=3)

        self.plot_macd_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot_options_frame, text="MACD",
                        variable=self.plot_macd_var).pack(side=tk.LEFT, padx=3)

        ttk.Separator(plot_options_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 刷新图表按钮
        ttk.Button(plot_options_frame, text="刷新图表",
                   command=self.plot_chart).pack(side=tk.LEFT)

        # 图例说明按钮
        ttk.Button(plot_options_frame, text="图例说明",
                   command=self.show_legend).pack(side=tk.LEFT, padx=(10, 0))

        # === 主内容区域（图表 + 图例） ===
        content_frame = ttk.Frame(self)
        content_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # 图表区域（自适应大小）
        chart_frame = ttk.Frame(content_frame)
        chart_frame.grid(row=0, column=0, sticky="nsew")
        chart_frame.grid_rowconfigure(0, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)

        # matplotlib 画布
        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # 右侧面板（选项卡：图例 + 日志）
        right_panel = ttk.Notebook(content_frame)
        right_panel.grid(row=0, column=1, sticky="ns", padx=(5, 0))

        # 图例标签页
        legend_frame = ttk.Frame(right_panel, padding="5")
        right_panel.add(legend_frame, text="买卖点说明")

        legend_text = tk.Text(legend_frame, width=22, height=20, font=("Consolas", 9),
                               bg="#f5f5f5", relief=tk.FLAT)
        legend_text.insert(tk.END, self.get_short_legend())
        legend_text.config(state=tk.DISABLED)
        legend_text.pack(fill=tk.BOTH, expand=True)

        # 日志标签页
        log_frame = ttk.Frame(right_panel, padding="5")
        right_panel.add(log_frame, text="分析日志")

        # 日志文本框（带滚动条）
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, width=30, height=20, font=("Consolas", 9),
                                 bg="#1e1e1e", fg="#d4d4d4", relief=tk.FLAT,
                                 yscrollcommand=log_scroll.set, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

        # 配置日志文本标签颜色
        self.log_text.tag_configure("warning", foreground="#ffcc00")
        self.log_text.tag_configure("error", foreground="#ff6b6b")
        self.log_text.tag_configure("info", foreground="#4fc3f7")
        self.log_text.tag_configure("normal", foreground="#d4d4d4")

        # 清空日志按钮
        clear_log_btn = ttk.Button(log_frame, text="清空日志", command=self.clear_log)
        clear_log_btn.pack(pady=(5, 0))

        # === 状态栏 ===
        status_frame = ttk.Frame(self)
        status_frame.grid(row=3, column=0, sticky="ew")

        self.status_var = tk.StringVar(value='就绪 - 输入股票代码或名称搜索，点击"分析"')
        self.status_bar = ttk.Label(status_frame, textvariable=self.status_var,
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)

        # 股票名称显示
        self.stock_name_var = tk.StringVar(value='')
        self.stock_name_label = ttk.Label(
            status_frame, textvariable=self.stock_name_var,
            font=("Arial", 10, "bold"), foreground="#0066cc"
        )
        self.stock_name_label.pack(side=tk.RIGHT, padx=10)

    def get_short_legend(self) -> str:
        """获取简短图例说明"""
        return """买点 (b=buy):
 b1   趋势背驰买点
 b2   回调不破买点
 b3a  中枢后三买
 b3b  中枢前三买
 b1p  盘整背驰买点
 b2s  类二买点

卖点 (s=sell):
 s1   趋势背驰卖点
 s2   反弹不破卖点
 s3a  中枢后三卖
 s3b  中枢前三卖
 s1p  盘整背驰卖点
 s2s  类二卖点

图形:
 ─── 实线=已确认
 --- 虚线=未确认
 [橙框] 中枢区间
"""

    def show_legend(self):
        """显示完整图例说明"""
        messagebox.showinfo("买卖点图例说明", BSP_LEGEND)

    def _poll_log_queue(self):
        """轮询日志队列，更新日志显示"""
        try:
            while True:
                try:
                    msg = ChanViewerWindow._log_queue.get_nowait()
                    self._append_log(msg)
                except queue.Empty:
                    break
        except Exception:
            pass
        # 继续轮询
        self.after(100, self._poll_log_queue)

    def _append_log(self, text: str):
        """追加日志到文本框"""
        if not hasattr(self, 'log_text'):
            return

        # 根据内容确定标签
        tag = "normal"
        if "[WARNING" in text:
            tag = "warning"
        elif "[ERROR" in text or "[错误]" in text:
            tag = "error"
        elif "[分析]" in text or "正在" in text or "完成" in text or "加载" in text:
            tag = "info"

        self.log_text.insert(tk.END, text + "\n", tag)
        self.log_text.see(tk.END)  # 自动滚动到底部

    def clear_log(self):
        """清空日志"""
        if hasattr(self, 'log_text'):
            self.log_text.delete(1.0, tk.END)

    def get_current_code(self) -> str:
        """获取当前选择的股票代码"""
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
            parts = text.split('  ')
            if len(parts) >= 2:
                return parts[1]
        return ""

    def get_chan_config(self) -> CChanConfig:
        """获取配置"""
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
            "print_warning": True,  # 启用日志输出
            "print_err_time": True,  # 启用错误时间输出
            "zs_algo": "normal",
        })

    def get_plot_config(self) -> dict:
        """获取绑图配置"""
        return {
            "plot_kline": self.plot_kline_var.get(),
            "plot_kline_combine": self.plot_combine_var.get(),
            "plot_bi": self.plot_bi_var.get(),
            "plot_seg": self.plot_seg_var.get(),
            "plot_zs": self.plot_zs_var.get(),
            "plot_bsp": self.plot_bsp_var.get(),
            "plot_macd": self.plot_macd_var.get(),
        }

    def calc_days_from_periods(self, periods: int, kl_type: KL_TYPE) -> int:
        """根据周期数和K线类型计算需要的天数"""
        if kl_type == KL_TYPE.K_1M:
            # 1分钟K线：每天约240根（4小时交易时间），akshare最多5天数据
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

    def toggle_analysis(self):
        """切换分析/停止状态"""
        if self.is_analyzing:
            self.stop_analysis()
        else:
            self.start_analysis()

    def stop_analysis(self):
        """停止分析"""
        self.is_analyzing = False
        self.analyze_btn.config(text="分析")
        self.status_var.set('分析已停止')

    def start_analysis(self):
        """开始分析"""
        if self.is_analyzing:
            return

        code = self.get_current_code()
        if not code:
            messagebox.showwarning("警告", "请输入股票代码")
            return

        self.current_stock_name = self.get_current_stock_name()
        self.is_analyzing = True
        self.analyze_btn.config(text="停止")
        self.status_var.set(f'正在分析 {code} {self.current_stock_name}...')
        self.update()

        # 在后台线程执行分析
        self.analysis_thread = threading.Thread(target=self._do_analysis_thread, args=(code,), daemon=True)
        self.analysis_thread.start()

    def _do_analysis_thread(self, code: str):
        """在线程中执行分析"""
        try:
            kl_type_name = self.kl_type_var.get()
            kl_type = KL_TYPE_MAP.get(kl_type_name, KL_TYPE.K_DAY)
            periods = self.periods_var.get()
            days = self.calc_days_from_periods(periods, kl_type)
            begin_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            # 根据 K线类型选择数据源
            # 分钟级别K线使用 akshare（数据更新更及时，盘中可获取当天数据）
            # 日/周/月线使用 BaoStock（历史数据更完整）
            if kl_type in AKSHARE_KL_TYPES:
                data_src = DATA_SRC.AKSHARE
                data_src_name = "AkShare"
            else:
                data_src = DATA_SRC.BAO_STOCK
                data_src_name = "BaoStock"

            # GUI层面的进度日志（不修改原始项目代码）
            print(f"[分析] 开始分析 {code} ({kl_type_name})")
            print(f"[分析] 时间范围: {begin_time} ~ 今天, 约 {periods} 个周期")
            print(f"[分析] 正在连接 {data_src_name} 获取数据...")

            chan = CChan(
                code=code,
                begin_time=begin_time,
                end_time=None,
                data_src=data_src,
                lv_list=[kl_type],
                config=self.get_chan_config(),
                autype=AUTYPE.QFQ,
            )

            # 输出分析结果统计
            kl_data = chan[0]
            print(f"[分析] 数据获取完成，共 {len(kl_data)} 根K线")
            print(f"[分析] 缠论计算完成:")
            print(f"       - 笔: {len(kl_data.bi_list)} 个")
            print(f"       - 线段: {len(kl_data.seg_list)} 个")
            print(f"       - 中枢: {len(kl_data.zs_list)} 个")
            print(f"       - 买卖点: {len(kl_data.bs_point_lst)} 个")

            # 在主线程更新 UI
            self.after(0, lambda: self._on_analysis_done(chan, code, kl_type_name))

        except Exception as e:
            error_msg = str(e)
            print(f"[错误] 分析失败: {error_msg}")
            self.after(0, lambda msg=error_msg: self._on_analysis_error(msg))

    def _on_analysis_done(self, chan: CChan, code: str, kl_type_name: str):
        """分析完成回调"""
        if not self.is_analyzing:
            # 已被停止
            return

        self.chan = chan
        self.is_analyzing = False
        self.analyze_btn.config(text="分析")

        # 更新窗口标题和股票名称显示
        display_name = f"{code} {self.current_stock_name}" if self.current_stock_name else code
        self.title(f'{display_name} - {kl_type_name}')
        self.stock_name_var.set(display_name)

        # 添加到历史记录
        self._add_to_history(code, self.current_stock_name)

        # 绑制图表
        self.plot_chart()

        # 统计信息
        kl_data = chan[0]
        bi_count = len(kl_data.bi_list)
        seg_count = len(kl_data.seg_list)
        zs_count = len(kl_data.zs_list)
        bsp_count = len(kl_data.bs_point_lst)

        self.status_var.set(
            f'分析完成 | K线: {len(kl_data)} | 笔: {bi_count} | '
            f'线段: {seg_count} | 中枢: {zs_count} | 买卖点: {bsp_count}'
        )

    def _on_analysis_error(self, error_msg: str):
        """分析出错回调"""
        self.is_analyzing = False
        self.analyze_btn.config(text="分析")
        messagebox.showerror("分析错误", f"分析失败:\n{error_msg}")
        self.status_var.set('分析失败')

    def plot_chart(self):
        """绘制图表（自适应窗口大小）"""
        if not self.chan:
            return

        try:
            from Plot.PlotDriver import CPlotDriver

            # 关闭旧的 figure
            plt.close('all')

            plot_config = self.get_plot_config()

            # 获取画布实际大小
            canvas_widget = self.canvas.get_tk_widget()
            canvas_width = canvas_widget.winfo_width()
            canvas_height = canvas_widget.winfo_height()

            # 计算合适的图表尺寸（自适应）
            dpi = 100
            fig_width = max(canvas_width / dpi, 10)

            # 计算基础高度（不含MACD）
            # PlotDriver中MACD会使用额外的 h * macd_h_ratio 空间
            # 默认 macd_h_ratio = 0.3
            # 所以如果启用MACD，总高度会变成 h * (1 + 0.3) = h * 1.3
            # 我们需要反向计算，使得最终总高度符合画布高度
            if plot_config.get("plot_macd", False):
                # 启用MACD时，PlotDriver会创建 h * 1.3 的总高度
                # 所以传入的 h 应该是 canvas_height / 1.3
                macd_h_ratio = 0.3
                fig_height = max(canvas_height / dpi / (1 + macd_h_ratio), 5)
            else:
                fig_height = max(canvas_height / dpi, 6)

            plot_para = {
                "figure": {
                    "w": fig_width,
                    "h": fig_height,
                }
            }

            plot_driver = CPlotDriver(
                self.chan,
                plot_config=plot_config,
                plot_para=plot_para
            )

            # 更新画布
            self.fig = plot_driver.figure
            self.canvas.figure = self.fig
            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("绑图错误", str(e))

    def save_chart(self):
        """保存图表为图片"""
        if not self.chan:
            messagebox.showwarning("警告", "请先分析股票")
            return

        code = self.get_current_code().replace('.', '_')
        name = self.current_stock_name
        kl_type = self.kl_type_var.get()
        default_name = f"{code}_{name}_{kl_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")],
            initialfile=default_name
        )

        if filename:
            self.fig.savefig(filename, dpi=150, bbox_inches='tight')
            self.status_var.set(f'图片已保存: {filename}')

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

    def open_new_window(self):
        """打开新窗口"""
        ChanViewerWindow(self.master)

    def open_multilevel_viewer(self):
        """打开多级别区间套分析器"""
        try:
            from chan_viewer_multilevel_tk import MultiLevelViewerWindow
            # 传递当前股票信息
            multilevel_window = MultiLevelViewerWindow(self.master)
            # 同步当前股票代码到新窗口
            current_code = self.code_var.get()
            if current_code:
                multilevel_window.code_var.set(current_code)
        except ImportError:
            # 如果导入失败，使用 subprocess 启动
            import subprocess
            script_path = Path(__file__).parent / "chan_viewer_multilevel_tk.py"
            subprocess.Popen([sys.executable, str(script_path)])

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
        """窗口关闭事件"""
        # 停止分析
        if self.is_analyzing:
            self.stop_analysis()

        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)

        if self in ChanViewerWindow.instances:
            ChanViewerWindow.instances.remove(self)

        # 只有当 master 是 ChanViewerApp（独立运行）时才退出主程序
        # 如果是从 ChanApp 统一入口启动的，不要退出
        if len(ChanViewerWindow.instances) == 0:
            if isinstance(self.master, ChanViewerApp):
                self.master.quit()

        self.destroy()


class ChanViewerApp(tk.Tk):
    """主应用程序"""

    def __init__(self):
        super().__init__()
        self.withdraw()  # 隐藏主窗口
        self.first_window = ChanViewerWindow(self)

    def run(self):
        self.mainloop()


def main():
    """程序入口"""
    print("启动 K线形态分析器...")
    # 预加载股票列表
    load_stock_list()
    app = ChanViewerApp()
    app.run()


if __name__ == '__main__':
    main()
