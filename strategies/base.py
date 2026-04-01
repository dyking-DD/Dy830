"""
策略基类
所有策略继承此类
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:
    """交易信号"""
    ts_code: str
    trade_date: str
    action: str  # 'buy', 'sell', 'hold'
    price: float
    volume: int
    reason: str
    confidence: float = 0.5  # 0-1


@dataclass
class Position:
    """持仓"""
    ts_code: str
    volume: int
    avg_cost: float
    current_price: float = 0
    
    @property
    def market_value(self) -> float:
        return self.volume * self.current_price
    
    @property
    def profit_loss(self) -> float:
        return (self.current_price - self.avg_cost) * self.volume
    
    @property
    def profit_loss_pct(self) -> float:
        if self.avg_cost == 0:
            return 0
        return (self.current_price - self.avg_cost) / self.avg_cost * 100


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str, params: Optional[Dict] = None):
        """
        Args:
            name: 策略名称
            params: 策略参数
        """
        self.name = name
        self.params = params or {}
        self.signals: List[Signal] = []
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号
        
        Args:
            data: 股票数据DataFrame
            
        Returns:
            信号列表
        """
        pass
    
    @abstractmethod
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        """每次数据更新时调用
        
        Args:
            data: 当前数据
            positions: 当前持仓
            
        Returns:
            新的交易信号
        """
        pass
    
    def get_required_data(self) -> List[str]:
        """返回策略需要的数据字段"""
        return ['open', 'high', 'low', 'close', 'vol']


class MovingAverageCrossStrategy(BaseStrategy):
    """双均线交叉策略 (示例)"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20):
        super().__init__("MA_Cross", {"fast": fast_period, "slow": slow_period})
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """均线金叉买入，死叉卖出"""
        signals = []
        
        if len(data) < self.slow_period + 1:
            return signals
        
        # 计算均线
        data['fast_ma'] = data['close'].rolling(self.fast_period).mean()
        data['slow_ma'] = data['close'].rolling(self.slow_period).mean()
        
        # 最新数据
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else None
        
        if prev is None:
            return signals
        
        ts_code = latest.get('ts_code', 'unknown')
        trade_date = str(latest['trade_date'])
        
        # 金叉: 短均线上穿长均线
        if prev['fast_ma'] <= prev['slow_ma'] and latest['fast_ma'] > latest['slow_ma']:
            signals.append(Signal(
                ts_code=ts_code,
                trade_date=trade_date,
                action='buy',
                price=latest['close'],
                volume=100,  # 默认手数
                reason=f"金叉: MA{self.fast_period} 上穿 MA{self.slow_period}",
                confidence=0.7
            ))
        
        # 死叉: 短均线下穿长均线
        elif prev['fast_ma'] >= prev['slow_ma'] and latest['fast_ma'] < latest['slow_ma']:
            signals.append(Signal(
                ts_code=ts_code,
                trade_date=trade_date,
                action='sell',
                price=latest['close'],
                volume=100,
                reason=f"死叉: MA{self.fast_period} 下穿 MA{self.slow_period}",
                confidence=0.7
            ))
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


if __name__ == "__main__":
    # 测试
    import numpy as np
    
    # 生成测试数据
    dates = pd.date_range('20240101', periods=100, freq='B')
    data = pd.DataFrame({
        'trade_date': dates.strftime('%Y%m%d'),
        'open': np.random.randn(100).cumsum() + 10,
        'high': np.random.randn(100).cumsum() + 11,
        'low': np.random.randn(100).cumsum() + 9,
        'close': np.random.randn(100).cumsum() + 10,
        'vol': np.random.randint(1000, 10000, 100)
    })
    
    strategy = MovingAverageCrossStrategy(fast_period=5, slow_period=10)
    signals = strategy.generate_signals(data)
    print(f"生成 {len(signals)} 个信号")
    for s in signals[:5]:
        print(f"  {s.action}: {s.reason}")
