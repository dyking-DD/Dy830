"""
扩展策略库
包含：MACD、布林带、KDJ、RSI、动量突破、多因子共振等策略
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from strategies.base import BaseStrategy, Signal, Position


class RSIStrategy(BaseStrategy):
    """
    RSI相对强弱指标策略
    
    买入: RSI从超卖区反弹 (RSI < oversold后回升)
    卖出: RSI从超买区回落 (RSI > overbought后下降)
    """
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("RSI", {"period": period, "oversold": oversold, "overbought": overbought})
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.period + 1:
            return signals
        
        df = data.copy()
        df['rsi'] = self._calculate_rsi(df['close'])
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        ts_code = str(latest.get('ts_code', 'UNKNOWN'))
        trade_date = str(latest['trade_date'])
        
        if prev is not None:
            # RSI从超卖区反弹 - 买入信号
            if prev['rsi'] < self.oversold and latest['rsi'] >= self.oversold:
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='buy',
                    price=float(latest['close']),
                    volume=500,
                    reason=f"RSI超卖反弹: {latest['rsi']:.1f} (阈值{self.oversold})",
                    confidence=0.7
                ))
            
            # RSI从超买区回落 - 卖出信号
            elif prev['rsi'] > self.overbought and latest['rsi'] <= self.overbought:
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='sell',
                    price=float(latest['close']),
                    volume=500,
                    reason=f"RSI超买回落: {latest['rsi']:.1f} (阈值{self.overbought})",
                    confidence=0.7
                ))
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


class MACrossVolumeStrategy(BaseStrategy):
    """
    均线交叉 + 成交量确认策略
    在MA交叉基础上增加成交量过滤
    """
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20, 
                 volume_multiplier: float = 1.5):
        super().__init__("MA_Cross_Volume", {
            "fast": fast_period, 
            "slow": slow_period,
            "volume_mult": volume_multiplier
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.volume_multiplier = volume_multiplier
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.slow_period + 1:
            return signals
        
        df = data.copy()
        df['fast_ma'] = df['close'].rolling(self.fast_period).mean()
        df['slow_ma'] = df['close'].rolling(self.slow_period).mean()
        df['vol_ma20'] = df['vol'].rolling(20).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        if prev is None:
            return signals
        
        ts_code = str(latest.get('ts_code', 'UNKNOWN'))
        trade_date = str(latest['trade_date'])
        
        # 成交量确认
        volume_confirmed = latest['vol'] > latest['vol_ma20'] * self.volume_multiplier
        
        # 金叉 + 放量
        if prev['fast_ma'] <= prev['slow_ma'] and latest['fast_ma'] > latest['slow_ma']:
            if volume_confirmed:
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='buy',
                    price=float(latest['close']),
                    volume=500,
                    reason=f"放量金叉: MA{self.fast_period}上穿MA{self.slow_period}, 成交量{latest['vol']/latest['vol_ma20']:.1f}倍",
                    confidence=0.75
                ))
        
        # 死叉
        elif prev['fast_ma'] >= prev['slow_ma'] and latest['fast_ma'] < latest['slow_ma']:
            signals.append(Signal(
                ts_code=ts_code,
                trade_date=trade_date,
                action='sell',
                price=float(latest['close']),
                volume=500,
                reason=f"死叉: MA{self.fast_period}下穿MA{self.slow_period}",
                confidence=0.7
            ))
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


class MACDStrategy(BaseStrategy):
    """
    MACD指标策略 - 趋势跟踪
    
    买入: MACD金叉 (DIF上穿DEA) + MACD柱状线转正
    卖出: MACD死叉 (DIF下穿DEA) + MACD柱状线转负
    """
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD", {"fast": fast, "slow": slow, "signal": signal})
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def _calculate_macd(self, prices: pd.Series) -> tuple:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=self.fast, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=self.signal, adjust=False).mean()
        macd_hist = 2 * (dif - dea)
        return dif, dea, macd_hist
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.slow + self.signal:
            return signals
        
        df = data.copy()
        df['dif'], df['dea'], df['macd_hist'] = self._calculate_macd(df['close'])
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        ts_code = str(latest.get('ts_code', 'UNKNOWN'))
        trade_date = str(latest['trade_date'])
        
        if prev is not None:
            # MACD金叉: DIF上穿DEA + 柱状线转正
            if (prev['dif'] <= prev['dea'] and latest['dif'] > latest['dea'] and 
                latest['macd_hist'] > 0):
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='buy',
                    price=float(latest['close']),
                    volume=500,
                    reason=f"MACD金叉: DIF({latest['dif']:.2f})上穿DEA({latest['dea']:.2f})",
                    confidence=0.75
                ))
            
            # MACD死叉: DIF下穿DEA + 柱状线转负
            elif (prev['dif'] >= prev['dea'] and latest['dif'] < latest['dea'] and 
                  latest['macd_hist'] < 0):
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='sell',
                    price=float(latest['close']),
                    volume=500,
                    reason=f"MACD死叉: DIF({latest['dif']:.2f})下穿DEA({latest['dea']:.2f})",
                    confidence=0.75
                ))
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


class BollingerBandsStrategy(BaseStrategy):
    """
    布林带(BOLL)均值回归策略
    
    买入: 价格触及下轨后反弹向上 + 带宽收缩
    卖出: 价格触及上轨后回落向下 + 带宽扩张
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0, 
                 bandwidth_threshold: float = 0.1):
        super().__init__("BollingerBands", {
            "period": period, 
            "std_dev": std_dev,
            "bandwidth_threshold": bandwidth_threshold
        })
        self.period = period
        self.std_dev = std_dev
        self.bandwidth_threshold = bandwidth_threshold
    
    def _calculate_bollinger(self, prices: pd.Series) -> tuple:
        """计算布林带"""
        middle = prices.rolling(window=self.period).mean()
        std = prices.rolling(window=self.period).std()
        upper = middle + self.std_dev * std
        lower = middle - self.std_dev * std
        return upper, middle, lower
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.period + 1:
            return signals
        
        df = data.copy()
        df['upper'], df['middle'], df['lower'] = self._calculate_bollinger(df['close'])
        df['bb_width'] = (df['upper'] - df['lower']) / df['middle']
        df['bb_position'] = (df['close'] - df['lower']) / (df['upper'] - df['lower'])
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        ts_code = str(latest.get('ts_code', 'UNKNOWN'))
        trade_date = str(latest['trade_date'])
        
        if prev is not None:
            current_price = latest['close']
            
            # 买入信号: 价格从下轨下方反弹 + 带宽足够
            if (prev['close'] <= prev['lower'] and current_price > prev['lower'] and 
                current_price > prev['close'] and latest['bb_width'] > self.bandwidth_threshold):
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='buy',
                    price=float(current_price),
                    volume=500,
                    reason=f"布林带下轨反弹: 价格{current_price:.2f}从下轨{latest['lower']:.2f}反弹, 带宽{latest['bb_width']:.3f}",
                    confidence=0.7
                ))
            
            # 卖出信号: 价格从上轨上方回落
            elif prev['close'] >= prev['upper'] and current_price < prev['upper'] and current_price < prev['close']:
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='sell',
                    price=float(current_price),
                    volume=500,
                    reason=f"布林带上轨回落: 价格{current_price:.2f}从上轨{latest['upper']:.2f}回落",
                    confidence=0.7
                ))
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


class KDJStrategy(BaseStrategy):
    """
    KDJ随机指标策略
    
    买入: K值上穿D值且在低位(<30)
    卖出: K值下穿D值且在高位(>70)
    """
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        super().__init__("KDJ", {"n": n, "m1": m1, "m2": m2})
        self.n = n
        self.m1 = m1
        self.m2 = m2
    
    def _calculate_kdj(self, high: pd.Series, low: pd.Series, close: pd.Series) -> tuple:
        """计算KDJ指标"""
        lowest_low = low.rolling(window=self.n).min()
        highest_high = high.rolling(window=self.n).max()
        
        rsv = 100 * (close - lowest_low) / (highest_high - lowest_low)
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(com=self.m1-1, adjust=False).mean()
        d = k.ewm(com=self.m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return k, d, j
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.n + self.m1 + self.m2:
            return signals
        
        df = data.copy()
        df['k'], df['d'], df['j'] = self._calculate_kdj(df['high'], df['low'], df['close'])
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        ts_code = str(latest.get('ts_code', 'UNKNOWN'))
        trade_date = str(latest['trade_date'])
        
        if prev is not None:
            # KDJ金叉且在低位
            if prev['k'] <= prev['d'] and latest['k'] > latest['d'] and latest['k'] < 30:
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='buy',
                    price=float(latest['close']),
                    volume=500,
                    reason=f"KDJ低位金叉: K({latest['k']:.1f})上穿D({latest['d']:.1f})",
                    confidence=0.75
                ))
            
            # KDJ死叉且在高位
            elif prev['k'] >= prev['d'] and latest['k'] < latest['d'] and latest['k'] > 70:
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='sell',
                    price=float(latest['close']),
                    volume=500,
                    reason=f"KDJ高位死叉: K({latest['k']:.1f})下穿D({latest['d']:.1f})",
                    confidence=0.75
                ))
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


class MomentumBreakoutStrategy(BaseStrategy):
    """
    动量突破策略
    
    买入条件：
    1. 价格突破前N日高点
    2. 成交量放大 (>20日均量 * multiplier)
    3. 价格上涨幅度 > threshold
    
    卖出条件：
    1. 价格跌破前N日低点
    2. 或 跌破入场价 * (1 - stop_loss)
    """
    
    def __init__(self, lookback: int = 20, volume_mult: float = 2.0, 
                 price_threshold: float = 0.03, stop_loss: float = 0.05):
        super().__init__("MomentumBreakout", {
            "lookback": lookback,
            "volume_mult": volume_mult,
            "price_threshold": price_threshold,
            "stop_loss": stop_loss
        })
        self.lookback = lookback
        self.volume_mult = volume_mult
        self.price_threshold = price_threshold
        self.stop_loss = stop_loss
        self.entry_prices: Dict[str, float] = {}  # 记录入场价
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.lookback + 20:
            return signals
        
        df = data.copy()
        df['hh'] = df['high'].rolling(self.lookback).max()  # 前N日高点
        df['ll'] = df['low'].rolling(self.lookback).min()   # 前N日低点
        df['vol_ma20'] = df['vol'].rolling(20).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        ts_code = str(latest.get('ts_code', 'UNKNOWN'))
        trade_date = str(latest['trade_date'])
        
        if prev is None:
            return signals
        
        current_price = latest['close']
        prev_high = prev['hh']
        prev_low = prev['ll']
        vol_avg = latest['vol_ma20']
        
        # 突破买入：价格突破前高 + 放量 + 涨幅足够
        price_change = (current_price - prev['close']) / prev['close']
        volume_surge = latest['vol'] > vol_avg * self.volume_mult
        breakout = current_price > prev_high * 0.995  # 允许0.5%误差
        
        if breakout and volume_surge and price_change > self.price_threshold:
            self.entry_prices[ts_code] = current_price
            signals.append(Signal(
                ts_code=ts_code,
                trade_date=trade_date,
                action='buy',
                price=float(current_price),
                volume=500,
                reason=f"动量突破: 突破{self.lookback}日高点{prev_high:.2f}, 涨幅{price_change*100:.1f}%, 放量{latest['vol']/vol_avg:.1f}倍",
                confidence=0.8
            ))
        
        # 止损卖出：跌破前低或入场价止损
        elif ts_code in self.entry_prices:
            entry_price = self.entry_prices[ts_code]
            stop_price = entry_price * (1 - self.stop_loss)
            
            if current_price < prev_low or current_price < stop_price:
                reason = f"动量止损: 跌破"
                if current_price < prev_low:
                    reason += f"{self.lookback}日低点{prev_low:.2f}"
                else:
                    reason += f"止损位{stop_price:.2f}"
                
                signals.append(Signal(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    action='sell',
                    price=float(current_price),
                    volume=500,
                    reason=reason,
                    confidence=0.75
                ))
                del self.entry_prices[ts_code]
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


class CombinedStrategy(BaseStrategy):
    """
    多因子共振策略 - 升级版
    
    结合多个技术指标，多条件共振才产生信号
    - 趋势判断：均线排列
    - 动量确认：MACD
    - 超买超卖：RSI
    - 波动率：布林带位置
    - 量能确认：成交量
    
    买入：至少3个条件同时满足
    卖出：任一重要条件反转
    """
    
    def __init__(self, 
                 ma_fast: int = 5,
                 ma_slow: int = 20,
                 rsi_period: int = 14,
                 rsi_oversold: int = 35,
                 rsi_overbought: int = 65,
                 min_conditions: int = 3):
        super().__init__("Combined_Resonance", {
            "ma_fast": ma_fast, "ma_slow": ma_slow,
            "rsi_period": rsi_period,
            "rsi_oversold": rsi_oversold,
            "rsi_overbought": rsi_overbought,
            "min_conditions": min_conditions
        })
        self.ma_fast = ma_fast
        self.ma_slow = ma_slow
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.min_conditions = min_conditions
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < max(self.ma_slow, self.rsi_period, 26) + 1:
            return signals
        
        df = data.copy()
        
        # 计算均线
        df[f'ma_{self.ma_fast}'] = df['close'].rolling(self.ma_fast).mean()
        df[f'ma_{self.ma_slow}'] = df['close'].rolling(self.ma_slow).mean()
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 计算MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['dif'] = ema_fast - ema_slow
        df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = 2 * (df['dif'] - df['dea'])
        
        # 计算布林带位置
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 成交量
        df['vol_ma20'] = df['vol'].rolling(20).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        ts_code = str(latest.get('ts_code', 'UNKNOWN'))
        trade_date = str(latest['trade_date'])
        
        if prev is None:
            return signals
        
        # 评估买入条件
        buy_conditions = []
        
        # 1. 均线多头排列
        if latest[f'ma_{self.ma_fast}'] > latest[f'ma_{self.ma_slow}']:
            buy_conditions.append("均线多头排列")
        
        # 2. MACD金叉或红柱
        if latest['dif'] > latest['dea'] and latest['macd_hist'] > 0:
            buy_conditions.append("MACD多头")
        
        # 3. RSI从超卖反弹
        if prev['rsi'] < self.rsi_oversold and latest['rsi'] >= self.oversold:
            buy_conditions.append("RSI超卖反弹")
        elif self.rsi_oversold <= latest['rsi'] <= 55:
            buy_conditions.append("RSI健康区间")
        
        # 4. 布林带中轨上方
        if latest['bb_position'] > 0.5:
            buy_conditions.append("布林带强势区")
        
        # 5. 放量
        if latest['vol'] > latest['vol_ma20'] * 1.5:
            buy_conditions.append("成交量放大")
        
        # 买入信号：满足最少条件数
        if len(buy_conditions) >= self.min_conditions:
            signals.append(Signal(
                ts_code=ts_code,
                trade_date=trade_date,
                action='buy',
                price=float(latest['close']),
                volume=500,
                reason=f"多因子共振买入({len(buy_conditions)}/5): {', '.join(buy_conditions)}",
                confidence=0.5 + len(buy_conditions) * 0.1
            ))
        
        # 评估卖出条件（任一重要条件反转）
        sell_conditions = []
        
        # 1. 均线死叉
        if prev[f'ma_{self.ma_fast}'] >= prev[f'ma_{self.ma_slow}'] and \
           latest[f'ma_{self.ma_fast}'] < latest[f'ma_{self.ma_slow}']:
            sell_conditions.append("均线死叉")
        
        # 2. MACD死叉
        if prev['dif'] >= prev['dea'] and latest['dif'] < latest['dea']:
            sell_conditions.append("MACD死叉")
        
        # 3. RSI超买回落
        if prev['rsi'] > self.rsi_overbought and latest['rsi'] <= self.rsi_overbought:
            sell_conditions.append("RSI超买回落")
        
        # 4. 跌破布林带中轨
        if prev['close'] >= prev['bb_middle'] and latest['close'] < latest['bb_middle']:
            sell_conditions.append("跌破布林带中轨")
        
        # 卖出信号：任一重要条件
        if len(sell_conditions) >= 1:
            signals.append(Signal(
                ts_code=ts_code,
                trade_date=trade_date,
                action='sell',
                price=float(latest['close']),
                volume=500,
                reason=f"因子反转卖出: {', '.join(sell_conditions)}",
                confidence=0.7
            ))
        
        return signals
    
    def on_data(self, data: pd.DataFrame, positions: Dict[str, Position]) -> List[Signal]:
        return self.generate_signals(data)


# 策略注册表
STRATEGIES = {
    'rsi': RSIStrategy,
    'macd': MACDStrategy,
    'bollinger': BollingerBandsStrategy,
    'kdj': KDJStrategy,
    'momentum_breakout': MomentumBreakoutStrategy,
    'combined': CombinedStrategy,
    'ma_cross_volume': MACrossVolumeStrategy,
}


def get_strategy(name: str, **kwargs):
    """获取策略实例"""
    if name not in STRATEGIES:
        raise ValueError(f"未知策略: {name}. 可用策略: {list(STRATEGIES.keys())}")
    return STRATEGIES[name](**kwargs)


if __name__ == "__main__":
    # 测试
    import numpy as np
    
    # 生成测试数据
    np.random.seed(42)
    dates = pd.date_range('20240101', periods=100, freq='B')
    prices = 10 + np.random.randn(100).cumsum() * 0.5
    
    data = pd.DataFrame({
        'trade_date': dates.strftime('%Y%m%d'),
        'open': prices + np.random.randn(100) * 0.1,
        'high': prices + abs(np.random.randn(100)) * 0.2,
        'low': prices - abs(np.random.randn(100)) * 0.2,
        'close': prices,
        'vol': np.random.randint(10000, 100000, 100)
    })
    
    # 测试所有策略
    test_strategies = [
        ('RSI', RSIStrategy()),
        ('MACD', MACDStrategy()),
        ('Bollinger', BollingerBandsStrategy()),
        ('KDJ', KDJStrategy()),
        ('MomentumBreakout', MomentumBreakoutStrategy()),
        ('Combined', CombinedStrategy()),
        ('MA+Volume', MACrossVolumeStrategy()),
    ]
    
    for name, strategy in test_strategies:
        signals = strategy.generate_signals(data)
        print(f"\n{'='*50}")
        print(f"策略: {name}")
        print(f"生成 {len(signals)} 个交易信号")
        
        for s in signals[:3]:  # 只显示前3个信号
            print(f"  [{s.action.upper()}] {s.trade_date}")
            print(f"    价格: {s.price:.2f}, 置信度: {s.confidence}")
            print(f"    原因: {s.reason}")
