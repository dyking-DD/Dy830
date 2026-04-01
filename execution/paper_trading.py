"""
模拟交易引擎 - Paper Trading Engine

功能：
- 模拟撮合（按收盘价或滑点成交）
- 模拟持仓管理
- 每日收益跟踪
- 交易信号执行
- 生成每日交易报告
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"  # 市价单（按收盘价）
    LIMIT = "limit"    # 限价单


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: int
    order_type: OrderType
    price: Optional[float] = None  # 限价单价格
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    commission: float = 0.0
    reason: str = ""  # 拒绝原因


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    cost_basis: float  # 总成本
    avg_price: float   # 均价
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    def update_price(self, price: float):
        """更新价格"""
        self.current_price = price
        self.market_value = self.quantity * price
        self.unrealized_pnl = self.market_value - self.cost_basis
        if self.cost_basis > 0:
            self.unrealized_pnl_pct = self.unrealized_pnl / self.cost_basis


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    order_id: str
    symbol: str
    action: str
    quantity: int
    price: float
    amount: float
    commission: float
    timestamp: datetime


class PaperTradingEngine:
    """
    模拟交易引擎
    
    模拟真实交易环境：
    - 按收盘价撮合（或使用滑点模拟）
    - 计算手续费、印花税
    - 管理现金和持仓
    - 记录所有交易历史
    """
    
    def __init__(self, 
                 initial_capital: float = 100000.0,
                 commission_rate: float = 0.0003,  # 券商佣金 万分之3
                 stamp_tax_rate: float = 0.001,    # 印花税 千分之1（卖出）
                 min_commission: float = 5.0,      # 最低佣金5元
                 slippage: float = 0.001,          # 滑点 千分之1
                 data_dir: str = "data"):
        """
        初始化模拟交易引擎
        
        Args:
            initial_capital: 初始资金
            commission_rate: 佣金费率
            stamp_tax_rate: 印花税率
            min_commission: 最低佣金
            slippage: 滑点（模拟市价单成交价差）
            data_dir: 数据目录
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.min_commission = min_commission
        self.slippage = slippage
        self.data_dir = data_dir
        
        # 账户状态
        self.cash = initial_capital
        self.equity = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        
        # 每日记录
        self.daily_records = []
        
        # 加载历史状态
        self._load_state()
        
        logger.info(f"模拟交易引擎初始化完成，初始资金: {initial_capital:,.2f}")
    
    def _load_state(self):
        """加载历史状态"""
        state_file = os.path.join(self.data_dir, "paper_trading_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.cash = state.get('cash', self.initial_capital)
                    self.positions = {
                        k: Position(**v) for k, v in state.get('positions', {}).items()
                    }
                logger.info(f"已加载历史状态，当前现金: {self.cash:,.2f}")
            except Exception as e:
                logger.warning(f"加载状态失败: {e}")
    
    def _save_state(self):
        """保存当前状态"""
        state = {
            'cash': self.cash,
            'positions': {
                k: {
                    'symbol': v.symbol,
                    'quantity': v.quantity,
                    'cost_basis': v.cost_basis,
                    'avg_price': v.avg_price,
                    'current_price': v.current_price,
                    'market_value': v.market_value,
                    'unrealized_pnl': v.unrealized_pnl,
                    'unrealized_pnl_pct': v.unrealized_pnl_pct
                }
                for k, v in self.positions.items()
            },
            'equity': self.equity,
            'updated_at': datetime.now().isoformat()
        }
        
        os.makedirs(self.data_dir, exist_ok=True)
        state_file = os.path.join(self.data_dir, "paper_trading_state.json")
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def submit_order(self, 
                    symbol: str,
                    action: str,
                    quantity: int,
                    order_type: OrderType = OrderType.MARKET,
                    price: Optional[float] = None,
                    current_price: Optional[float] = None) -> Order:
        """
        提交订单
        
        Args:
            symbol: 股票代码
            action: 'buy' or 'sell'
            quantity: 数量
            order_type: 订单类型
            price: 限价（限价单使用）
            current_price: 当前市场价（用于撮合）
        
        Returns:
            Order: 订单对象
        """
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{len(self.orders):04d}"
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            price=price
        )
        
        # 如果没有提供当前价，尝试撮合
        if current_price:
            self._execute_order(order, current_price)
        
        self.orders.append(order)
        return order
    
    def _execute_order(self, order: Order, market_price: float):
        """
        执行订单撮合
        
        Args:
            order: 订单
            market_price: 市场价格
        """
        # 市价单应用滑点
        if order.order_type == OrderType.MARKET:
            if order.action == 'buy':
                fill_price = market_price * (1 + self.slippage)
            else:
                fill_price = market_price * (1 - self.slippage)
        else:
            # 限价单检查
            if order.action == 'buy' and market_price > order.price:
                order.status = OrderStatus.REJECTED
                order.reason = "市场价格高于限价"
                return
            if order.action == 'sell' and market_price < order.price:
                order.status = OrderStatus.REJECTED
                order.reason = "市场价格低于限价"
                return
            fill_price = order.price
        
        # 计算金额
        amount = fill_price * order.quantity
        
        # 计算费用
        commission = max(amount * self.commission_rate, self.min_commission)
        stamp_tax = amount * self.stamp_tax_rate if order.action == 'sell' else 0
        total_cost = amount + commission + stamp_tax
        
        # 检查资金
        if order.action == 'buy':
            if total_cost > self.cash:
                order.status = OrderStatus.REJECTED
                order.reason = f"资金不足，需要 {total_cost:,.2f}，可用 {self.cash:,.2f}"
                return
            self.cash -= total_cost
            
            # 更新持仓
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_quantity = pos.quantity + order.quantity
                total_cost_basis = pos.cost_basis + amount
                pos.quantity = total_quantity
                pos.cost_basis = total_cost_basis
                pos.avg_price = total_cost_basis / total_quantity
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    cost_basis=amount,
                    avg_price=fill_price
                )
        
        else:  # sell
            if order.symbol not in self.positions:
                order.status = OrderStatus.REJECTED
                order.reason = "未持有该股票"
                return
            
            pos = self.positions[order.symbol]
            if pos.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                order.reason = f"持仓不足，持有 {pos.quantity}，试图卖出 {order.quantity}"
                return
            
            # 卖出收入
            self.cash += (amount - commission - stamp_tax)
            
            # 更新持仓
            sold_cost = pos.avg_price * order.quantity
            pos.quantity -= order.quantity
            pos.cost_basis -= sold_cost
            
            if pos.quantity == 0:
                del self.positions[order.symbol]
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.filled_at = datetime.now()
        order.commission = commission + stamp_tax
        
        # 记录成交
        trade = Trade(
            trade_id=f"TRD{order.order_id[3:]}",
            order_id=order.order_id,
            symbol=order.symbol,
            action=order.action,
            quantity=order.quantity,
            price=fill_price,
            amount=amount,
            commission=commission + stamp_tax,
            timestamp=order.filled_at
        )
        self.trades.append(trade)
        
        logger.info(f"成交: {order.action.upper()} {order.symbol} {order.quantity}股 @ {fill_price:.2f}")
    
    def update_prices(self, prices: Dict[str, float]):
        """
        更新持仓价格
        
        Args:
            prices: {symbol: price} 字典
        """
        total_market_value = 0
        
        for symbol, pos in self.positions.items():
            if symbol in prices:
                pos.update_price(prices[symbol])
                total_market_value += pos.market_value
        
        self.equity = self.cash + total_market_value
    
    def get_portfolio_summary(self) -> Dict:
        """获取投资组合摘要"""
        total_pnl = self.equity - self.initial_capital
        total_pnl_pct = (total_pnl / self.initial_capital) * 100
        
        return {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'equity': self.equity,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'position_count': len(self.positions),
            'positions_market_value': sum(p.market_value for p in self.positions.values()),
            'cash_ratio': self.cash / self.equity if self.equity > 0 else 0
        }
    
    def get_positions_df(self) -> pd.DataFrame:
        """获取持仓DataFrame"""
        if not self.positions:
            return pd.DataFrame()
        
        data = []
        for pos in self.positions.values():
            data.append({
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'avg_price': pos.avg_price,
                'current_price': pos.current_price,
                'market_value': pos.market_value,
                'cost_basis': pos.cost_basis,
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_pct': pos.unrealized_pnl_pct
            })
        
        return pd.DataFrame(data)
    
    def record_daily_snapshot(self, date: Optional[datetime] = None):
        """
        记录每日快照
        
        Args:
            date: 日期，默认今天
        """
        if date is None:
            date = datetime.now()
        
        snapshot = {
            'date': date.strftime('%Y-%m-%d'),
            'cash': self.cash,
            'equity': self.equity,
            'positions': len(self.positions),
            'summary': self.get_portfolio_summary()
        }
        
        self.daily_records.append(snapshot)
        self._save_state()
        
        logger.info(f"记录 {snapshot['date']} 快照，权益: {self.equity:,.2f}")
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> str:
        """
        生成每日交易报告
        
        Args:
            date: 日期，默认今天
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        summary = self.get_portfolio_summary()
        positions_df = self.get_positions_df()
        
        # 今日成交
        today_trades = [t for t in self.trades 
                       if t.timestamp.strftime('%Y-%m-%d') == date_str]
        
        report = f"""
{'='*60}
模拟交易日报 - {date_str}
{'='*60}

【账户概览】
初始资金: {summary['initial_capital']:,.2f}
当前现金: {summary['cash']:,.2f}
总资产:   {summary['equity']:,.2f}
累计盈亏: {summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:+.2f}%)
持仓数量: {summary['position_count']} 只
现金比例: {summary['cash_ratio']:.1%}

【持仓明细】
"""
        
        if positions_df.empty:
            report += "无持仓\n"
        else:
            report += positions_df.to_string(index=False)
            report += "\n"
        
        report += f"""
【今日成交】 ({len(today_trades)} 笔)
"""
        
        if not today_trades:
            report += "无成交\n"
        else:
            for trade in today_trades:
                report += f"  {trade.action.upper()} {trade.symbol} {trade.quantity}股 @ {trade.price:.2f}\n"
        
        report += f"""
{'='*60}
"""
        
        return report


if __name__ == "__main__":
    # 测试模拟交易引擎
    print("="*60)
    print("模拟交易引擎测试")
    print("="*60)
    
    # 初始化
    engine = PaperTradingEngine(initial_capital=100000)
    
    # 模拟买入
    print("\n--- 买入测试 ---")
    order1 = engine.submit_order('000001.SZ', 'buy', 1000, 
                                  order_type=OrderType.MARKET,
                                  current_price=10.0)
    print(f"买入订单: {order1.order_id} - {order1.status.value}")
    print(f"现金: {engine.cash:,.2f}")
    
    # 更新价格
    engine.update_prices({'000001.SZ': 10.5})
    print(f"权益: {engine.equity:,.2f}")
    
    # 模拟卖出
    print("\n--- 卖出测试 ---")
    order2 = engine.submit_order('000001.SZ', 'sell', 500,
                                  order_type=OrderType.MARKET,
                                  current_price=10.5)
    print(f"卖出订单: {order2.order_id} - {order2.status.value}")
    print(f"现金: {engine.cash:,.2f}")
    print(f"权益: {engine.equity:,.2f}")
    
    # 查看持仓
    print("\n--- 持仓 ---")
    print(engine.get_positions_df())
    
    # 生成报告
    print("\n--- 日报 ---")
    print(engine.generate_daily_report())
    
    print("\n" + "="*60)
    print("模拟交易引擎测试完成")
    print("="*60)
