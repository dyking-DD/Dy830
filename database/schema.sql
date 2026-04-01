-- 量化交易系统数据库 Schema
-- 包含交易记录、持仓、资金流水、策略绩效等核心表

-- 1. 交易记录表
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL,           -- 股票代码
    trade_date TEXT NOT NULL,         -- 交易日期
    trade_time TEXT,                  -- 交易时间
    action TEXT NOT NULL CHECK(action IN ('buy', 'sell')),  -- 买卖
    price REAL NOT NULL,              -- 成交价格
    volume INTEGER NOT NULL,          -- 成交数量
    amount REAL GENERATED ALWAYS AS (price * volume) STORED,  -- 成交金额
    strategy TEXT,                    -- 触发策略
    confidence REAL,                  -- 策略置信度
    status TEXT DEFAULT 'executed' CHECK(status IN ('pending', 'executed', 'cancelled', 'failed')),
    order_id TEXT,                    -- 订单号
    notes TEXT,                       -- 备注
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 持仓表
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL UNIQUE,     -- 股票代码
    volume INTEGER NOT NULL,          -- 持仓数量
    avg_cost REAL NOT NULL,           -- 平均成本
    current_price REAL,               -- 当前价格
    market_value REAL GENERATED ALWAYS AS (volume * COALESCE(current_price, avg_cost)) STORED,
    unrealized_pnl REAL,              -- 浮动盈亏
    strategy TEXT,                    -- 所属策略
    open_date TEXT,                   -- 开仓日期
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 资金流水表
CREATE TABLE IF NOT EXISTS cash_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,         -- 日期
    type TEXT NOT NULL CHECK(type IN ('deposit', 'withdraw', 'trade', 'dividend', 'fee')),
    amount REAL NOT NULL,             -- 金额（正入负出）
    balance REAL NOT NULL,            -- 余额
    description TEXT,                 -- 说明
    related_trade_id INTEGER REFERENCES trades(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 策略绩效表（每日汇总）
CREATE TABLE IF NOT EXISTS strategy_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,         -- 日期
    strategy TEXT NOT NULL,           -- 策略名称
    total_trades INTEGER DEFAULT 0,   -- 总交易次数
    win_count INTEGER DEFAULT 0,      -- 盈利次数
    loss_count INTEGER DEFAULT 0,     -- 亏损次数
    gross_profit REAL DEFAULT 0,      -- 总盈利
    gross_loss REAL DEFAULT 0,        -- 总亏损
    net_pnl REAL DEFAULT 0,           -- 净盈亏
    win_rate REAL GENERATED ALWAYS AS (
        CASE WHEN total_trades > 0 THEN ROUND(100.0 * win_count / total_trades, 2) ELSE 0 END
    ) STORED,
    profit_factor REAL,               -- 盈亏比
    sharpe_ratio REAL,                -- 夏普比率
    max_drawdown REAL,                -- 最大回撤
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trade_date, strategy)
);

-- 5. 每日账户快照
CREATE TABLE IF NOT EXISTS account_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL UNIQUE,  -- 日期
    total_assets REAL NOT NULL,       -- 总资产
    cash_balance REAL NOT NULL,       -- 现金余额
    position_value REAL NOT NULL,     -- 持仓市值
    day_pnl REAL,                     -- 当日盈亏
    cumulative_pnl REAL,              -- 累计盈亏
    benchmark_return REAL,            -- 基准收益（如沪深300）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_trades_date ON trades(trade_date);
CREATE INDEX idx_trades_code ON trades(ts_code);
CREATE INDEX idx_trades_strategy ON trades(strategy);
CREATE INDEX idx_positions_code ON positions(ts_code);
CREATE INDEX idx_cash_flow_date ON cash_flow(trade_date);
CREATE INDEX idx_perf_date ON strategy_performance(trade_date);
CREATE INDEX idx_perf_strategy ON strategy_performance(strategy);

-- 插入测试数据
INSERT INTO trades (ts_code, trade_date, trade_time, action, price, volume, strategy, confidence) VALUES
('000001.SZ', '2026-03-25', '09:35:00', 'buy', 12.50, 1000, 'MA_CROSS', 0.85),
('000002.SZ', '2026-03-25', '10:15:00', 'buy', 18.30, 500, 'RSI_OVERSOLD', 0.78),
('000001.SZ', '2026-03-26', '14:20:00', 'sell', 13.20, 1000, 'MA_CROSS', 0.82),
('600519.SH', '2026-03-27', '09:45:00', 'buy', 1680.00, 50, 'MOMENTUM', 0.91),
('000002.SZ', '2026-03-28', '11:00:00', 'sell', 17.80, 500, 'RSI_OVERBOUGHT', 0.75);

INSERT INTO positions (ts_code, volume, avg_cost, current_price, strategy, open_date) VALUES
('600519.SH', 50, 1680.00, 1695.50, 'MOMENTUM', '2026-03-27');

INSERT INTO cash_flow (trade_date, type, amount, balance, description) VALUES
('2026-03-25', 'deposit', 100000.00, 100000.00, '初始资金'),
('2026-03-25', 'trade', -12500.00, 87500.00, '买入 000001.SZ'),
('2026-03-25', 'trade', -9150.00, 78350.00, '买入 000002.SZ'),
('2026-03-26', 'trade', 13200.00, 91550.00, '卖出 000001.SZ'),
('2026-03-27', 'trade', -84000.00, 7550.00, '买入 600519.SH'),
('2026-03-28', 'trade', 8900.00, 16450.00, '卖出 000002.SZ');

INSERT INTO strategy_performance (trade_date, strategy, total_trades, win_count, loss_count, gross_profit, gross_loss, net_pnl) VALUES
('2026-03-25', 'MA_CROSS', 1, 0, 0, 0, 0, 0),
('2026-03-25', 'RSI_OVERSOLD', 1, 0, 0, 0, 0, 0),
('2026-03-26', 'MA_CROSS', 1, 1, 0, 700, 0, 700),
('2026-03-27', 'MOMENTUM', 1, 0, 0, 0, 0, 0),
('2026-03-28', 'RSI_OVERBOUGHT', 1, 0, 1, 0, -250, -250);

INSERT INTO account_snapshot (trade_date, total_assets, cash_balance, position_value, day_pnl, cumulative_pnl) VALUES
('2026-03-25', 100000.00, 78350.00, 21650.00, 0, 0),
('2026-03-26', 100700.00, 91550.00, 9150.00, 700, 700),
('2026-03-27', 101475.00, 7550.00, 93925.00, 775, 1475),
('2026-03-28', 101225.00, 16450.00, 84775.00, -250, 1225);
