"""
实盘交易接口 - Live Trading Interface

为券商API提供统一抽象层，支持：
- 模拟实盘（纸交易）
- 真实券商API（需按需实现）

注意：实盘交易涉及真实资金，使用前请充分测试！
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .paper_trading import PaperTradingEngine, Order, OrderType, OrderStatus
from ..risk.risk_manager import RiskManager
from ..execution.notifier import NotificationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """交易模式"""
    PAPER = "paper"      # 模拟交易
    LIVE = "live"        # 实盘交易
    DRY_RUN = "dry_run"  # 干跑（模拟但不执行）


@dataclass
class AccountInfo:
    """账户信息"""
    account_id: str
    total_assets: float
    available_cash: float
    market_value: float
    total_pnl: float
    total_return_pct: float
    margin_available: float = 0.0
    margin_used: float = 0.0


@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float = 0.0


class TradingInterface(ABC):
    """交易接口抽象基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接券商API"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[PositionInfo]:
        """获取持仓列表"""
        pass
    
    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> Optional[str]:
        """
        提交订单
        
        Args:
            symbol: 股票代码
            action: 'buy' 或 'sell'
            quantity: 数量
            order_type: 订单类型
            price: 限价价格（限价单需要）
        
        Returns:
            order_id: 订单ID，失败返回None
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """获取订单状态"""
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """获取实时行情"""
        pass


class PaperTradingInterface(TradingInterface):
    """
    模拟交易接口
    使用 PaperTradingEngine 作为底层实现
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        data_dir: str = "data/paper_trading"
    ):
        self.engine = PaperTradingEngine(
            initial_capital=initial_capital,
            data_dir=data_dir
        )
        self.connected = False
        self.risk_manager = RiskManager()
    
    def connect(self) -> bool:
        """连接（模拟）"""
        self.connected = True
        logger.info("模拟交易接口已连接")
        return True
    
    def disconnect(self):
        """断开连接"""
        self.engine.save_state()
        self.connected = False
        logger.info("模拟交易接口已断开")
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        state = self.engine.get_portfolio_state()
        return AccountInfo(
            account_id="PAPER_001",
            total_assets=state['total_value'],
            available_cash=state['cash'],
            market_value=state['total_value'] - state['cash'],
            total_pnl=state['total_pnl'],
            total_return_pct=state['total_return_pct']
        )
    
    def get_positions(self) -> List[PositionInfo]:
        """获取持仓列表"""
        positions = []
        for symbol, pos in self.engine.positions.items():
            positions.append(PositionInfo(
                symbol=symbol,
                quantity=pos.quantity,
                avg_cost=pos.avg_cost,
                current_price=pos.current_price,
                market_value=pos.market_value,
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_pct=pos.unrealized_pnl_pct,
                realized_pnl=pos.realized_pnl
            ))
        return positions
    
    def submit_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> Optional[str]:
        """提交订单"""
        # 获取当前价格
        current_price = price or self._get_current_price(symbol)
        if not current_price:
            logger.error(f"无法获取 {symbol} 的当前价格")
            return None
        
        # 风控检查
        risk_check = self.risk_manager.check_order(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=current_price,
            portfolio_state=self.engine.get_portfolio_state()
        )
        
        if not risk_check['allowed']:
            logger.warning(f"风控拦截: {risk_check['reason']}")
            return None
        
        # 提交订单
        order = self.engine.submit_order(
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            current_price=current_price
        )
        
        if order:
            logger.info(f"模拟订单提交成功: {order.order_id}")
            return order.order_id
        
        return None
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单（模拟交易通常立即成交）"""
        logger.info(f"模拟订单取消: {order_id}")
        return True
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """获取订单状态"""
        # 模拟交易通常立即成交
        return {
            'order_id': order_id,
            'status': 'filled',
            'filled_quantity': 0,  # 需要实际查询
            'avg_price': 0.0
        }
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """获取实时行情（模拟）"""
        # 从持仓或获取最新价格
        if symbol in self.engine.positions:
            pos = self.engine.positions[symbol]
            return {
                'symbol': symbol,
                'price': pos.current_price,
                'bid': pos.current_price * 0.999,
                'ask': pos.current_price * 1.001,
                'volume': 0
            }
        return None
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        if symbol in self.engine.positions:
            return self.engine.positions[symbol].current_price
        # 这里应该从数据源获取
        return None


class LiveTradingManager:
    """
    实盘交易管理器
    统一管理模拟/实盘交易切换
    """
    
    def __init__(self, mode: TradingMode = TradingMode.PAPER):
        self.mode = mode
        self.interface: Optional[TradingInterface] = None
        self.risk_manager = RiskManager()
        self.notifier = None
        
        # 尝试初始化通知器
        try:
            self.notifier = NotificationManager()
        except:
            pass
        
        self._init_interface()
    
    def _init_interface(self):
        """初始化交易接口"""
        if self.mode == TradingMode.PAPER:
            self.interface = PaperTradingInterface()
        elif self.mode == TradingMode.LIVE:
            # TODO: 实现真实券商API接口
            logger.error("实盘交易接口尚未实现")
            raise NotImplementedError("实盘交易接口需要配置券商API")
        elif self.mode == TradingMode.DRY_RUN:
            self.interface = PaperTradingInterface()
            logger.info("干跑模式：模拟交易但不保存状态")
    
    def connect(self) -> bool:
        """连接交易接口"""
        if self.interface:
            return self.interface.connect()
        return False
    
    def disconnect(self):
        """断开连接"""
        if self.interface:
            self.interface.disconnect()
    
    def submit_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        strategy: str = "manual",
        reason: str = ""
    ) -> Optional[str]:
        """
        提交订单（带风控和通知）
        
        Args:
            symbol: 股票代码
            action: 'buy' 或 'sell'
            quantity: 数量
            strategy: 触发策略
            reason: 下单原因
        """
        if not self.interface:
            logger.error("交易接口未初始化")
            return None
        
        # 获取账户信息
        account = self.interface.get_account_info()
        if not account:
            logger.error("无法获取账户信息")
            return None
        
        # 获取实时价格
        quote = self.interface.get_quote(symbol)
        price = quote['price'] if quote else None
        
        # 风控检查
        portfolio = {
            'cash': account.available_cash,
            'positions': self.interface.get_positions()
        }
        
        risk_check = self.risk_manager.check_order(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price or 0,
            portfolio_state=portfolio
        )
        
        if not risk_check['allowed']:
            logger.warning(f"风控拦截: {risk_check['reason']}")
            if self.notifier:
                self.notifier.send_risk_alert(
                    title="交易被风控拦截",
                    content=f"{action.upper()} {symbol} {quantity}股\n原因: {risk_check['reason']}",
                    level="warning"
                )
            return None
        
        # 提交订单
        order_id = self.interface.submit_order(
            symbol=symbol,
            action=action,
            quantity=quantity
        )
        
        if order_id:
            logger.info(f"订单提交成功: {order_id}")
            
            # 发送通知
            if self.notifier:
                if action == 'buy':
                    self.notifier.send_buy_signal(symbol, quantity, price or 0, reason)
                else:
                    self.notifier.send_sell_signal(symbol, quantity, price or 0, reason)
        
        return order_id
    
    def get_portfolio_summary(self) -> Dict:
        """获取投资组合摘要"""
        if not self.interface:
            return {}
        
        account = self.interface.get_account_info()
        positions = self.interface.get_positions()
        
        return {
            'account': account,
            'positions': positions,
            'position_count': len(positions),
            'mode': self.mode.value
        }


# 便捷函数
def create_trading_manager(mode: str = "paper") -> LiveTradingManager:
    """创建交易管理器"""
    mode_map = {
        "paper": TradingMode.PAPER,
        "live": TradingMode.LIVE,
        "dry_run": TradingMode.DRY_RUN
    }
    
    trading_mode = mode_map.get(mode, TradingMode.PAPER)
    return LiveTradingManager(trading_mode)


if __name__ == "__main__":
    # 测试
    manager = create_trading_manager("paper")
    
    if manager.connect():
        print("账户信息:", manager.get_portfolio_summary())
        manager.disconnect()
