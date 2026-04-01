"""
数据库初始化模块
"""
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_sqlite_db(db_path: str = "data/processed/stock_data.db") -> None:
    """初始化SQLite数据库
    
    Creates tables:
    - stocks: 股票基本信息
    - daily_prices: 日线价格数据
    - trades: 交易记录
    - portfolio: 持仓记录
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 股票基本信息表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        ts_code TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        name TEXT,
        area TEXT,
        industry TEXT,
        list_date TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 日线数据表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        pre_close REAL,
        change REAL,
        pct_chg REAL,
        vol REAL,
        amount REAL,
        ma5 REAL,
        ma10 REAL,
        ma20 REAL,
        ma60 REAL,
        UNIQUE(ts_code, trade_date)
    )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_ts_code ON daily_prices(ts_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_prices(trade_date)")
    
    # 模拟交易记录表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        trade_type TEXT CHECK(trade_type IN ('buy', 'sell')),
        price REAL NOT NULL,
        volume INTEGER NOT NULL,
        amount REAL,
        strategy TEXT,
        signal_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 持仓表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_code TEXT NOT NULL UNIQUE,
        volume INTEGER DEFAULT 0,
        avg_cost REAL DEFAULT 0,
        current_price REAL,
        market_value REAL,
        profit_loss REAL,
        profit_loss_pct REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 账户资金表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS account (
        id INTEGER PRIMARY KEY,
        initial_capital REAL DEFAULT 1000000,
        available_cash REAL DEFAULT 1000000,
        total_value REAL DEFAULT 1000000,
        total_profit_loss REAL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 初始化账户
    cursor.execute("INSERT OR IGNORE INTO account (id) VALUES (1)")
    
    conn.commit()
    conn.close()
    logger.info(f"数据库初始化完成: {db_path}")


if __name__ == "__main__":
    init_sqlite_db()
