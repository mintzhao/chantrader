/**
 * 股票搜索组件
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { Search, X, History, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { stockApi } from '../services/api';
import { useAppStore } from '../stores/appStore';
import type { StockInfo } from '../types';

interface StockSearchProps {
  onSelect?: (stock: StockInfo) => void;
}

export function StockSearch({ onSelect }: StockSearchProps) {
  const [keyword, setKeyword] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const { currentStock, setCurrentStock, history, addToHistory } = useAppStore();

  // 搜索查询
  const { data: searchResults, isLoading } = useQuery({
    queryKey: ['stockSearch', keyword],
    queryFn: () => stockApi.search(keyword, 20),
    enabled: keyword.length >= 1,
    staleTime: 30000,
  });

  // 显示的列表（搜索结果或历史记录）
  const displayList = keyword.length >= 1 ? searchResults || [] : history;

  // 选择股票
  const handleSelect = useCallback(
    (stock: StockInfo) => {
      setCurrentStock(stock);
      addToHistory(stock);
      setKeyword(`${stock.code}  ${stock.name}`);
      setIsOpen(false);
      onSelect?.(stock);
    },
    [setCurrentStock, addToHistory, onSelect]
  );

  // 键盘导航
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || displayList.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < displayList.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : displayList.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (displayList[selectedIndex]) {
          handleSelect(displayList[selectedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        listRef.current &&
        !listRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 重置选中索引
  useEffect(() => {
    setSelectedIndex(0);
  }, [displayList]);

  return (
    <div className="relative w-80">
      {/* 输入框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          value={keyword}
          onChange={(e) => {
            setKeyword(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="搜索股票代码或名称..."
          className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     text-sm"
        />
        {keyword && (
          <button
            onClick={() => {
              setKeyword('');
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-blue-500 animate-spin" />
        )}
      </div>

      {/* 下拉列表 */}
      {isOpen && displayList.length > 0 && (
        <div
          ref={listRef}
          className="absolute z-50 w-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200
                     max-h-80 overflow-auto"
        >
          {keyword.length === 0 && (
            <div className="px-3 py-2 text-xs text-gray-400 border-b border-gray-100 flex items-center gap-1">
              <History className="w-3 h-3" />
              历史记录
            </div>
          )}
          {displayList.map((stock, index) => (
            <div
              key={stock.code}
              onClick={() => handleSelect(stock)}
              className={`px-3 py-2 cursor-pointer flex items-center justify-between
                         ${
                           index === selectedIndex
                             ? 'bg-blue-50 text-blue-700'
                             : 'hover:bg-gray-50'
                         }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-gray-500 font-mono text-sm">
                  {stock.code}
                </span>
                <span className="text-gray-800">{stock.name}</span>
              </div>
              {currentStock?.code === stock.code && (
                <span className="text-xs text-blue-500">当前</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 无结果提示 */}
      {isOpen &&
        keyword.length >= 1 &&
        !isLoading &&
        displayList.length === 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 p-4 text-center text-gray-400 text-sm">
            未找到匹配的股票
          </div>
        )}
    </div>
  );
}

export default StockSearch;
