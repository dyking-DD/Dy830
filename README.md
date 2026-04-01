# 量化交易系统

个人量化交易工作站，支持股票分析、策略回测、模拟交易和飞书通知。

## 功能模块

- **数据采集**：A股实时数据、历史K线、新闻舆情
- **策略框架**：MA交叉、Minervini SEPA、市场择时
- **回测引擎**：完整回测+可视化报告
- **风控系统**：仓位控制、熔断机制、黑名单
- **模拟交易**：纸面交易+飞书实时通知
- **定时任务**：每日15:00自动扫描+推送

## 技术栈

- Python 3.12
- FastAPI + WebSocket
- SQLite + SQLAlchemy
- AKShare/Tushare 数据源
- 飞书机器人通知
- ECharts 可视化

## 快速开始

```bash
pip install -r requirements.txt
python trading_desk.py
```

## 目录结构

```
daily_stock_analysis/
├── backtest/          # 回测系统
├── strategies/        # 策略模块
├── data/             # 数据存储
├── database/         # 数据库
├── execution/        # 交易执行
├── risk/             # 风险管理
├── utils/            # 工具函数
├── scripts/          # 脚本工具
├── reports/          # 报告输出
└── visualization/    # 可视化
```

## 配置

复制 `.env.example` 为 `.env`，填入：
- 飞书 webhook 地址
- 数据源 API Key

## 作者

dyking999
