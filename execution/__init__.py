"""
执行模块 (Execution Module)

提供量化交易系统的执行功能，包括：
- 模拟交易引擎 (Paper Trading)
- 实盘交易接口 (Live Trading)
- 东方财富 Choice 接口
- 通知管理 (Notification)
- 订单管理 (Order Management)

使用示例:
    from execution import (
        PaperTradingEngine, OrderType, 
        NotificationManager, OrderManager,
        LiveTradingManager, TradingMode,
        ChoiceTrader  # 东方财富 Choice 终端
    )
    
    # 东方财富 Choice 交易
    trader = ChoiceTrader()
    if trader.connect():
        trader.buy('000001.SZ', 10.5, 100)
        trader.disconnect()
"""

from .paper_trading import PaperTradingEngine, Order, Trade, Position, OrderType, OrderStatus
from .notifier import NotificationManager
from .order_manager import OrderManager, OrderSource, OrderRecord
from .live_trading import (
    LiveTradingManager, 
    TradingMode, 
    TradingInterface,
    PaperTradingInterface,
    AccountInfo,
    PositionInfo
)

try:
    from .dongcai_choice import ChoiceTrader
except ImportError:
    ChoiceTrader = None

__all__ = [
    # 模拟交易
    'PaperTradingEngine',
    'Order',
    'Trade',
    'Position',
    'OrderType',
    'OrderStatus',
    # 实盘交易
    'LiveTradingManager',
    'TradingMode',
    'TradingInterface',
    'PaperTradingInterface',
    'AccountInfo',
    'PositionInfo',
    # 东方财富
    'ChoiceTrader',
    # 通知和订单
    'NotificationManager',
    'OrderManager',
    'OrderSource',
    'OrderRecord',
]