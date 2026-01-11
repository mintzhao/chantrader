/**
 * 全局状态管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  StockInfo,
  KLineType,
  ChanAnalysisResult,
  MultiLevelResult,
  PlotConfig,
  SystemConfig,
} from '../types';

// 应用状态
interface AppState {
  // 当前股票
  currentStock: StockInfo | null;
  setCurrentStock: (stock: StockInfo | null) => void;

  // 分析结果
  analysisResult: ChanAnalysisResult | null;
  setAnalysisResult: (result: ChanAnalysisResult | null) => void;

  // 多级别结果
  multiLevelResult: MultiLevelResult | null;
  setMultiLevelResult: (result: MultiLevelResult | null) => void;

  // 分析中状态
  isAnalyzing: boolean;
  setIsAnalyzing: (value: boolean) => void;

  // K线类型
  klType: KLineType;
  setKlType: (type: KLineType) => void;

  // 周期数
  periods: number;
  setPeriods: (periods: number) => void;

  // 多级别组合
  selectedLevels: KLineType[];
  setSelectedLevels: (levels: KLineType[]) => void;

  // 绘图配置
  plotConfig: PlotConfig;
  setPlotConfig: (config: Partial<PlotConfig>) => void;

  // 历史记录
  history: StockInfo[];
  addToHistory: (stock: StockInfo) => void;
  clearHistory: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      currentStock: null,
      setCurrentStock: (stock) => set({ currentStock: stock }),

      analysisResult: null,
      setAnalysisResult: (result) => set({ analysisResult: result }),

      multiLevelResult: null,
      setMultiLevelResult: (result) => set({ multiLevelResult: result }),

      isAnalyzing: false,
      setIsAnalyzing: (value) => set({ isAnalyzing: value }),

      klType: '日线',
      setKlType: (type) => set({ klType: type }),

      periods: 300,
      setPeriods: (periods) => set({ periods }),

      selectedLevels: ['日线', '60分钟', '15分钟'],
      setSelectedLevels: (levels) => set({ selectedLevels: levels }),

      plotConfig: {
        showKline: true,
        showBi: true,
        showSeg: true,
        showZs: true,
        showBsp: true,
        showMacd: true,
      },
      setPlotConfig: (config) =>
        set((state) => ({
          plotConfig: { ...state.plotConfig, ...config },
        })),

      history: [],
      addToHistory: (stock) =>
        set((state) => {
          const filtered = state.history.filter((s) => s.code !== stock.code);
          return {
            history: [stock, ...filtered].slice(0, 20),
          };
        }),
      clearHistory: () => set({ history: [] }),
    }),
    {
      name: 'chan-web-storage',
      partialize: (state) => ({
        klType: state.klType,
        periods: state.periods,
        selectedLevels: state.selectedLevels,
        plotConfig: state.plotConfig,
        history: state.history,
      }),
    }
  )
);
