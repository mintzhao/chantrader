/**
 * 单级别分析页面
 */
import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import {
  StockSearch,
  AdvancedChanChart,
  RealtimePanel,
  PlotConfigPanel,
} from '../components';
import { analysisApi } from '../services/api';
import { useAppStore } from '../stores/appStore';
import type { StockInfo } from '../types';

export function SingleLevelPage() {
  const {
    currentStock,
    setCurrentStock,
    analysisResult,
    setAnalysisResult,
    klType,
    periods,
    plotConfig,
    addToHistory,
  } = useAppStore();

  // 分析 mutation
  const analyzeMutation = useMutation({
    mutationFn: analysisApi.single,
    onSuccess: (data) => {
      setAnalysisResult(data);
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
      kl_type: klType,
      periods: periods,
    });
  }, [currentStock, klType, periods, analyzeMutation]);

  // 选择股票后自动分析
  const handleSelectStock = useCallback(
    (stock: StockInfo) => {
      setCurrentStock(stock);
      analyzeMutation.mutate({
        code: stock.code,
        kl_type: klType,
        periods: periods,
      });
    },
    [setCurrentStock, klType, periods, analyzeMutation]
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-screen-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-bold text-gray-800">
              缠论分析器 <span className="text-sm font-normal text-gray-400">Web</span>
            </h1>
            <StockSearch onSelect={handleSelectStock} />
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            {currentStock && (
              <span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full">
                {currentStock.name} ({currentStock.code})
              </span>
            )}
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="max-w-screen-2xl mx-auto p-4">
        <div className="grid grid-cols-12 gap-4">
          {/* 左侧配置面板 */}
          <aside className="col-span-2 space-y-4">
            <PlotConfigPanel
              onAnalyze={handleAnalyze}
              isAnalyzing={analyzeMutation.isPending}
            />

            {/* 实时行情 */}
            <RealtimePanel code={currentStock?.code || null} />
          </aside>

          {/* 中间图表区 */}
          <div className="col-span-10">
            {/* 加载状态 */}
            {analyzeMutation.isPending && (
              <div className="bg-white rounded-lg border border-gray-200 p-8 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <span className="ml-3 text-gray-600">正在分析...</span>
              </div>
            )}

            {/* 错误状态 */}
            {analyzeMutation.isError && (
              <div className="bg-red-50 rounded-lg border border-red-200 p-4 text-red-600">
                分析失败: {(analyzeMutation.error as Error).message}
              </div>
            )}

            {/* 图表 */}
            {!analyzeMutation.isPending && (
              <AdvancedChanChart
                data={analysisResult}
                config={plotConfig}
                height={600}
              />
            )}

            {/* 买卖点汇总 */}
            {analysisResult && analysisResult.bsp_list.length > 0 && (
              <div className="mt-4 bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3">
                  买卖点汇总
                </h3>
                <div className="flex flex-wrap gap-2">
                  {analysisResult.bsp_list.slice(-10).map((bsp, idx) => (
                    <span
                      key={idx}
                      className={`px-2 py-1 rounded text-xs font-medium
                                 ${
                                   bsp.is_buy
                                     ? 'bg-red-100 text-red-700'
                                     : 'bg-green-100 text-green-700'
                                 }`}
                    >
                      {bsp.is_buy ? '买' : '卖'} {bsp.type}
                      {!bsp.is_sure && ' (未确认)'}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default SingleLevelPage;
