/**
 * 多级别分析页面
 */
import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Loader2, Layers } from 'lucide-react';
import { StockSearch, AdvancedChanChart, RealtimePanel } from '../components';
import { analysisApi } from '../services/api';
import { useAppStore } from '../stores/appStore';
import type { StockInfo, KLineType } from '../types';

// 预设级别组合
const PRESET_LEVELS: { name: string; levels: KLineType[] }[] = [
  { name: '日线 + 60分钟', levels: ['日线', '60分钟'] },
  { name: '日线 + 60分钟 + 15分钟', levels: ['日线', '60分钟', '15分钟'] },
  { name: '日线 + 30分钟 + 5分钟', levels: ['日线', '30分钟', '5分钟'] },
  { name: '周线 + 日线', levels: ['周线', '日线'] },
  { name: '周线 + 日线 + 60分钟', levels: ['周线', '日线', '60分钟'] },
  { name: '60分钟 + 15分钟 + 5分钟', levels: ['60分钟', '15分钟', '5分钟'] },
];

export function MultiLevelPage() {
  const {
    currentStock,
    setCurrentStock,
    multiLevelResult,
    setMultiLevelResult,
    selectedLevels,
    setSelectedLevels,
    periods,
    setPeriods,
    plotConfig,
    addToHistory,
  } = useAppStore();

  const [selectedPreset, setSelectedPreset] = useState(1); // 默认日线+60分钟+15分钟

  // 分析 mutation
  const analyzeMutation = useMutation({
    mutationFn: analysisApi.multiLevel,
    onSuccess: (data) => {
      setMultiLevelResult(data);
      if (currentStock) {
        addToHistory(currentStock);
      }
    },
  });

  // 开始分析
  const handleAnalyze = useCallback(() => {
    if (!currentStock) return;

    analyzeMutation.mutate({
      code: currentStock.code,
      levels: selectedLevels,
      periods: periods,
    });
  }, [currentStock, selectedLevels, periods, analyzeMutation]);

  // 选择股票
  const handleSelectStock = useCallback(
    (stock: StockInfo) => {
      setCurrentStock(stock);
      analyzeMutation.mutate({
        code: stock.code,
        levels: selectedLevels,
        periods: periods,
      });
    },
    [setCurrentStock, selectedLevels, periods, analyzeMutation]
  );

  // 选择预设
  const handlePresetChange = (index: number) => {
    setSelectedPreset(index);
    setSelectedLevels(PRESET_LEVELS[index].levels);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-screen-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-500" />
              多级别区间套
            </h1>
            <StockSearch onSelect={handleSelectStock} />
          </div>

          <div className="flex items-center gap-4">
            {/* 级别选择 */}
            <select
              value={selectedPreset}
              onChange={(e) => handlePresetChange(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {PRESET_LEVELS.map((preset, idx) => (
                <option key={idx} value={idx}>
                  {preset.name}
                </option>
              ))}
            </select>

            {/* 周期数 */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">周期数:</label>
              <input
                type="number"
                min={50}
                max={500}
                value={periods}
                onChange={(e) => setPeriods(Number(e.target.value))}
                className="w-20 px-2 py-1 border border-gray-300 rounded text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 分析按钮 */}
            <button
              onClick={handleAnalyze}
              disabled={!currentStock || analyzeMutation.isPending}
              className={`px-4 py-2 rounded-lg font-medium transition-colors
                         ${
                           !currentStock || analyzeMutation.isPending
                             ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                             : 'bg-blue-600 text-white hover:bg-blue-700'
                         }`}
            >
              {analyzeMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  分析中...
                </span>
              ) : (
                '开始分析'
              )}
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="max-w-screen-2xl mx-auto p-4">
        <div className="grid grid-cols-12 gap-4">
          {/* 图表区 */}
          <div className="col-span-10 space-y-4">
            {/* 加载状态 */}
            {analyzeMutation.isPending && (
              <div className="bg-white rounded-lg border border-gray-200 p-8 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <span className="ml-3 text-gray-600">正在分析多级别数据...</span>
              </div>
            )}

            {/* 错误状态 */}
            {analyzeMutation.isError && (
              <div className="bg-red-50 rounded-lg border border-red-200 p-4 text-red-600">
                分析失败: {(analyzeMutation.error as Error).message}
              </div>
            )}

            {/* 多级别图表 */}
            {!analyzeMutation.isPending && multiLevelResult && (
              <div className="space-y-4">
                {selectedLevels.map((level) => {
                  const data = multiLevelResult.levels[level];
                  if (!data) return null;

                  const chartHeight =
                    selectedLevels.length === 2
                      ? 400
                      : selectedLevels.length === 3
                      ? 300
                      : 250;

                  return (
                    <AdvancedChanChart
                      key={level}
                      data={data}
                      config={plotConfig}
                      height={chartHeight}
                      title={`${multiLevelResult.name} - ${level}`}
                    />
                  );
                })}
              </div>
            )}

            {/* 空状态 */}
            {!analyzeMutation.isPending && !multiLevelResult && (
              <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
                <Layers className="w-12 h-12 mx-auto mb-4 opacity-30" />
                <p>请选择股票并开始多级别分析</p>
                <p className="text-sm mt-2">
                  多级别区间套可以帮助您更精确地定位买卖点
                </p>
              </div>
            )}
          </div>

          {/* 右侧面板 */}
          <aside className="col-span-2 space-y-4">
            {/* 实时行情 */}
            <RealtimePanel code={currentStock?.code || null} />

            {/* 区间套说明 */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                区间套原理
              </h3>
              <div className="text-xs text-gray-500 space-y-2">
                <p>1. 大级别确定方向和区间</p>
                <p>2. 次级别细化买卖区间</p>
                <p>3. 小级别精确入场点位</p>
                <p className="pt-2 border-t border-gray-100 text-blue-600">
                  ★ 多级别共振确认度最高
                </p>
              </div>
            </div>

            {/* 买卖点汇总 */}
            {multiLevelResult && (
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3">
                  各级别买卖点
                </h3>
                <div className="space-y-3">
                  {selectedLevels.map((level) => {
                    const data = multiLevelResult.levels[level];
                    if (!data) return null;

                    const recentBsp = data.bsp_list.slice(-3);

                    return (
                      <div key={level}>
                        <div className="text-xs text-gray-500 mb-1">{level}</div>
                        <div className="flex flex-wrap gap-1">
                          {recentBsp.length > 0 ? (
                            recentBsp.map((bsp, idx) => (
                              <span
                                key={idx}
                                className={`px-1.5 py-0.5 rounded text-xs
                                           ${
                                             bsp.is_buy
                                               ? 'bg-red-100 text-red-600'
                                               : 'bg-green-100 text-green-600'
                                           }`}
                              >
                                {bsp.is_buy ? 'B' : 'S'}
                                {bsp.type}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-gray-400">无</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}

export default MultiLevelPage;
