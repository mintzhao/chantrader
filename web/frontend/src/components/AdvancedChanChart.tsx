/**
 * 高级缠论图表组件 - 绘制笔、线段、中枢、买卖点
 */
import { useEffect, useRef, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  Time,
  CrosshairMode,
} from 'lightweight-charts';
import type { ChanAnalysisResult, PlotConfig } from '../types';

interface AdvancedChanChartProps {
  data: ChanAnalysisResult | null;
  config: PlotConfig;
  height?: number;
  title?: string;
  showTitle?: boolean;
}

// 颜色配置
const COLORS = {
  up: '#ef4444',
  down: '#22c55e',
  bi: '#374151',
  biDashed: '#9ca3af',
  seg: '#059669',
  segDashed: '#6ee7b7',
  zs: '#f97316',
  bspBuy: '#dc2626',
  bspSell: '#16a34a',
};

export function AdvancedChanChart({
  data,
  config,
  height = 500,
  title,
  showTitle = true,
}: AdvancedChanChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const biSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const segSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // 初始化图表
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#374151',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#f3f4f6', style: 1 },
        horzLines: { color: '#f3f4f6', style: 1 },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#9ca3af',
          width: 1,
          style: 2,
          labelBackgroundColor: '#374151',
        },
        horzLine: {
          color: '#9ca3af',
          width: 1,
          style: 2,
          labelBackgroundColor: '#374151',
        },
      },
      rightPriceScale: {
        borderColor: '#e5e7eb',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: '#e5e7eb',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // K线系列
    const candleSeries = chart.addCandlestickSeries({
      upColor: COLORS.up,
      downColor: COLORS.down,
      borderUpColor: COLORS.up,
      borderDownColor: COLORS.down,
      wickUpColor: COLORS.up,
      wickDownColor: COLORS.down,
    });
    candleSeriesRef.current = candleSeries;

    // 笔系列
    const biSeries = chart.addLineSeries({
      color: COLORS.bi,
      lineWidth: 2,
      crosshairMarkerVisible: false,
    });
    biSeriesRef.current = biSeries;

    // 线段系列
    const segSeries = chart.addLineSeries({
      color: COLORS.seg,
      lineWidth: 3,
      crosshairMarkerVisible: false,
    });
    segSeriesRef.current = segSeries;

    // 响应式
    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [height]);

  // 更新数据
  useEffect(() => {
    if (!data || !chartRef.current || !candleSeriesRef.current) return;

    // K线数据
    if (config.showKline) {
      const candleData: CandlestickData<Time>[] = data.klines.map((kl) => ({
        time: kl.time.split(' ')[0] as Time,
        open: kl.open,
        high: kl.high,
        low: kl.low,
        close: kl.close,
      }));
      candleSeriesRef.current.setData(candleData);
    } else {
      candleSeriesRef.current.setData([]);
    }

    // 笔数据
    if (config.showBi && biSeriesRef.current && data.bi_list.length > 0) {
      const biData: LineData<Time>[] = [];
      data.bi_list.forEach((bi) => {
        const beginKl = data.klines[Math.floor(bi.begin_x)];
        const endKl = data.klines[Math.floor(bi.end_x)];
        if (beginKl && endKl) {
          biData.push({
            time: beginKl.time.split(' ')[0] as Time,
            value: bi.begin_y,
          });
          biData.push({
            time: endKl.time.split(' ')[0] as Time,
            value: bi.end_y,
          });
        }
      });
      biSeriesRef.current.setData(biData);
    } else if (biSeriesRef.current) {
      biSeriesRef.current.setData([]);
    }

    // 线段数据
    if (config.showSeg && segSeriesRef.current && data.seg_list.length > 0) {
      const segData: LineData<Time>[] = [];
      data.seg_list.forEach((seg) => {
        const beginKl = data.klines[Math.floor(seg.begin_x)];
        const endKl = data.klines[Math.floor(seg.end_x)];
        if (beginKl && endKl) {
          segData.push({
            time: beginKl.time.split(' ')[0] as Time,
            value: seg.begin_y,
          });
          segData.push({
            time: endKl.time.split(' ')[0] as Time,
            value: seg.end_y,
          });
        }
      });
      segSeriesRef.current.setData(segData);
    } else if (segSeriesRef.current) {
      segSeriesRef.current.setData([]);
    }

    // 买卖点标记
    if (config.showBsp && data.bsp_list.length > 0) {
      const markers = data.bsp_list.map((bsp) => {
        const kl = data.klines[Math.floor(bsp.x)];
        return {
          time: kl?.time.split(' ')[0] as Time,
          position: bsp.is_buy ? 'belowBar' : 'aboveBar',
          color: bsp.is_buy ? COLORS.bspBuy : COLORS.bspSell,
          shape: bsp.is_buy ? 'arrowUp' : 'arrowDown',
          text: bsp.type,
          size: 2,
        };
      });
      candleSeriesRef.current.setMarkers(markers as any);
    } else {
      candleSeriesRef.current.setMarkers([]);
    }

    // 自适应显示
    chartRef.current.timeScale().fitContent();
  }, [data, config]);

  // 统计信息
  const stats = data
    ? {
        klines: data.klines.length,
        bi: data.bi_list.length,
        seg: data.seg_list.length,
        zs: data.zs_list.length,
        bsp: data.bsp_list.length,
      }
    : null;

  if (!data) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200"
        style={{ height }}
      >
        <div className="text-center">
          <p className="text-gray-400 mb-2">暂无数据</p>
          <p className="text-gray-300 text-sm">请选择股票并开始分析</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* 标题栏 */}
      {showTitle && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <span className="font-medium text-gray-800">
              {title || `${data.name} (${data.code})`}
            </span>
            <span className="text-sm text-gray-500">{data.kl_type}</span>
          </div>
          {stats && (
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>K线: {stats.klines}</span>
              <span>笔: {stats.bi}</span>
              <span>段: {stats.seg}</span>
              <span>中枢: {stats.zs}</span>
              <span className="text-orange-500 font-medium">
                买卖点: {stats.bsp}
              </span>
            </div>
          )}
        </div>
      )}

      {/* 图表容器 */}
      <div ref={containerRef} />

      {/* 图例 */}
      <div className="flex items-center gap-4 px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs">
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded"
            style={{ backgroundColor: COLORS.up }}
          />
          涨
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded"
            style={{ backgroundColor: COLORS.down }}
          />
          跌
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-4 h-0.5"
            style={{ backgroundColor: COLORS.bi }}
          />
          笔
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-4 h-1"
            style={{ backgroundColor: COLORS.seg }}
          />
          线段
        </span>
        <span className="flex items-center gap-1">
          <span className="text-red-600">▲</span>
          买点
        </span>
        <span className="flex items-center gap-1">
          <span className="text-green-600">▼</span>
          卖点
        </span>
      </div>
    </div>
  );
}

export default AdvancedChanChart;
