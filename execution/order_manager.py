"""
订单管理器 - Order Manager

统一管理订单的生命周期：
- 订单创建与验证
- 订单状态跟踪
- 订单历史记录
- 与模拟交易引擎集成
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .paper_trading import PaperTradingEngine, Order, OrderType, OrderStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderSource(Enum):
    """订单来源"""
    MANUAL = "manual"      # 手动下单
    STRATEGY = "strategy"  # 策略信号
    STOP_LOSS = "stop_loss" # 止损触发
    TAKE_PROFIT = "take_profit" # 止盈触发


@dataclass
class OrderRecord:
    """订单记录（扩展信息）"""
    order_id: str
    symbol: str
    action: str
    quantity: int
    price: Optional[float]
    order_type: str
    source: str  # OrderSource
    strategy: Optional[str] = None  # 触发策略名称
    reason: Optional[str] = None    # 下单原因
    created_at: str = None
    executed_at: Optional[str] = None
    status: str = "pending"
    filled_quantity: int = 0
    avg_price: Optional[float] = None
    commission: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class OrderManager:
    """订单管理器"""
    
    def __init__(self, trading_engine: PaperTradingEngine, data_dir: str = "data/orders"):
        """
        初始化订单管理器
        
        Args:
            trading_engine: 模拟交易引擎实例
            data_dir: 订单数据保存目录
        """
        self.engine = trading_engine
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.orders_file = self.data_dir / "orders.json"
        self.pending_orders: Dict[str, OrderRecord] = {}
        self.order_history: List[OrderRecord] = []
        
        self._load_orders()
        self._register_callbacks()
    
    def _load_orders(self):
        """加载历史订单"""
        if self.orders_file.exists():
            try:
                with open(self.orders_file, 'r') as f:
                    data = json.load(f)
                    for order_data in data.get("history", []):
                        self.order_history.append(OrderRecord(**order_data))
                    for order_id, order_data in data.get("pending", {}).items():
                        self.pending_orders[order_id] = OrderRecord(**order_data)
                logger.info(f"已加载 {len(self.order_history)} 条历史订单")
            except Exception as e:
                logger.error(f"加载订单失败: {e}")
    
    def _save_orders(self):
        """保存订单数据"""
        try:
            data = {
                "history": [asdict(o) for o in self.order_history],
                "pending": {oid: asdict(o) for oid, o in self.pending_orders.items()}
            }
            with open(self.orders_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存订单失败: {e}")
    
    def _register_callbacks(self):
        """注册交易引擎回调"""
        # 可以在这里注册订单状态变化回调
        pass
    
    def submit_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET,
        source: OrderSource = OrderSource.MANUAL,
        strategy: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Optional[OrderRecord]:
        """
        提交订单
        
        Args:
            symbol: 股票代码
            action: 'buy' 或 'sell'
            quantity: 数量
            price: 价格（限价单需要）
            order_type: 订单类型
            source: 订单来源
            strategy: 触发策略名称
            reason: 下单原因
        
        Returns:
            OrderRecord: 订单记录，失败返回 None
        """
        try:
            # 生成订单ID
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
            
            # 验证参数
            if action not in ['buy', 'sell']:
                logger.error(f"无效的action: {action}")
                return None
            
            if quantity <= 0:
                logger.error(f"无效的quantity: {quantity}")
                return None
            
            # 创建订单记录
            record = OrderRecord(
                order_id=order_id,
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=price,
                order_type=order_type.value,
                source=source.value,
                strategy=strategy,
                reason=reason
            )
            
            # 提交到交易引擎
            current_price = price or self._get_current_price(symbol)
            if current_price is None:
                logger.error(f"无法获取 {symbol} 的当前价格")
                return None
            
            order = self.engine.submit_order(
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type=order_type,
                current_price=current_price
            )
            
            if order:
                record.status = order.status.value
                record.executed_at = datetime.now().isoformat()
                record.filled_quantity = quantity  # 简化处理，假设全部成交
                record.avg_price = current_price
                
                # 计算佣金（假设万3）
                record.commission = quantity * current_price * 0.0003
                
                self.order_history.append(record)
                logger.info(f"订单提交成功: {order_id} {action} {symbol} {quantity}股")
            else:
                record.status = "rejected"
                logger.warning(f"订单被拒绝: {order_id}")
            
            self._save_orders()
            return record
            
        except Exception as e:
            logger.error(f"提交订单失败: {e}")
            return None
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格（简化实现）"""
        # 这里应该从数据源获取实际价格
        # 简化处理：从持仓中获取，或使用默认值
        if symbol in self.engine.positions:
            return self.engine.positions[symbol].current_price
        return None
    
    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        """获取订单详情"""
        # 先查待处理
        if order_id in self.pending_orders:
            return self.pending_orders[order_id]
        
        # 再查历史
        for order in reversed(self.order_history):
            if order.order_id == order_id:
                return order
        
        return None
    
    def get_orders_by_symbol(self, symbol: str) -> List[OrderRecord]:
        """获取某股票的所有订单"""
        return [
            o for o in self.order_history
            if o.symbol == symbol
        ]
    
    def get_orders_by_date(self, date_str: str) -> List[OrderRecord]:
        """获取某日的所有订单"""
        return [
            o for o in self.order_history
            if o.created_at.startswith(date_str)
        ]
    
    def get_strategy_orders(self, strategy_name: str) -> List[OrderRecord]:
        """获取某策略的所有订单"""
        return [
            o for o in self.order_history
            if o.strategy == strategy_name
        ]
    
    def get_statistics(self) -> Dict:
        """获取订单统计"""
        if not self.order_history:
            return {
                "total_orders": 0,
                "buy_orders": 0,
                "sell_orders": 0,
                "total_commission": 0.0
            }
        
        buy_orders = [o for o in self.order_history if o.action == 'buy']
        sell_orders = [o for o in self.order_history if o.action == 'sell']
        
        return {
            "total_orders": len(self.order_history),
            "buy_orders": len(buy_orders),
            "sell_orders": len(sell_orders),
            "total_commission": sum(o.commission for o in self.order_history),
            "strategy_orders": len([o for o in self.order_history if o.source == OrderSource.STRATEGY.value]),
            "manual_orders": len([o for o in self.order_history if o.source == OrderSource.MANUAL.value])
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if order_id in self.pending_orders:
            order = self.pending_orders.pop(order_id)
            order.status = "cancelled"
            self.order_history.append(order)
            self._save_orders()
            logger.info(f"订单已取消: {order_id}")
            return True
        return False
    
    def export_orders(self, filepath: str):
        """导出订单到CSV"""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            if not self.order_history:
                return
            
            fieldnames = ['order_id', 'symbol', 'action', 'quantity', 'price', 
                         'order_type', 'source', 'strategy', 'reason', 
                         'created_at', 'status', 'commission']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for order in self.order_history:
                writer.writerow(asdict(order))
        
        logger.info(f"订单已导出到: {filepath}")


# 便捷函数
def create_order_manager(initial_capital: float = 100000, data_dir: str = "data/orders") -> OrderManager:
    """创建订单管理器（带默认交易引擎）"""
    engine = PaperTradingEngine(initial_capital=initial_capital)
    return OrderManager(engine, data_dir)


if __name__ == "__main__":
    # 测试
    manager = create_order_manager()
    
    # 模拟添加持仓
    manager.engine.positions['000001.SZ'] = type('Position', (), {
        'current_price': 10.5,
        'quantity': 1000
    })()
    
    # 提交测试订单
    order = manager.submit_order(
        symbol='000001.SZ',
        action='buy',
        quantity=100,
        source=OrderSource.STRATEGY,
        strategy='SEPA',
        reason='突破买入信号'
    )
    
    print(f"订单统计: {manager.get_statistics()}")
