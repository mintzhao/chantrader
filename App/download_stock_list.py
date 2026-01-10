#!/usr/bin/env python
"""
下载 A 股股票列表脚本

功能：
    - 使用 akshare 获取全量 A 股股票列表
    - 过滤 ST、科创板、北交所、B股、CDR
    - 添加常用指数
    - 保存为 CSV 文件供 chan_viewer_tk.py 读取

使用方法：
    python App/download_stock_list.py

输出文件：
    App/stock_list.csv
"""
import sys
from pathlib import Path

# 将项目根目录加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def download_stock_list():
    """下载并保存股票列表"""
    import akshare as ak
    import pandas as pd

    print("正在从 akshare 获取 A 股股票列表...")

    try:
        df = ak.stock_zh_a_spot_em()
        print(f"获取到 {len(df)} 条原始数据")

        # 过滤条件
        original_count = len(df)

        # 1. 剔除 ST 股票
        df = df[~df['名称'].str.contains('ST', case=False, na=False)]
        print(f"剔除 ST 后: {len(df)} 条")

        # 2. 剔除科创板（688开头）
        df = df[~df['代码'].str.startswith('688')]
        print(f"剔除科创板后: {len(df)} 条")

        # 3. 剔除北交所（8开头、43开头）
        df = df[~df['代码'].str.startswith('8')]
        df = df[~df['代码'].str.startswith('43')]
        print(f"剔除北交所后: {len(df)} 条")

        # 4. 剔除 B 股（200开头、900开头）
        df = df[~df['代码'].str.startswith('200')]
        df = df[~df['代码'].str.startswith('900')]
        print(f"剔除 B 股后: {len(df)} 条")

        # 5. 剔除 CDR（920开头）
        df = df[~df['代码'].str.startswith('920')]
        print(f"剔除 CDR 后: {len(df)} 条")

        # 转换为 baostock 格式并构建结果
        result = []
        for _, row in df.iterrows():
            code = row['代码']
            name = row['名称']
            # 转换为 baostock 格式
            if code.startswith('6'):
                bao_code = f"sh.{code}"
            else:
                bao_code = f"sz.{code}"
            result.append({
                'code': bao_code,
                'name': name
            })

        # 添加常用指数
        indices = [
            {"code": "sh.000001", "name": "上证指数"},
            {"code": "sz.399001", "name": "深证成指"},
            {"code": "sz.399006", "name": "创业板指"},
            {"code": "sh.000300", "name": "沪深300"},
            {"code": "sh.000016", "name": "上证50"},
            {"code": "sh.000905", "name": "中证500"},
            {"code": "sh.000852", "name": "中证1000"},
        ]
        result.extend(indices)

        # 保存到 CSV
        result_df = pd.DataFrame(result)
        output_path = Path(__file__).parent / "stock_list.csv"
        result_df.to_csv(output_path, index=False, encoding='utf-8')

        print(f"\n保存成功!")
        print(f"文件路径: {output_path}")
        print(f"股票数量: {len(result)} 条")
        print(f"  - A股: {len(result) - len(indices)} 只")
        print(f"  - 指数: {len(indices)} 个")

        return output_path

    except Exception as e:
        print(f"下载失败: {e}")
        return None


if __name__ == '__main__':
    download_stock_list()
