#!/usr/bin/env python3
"""
交易数据库管理工具
封装 SQLite 操作，便于量化系统使用
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from contextlib import contextmanager
import os

@dataclass
class Trade:
    """交易记录"""
    ts_code: str
    trade_date: str
    action: str  # 'buy' or 'sell'
    price: float
    volume: int
    strategy: str
    confidence: float
    trade_time: Optional[str] = None
    order_id: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class Position:
    """持仓记录"""
    ts_code: str
    volume: int
    avg_cost: float
    current_price: Optional[float] = None
    strategy: Optional[str] = None
    open_date: Optional[str] = None

class TradingDB:
    """交易数据库管理类"""
    
    def __init__(self, db_path: str = 'database/trading.db'):
        """初始化数据库连接"""
        self.db_path = db_path
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接上下文"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_tables(self):
        """初始化表结构"""
        try:
            with open('database/schema.sql', 'r') as f:
                schema = f.read()
            
            with self._get_connection() as conn:
                conn.executescript(schema)
                conn.commit()
        except sqlite3.OperationalError as e:
            # 忽略已存在的索引错误
            if 'already exists' in str(e):
                pass
            else:
                raise
    
    # ========== 交易记录操作 ==========
    
    def record_trade(self, trade: Trade) -> int:
        """记录一笔交易"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO trades (ts_code, trade_date, trade_time, action, price, 
                                   volume, strategy, confidence, order_id, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade.ts_code, trade.trade_date, trade.trade_time or datetime.now().strftime('%H:%M:%S'),
                  trade.action, trade.price, trade.volume, trade.strategy, 
                  trade.confidence, trade.order_id, trade.notes))
            conn.commit()
            return cursor.lastrowid
    
    def get_trades(self, start_date: str = None, end_date: str = None, 
                   strategy: str = None) -> pd.DataFrame:
        """查询交易记录"""
        query = 'SELECT * FROM trades WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND trade_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND trade_date <= ?'
            params.append(end_date)
        if strategy:
            query += ' AND strategy = ?'
            params.append(strategy)
        
        query += ' ORDER BY trade_date DESC, trade_time DESC'
        
        with self._get_connection() as conn:
            return pd.read_sql(query, conn, params=params)
    
    # ========== 持仓操作 ==========
    
    def update_position(self, position: Position):
        """更新或创建持仓"""
        with self._get_connection() as conn:
            # 检查是否已存在
            existing = conn.execute(
                'SELECT * FROM positions WHERE ts_code = ?', (position.ts_code,)
            ).fetchone()
            
            if existing:
                conn.execute('''
                    UPDATE positions 
                    SET volume = ?, avg_cost = ?, current_price = ?, 
                        strategy = ?, open_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE ts_code = ?
                ''', (position.volume, position.avg_cost, position.current_price,
                      position.strategy, position.open_date, position.ts_code))
            else:
                conn.execute('''
                    INSERT INTO positions (ts_code, volume, avg_cost, current_price, 
                                          strategy, open_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (position.ts_code, position.volume, position.avg_cost, 
                      position.current_price, position.strategy, position.open_date))
            conn.commit()
    
    def get_positions(self) -> pd.DataFrame:
        """获取当前持仓"""
        with self._get_connection() as conn:
            return pd.read_sql('SELECT * FROM positions', conn)
    
    def close_position(self, ts_code: str):
        """清仓"""
        with self._get_connection() as conn:
            conn.execute('DELETE FROM positions WHERE ts_code = ?', (ts_code,))
            conn.commit()
    
    # ========== 账户快照 ==========
    
    def record_snapshot(self, total_assets: float, cash_balance: float, 
                       position_value: float, day_pnl: float = 0,
                       benchmark_return: float = None):
        """记录每日账户快照"""
        trade_date = datetime.now().strftime('%Y-%m-%d')
        
        with self._get_connection() as conn:
            # 获取昨日累计盈亏
            yesterday = conn.execute('''
                SELECT cumulative_pnl FROM account_snapshot 
                WHERE trade_date < ? ORDER BY trade_date DESC LIMIT 1
            ''', (trade_date,)).fetchone()
            
            cumulative_pnl = (yesterday['cumulative_pnl'] if yesterday else 0) + day_pnl
            
            conn.execute('''
                INSERT OR REPLACE INTO account_snapshot 
                (trade_date, total_assets, cash_balance, position_value, day_pnl, 
                 cumulative_pnl, benchmark_return)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (trade_date, total_assets, cash_balance, position_value, day_pnl,
                  cumulative_pnl, benchmark_return))
            conn.commit()
    
    def get_performance_summary(self) -> Dict:
        """获取绩效摘要"""
        with self._get_connection() as conn:
            # 总交易次数
            total_trades = conn.execute(
                'SELECT COUNT(*) FROM trades'
            ).fetchone()[0]
            
            # 盈利次数（简化：卖出即视为平仓）
            sell_trades = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE action = 'sell'"
            ).fetchone()[0]
            
            # 最新资产
            latest = conn.execute('''
                SELECT * FROM account_snapshot ORDER BY trade_date DESC LIMIT 1
            ''').fetchone()
            
            return {
                'total_trades': total_trades,
                'closed_trades': sell_trades,
                'total_assets': latest['total_assets'] if latest else 0,
                'cash_balance': latest['cash_balance'] if latest else 0,
                'position_value': latest['position_value'] if latest else 0,
                'cumulative_pnl': latest['cumulative_pnl'] if latest else 0,
                'return_rate': (latest['cumulative_pnl'] / 100000 * 100) if latest else 0
            }

# 使用示例
if __name__ == '__main__':
    db = TradingDB()
    
    # 示例：记录一笔买入
    trade = Trade(
        ts_code='000001.SZ',
        trade_date='2026-03-30',
        action='buy',
        price=12.50,
        volume=1000,
        strategy='MA_CROSS',
        confidence=0.85,
        notes='测试交易'
    )
    trade_id = db.record_trade(trade)
    print(f'✅ 交易记录已保存，ID: {trade_id}')
    
    # 查询最近交易
    trades = db.get_trades()
    print(f'\n📊 最近交易:\n{trades}')
    
    # 查看绩效摘要
    summary = db.get_performance_summary()
    print(f'\n📈 绩效摘要:')
    for k, v in summary.items():
        print(f'  {k}: {v}')
