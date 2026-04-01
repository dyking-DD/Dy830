# daily_stock_analysis
# A股实时量化交易系统

## 项目结构

```
daily_stock_analysis/
├── config/              # 配置文件
│   ├── database.yaml   # 数据库配置
│   ├── tushare.yaml    # Tushare API配置
│   └── strategy.yaml   # 策略参数
├── data/               # 数据目录
│   ├── raw/           # 原始数据
│   ├── processed/     # 清洗后数据
│   └── backtest/      # 回测数据
├── strategies/         # 策略目录
│   ├── base.py        # 策略基类
│   └── examples/      # 示例策略
├── execution/          # 交易执行
│   ├── paper_trading.py  # 模拟交易
│   └── live_trading.py   # 实盘交易
├── risk/              # 风控模块
│   └── risk_manager.py
├── notebooks/         # Jupyter分析
├── logs/             # 日志文件
└── utils/            # 工具函数
```

## 快速开始

1. 安装依赖: `pip install -r requirements.txt`
2. 配置Tushare token: 修改 `config/tushare.yaml`
3. 初始化数据库: `python scripts/init_db.py`
4. 下载历史数据: `python scripts/download_history.py`
5. 运行回测: `python backtest.py --strategy ma_cross`

## 数据源

- **Tushare Pro**: 股票列表、日线、分钟线、财务数据
- **AkShare**: 实时行情（备选）
- **东财**: 实时资金流（爬虫）

## 风控规则

- 单票最大仓位: 10%
- 单日最大亏损: 3%
- 最大回撤: 15%
- 连续亏损3天暂停

## 免责声明

本系统仅供学习研究，不构成投资建议。股市有风险，投资需谨慎。
