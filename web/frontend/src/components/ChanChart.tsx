/**
 * 缠论K线图表组件 - 使用 TradingView Lightweight Charts
 */
import { useEffect, useRef, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  LineData,
  Time,
} from 'lightweight-charts';
import type { ChanAnalysisResult, PlotConfig } from '../types';

interface ChanChartProps {
  data: ChanAnalysisResult | null;
  config: PlotConfig;
  height?: number;
  title?: string;
}

export function ChanChart({ data, config, height = 500, title }: ChanChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const macdHistogramRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const difLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const deaLineRef = useRef<ISeriesApi<'Line'> | null>(null);

  // 初始化图表
  useEffect(() => {
    if (!containerRef.current) return;

    // 创建图表
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#e0e0e0',
      },
      timeScale: {
        borderColor: '#e0e0e0',
        timeVisible: true,
      },
    });

    chartRef.current = chart;

    // 创建K线系列
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#ef4444',
      downColor: '#22c55e',
      borderUpColor: '#ef4444',
      borderDownColor: '#22c55e',
      wickUpColor: '#ef4444',
      wickDownColor: '#22c55e',
    });
    candleSeriesRef.current = candleSeries;

    // 响应式调整
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
    if (!data || !candleSeriesRef.current || !chartRef.current) return;

    // 转换 K线数据
    const candleData: CandlestickData<Time>[] = data.klines.map((kl) => ({
      time: kl.time.split(' ')[0] as Time, // 使用日期部分
      open: kl.open,
      high: kl.high,
      low: kl.low,
      close: kl.close,
    }));

    candleSeriesRef.current.setData(candleData);

    // 绘制笔
    if (config.showBi && data.bi_list.length > 0) {
      const biMarkers = data.bi_list.flatMap((bi) => {
        const beginTime = data.klines[Math.floor(bi.begin_x)]?.time.split(' ')[0];
        const endTime = data.klines[Math.floor(bi.end_x)]?.time.split(' ')[0];
        if (!beginTime || !endTime) return [];

        return [
          {
            time: beginTime as Time,
            position: bi.direction === 'up' ? 'belowBar' : 'aboveBar',
            color: '#1f2937',
            shape: bi.direction === 'up' ? 'arrowUp' : 'arrowDown',
            size: 1,
          },
        ];
      });
      candleSeriesRef.current.setMarkers(biMarkers as any);
    }

    // 绘制买卖点
    if (config.showBsp && data.bsp_list.length > 0) {
      const bspMarkers = data.bsp_list.map((bsp) => {
        const time = data.klines[Math.floor(bsp.x)]?.time.split(' ')[0];
        return {
          time: time as Time,
          position: bsp.is_buy ? 'belowBar' : 'aboveBar',
          color: bsp.is_buy ? '#ef4444' : '#22c55e',
          shape: bsp.is_buy ? 'arrowUp' : 'arrowDown',
          text: bsp.type,
          size: 2,
        };
      });
      candleSeriesRef.current.setMarkers(bspMarkers as any);
    }

    // 自适应显示范围
    chartRef.current.timeScale().fitContent();
  }, [data, config]);

  if (!data) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded-lg"
        style={{ height }}
      >
        <p className="text-gray-400">请选择股票并开始分析</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {title && (
        <div className="absolute top-2 left-4 z-10 bg-white/80 px-2 py-1 rounded text-sm font-medium text-gray-700">
          {title}
        </div>
      )}
      <div ref={containerRef} className="rounded-lg overflow-hidden" />
    </div>
  );
}

export default ChanChart;
