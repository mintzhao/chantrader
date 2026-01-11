/**
 * 绘图配置面板
 */
import { useAppStore } from '../stores/appStore';
import type { PlotConfig, KLineType } from '../types';

const KL_TYPES: { value: KLineType; label: string }[] = [
  { value: '1分钟', label: '1分钟' },
  { value: '5分钟', label: '5分钟' },
  { value: '15分钟', label: '15分钟' },
  { value: '30分钟', label: '30分钟' },
  { value: '60分钟', label: '60分钟' },
  { value: '日线', label: '日线' },
  { value: '周线', label: '周线' },
  { value: '月线', label: '月线' },
];

interface PlotConfigPanelProps {
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
}

export function PlotConfigPanel({ onAnalyze, isAnalyzing }: PlotConfigPanelProps) {
  const {
    klType,
    setKlType,
    periods,
    setPeriods,
    plotConfig,
    setPlotConfig,
  } = useAppStore();

  const toggleOption = (key: keyof PlotConfig) => {
    setPlotConfig({ [key]: !plotConfig[key] });
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-4">
      {/* K线类型 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          K线周期
        </label>
        <select
          value={klType}
          onChange={(e) => setKlType(e.target.value as KLineType)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        >
          {KL_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      {/* 周期数 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          周期数
        </label>
        <input
          type="number"
          min={50}
          max={2000}
          value={periods}
          onChange={(e) => setPeriods(Number(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        />
      </div>

      {/* 显示选项 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          显示选项
        </label>
        <div className="grid grid-cols-2 gap-2">
          {[
            { key: 'showKline' as const, label: 'K线' },
            { key: 'showBi' as const, label: '笔' },
            { key: 'showSeg' as const, label: '线段' },
            { key: 'showZs' as const, label: '中枢' },
            { key: 'showBsp' as const, label: '买卖点' },
            { key: 'showMacd' as const, label: 'MACD' },
          ].map((option) => (
            <label
              key={option.key}
              className="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={plotConfig[option.key]}
                onChange={() => toggleOption(option.key)}
                className="w-4 h-4 text-blue-600 rounded border-gray-300
                           focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* 分析按钮 */}
      {onAnalyze && (
        <button
          onClick={onAnalyze}
          disabled={isAnalyzing}
          className={`w-full py-2 rounded-lg font-medium transition-colors
                     ${
                       isAnalyzing
                         ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                         : 'bg-blue-600 text-white hover:bg-blue-700'
                     }`}
        >
          {isAnalyzing ? '分析中...' : '开始分析'}
        </button>
      )}
    </div>
  );
}

export default PlotConfigPanel;
