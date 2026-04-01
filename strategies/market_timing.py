"""
市场择时模块 - Market Timing Module

提供大盘择时功能，用于过滤个股交易信号
- 指数趋势判断
- 市场情绪指标
- 波动率过滤
- 多指数共振
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MarketTimingSignal:
    """择时信号"""
    index_code: str
    date: str
    trend: str  # 'bull', 'bear', 'neutral'
    trend_strength: float  # 0-1
    allow_long: bool  # 允许做多
    allow_short: bool  # 允许做空
    indicators: Dict = None
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}


class MarketTimingModule:
    """
    大盘择时模块
    
    综合判断市场状态，过滤个股信号
    """
    
    def __init__(self, 
                 index_code: str = '000001.SH',  # 上证指数
                 ma_short: int = 20,
                 ma_long: int = 60,
                 volatility_period: int = 20):
        self.index_code = index_code
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.volatility_period = volatility_period
        self.data_fetcher = None
        
    def _get_index_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指数数据"""
        try:
            import akshare as ak
            
            # 获取上证指数数据
            if self.index_code == '000001.SH':
                df = ak.index_zh_a_hist(symbol="000001", period="daily",
                                        start_date=start_date, end_date=end_date)
                if df is not None and not df.empty:
                    df = df.rename(columns={
                        '日期': 'trade_date',
                        '开盘': 'open',
                        '最高': 'high',
                        '最低': 'low',
                        '收盘': 'close',
                        '成交量': 'vol'
                    })
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
                    return df
            
            # 沪深300
            elif self.index_code == '000300.SH':
                df = ak.index_zh_a_hist(symbol="000300", period="daily",
                                        start_date=start_date, end_date=end_date)
                if df is not None and not df.empty:
                    df = df.rename(columns={
                        '日期': 'trade_date',
                        '开盘': 'open',
                        '最高': 'high',
                        '最低': 'low',
                        '收盘': 'close',
                        '成交量': 'vol'
                    })
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
                    return df
                    
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
        
        return pd.DataFrame()
    
    def analyze_market(self, as_of_date: str = None) -> MarketTimingSignal:
        """
        分析市场状态
        
        Returns:
            MarketTimingSignal 择时信号
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime('%Y%m%d')
        
        # 获取最近150天数据
        end_dt = datetime.strptime(as_of_date, '%Y%m%d')
        start_dt = end_dt - timedelta(days=150)
        
        df = self._get_index_data(start_dt.strftime('%Y%m%d'), as_of_date)
        
        if df.empty or len(df) < self.ma_long:
            logger.warning("指数数据不足，默认允许交易")
            return MarketTimingSignal(
                index_code=self.index_code,
                date=as_of_date,
                trend='neutral',
                trend_strength=0.5,
                allow_long=True,
                allow_short=False
            )
        
        # 计算技术指标
        df['ma_short'] = df['close'].rolling(self.ma_short).mean()
        df['ma_long'] = df['close'].rolling(self.ma_long).mean()
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(self.volatility_period).std() * np.sqrt(252)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        # 趋势判断
        ma_bullish = latest['ma_short'] > latest['ma_long']
        price_above_ma = latest['close'] > latest['ma_short']
        
        # 波动率判断
        volatility_low = latest['volatility'] < 0.25  # 年化波动率<25%
        volatility_high = latest['volatility'] > 0.40  # 年化波动率>40%
        
        # 趋势强度 (0-1)
        ma_spread = (latest['ma_short'] - latest['ma_long']) / latest['ma_long']
        trend_strength = min(abs(ma_spread) * 20, 1.0)  # 标准化到0-1
        
        # 综合判断
        if ma_bullish and price_above_ma and not volatility_high:
            trend = 'bull'
            allow_long = True
            allow_short = False
        elif not ma_bullish and not price_above_ma:
            trend = 'bear'
            allow_long = False
            allow_short = True
        else:
            trend = 'neutral'
            allow_long = volatility_low  # 低波动时允许做多
            allow_short = False
        
        return MarketTimingSignal(
            index_code=self.index_code,
            date=as_of_date,
            trend=trend,
            trend_strength=trend_strength,
            allow_long=allow_long,
            allow_short=allow_short,
            indicators={
                'ma_short': latest['ma_short'],
                'ma_long': latest['ma_long'],
                'close': latest['close'],
                'volatility': latest['volatility'],
                'ma_bullish': ma_bullish,
                'price_above_ma': price_above_ma
            }
        )
    
    def filter_signals(self, signals: List, as_of_date: str = None) -> List:
        """
        根据市场择时过滤个股信号
        
        Args:
            signals: 原始交易信号列表
            as_of_date: 日期
            
        Returns:
            过滤后的信号列表
        """
        if not signals:
            return []
        
        market_signal = self.analyze_market(as_of_date)
        
        filtered = []
        for signal in signals:
            if signal.action == 'buy' and not market_signal.allow_long:
                logger.info(f"市场择时过滤买入信号: {signal.ts_code}")
                continue
            if signal.action == 'sell' and not market_signal.allow_short:
                logger.info(f"市场择时过滤卖出信号: {signal.ts_code}")
                continue
            filtered.append(signal)
        
        logger.info(f"择时过滤: {len(signals)} -> {len(filtered)} 个信号")
        return filtered


class MultiIndexTiming:
    """
    多指数择时 - 更严格的市场判断
    
    同时监控多个指数，综合判断市场状态
    """
    
    def __init__(self):
        self.indices = {
            '000001.SH': '上证指数',
            '000300.SH': '沪深300',
            '399006.SZ': '创业板指',
        }
        self.timing_modules = {
            code: MarketTimingModule(index_code=code)
            for code in self.indices.keys()
        }
    
    def get_composite_signal(self, as_of_date: str = None) -> Dict:
        """
        获取综合择时信号
        
        Returns:
            {
                'overall_trend': 'bull'/'bear'/'neutral',
                'consensus': float,  # 0-1 一致性
                'allow_long': bool,
                'details': {index_code: MarketTimingSignal}
            }
        """
        signals = {}
        bull_count = 0
        bear_count = 0
        
        for code, module in self.timing_modules.items():
            signal = module.analyze_market(as_of_date)
            signals[code] = signal
            
            if signal.trend == 'bull':
                bull_count += 1
            elif signal.trend == 'bear':
                bear_count += 1
        
        total = len(self.indices)
        
        # 综合判断
        if bull_count >= 2:
            overall = 'bull'
            allow_long = True
        elif bear_count >= 2:
            overall = 'bear'
            allow_long = False
        else:
            overall = 'neutral'
            allow_long = bull_count > bear_count
        
        consensus = max(bull_count, bear_count) / total
        
        return {
            'overall_trend': overall,
            'consensus': consensus,
            'allow_long': allow_long,
            'details': signals
        }


if __name__ == "__main__":
    # 测试
    print("="*60)
    print("大盘择时模块测试")
    print("="*60)
    
    # 单指数择时
    timing = MarketTimingModule(index_code='000001.SH')
    signal = timing.analyze_market()
    
    print(f"\n上证指数择时:")
    print(f"  趋势: {signal.trend}")
    print(f"  趋势强度: {signal.trend_strength:.2f}")
    print(f"  允许做多: {signal.allow_long}")
    print(f"  指标: {signal.indicators}")
    
    # 多指数择时
    print(f"\n多指数综合择时:")
    multi = MultiIndexTiming()
    composite = multi.get_composite_signal()
    print(f"  综合趋势: {composite['overall_trend']}")
    print(f"  一致性: {composite['consensus']:.2f}")
    print(f"  允许做多: {composite['allow_long']}")
