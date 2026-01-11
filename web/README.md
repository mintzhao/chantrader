# Chan.py Web

缠论分析器 Web 版 - 基于 chan.py 核心库

## 项目结构

```
web/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由
│   │   │   ├── stocks.py    # 股票搜索、实时行情
│   │   │   ├── analysis.py  # 缠论分析
│   │   │   ├── config.py    # 系统配置
│   │   │   └── scanner.py   # 批量扫描 WebSocket
│   │   ├── core/            # 核心配置
│   │   ├── models/          # Pydantic 模型
│   │   └── services/        # 业务逻辑
│   ├── requirements.txt
│   └── main.py
├── frontend/                # React 前端
│   ├── src/
│   │   ├── components/      # UI 组件
│   │   │   ├── ChanChart.tsx
│   │   │   ├── AdvancedChanChart.tsx
│   │   │   ├── StockSearch.tsx
│   │   │   ├── RealtimePanel.tsx
│   │   │   └── PlotConfigPanel.tsx
│   │   ├── pages/           # 页面
│   │   │   ├── SingleLevelPage.tsx
│   │   │   └── MultiLevelPage.tsx
│   │   ├── services/        # API 服务
│   │   ├── stores/          # Zustand 状态
│   │   └── types/           # TypeScript 类型
│   └── package.json
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── nginx.conf
└── README.md
```

## 快速开始

### 开发模式

**1. 启动后端**

```bash
cd web/backend
pip install -r requirements.txt
python main.py
# 或
uvicorn main:app --reload --port 8000
```

后端运行在 http://localhost:8000，API 文档在 http://localhost:8000/docs

**2. 启动前端**

```bash
cd web/frontend
pnpm install
pnpm dev
```

前端运行在 http://localhost:5173

### Docker 部署

```bash
cd web
docker-compose up -d --build
```

访问 http://localhost 即可使用。

## 功能特性

### 已实现

- ✅ 股票搜索 - 支持代码、名称模糊搜索
- ✅ 单级别 K 线分析 - 支持 1分钟 ~ 月线
- ✅ 多级别区间套分析 - 多图表联动
- ✅ 实时行情 - 自动刷新
- ✅ 买卖点识别与标注 - b1/b2/b3/s1/s2/s3
- ✅ 笔、线段、中枢可视化
- ✅ MACD 指标
- ✅ 批量扫描（WebSocket）
- ✅ 系统配置持久化
- ✅ 历史记录

### 计划中

- 🔲 用户自定义配色方案
- 🔲 更多技术指标
- 🔲 自选股管理
- 🔲 买卖点提醒

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI, Python 3.11, Pydantic |
| **前端** | React 18, TypeScript, Vite |
| **图表** | TradingView Lightweight Charts |
| **状态管理** | Zustand |
| **数据请求** | TanStack Query (React Query) |
| **样式** | Tailwind CSS |
| **部署** | Docker, Nginx |

## API 接口

### 股票

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stocks/search?q=xxx` | 搜索股票 |
| GET | `/api/stocks/realtime/{code}` | 实时行情 |
| GET | `/api/stocks/list` | 股票列表 |

### 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analysis/single` | 单级别分析 |
| POST | `/api/analysis/multilevel` | 多级别分析 |
| GET | `/api/analysis/kl-types` | K线类型列表 |
| GET | `/api/analysis/preset-levels` | 预设级别组合 |

### 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取配置 |
| PUT | `/api/config` | 更新配置 |
| POST | `/api/config/reset` | 重置配置 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `/api/scanner/ws` | 批量扫描 |

## 截图

(待添加)

## 许可证

MIT License
