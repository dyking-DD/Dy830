"""
策略模块 - Strategies Module

包含：
- base: 基础策略类和数据结构
- examples: 示例策略实现 (MA、RSI、MACD、布林带、KDJ、动量突破、多因子共振)
- market_timing: 大盘择时模块
- parameter_optimizer: 动态参数优化 (网格搜索、遗传算法)
- portfolio: 策略组合引擎 (投票、轮动、组合管理)
- minervini_sepa: SEPA选股策略
"""

from .base import BaseStrategy, Signal, Position
from .examples import (
    RSIStrategy,
    MACrossVolumeStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
    KDJStrategy,
    MomentumBreakoutStrategy,
    CombinedStrategy,
    get_strategy,
    STRATEGIES
)
from .market_timing import MarketTimingModule, MultiIndexTiming, MarketTimingSignal
from .portfolio import (
    PortfolioConfig,
    AggregatedSignal,
    SignalVotingEngine,
    StrategyRotationEngine,
    PortfolioManager
)
from .parameter_optimizer import (
    ParameterSpace,
    OptimizationResult,
    ParameterOptimizer,
    GridSearchOptimizer,
    GeneticOptimizer
)

__all__ = [
    # 基础
    'BaseStrategy', 'Signal', 'Position',
    # 策略
    'RSIStrategy', 'MACrossVolumeStrategy', 'MACDStrategy',
    'BollingerBandsStrategy', 'KDJStrategy', 'MomentumBreakoutStrategy',
    'CombinedStrategy', 'get_strategy', 'STRATEGIES',
    # 择时
    'MarketTimingModule', 'MultiIndexTiming', 'MarketTimingSignal',
    # 组合
    'PortfolioConfig', 'AggregatedSignal', 'SignalVotingEngine',
    'StrategyRotationEngine', 'PortfolioManager',
    # 优化
    'ParameterSpace', 'OptimizationResult', 'ParameterOptimizer',
    'GridSearchOptimizer', 'GeneticOptimizer'
]
