/**
 * Chan.py Web - 主应用
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { TrendingUp, Layers, Settings, BarChart2 } from 'lucide-react';
import { SingleLevelPage, MultiLevelPage } from './pages';

// 创建 React Query 客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// 导航链接样式
const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 px-4 py-2 rounded-lg transition-colors
   ${
     isActive
       ? 'bg-blue-100 text-blue-700 font-medium'
       : 'text-gray-600 hover:bg-gray-100'
   }`;

function AppLayout() {
  return (
    <div className="flex min-h-screen">
      {/* 侧边导航 */}
      <nav className="w-56 bg-white border-r border-gray-200 p-4 flex flex-col">
        {/* Logo */}
        <div className="mb-8">
          <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-blue-500" />
            Chan.py
          </h1>
          <p className="text-xs text-gray-400 mt-1">缠论分析器 Web 版</p>
        </div>

        {/* 导航链接 */}
        <div className="space-y-2 flex-1">
          <NavLink to="/" className={navLinkClass}>
            <TrendingUp className="w-4 h-4" />
            单级别分析
          </NavLink>
          <NavLink to="/multilevel" className={navLinkClass}>
            <Layers className="w-4 h-4" />
            多级别区间套
          </NavLink>
        </div>

        {/* 底部 */}
        <div className="pt-4 border-t border-gray-200">
          <a
            href="https://github.com/entropage/chan.py"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Powered by chan.py
          </a>
        </div>
      </nav>

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<SingleLevelPage />} />
          <Route path="/multilevel" element={<MultiLevelPage />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
