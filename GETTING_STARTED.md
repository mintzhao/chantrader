# Chan.py 快速入门指南

> 本文档帮助你在 5 分钟内运行 chan.py 项目，并查看 sz.000001（平安银行）的缠论分析图。

---

## 目录

1. [环境要求](#1-环境要求)
2. [安装依赖](#2-安装依赖)
3. [运行示例](#3-运行示例)
4. [常见问题](#4-常见问题)
5. [进阶使用](#5-进阶使用)

---

## 1. 环境要求

- **Python 版本**: >= 3.11（必须，项目针对 3.11 优化）
- **操作系统**: Windows / macOS / Linux

检查 Python 版本：
```bash
python3 --version
# 或
python --version
```

如果版本低于 3.11，请先升级 Python。

---

## 2. 安装依赖

### 方式一：使用 requirements.txt（推荐）

```bash
cd /home/mintzhao/chan.py
pip install -r Script/requirements.txt
```

### 方式二：手动安装

```bash
pip install baostock>=0.8.8 matplotlib>=3.5.3 numpy>=1.23.3 pandas>=1.4.2
```

### 依赖说明

| 包名 | 用途 |
|------|------|
| `baostock` | A股数据源（默认数据源） |
| `matplotlib` | 绑图库 |
| `numpy` | 数值计算 |
| `pandas` | 数据处理 |

---

## 3. 运行示例

### 3.1 直接运行 main.py

```bash
cd /home/mintzhao/chan.py
python main.py
```

**预期结果**：
- 程序会从 BaoStock 获取 `sz.000001`（平安银行）的日线数据
- 计算缠论元素（笔、线段、中枢、买卖点）
- 显示绘图窗口
- 在当前目录生成 `test.png` 图片文件

### 3.2 如果窗口闪退

某些系统上 matplotlib 窗口会在程序结束后自动关闭。解决方法：

**方法一：在 Jupyter Notebook 中运行**

```python
# 在 Jupyter Notebook 中运行以下代码
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PlotDriver import CPlotDriver

# 配置
code = "sz.000001"
begin_time = "2023-01-01"
end_time = None
data_src = DATA_SRC.BAO_STOCK
lv_list = [KL_TYPE.K_DAY]

config = CChanConfig({
    "trigger_step": False,
})

# 计算缠论
chan = CChan(
    code=code,
    begin_time=begin_time,
    end_time=end_time,
    data_src=data_src,
    lv_list=lv_list,
    config=config,
    autype=AUTYPE.QFQ,
)

# 绑图配置
plot_config = {
    "plot_kline": True,
    "plot_bi": True,
    "plot_seg": True,
    "plot_zs": True,
    "plot_bsp": True,
}

# 绑图
plot_driver = CPlotDriver(chan, plot_config=plot_config)
plot_driver.figure.show()
```

**方法二：在脚本末尾添加 input()**

创建一个新文件 `my_demo.py`：

```python
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PlotDriver import CPlotDriver

if __name__ == "__main__":
    code = "sz.000001"
    begin_time = "2023-01-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "trigger_step": False,
    })

    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    plot_config = {
        "plot_kline": True,
        "plot_bi": True,
        "plot_seg": True,
        "plot_zs": True,
        "plot_bsp": True,
    }

    plot_driver = CPlotDriver(chan, plot_config=plot_config)
    plot_driver.figure.show()

    # 保存图片
    plot_driver.save2img("sz000001_chan.png")
    print("图片已保存到 sz000001_chan.png")

    # 防止窗口关闭
    input("按回车键退出...")
```

运行：
```bash
python my_demo.py
```

---

## 4. 常见问题

### Q1: 报错 `ModuleNotFoundError: No module named 'baostock'`

```bash
pip install baostock
```

### Q2: 报错 `bs.login()` 相关错误

BaoStock 需要网络连接，请检查：
- 网络是否正常
- 是否在交易时间外（BaoStock 在非交易时间可能不稳定）

### Q3: 运行很慢

首次运行会从 BaoStock 下载数据，可能需要几秒到几十秒。后续可以考虑：
- 缩短时间范围（修改 `begin_time`）
- 使用本地 CSV 数据源

### Q4: 图片显示不完整或太小

调整 `plot_para` 中的图片参数：

```python
plot_para = {
    "figure": {
        "w": 24,      # 图片宽度
        "h": 10,      # 图片高度
        "x_range": 200,  # 只显示最后 200 根 K 线
    },
}
```

### Q5: 想看其他股票

修改 `code` 参数：
- A股格式：`sz.000001`（深圳）或 `sh.600000`（上海）
- 注意：BaoStock 仅支持 A股数据

### Q6: 想看不同级别（如60分钟线）

```python
lv_list = [KL_TYPE.K_60M]  # 60分钟
# 或
lv_list = [KL_TYPE.K_DAY, KL_TYPE.K_60M]  # 多级别联立
```

可用级别：
- `KL_TYPE.K_DAY` - 日线
- `KL_TYPE.K_WEEK` - 周线
- `KL_TYPE.K_MON` - 月线
- `KL_TYPE.K_60M` - 60分钟
- `KL_TYPE.K_30M` - 30分钟
- `KL_TYPE.K_15M` - 15分钟
- `KL_TYPE.K_5M` - 5分钟

---

## 5. 进阶使用

### 5.1 绘图元素开关

```python
plot_config = {
    "plot_kline": True,          # K线
    "plot_kline_combine": True,  # 合并K线
    "plot_bi": True,             # 笔
    "plot_seg": True,            # 线段
    "plot_zs": True,             # 中枢
    "plot_bsp": True,            # 买卖点
    "plot_macd": True,           # MACD指标
    "plot_eigen": False,         # 特征序列（调试用）
    "plot_rsi": False,           # RSI指标
    "plot_kdj": False,           # KDJ指标
}
```

### 5.2 核心配置参数

```python
config = CChanConfig({
    # 笔配置
    "bi_strict": True,           # 严格笔定义
    "bi_fx_check": "strict",     # 分形检查方法

    # 线段配置
    "seg_algo": "chan",          # 线段算法: chan/1+1/break

    # 中枢配置
    "zs_combine": True,          # 中枢合并
    "zs_algo": "normal",         # 中枢算法: normal/over_seg/auto

    # 买卖点配置
    "divergence_rate": 0.9,      # 背驰比例
    "min_zs_cnt": 1,             # 最少中枢数
    "bs_type": "1,2,3a,3b,1p,2s", # 买卖点类型
})
```

### 5.3 获取缠论元素

```python
# 获取日线级别数据
kl_data = chan[KL_TYPE.K_DAY]
# 或者如果只有一个级别
kl_data = chan[0]

# 获取笔列表
for bi in kl_data.bi_list:
    print(f"第{bi.idx}笔, 方向:{bi.dir}, 确定:{bi.is_sure}")

# 获取线段列表
for seg in kl_data.seg_list:
    print(f"第{seg.idx}段, 方向:{seg.dir}")

# 获取中枢列表
for zs in kl_data.zs_list:
    print(f"中枢: [{zs.low}, {zs.high}]")

# 获取买卖点
for bsp in kl_data.bs_point_lst:
    print(f"买卖点类型:{bsp.type}, 是否买点:{bsp.is_buy}")
```

### 5.4 使用其他数据源

**Akshare 数据源**（需要安装 akshare）：

```bash
pip install akshare
```

```python
from Common.CEnum import DATA_SRC

data_src = DATA_SRC.AKSHARE
code = "000001"  # Akshare 格式不需要前缀
```

**CSV 本地数据**：

```python
data_src = DATA_SRC.CSV
code = "/path/to/your/data.csv"
```

CSV 文件格式要求：
- 必须包含列：`date`, `open`, `high`, `low`, `close`
- 可选列：`volume`, `amount`, `turn`

---

## 附录：项目结构（开源部分）

```
chan.py/
├── Chan.py              # 核心计算类
├── ChanConfig.py        # 配置类
├── main.py              # 示例入口
├── Bi/                  # 笔计算模块
├── Seg/                 # 线段计算模块
├── ZS/                  # 中枢计算模块
├── KLine/               # K线处理模块
├── BuySellPoint/        # 买卖点计算模块
├── DataAPI/             # 数据源接口
├── Plot/                # 绑图模块
├── Math/                # 技术指标计算
├── Common/              # 通用工具
└── Debug/               # 示例策略
```

---

## 更多资源

- [快速上手指南](./quick_guide.md) - 官方详细文档
- [README.md](./README.md) - 完整版说明（部分功能仅完整版可用）
- [Telegram 讨论组](https://t.me/zen_python)
- [B站视频教程](https://www.bilibili.com/video/BV1nu411c7oG/)

---

**祝你使用愉快！** 🎉
