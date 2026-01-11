/**
 * 缠论分析 Web 版 - 类型定义
 */

// K线类型枚举
export type KLineType =
  | '1分钟'
  | '5分钟'
  | '15分钟'
  | '30分钟'
  | '60分钟'
  | '日线'
  | '周线'
  | '月线';

// 股票信息
export interface StockInfo {
  code: string;
  name: string;
}

// K线单元
export interface KLineUnit {
  idx: number;
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 笔信息
export interface BiInfo {
  idx: number;
  begin_idx: number;
  end_idx: number;
  begin_x: number;
  end_x: number;
  begin_y: number;
  end_y: number;
  is_sure: boolean;
  direction: 'up' | 'down';
}

// 线段信息
export interface SegInfo {
  idx: number;
  begin_idx: number;
  end_idx: number;
  begin_x: number;
  end_x: number;
  begin_y: number;
  end_y: number;
  is_sure: boolean;
  direction: 'up' | 'down';
}

// 中枢信息
export interface ZSInfo {
  idx: number;
  begin: number;
  end: number;
  low: number;
  high: number;
  is_sure: boolean;
}

// 买卖点信息
export interface BSPInfo {
  idx: number;
  x: number;
  y: number;
  is_buy: boolean;
  type: string;
  is_sure: boolean;
}

// MACD 信息
export interface MACDInfo {
  idx: number;
  dif: number;
  dea: number;
  macd: number;
}

// 缠论分析结果
export interface ChanAnalysisResult {
  code: string;
  name: string;
  kl_type: string;
  klines: KLineUnit[];
  bi_list: BiInfo[];
  seg_list: SegInfo[];
  zs_list: ZSInfo[];
  bsp_list: BSPInfo[];
  macd_list: MACDInfo[];
  dateticks: string[];
}

// 多级别分析结果
export interface MultiLevelResult {
  code: string;
  name: string;
  levels: Record<string, ChanAnalysisResult>;
}

// 实时行情数据
export interface RealtimeData {
  code: string;
  name: string;
  latest_price: number;
  change_pct: number;
  change_amount: number;
  volume: string;
  turnover: string;
  high: number;
  low: number;
  open_price: number;
  prev_close: number;
  volume_ratio: number;
  turnover_rate: number;
  total_market_cap: string;
  circulating_market_cap: string;
  avg_price: number;
  limit_up: number;
  limit_down: number;
  industry: string;
  update_time: string;
}

// 缠论配置
export interface ChanConfig {
  bi_strict: boolean;
  trigger_step: boolean;
  divergence_rate: number;
  bsp2_follow_1: boolean;
  bsp3_follow_1: boolean;
  min_zs_cnt: number;
  bs1_peak: boolean;
  macd_algo: string;
  bs_type: string;
  zs_algo: string;
}

// 系统配置
export interface SystemConfig {
  chan_config: ChanConfig;
  default_kl_type: KLineType;
  default_periods: number;
  auto_refresh_interval: number;
  theme: 'light' | 'dark';
}

// 单级别分析请求
export interface SingleAnalysisRequest {
  code: string;
  kl_type: KLineType;
  periods: number;
}

// 多级别分析请求
export interface MultiLevelRequest {
  code: string;
  levels: KLineType[];
  periods: number;
}

// 扫描进度
export interface ScannerProgress {
  type: 'progress' | 'found' | 'finished' | 'error' | 'status' | 'stopped';
  current?: number;
  total?: number;
  stock_info?: string;
  data?: {
    code?: string;
    name?: string;
    price?: number;
    change_pct?: number;
    bsp_type?: string;
    success?: number;
    failed?: number;
    found?: number;
  };
  message?: string;
}

// 预设级别组合
export interface PresetLevel {
  name: string;
  levels: KLineType[];
}

// 绘图配置
export interface PlotConfig {
  showKline: boolean;
  showBi: boolean;
  showSeg: boolean;
  showZs: boolean;
  showBsp: boolean;
  showMacd: boolean;
}
