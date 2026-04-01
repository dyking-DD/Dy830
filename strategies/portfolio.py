"""
策略组合引擎 - Strategy Portfolio Engine

支持：
- 多策略权重配置
- 信号投票机制
- 策略轮动
- 风险平价分配
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from collections import defaultdict

# 导入基础类
try:
    from .base import BaseStrategy, Signal, Position
except ImportError:
    from base import BaseStrategy, Signal, Position

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PortfolioConfig:
    """组合配置"""
    name: str
    strategy_weights: Dict[str, float]  # 策略权重
    signal_threshold: float = 0.5  # 信号投票阈值
    max_positions: int = 10  # 最大持仓数
    rebalance_freq: str = 'daily'  # 'daily', 'weekly', 'monthly'
    risk_budget: Optional[Dict[str, float]] = None  # 风险预算


@dataclass
class AggregatedSignal:
    """聚合信号"""
    ts_code: str
    date: str
    action: str
    confidence: float
    votes: Dict[str, float]  # 各策略投票
    final_score: float
    reasons: List[str]


class SignalVotingEngine:
    """
    信号投票引擎
    
    多策略信号聚合，投票决策
    """
    
    def __init__(self, strategies: Dict[str, BaseStrategy], 
                 weights: Optional[Dict[str, float]] = None,
                 threshold: float = 0.5):
        """
        Args:
            strategies: 策略字典 {name: strategy_instance}
            weights: 策略权重 {name: weight}, 为None则等权
            threshold: 投票阈值 (0-1)
        """
        self.strategies = strategies
        self.weights = weights or {name: 1.0/len(strategies) for name in strategies}
        self.threshold = threshold
        
        # 归一化权重
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
    
    def aggregate_signals(self, data: pd.DataFrame) -> List[AggregatedSignal]:
        """
        聚合所有策略的信号
        
        Returns:
            List[AggregatedSignal]
        """
        # 收集各策略信号
        strategy_signals = {}
        for name, strategy in self.strategies.items():
            signals = strategy.generate_signals(data)
            strategy_signals[name] = {s.ts_code: s for s in signals}
        
        # 汇总所有涉及的股票
        all_stocks = set()
        for signals in strategy_signals.values():
            all_stocks.update(signals.keys())
        
        # 聚合投票
        aggregated = []
        latest = data.iloc[-1] if not data.empty else None
        
        for ts_code in all_stocks:
            votes = {}
            buy_score = 0.0
            sell_score = 0.0
            reasons = []
            
            for strategy_name, weight in self.weights.items():
                if strategy_name not in strategy_signals:
                    continue
                    
                signal = strategy_signals[strategy_name].get(ts_code)
                if signal:
                    votes[strategy_name] = signal.confidence
                    
                    if signal.action == 'buy':
                        buy_score += weight * signal.confidence
                        reasons.append(f"{strategy_name}: {signal.reason}")
                    elif signal.action == 'sell':
                        sell_score += weight * signal.confidence
                        reasons.append(f"{strategy_name}: {signal.reason}")
            
            # 决策
            if buy_score >= self.threshold and buy_score > sell_score:
                agg_signal = AggregatedSignal(
                    ts_code=ts_code,
                    date=str(latest['trade_date']) if latest else datetime.now().strftime('%Y%m%d'),
                    action='buy',
                    confidence=buy_score,
                    votes=votes,
                    final_score=buy_score,
                    reasons=reasons
                )
                aggregated.append(agg_signal)
            elif sell_score >= self.threshold and sell_score > buy_score:
                agg_signal = AggregatedSignal(
                    ts_code=ts_code,
                    date=str(latest['trade_date']) if latest else datetime.now().strftime('%Y%m%d'),
                    action='sell',
                    confidence=sell_score,
                    votes=votes,
                    final_score=-sell_score,
                    reasons=reasons
                )
                aggregated.append(agg_signal)
        
        # 按置信度排序
        aggregated.sort(key=lambda x: abs(x.final_score), reverse=True)
        
        return aggregated
    
    def get_top_signals(self, data: pd.DataFrame, top_n: int = 5) -> List[AggregatedSignal]:
        """获取Top N信号"""
        all_signals = self.aggregate_signals(data)
        return all_signals[:top_n]


class StrategyRotationEngine:
    """
    策略轮动引擎
    
    根据市场状态动态调整策略权重
    """
    
    def __init__(self, strategies: Dict[str, BaseStrategy],
                 lookback_period: int = 60):
        self.strategies = strategies
        self.lookback_period = lookback_period
        self.performance_history = defaultdict(list)
        self.current_weights = {name: 1.0/len(strategies) for name in strategies}
    
    def update_performance(self, strategy_name: str, returns: float):
        """更新策略表现"""
        self.performance_history[strategy_name].append(returns)
        
        # 保留最近数据
        if len(self.performance_history[strategy_name]) > self.lookback_period:
            self.performance_history[strategy_name].pop(0)
    
    def calculate_strategy_scores(self) -> Dict[str, float]:
        """
        计算各策略得分 (夏普比率 + 动量)
        """
        scores = {}
        
        for name, returns in self.performance_history.items():
            if len(returns) < 20:
                scores[name] = 0.0
                continue
            
            returns = np.array(returns)
            
            # 夏普比率
            sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
            
            # 近期动量 (最近10天 vs 前10天)
            if len(returns) >= 20:
                recent = np.mean(returns[-10:])
                previous = np.mean(returns[-20:-10])
                momentum = recent - previous
            else:
                momentum = 0
            
            scores[name] = sharpe + momentum * 10
        
        return scores
    
    def rotate(self, method: str = 'momentum') -> Dict[str, float]:
        """
        执行轮动
        
        Args:
            method: 'momentum'(动量), 'risk_parity'(风险平价), 'equal'(等权)
            
        Returns:
            新权重
        """
        if method == 'equal':
            n = len(self.strategies)
            new_weights = {name: 1.0/n for name in self.strategies}
        
        elif method == 'momentum':
            scores = self.calculate_strategy_scores()
            
            # Softmax归一化
            exp_scores = {k: np.exp(max(s, 0)) for k, s in scores.items()}
            total = sum(exp_scores.values())
            new_weights = {k: v/total for k, v in exp_scores.items()} if total > 0 else self.current_weights
        
        elif method == 'risk_parity':
            # 风险平价：权重与波动率成反比
            volatilities = {}
            for name, returns in self.performance_history.items():
                if len(returns) >= 20:
                    volatilities[name] = np.std(returns[-20:])
                else:
                    volatilities[name] = 0.01  # 默认波动率
            
            inv_vol = {k: 1.0/(v + 1e-8) for k, v in volatilities.items()}
            total = sum(inv_vol.values())
            new_weights = {k: v/total for k, v in inv_vol.items()}
        
        else:
            raise ValueError(f"未知轮动方法: {method}")
        
        # 平滑过渡
        alpha = 0.3  # 轮动速度
        smoothed = {}
        for name in self.strategies:
            smoothed[name] = alpha * new_weights.get(name, 0) + (1-alpha) * self.current_weights.get(name, 0)
        
        # 再归一化
        total = sum(smoothed.values())
        self.current_weights = {k: v/total for k, v in smoothed.items()}
        
        logger.info(f"策略轮动完成: {self.current_weights}")
        return self.current_weights


class PortfolioManager:
    """
    组合管理器 - 整合所有功能
    """
    
    def __init__(self, config: PortfolioConfig):
        self.config = config
        self.strategies: Dict[str, BaseStrategy] = {}
        self.voting_engine: Optional[SignalVotingEngine] = None
        self.rotation_engine: Optional[StrategyRotationEngine] = None
        self.positions: Dict[str, Dict] = {}  # 当前持仓
        self.trade_history: List[Dict] = []
    
    def add_strategy(self, name: str, strategy: BaseStrategy, weight: Optional[float] = None):
        """添加策略"""
        self.strategies[name] = strategy
        
        if weight is not None:
            self.config.strategy_weights[name] = weight
    
    def initialize(self):
        """初始化引擎"""
        # 投票引擎
        weights = self.config.strategy_weights or {name: 1.0/len(self.strategies) 
                                                     for name in self.strategies}
        self.voting_engine = SignalVotingEngine(
            self.strategies, weights, self.config.signal_threshold
        )
        
        # 轮动引擎
        self.rotation_engine = StrategyRotationEngine(self.strategies)
        
        logger.info(f"组合管理器初始化完成: {self.config.name}")
    
    def generate_portfolio_signals(self, data: Dict[str, pd.DataFrame]) -> List[AggregatedSignal]:
        """
        生成组合信号
        
        Args:
            data: {ts_code: dataframe} 多只股票数据
            
        Returns:
            聚合信号列表
        """
        all_signals = []
        
        for ts_code, df in data.items():
            signals = self.voting_engine.aggregate_signals(df)
            all_signals.extend(signals)
        
        # 按得分排序
        all_signals.sort(key=lambda x: abs(x.final_score), reverse=True)
        
        # 限制持仓数
        if len(all_signals) > self.config.max_positions:
            all_signals = all_signals[:self.config.max_positions]
        
        return all_signals
    
    def rebalance(self, market_data: Dict[str, pd.DataFrame], 
                  current_date: str = None) -> List[AggregatedSignal]:
        """
        再平衡
        
        1. 更新策略表现
        2. 执行策略轮动
        3. 生成新的交易信号
        """
        if current_date is None:
            current_date = datetime.now().strftime('%Y%m%d')
        
        # 更新各策略表现
        for name, strategy in self.strategies.items():
            # 简化的收益计算
            signals = []
            for ts_code, df in market_data.items():
                s = strategy.generate_signals(df)
                signals.extend(s)
            
            # 计算策略收益
            if len(signals) >= 2:
                returns = np.mean([s.confidence for s in signals]) / 10
                self.rotation_engine.update_performance(name, returns)
        
        # 执行轮动
        new_weights = self.rotation_engine.rotate(method='momentum')
        self.voting_engine.weights = new_weights
        
        # 生成新信号
        signals = self.generate_portfolio_signals(market_data)
        
        logger.info(f"再平衡完成: 生成 {len(signals)} 个信号")
        return signals
    
    def get_portfolio_report(self) -> Dict:
        """获取组合报告"""
        return {
            'config': {
                'name': self.config.name,
                'max_positions': self.config.max_positions,
                'threshold': self.config.signal_threshold
            },
            'strategies': {
                name: {
                    'weight': self.voting_engine.weights.get(name, 0) if self.voting_engine else 0,
                    'type': type(strategy).__name__
                }
                for name, strategy in self.strategies.items()
            },
            'current_positions': self.positions,
            'trade_count': len(self.trade_history)
        }


if __name__ == "__main__":
    print("="*60)
    print("策略组合引擎测试")
    print("="*60)
    
    # 导入策略
    import sys
    sys.path.insert(0, '/home/gem/workspace/agent/workspace/daily_stock_analysis')
    from strategies.examples import MACDStrategy, RSIStrategy, BollingerBandsStrategy
    from strategies.base import BaseStrategy, Signal, Position
    
    # 创建策略
    strategies = {
        'macd': MACDStrategy(fast=12, slow=26, signal=9),
        'rsi': RSIStrategy(period=14, oversold=30, overbought=70),
        'bollinger': BollingerBandsStrategy(period=20, std_dev=2.0)
    }
    
    # 配置
    config = PortfolioConfig(
        name="多因子组合",
        strategy_weights={'macd': 0.4, 'rsi': 0.3, 'bollinger': 0.3},
        signal_threshold=0.5,
        max_positions=5
    )
    
    # 创建组合管理器
    manager = PortfolioManager(config)
    for name, strategy in strategies.items():
        manager.add_strategy(name, strategy)
    manager.initialize()
    
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
    
    # 测试投票引擎
    print("\n信号投票测试:")
    signals = manager.voting_engine.aggregate_signals(data)
    print(f"生成 {len(signals)} 个聚合信号")
    
    for s in signals[:3]:
        print(f"  [{s.action.upper()}] {s.ts_code} 置信度: {s.confidence:.2f}")
        print(f"    投票: {s.votes}")
    
    # 测试轮动引擎
    print("\n策略轮动测试:")
    for i in range(10):
        manager.rotation_engine.update_performance('macd', np.random.randn() * 0.01)
        manager.rotation_engine.update_performance('rsi', np.random.randn() * 0.01)
        manager.rotation_engine.update_performance('bollinger', np.random.randn() * 0.01)
    
    new_weights = manager.rotation_engine.rotate(method='momentum')
    print(f"轮动后权重: {new_weights}")
    
    # 组合报告
    print("\n组合报告:")
    report = manager.get_portfolio_report()
    print(f"组合名称: {report['config']['name']}")
    print(f"策略配置: {report['strategies']}")
