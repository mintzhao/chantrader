/**
 * 实时行情面板
 */
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { stockApi } from '../services/api';
import type { RealtimeData } from '../types';

interface RealtimePanelProps {
  code: string | null;
}

export function RealtimePanel({ code }: RealtimePanelProps) {
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['realtime', code],
    queryFn: () => stockApi.getRealtime(code!),
    enabled: !!code,
    refetchInterval: 30000, // 30秒自动刷新
    staleTime: 10000,
  });

  if (!code) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-gray-400 text-center text-sm">请选择股票</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-200 rounded w-1/2" />
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-red-500 text-center text-sm mb-2">获取数据失败</p>
        <button
          onClick={() => refetch()}
          className="w-full py-1 text-sm text-blue-500 hover:text-blue-600"
        >
          重试
        </button>
      </div>
    );
  }

  const priceColor =
    data.change_pct > 0
      ? 'text-red-500'
      : data.change_pct < 0
      ? 'text-green-500'
      : 'text-gray-500';

  const PriceIcon =
    data.change_pct > 0
      ? TrendingUp
      : data.change_pct < 0
      ? TrendingDown
      : Minus;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* 头部 */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="font-medium text-gray-800">{data.name}</h3>
          <p className="text-xs text-gray-500">{data.code}</p>
        </div>
        <button
          onClick={() => refetch()}
          className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          title="刷新"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* 价格 */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className={`flex items-center gap-2 ${priceColor}`}>
          <span className="text-2xl font-bold">
            {data.latest_price.toFixed(2)}
          </span>
          <PriceIcon className="w-5 h-5" />
        </div>
        <div className={`flex items-center gap-2 text-sm ${priceColor}`}>
          <span>
            {data.change_pct > 0 ? '+' : ''}
            {data.change_pct.toFixed(2)}%
          </span>
          <span>
            {data.change_amount > 0 ? '+' : ''}
            {data.change_amount.toFixed(2)}
          </span>
        </div>
      </div>

      {/* 核心指标 */}
      <div className="px-4 py-3 space-y-2">
        <div className="text-xs text-blue-600 font-medium mb-2">核心指标</div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">总市值</span>
            <span className="text-gray-800">{data.total_market_cap}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">流通市值</span>
            <span className="text-gray-800">{data.circulating_market_cap}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">换手率</span>
            <span className="text-gray-800">{data.turnover_rate.toFixed(2)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">量比</span>
            <span className="text-gray-800">{data.volume_ratio.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* 价格信息 */}
      <div className="px-4 py-3 border-t border-gray-100 space-y-2">
        <div className="text-xs text-blue-600 font-medium mb-2">价格信息</div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">今开</span>
            <span className="text-gray-800">{data.open_price.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">昨收</span>
            <span className="text-gray-800">{data.prev_close.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">最高</span>
            <span className="text-red-500">{data.high.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">最低</span>
            <span className="text-green-500">{data.low.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">涨停</span>
            <span className="text-red-500">{data.limit_up.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">跌停</span>
            <span className="text-green-500">{data.limit_down.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* 成交信息 */}
      <div className="px-4 py-3 border-t border-gray-100 space-y-2">
        <div className="text-xs text-blue-600 font-medium mb-2">成交信息</div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">成交量</span>
            <span className="text-gray-800">{data.volume}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">成交额</span>
            <span className="text-gray-800">{data.turnover}</span>
          </div>
        </div>
      </div>

      {/* 底部 */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-400 flex justify-between">
        <span>{data.industry}</span>
        <span>更新: {data.update_time.split(' ')[1]}</span>
      </div>
    </div>
  );
}

export default RealtimePanel;
