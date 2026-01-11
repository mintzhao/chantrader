/**
 * API 服务
 */
import axios from 'axios';
import type {
  StockInfo,
  ChanAnalysisResult,
  MultiLevelResult,
  RealtimeData,
  SystemConfig,
  SingleAnalysisRequest,
  MultiLevelRequest,
  KLineType,
  PresetLevel,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

// 股票相关
export const stockApi = {
  // 搜索股票
  search: async (q: string, limit = 50): Promise<StockInfo[]> => {
    const { data } = await api.get('/stocks/search', { params: { q, limit } });
    return data;
  },

  // 获取实时行情
  getRealtime: async (code: string): Promise<RealtimeData> => {
    const { data } = await api.get(`/stocks/realtime/${code}`);
    return data;
  },

  // 获取股票列表
  getList: async (limit = 100): Promise<StockInfo[]> => {
    const { data } = await api.get('/stocks/list', { params: { limit } });
    return data;
  },
};

// 分析相关
export const analysisApi = {
  // 单级别分析
  single: async (request: SingleAnalysisRequest): Promise<ChanAnalysisResult> => {
    const { data } = await api.post('/analysis/single', request);
    return data;
  },

  // 多级别分析
  multiLevel: async (request: MultiLevelRequest): Promise<MultiLevelResult> => {
    const { data } = await api.post('/analysis/multilevel', request);
    return data;
  },

  // 获取 K线类型列表
  getKlTypes: async (): Promise<{ value: KLineType; label: string }[]> => {
    const { data } = await api.get('/analysis/kl-types');
    return data;
  },

  // 获取预设级别组合
  getPresetLevels: async (): Promise<PresetLevel[]> => {
    const { data } = await api.get('/analysis/preset-levels');
    return data;
  },
};

// 配置相关
export const configApi = {
  // 获取系统配置
  get: async (): Promise<SystemConfig> => {
    const { data } = await api.get('/config');
    return data;
  },

  // 更新系统配置
  update: async (config: SystemConfig): Promise<SystemConfig> => {
    const { data } = await api.put('/config', config);
    return data;
  },

  // 重置配置
  reset: async (): Promise<{ message: string; config: SystemConfig }> => {
    const { data } = await api.post('/config/reset');
    return data;
  },
};

export default api;
