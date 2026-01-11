"""
缠论分析器 - 统一入口
Powered by chan.py

功能说明:
    - 作为应用统一入口，管理所有分析窗口
    - 支持打开单级别K线分析器
    - 支持打开多级别区间套分析器
    - 各窗口独立运行，关闭子窗口不影响主程序

使用方法:
    python App/chan_app.py
"""
import sys
import os
from pathlib import Path

# PyInstaller 打包兼容：设置正确的模块搜索路径
def setup_paths():
    """设置模块搜索路径，兼容 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后运行
        # sys._MEIPASS 是 PyInstaller 解压临时目录
        base_path = sys._MEIPASS
    else:
        # 普通 Python 运行
        base_path = str(Path(__file__).resolve().parent.parent)

    # 将基础路径加入 sys.path
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    # 设置工作目录（用于加载数据文件如 stock_list.csv）
    if getattr(sys, 'frozen', False):
        # 打包后，数据文件在 _MEIPASS 目录
        os.chdir(base_path)

    return base_path

# 在导入其他模块前设置路径
BASE_PATH = setup_paths()

import tkinter as tk
from tkinter import ttk


class ChanApp(tk.Tk):
    """缠论分析器主应用"""

    def __init__(self):
        super().__init__()

        self.title("缠论分析器")
        self.geometry("400x380")
        self.resizable(False, False)

        # 窗口居中
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # 跟踪打开的窗口
        self.single_level_windows = []
        self.multi_level_windows = []
        self.scanner_windows = []

        self.init_ui()

        # 主窗口关闭时退出程序
        self.protocol("WM_DELETE_WINDOW", self._on_main_close)

        # 预加载股票列表
        self.after(100, self._preload_stock_list)

    def init_ui(self):
        """初始化界面"""
        # 标题
        title_frame = ttk.Frame(self, padding="20")
        title_frame.pack(fill=tk.X)

        ttk.Label(
            title_frame,
            text="缠论分析器",
            font=("Arial", 18, "bold")
        ).pack()

        ttk.Label(
            title_frame,
            text="Powered by chan.py",
            font=("Arial", 10),
            foreground="gray"
        ).pack(pady=(5, 0))

        # 分隔线
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # 功能按钮区
        button_frame = ttk.Frame(self, padding="20")
        button_frame.pack(fill=tk.BOTH, expand=True)

        # 单级别分析按钮
        single_btn = ttk.Button(
            button_frame,
            text="单级别K线分析",
            command=self.open_single_level,
            width=25
        )
        single_btn.pack(pady=10)

        ttk.Label(
            button_frame,
            text="支持日/周/月/分钟级别K线分析",
            font=("Arial", 9),
            foreground="gray"
        ).pack()

        # 多级别分析按钮
        multi_btn = ttk.Button(
            button_frame,
            text="多级别区间套分析",
            command=self.open_multi_level,
            width=25
        )
        multi_btn.pack(pady=(20, 10))

        ttk.Label(
            button_frame,
            text="支持多级别联合分析，区间套买卖点定位",
            font=("Arial", 9),
            foreground="gray"
        ).pack()

        # 买点扫描器按钮
        scanner_btn = ttk.Button(
            button_frame,
            text="A股买点扫描",
            command=self.open_bsp_scanner,
            width=25
        )
        scanner_btn.pack(pady=(20, 10))

        ttk.Label(
            button_frame,
            text="批量扫描A股，自动发现近期买点股票",
            font=("Arial", 9),
            foreground="gray"
        ).pack()

        # 状态栏
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        ).pack(fill=tk.X)

    def _preload_stock_list(self):
        """预加载股票列表"""
        self.status_var.set("正在加载股票列表...")
        self.update()

        try:
            from chan_viewer_tk import load_stock_list
            stock_list = load_stock_list()
            self.status_var.set(f"就绪 - 已加载 {len(stock_list)} 只股票")
        except Exception as e:
            self.status_var.set(f"加载股票列表失败: {e}")

    def open_single_level(self):
        """打开单级别分析窗口"""
        try:
            from chan_viewer_tk import ChanViewerWindow

            # 创建窗口，父窗口设为 self
            window = ChanViewerWindow(self)

            # 修改窗口关闭行为
            window.protocol("WM_DELETE_WINDOW", lambda w=window: self._on_child_close(w, self.single_level_windows))

            self.single_level_windows.append(window)
            self.status_var.set(f"已打开单级别分析窗口 (共 {len(self.single_level_windows)} 个)")

        except Exception as e:
            self.status_var.set(f"打开失败: {e}")
            import traceback
            traceback.print_exc()

    def open_multi_level(self):
        """打开多级别分析窗口"""
        try:
            from chan_viewer_multilevel_tk import MultiLevelViewerWindow

            # 创建窗口，父窗口设为 self
            window = MultiLevelViewerWindow(self)

            # 修改窗口关闭行为
            window.protocol("WM_DELETE_WINDOW", lambda w=window: self._on_child_close(w, self.multi_level_windows))

            self.multi_level_windows.append(window)
            self.status_var.set(f"已打开多级别分析窗口 (共 {len(self.multi_level_windows)} 个)")

        except Exception as e:
            self.status_var.set(f"打开失败: {e}")
            import traceback
            traceback.print_exc()

    def open_bsp_scanner(self):
        """打开买点扫描器窗口"""
        try:
            from ashare_bsp_scanner_tk import BspScannerWindow

            # 创建窗口，父窗口设为 self
            window = BspScannerWindow(self)

            # 修改窗口关闭行为
            window.protocol("WM_DELETE_WINDOW", lambda w=window: self._on_child_close(w, self.scanner_windows))

            self.scanner_windows.append(window)
            self.status_var.set(f"已打开买点扫描器窗口 (共 {len(self.scanner_windows)} 个)")

        except Exception as e:
            self.status_var.set(f"打开失败: {e}")
            import traceback
            traceback.print_exc()

    def _on_child_close(self, window, window_list):
        """处理子窗口关闭"""
        # 调用窗口自身的关闭逻辑（清理资源）
        if hasattr(window, 'on_close'):
            # 临时修改 on_close 行为，避免调用 quit()
            original_on_close = window.on_close

            def safe_close():
                # 停止分析
                if hasattr(window, 'is_analyzing') and window.is_analyzing:
                    window.stop_analysis()

                # 取消自动刷新
                if hasattr(window, 'auto_refresh_job') and window.auto_refresh_job:
                    window.after_cancel(window.auto_refresh_job)

                # 从类实例列表中移除
                if hasattr(window, '__class__'):
                    cls = window.__class__
                    if hasattr(cls, 'instances') and window in cls.instances:
                        cls.instances.remove(window)

            safe_close()

        # 从本地列表移除
        if window in window_list:
            window_list.remove(window)

        # 销毁窗口
        window.destroy()

        # 更新状态
        total = len(self.single_level_windows) + len(self.multi_level_windows) + len(self.scanner_windows)
        if total > 0:
            self.status_var.set(f"当前打开 {total} 个分析窗口")
        else:
            self.status_var.set("就绪")

    def _on_main_close(self):
        """主窗口关闭时，关闭所有子窗口并退出"""
        # 关闭所有子窗口
        for window in self.single_level_windows[:]:
            self._on_child_close(window, self.single_level_windows)
        for window in self.multi_level_windows[:]:
            self._on_child_close(window, self.multi_level_windows)
        for window in self.scanner_windows[:]:
            self._on_child_close(window, self.scanner_windows)

        # 退出程序
        self.quit()
        self.destroy()

    def run(self):
        """启动应用"""
        self.mainloop()


def main():
    """程序入口"""
    print("启动缠论分析器...")
    app = ChanApp()
    app.run()


if __name__ == '__main__':
    main()
