"""
缠论多窗口查看器 - Powered by chan.py

功能说明:
    - 支持选择股票代码、K线周期
    - 支持自动刷新（可配置间隔）
    - 支持多窗口同时查看不同股票
    - 可视化显示K线、笔、线段、中枢、买卖点、MACD等

数据来源:
    - BaoStock: A股历史数据（默认）
    - Akshare: A股实时数据

使用方法:
    python App/chan_viewer.py
"""
import sys
from pathlib import Path

# 将项目根目录加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QGroupBox,
    QMessageBox, QStatusBar, QSpinBox, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE


# K线周期映射
KL_TYPE_MAP = {
    "日线": KL_TYPE.K_DAY,
    "周线": KL_TYPE.K_WEEK,
    "月线": KL_TYPE.K_MON,
    "60分钟": KL_TYPE.K_60M,
    "30分钟": KL_TYPE.K_30M,
    "15分钟": KL_TYPE.K_15M,
    "5分钟": KL_TYPE.K_5M,
}

# 数据源映射
DATA_SRC_MAP = {
    "BaoStock": DATA_SRC.BAO_STOCK,
    "Akshare": DATA_SRC.AKSHARE,
}

# 预设股票列表
PRESET_STOCKS = [
    ("sz.000001", "平安银行"),
    ("sh.600000", "浦发银行"),
    ("sz.002639", "雪人股份"),
    ("sz.002703", "浙江世宝"),
    ("sh.600519", "贵州茅台"),
    ("sz.000858", "五粮液"),
    ("sh.601318", "中国平安"),
    ("sz.300750", "宁德时代"),
]


class AnalysisThread(QThread):
    """
    股票分析后台线程
    """
    finished = pyqtSignal(object, str)  # (CChan对象, 股票名称)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, code: str, kl_type: KL_TYPE, data_src: DATA_SRC,
                 config: CChanConfig, days: int = 365):
        super().__init__()
        self.code = code
        self.kl_type = kl_type
        self.data_src = data_src
        self.config = config
        self.days = days

    def run(self):
        try:
            self.progress.emit(f"正在获取 {self.code} 数据...")

            # 计算时间范围
            if self.kl_type in [KL_TYPE.K_5M, KL_TYPE.K_15M]:
                days = min(self.days, 60)  # 分钟线数据量大，限制天数
            elif self.kl_type in [KL_TYPE.K_30M, KL_TYPE.K_60M]:
                days = min(self.days, 120)
            else:
                days = self.days

            begin_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            self.progress.emit(f"正在计算 {self.code} 缠论元素...")

            chan = CChan(
                code=self.code,
                begin_time=begin_time,
                end_time=None,
                data_src=self.data_src,
                lv_list=[self.kl_type],
                config=self.config,
                autype=AUTYPE.QFQ,
            )

            # 尝试获取股票名称
            stock_name = self.code
            try:
                if hasattr(chan, 'name') and chan.name:
                    stock_name = chan.name
            except:
                pass

            self.finished.emit(chan, stock_name)

        except Exception as e:
            self.error.emit(str(e))


class ChanPlotCanvas(FigureCanvas):
    """
    嵌入 PyQt 的 Matplotlib 画布
    """
    def __init__(self, parent=None, width=14, height=8):
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(width, height), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(400)

    def clear(self):
        self.fig.clear()
        self.draw()


class ChanViewerWindow(QMainWindow):
    """
    缠论查看器窗口

    每个窗口独立显示一只股票的缠论分析图
    """

    # 窗口计数器（用于新窗口定位）
    window_count = 0
    # 所有窗口实例（防止被垃圾回收）
    instances: List['ChanViewerWindow'] = []

    def __init__(self, parent=None):
        super().__init__(parent)

        ChanViewerWindow.window_count += 1
        ChanViewerWindow.instances.append(self)

        self.chan: Optional[CChan] = None
        self.analysis_thread: Optional[AnalysisThread] = None
        self.auto_refresh_timer: Optional[QTimer] = None
        self.stock_name = ""

        self.init_ui()
        self.init_menu()

        # 设置窗口位置（每个新窗口偏移一点）
        offset = (ChanViewerWindow.window_count - 1) * 30
        self.move(100 + offset, 100 + offset)

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(f'缠论查看器 #{ChanViewerWindow.window_count}')
        self.setGeometry(100, 100, 1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # === 顶部控制栏 ===
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        control_layout = QHBoxLayout(control_frame)

        # 股票选择
        control_layout.addWidget(QLabel("股票代码:"))
        self.code_combo = QComboBox()
        self.code_combo.setEditable(True)
        self.code_combo.setMinimumWidth(150)
        for code, name in PRESET_STOCKS:
            self.code_combo.addItem(f"{code} {name}", code)
        self.code_combo.setCurrentText("sz.002639 雪人股份")
        control_layout.addWidget(self.code_combo)

        # K线周期
        control_layout.addWidget(QLabel("周期:"))
        self.kl_type_combo = QComboBox()
        for name in KL_TYPE_MAP.keys():
            self.kl_type_combo.addItem(name)
        self.kl_type_combo.setCurrentText("日线")
        control_layout.addWidget(self.kl_type_combo)

        # 数据源
        control_layout.addWidget(QLabel("数据源:"))
        self.data_src_combo = QComboBox()
        for name in DATA_SRC_MAP.keys():
            self.data_src_combo.addItem(name)
        control_layout.addWidget(self.data_src_combo)

        # 历史天数
        control_layout.addWidget(QLabel("历史天数:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(30, 1000)
        self.days_spin.setValue(365)
        control_layout.addWidget(self.days_spin)

        # 分析按钮
        self.analyze_btn = QPushButton("📊 分析")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        control_layout.addWidget(self.analyze_btn)

        control_layout.addWidget(self.create_separator())

        # 自动刷新
        self.auto_refresh_cb = QCheckBox("自动刷新")
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        control_layout.addWidget(self.auto_refresh_cb)

        control_layout.addWidget(QLabel("间隔(秒):"))
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(10, 3600)
        self.refresh_interval_spin.setValue(60)
        control_layout.addWidget(self.refresh_interval_spin)

        control_layout.addWidget(self.create_separator())

        # 新窗口按钮
        self.new_window_btn = QPushButton("➕ 新窗口")
        self.new_window_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 13px;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.new_window_btn.clicked.connect(self.open_new_window)
        control_layout.addWidget(self.new_window_btn)

        control_layout.addStretch()
        main_layout.addWidget(control_frame)

        # === 绑图选项 ===
        plot_options_frame = QFrame()
        plot_options_layout = QHBoxLayout(plot_options_frame)
        plot_options_layout.setContentsMargins(5, 2, 5, 2)

        plot_options_layout.addWidget(QLabel("显示:"))

        self.plot_kline_cb = QCheckBox("K线")
        self.plot_kline_cb.setChecked(True)
        plot_options_layout.addWidget(self.plot_kline_cb)

        self.plot_combine_cb = QCheckBox("合并K线")
        self.plot_combine_cb.setChecked(True)
        plot_options_layout.addWidget(self.plot_combine_cb)

        self.plot_bi_cb = QCheckBox("笔")
        self.plot_bi_cb.setChecked(True)
        plot_options_layout.addWidget(self.plot_bi_cb)

        self.plot_seg_cb = QCheckBox("线段")
        self.plot_seg_cb.setChecked(True)
        plot_options_layout.addWidget(self.plot_seg_cb)

        self.plot_zs_cb = QCheckBox("中枢")
        self.plot_zs_cb.setChecked(True)
        plot_options_layout.addWidget(self.plot_zs_cb)

        self.plot_bsp_cb = QCheckBox("买卖点")
        self.plot_bsp_cb.setChecked(True)
        plot_options_layout.addWidget(self.plot_bsp_cb)

        self.plot_macd_cb = QCheckBox("MACD")
        self.plot_macd_cb.setChecked(True)
        plot_options_layout.addWidget(self.plot_macd_cb)

        plot_options_layout.addWidget(self.create_separator())

        plot_options_layout.addWidget(QLabel("显示K线数:"))
        self.x_range_spin = QSpinBox()
        self.x_range_spin.setRange(50, 1000)
        self.x_range_spin.setValue(200)
        plot_options_layout.addWidget(self.x_range_spin)

        # 刷新图表按钮
        self.refresh_chart_btn = QPushButton("🔄 刷新图表")
        self.refresh_chart_btn.clicked.connect(self.plot_chart)
        plot_options_layout.addWidget(self.refresh_chart_btn)

        plot_options_layout.addStretch()
        main_layout.addWidget(plot_options_frame)

        # === 图表区域 ===
        self.canvas = ChanPlotCanvas(self, width=14, height=8)
        self.toolbar = NavigationToolbar(self.canvas, self)

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas, stretch=1)

        # === 状态栏 ===
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('就绪 - 选择股票后点击"分析"')

    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')

        new_action = QAction('新窗口(&N)', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.open_new_window)
        file_menu.addAction(new_action)

        save_action = QAction('保存图片(&S)', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_chart)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        close_action = QAction('关闭窗口(&W)', self)
        close_action.setShortcut('Ctrl+W')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        exit_action = QAction('退出(&Q)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(exit_action)

        # 分析菜单
        analyze_menu = menubar.addMenu('分析(&A)')

        refresh_action = QAction('立即分析(&R)', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.start_analysis)
        analyze_menu.addAction(refresh_action)

    def create_separator(self) -> QFrame:
        """创建垂直分隔线"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    def get_current_code(self) -> str:
        """获取当前选择的股票代码"""
        text = self.code_combo.currentText().strip()
        # 尝试从下拉框数据获取
        data = self.code_combo.currentData()
        if data:
            return data
        # 否则解析输入文本
        if ' ' in text:
            return text.split()[0]
        return text

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
            "print_warning": False,
            "zs_algo": "normal",
        })

    def get_plot_config(self) -> dict:
        """获取绑图配置"""
        return {
            "plot_kline": self.plot_kline_cb.isChecked(),
            "plot_kline_combine": self.plot_combine_cb.isChecked(),
            "plot_bi": self.plot_bi_cb.isChecked(),
            "plot_seg": self.plot_seg_cb.isChecked(),
            "plot_zs": self.plot_zs_cb.isChecked(),
            "plot_bsp": self.plot_bsp_cb.isChecked(),
            "plot_macd": self.plot_macd_cb.isChecked(),
        }

    def start_analysis(self):
        """开始分析"""
        code = self.get_current_code()
        if not code:
            QMessageBox.warning(self, "警告", "请输入股票代码")
            return

        kl_type_name = self.kl_type_combo.currentText()
        kl_type = KL_TYPE_MAP.get(kl_type_name, KL_TYPE.K_DAY)

        data_src_name = self.data_src_combo.currentText()
        data_src = DATA_SRC_MAP.get(data_src_name, DATA_SRC.BAO_STOCK)

        days = self.days_spin.value()
        config = self.get_chan_config()

        # 禁用按钮
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("分析中...")
        self.statusBar.showMessage(f'正在分析 {code} ({kl_type_name})...')

        # 启动后台线程
        self.analysis_thread = AnalysisThread(code, kl_type, data_src, config, days)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.progress.connect(lambda msg: self.statusBar.showMessage(msg))
        self.analysis_thread.start()

    def on_analysis_finished(self, chan: CChan, stock_name: str):
        """分析完成"""
        self.chan = chan
        self.stock_name = stock_name
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("📊 分析")

        # 更新窗口标题
        kl_type_name = self.kl_type_combo.currentText()
        self.setWindowTitle(f'{self.get_current_code()} - {kl_type_name} - 缠论查看器')

        # 绑制图表
        self.plot_chart()

        # 统计信息
        kl_data = chan[0]
        bi_count = len(kl_data.bi_list)
        seg_count = len(kl_data.seg_list)
        zs_count = len(kl_data.zs_list)
        bsp_count = len(kl_data.bs_point_lst)

        self.statusBar.showMessage(
            f'分析完成: {self.get_current_code()} | '
            f'笔: {bi_count} | 线段: {seg_count} | 中枢: {zs_count} | 买卖点: {bsp_count}'
        )

    def on_analysis_error(self, error_msg: str):
        """分析出错"""
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("📊 分析")
        QMessageBox.critical(self, "分析错误", f"分析失败:\n{error_msg}")
        self.statusBar.showMessage('分析失败')

    def plot_chart(self):
        """绑制图表"""
        if not self.chan:
            return

        try:
            from Plot.PlotDriver import CPlotDriver

            # 关闭旧的 figure
            plt.close('all')

            plot_config = self.get_plot_config()

            # 计算图表尺寸
            canvas_width = self.canvas.width()
            dpi = 100
            fig_width = max(canvas_width / dpi, 12)
            fig_height = fig_width * 0.55

            plot_para = {
                "figure": {
                    "w": fig_width,
                    "h": fig_height,
                    "x_range": self.x_range_spin.value(),
                }
            }

            plot_driver = CPlotDriver(
                self.chan,
                plot_config=plot_config,
                plot_para=plot_para
            )

            self.canvas.fig = plot_driver.figure
            self.canvas.figure = plot_driver.figure
            self.canvas.draw()
            self.toolbar.update()

        except Exception as e:
            QMessageBox.critical(self, "绑图错误", str(e))

    def save_chart(self):
        """保存图表为图片"""
        if not self.chan:
            QMessageBox.warning(self, "警告", "请先分析股票")
            return

        from PyQt6.QtWidgets import QFileDialog

        code = self.get_current_code().replace('.', '_')
        kl_type = self.kl_type_combo.currentText()
        default_name = f"{code}_{kl_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        filename, _ = QFileDialog.getSaveFileName(
            self, "保存图片", default_name, "PNG Files (*.png);;All Files (*)"
        )

        if filename:
            self.canvas.fig.savefig(filename, dpi=150, bbox_inches='tight')
            self.statusBar.showMessage(f'图片已保存: {filename}')

    def toggle_auto_refresh(self, state):
        """切换自动刷新"""
        if state == Qt.CheckState.Checked.value:
            interval = self.refresh_interval_spin.value() * 1000  # 转为毫秒
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self.start_analysis)
            self.auto_refresh_timer.start(interval)
            self.statusBar.showMessage(f'自动刷新已启用 (间隔: {self.refresh_interval_spin.value()}秒)')
        else:
            if self.auto_refresh_timer:
                self.auto_refresh_timer.stop()
                self.auto_refresh_timer = None
            self.statusBar.showMessage('自动刷新已关闭')

    def open_new_window(self):
        """打开新窗口"""
        new_window = ChanViewerWindow()
        new_window.show()

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止自动刷新
        if self.auto_refresh_timer:
            self.auto_refresh_timer.stop()

        # 从实例列表移除
        if self in ChanViewerWindow.instances:
            ChanViewerWindow.instances.remove(self)

        event.accept()


def main():
    """程序入口"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置应用程序信息
    app.setApplicationName('缠论查看器')
    app.setOrganizationName('chan.py')

    # 创建主窗口
    window = ChanViewerWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
