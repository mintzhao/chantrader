import akshare as ak
import pandas as pd

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def create_item_dict(row, autype, is_minute=False):
    """将DataFrame行转换为K线单元所需的字典格式"""
    item = {}

    if is_minute:
        # 分钟K线数据格式处理
        time_val = row['时间']
        if isinstance(time_val, pd.Timestamp):
            year, month, day = time_val.year, time_val.month, time_val.day
            hour, minute = time_val.hour, time_val.minute
        elif isinstance(time_val, str):
            # 格式: "2025-01-10 09:31" 或 "2025-01-10 09:31:00"
            date_part = time_val[:10]
            time_part = time_val[11:16]
            year = int(date_part[:4])
            month = int(date_part[5:7])
            day = int(date_part[8:10])
            hour = int(time_part[:2])
            minute = int(time_part[3:5])
        else:
            time_str = str(time_val)
            date_part = time_str[:10]
            time_part = time_str[11:16] if len(time_str) > 11 else "00:00"
            year = int(date_part[:4])
            month = int(date_part[5:7])
            day = int(date_part[8:10])
            hour = int(time_part[:2])
            minute = int(time_part[3:5])

        item[DATA_FIELD.FIELD_TIME] = CTime(year, month, day, hour, minute)
        item[DATA_FIELD.FIELD_OPEN] = str2float(row['开盘'])
        item[DATA_FIELD.FIELD_HIGH] = str2float(row['最高'])
        item[DATA_FIELD.FIELD_LOW] = str2float(row['最低'])
        item[DATA_FIELD.FIELD_CLOSE] = str2float(row['收盘'])
        item[DATA_FIELD.FIELD_VOLUME] = str2float(row['成交量'])
        item[DATA_FIELD.FIELD_TURNOVER] = str2float(row.get('成交额', 0))
    else:
        # 日线/周线/月线数据格式处理
        date_val = row['日期']
        if isinstance(date_val, pd.Timestamp):
            year, month, day = date_val.year, date_val.month, date_val.day
        elif isinstance(date_val, str):
            date_str = date_val
            if len(date_str) == 10:  # 格式: 2021-09-13
                year = int(date_str[:4])
                month = int(date_str[5:7])
                day = int(date_str[8:10])
            else:  # 格式: 20210913
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
        else:
            # 尝试转换
            date_str = str(date_val)[:10]
            year = int(date_str[:4])
            month = int(date_str[5:7])
            day = int(date_str[8:10])

        item[DATA_FIELD.FIELD_TIME] = CTime(year, month, day, 0, 0)
        item[DATA_FIELD.FIELD_OPEN] = str2float(row['开盘'])
        item[DATA_FIELD.FIELD_HIGH] = str2float(row['最高'])
        item[DATA_FIELD.FIELD_LOW] = str2float(row['最低'])
        item[DATA_FIELD.FIELD_CLOSE] = str2float(row['收盘'])
        item[DATA_FIELD.FIELD_VOLUME] = str2float(row['成交量'])
        item[DATA_FIELD.FIELD_TURNOVER] = str2float(row.get('成交额', 0))

        # 换手率可能不存在
        if '换手率' in row:
            item[DATA_FIELD.FIELD_TURNRATE] = str2float(row['换手率'])

    return item


class CAkshare(CCommonStockApi):
    """使用 akshare 获取A股数据"""

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CAkshare, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """获取K线数据"""
        # 转换复权类型
        adjust_dict = {
            AUTYPE.QFQ: "qfq",
            AUTYPE.HFQ: "hfq",
            AUTYPE.NONE: ""
        }
        adjust = adjust_dict.get(self.autype, "qfq")

        # 转换周期类型
        period = self.__convert_type()
        is_minute = self._is_minute_type()

        # 格式化日期
        start_date = self.begin_date.replace("-", "") if self.begin_date else "19900101"
        end_date = self.end_date.replace("-", "") if self.end_date else "20991231"

        # 提取纯数字股票代码（akshare API 需要纯数字代码）
        code_num = self.code
        if self.code.startswith('sh.') or self.code.startswith('sz.'):
            code_num = self.code[3:]
        elif self.code.startswith('sh') or self.code.startswith('sz'):
            code_num = self.code[2:]

        # 获取数据
        if is_minute:
            # 分钟K线数据 - 使用 stock_zh_a_hist_min_em
            # 注意：分钟数据只能获取最近5天的数据
            df = ak.stock_zh_a_hist_min_em(
                symbol=code_num,
                period=period,
                adjust=adjust
            )
            # 分钟数据的列名与日线不同，需要重命名
            if not df.empty:
                # akshare分钟数据列: ['时间', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '最新价']
                # 按时间排序
                df = df.sort_values('时间')
                # 筛选日期范围（分钟数据的时间格式是 "2025-01-10 09:31:00"）
                df['日期字符串'] = df['时间'].astype(str).str[:10].str.replace('-', '')
                df = df[(df['日期字符串'] >= start_date) & (df['日期字符串'] <= end_date)]
                df = df.drop(columns=['日期字符串'])

                # 过滤无效数据：开盘价为0的数据是无效的
                # AkShare 分钟数据可能返回开盘=0的异常行
                df = df[df['开盘'] > 0]

            # 遍历每一行生成K线单元
            for _, row in df.iterrows():
                yield CKLine_Unit(create_item_dict(row, self.autype, is_minute=True))
        elif self.is_stock:
            # 个股日线/周线/月线数据
            df = ak.stock_zh_a_hist(
                symbol=code_num,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            # 遍历每一行生成K线单元
            for _, row in df.iterrows():
                yield CKLine_Unit(create_item_dict(row, self.autype, is_minute=False))
        else:
            # 指数数据
            df = ak.stock_zh_index_daily(symbol=self.code)
            # 筛选日期范围
            df['日期'] = df['date'].astype(str)
            df = df.rename(columns={
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量'
            })
            if 'amount' in df.columns:
                df['成交额'] = df['amount']
            else:
                df['成交额'] = 0
            df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]

            # 遍历每一行生成K线单元
            for _, row in df.iterrows():
                yield CKLine_Unit(create_item_dict(row, self.autype, is_minute=False))

    def SetBasciInfo(self):
        """设置基本信息"""
        self.name = self.code
        # 判断是否为指数: sh000001, sz399001 等
        if self.code.startswith('sh') or self.code.startswith('sz'):
            code_num = self.code[2:]
            # 指数代码通常以 000, 399 开头
            if code_num.startswith('000') or code_num.startswith('399'):
                self.is_stock = False
            else:
                self.is_stock = True
        else:
            # 纯数字代码默认为股票
            self.is_stock = True

    @classmethod
    def do_init(cls):
        """初始化 (akshare不需要登录)"""
        pass

    @classmethod
    def do_close(cls):
        """关闭 (akshare不需要登出)"""
        pass

    def __convert_type(self):
        """转换K线周期类型"""
        _dict = {
            KL_TYPE.K_DAY: 'daily',
            KL_TYPE.K_WEEK: 'weekly',
            KL_TYPE.K_MON: 'monthly',
            KL_TYPE.K_1M: '1',
            KL_TYPE.K_5M: '5',
            KL_TYPE.K_15M: '15',
            KL_TYPE.K_30M: '30',
            KL_TYPE.K_60M: '60',
        }
        if self.k_type not in _dict:
            raise Exception(f"akshare不支持{self.k_type}级别的K线数据")
        return _dict[self.k_type]

    def _is_minute_type(self):
        """判断是否为分钟级别K线"""
        return self.k_type in [KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M]
