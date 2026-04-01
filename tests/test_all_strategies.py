"""
全量策略测试 - 验证策略库完整性
测试所有7个策略 + 择时 + 优化 + 组合
"""
import sys
sys.path.insert(0, '/home/gem/workspace/agent/workspace/daily_stock_analysis')

import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 生成测试数据
def generate_test_data(n_days=200, n_stocks=3, seed=42):
    """生成多股票测试数据"""
    np.random.seed(seed)
    dates = pd.date_range('20240101', periods=n_days, freq='B')
    
    data = {}
    for i in range(n_stocks):
        trend = np.random.choice([-1, 1]) * 0.0005
        prices = 10 + np.random.randn(n_days).cumsum() * 0.5 + np.arange(n_days) * trend
        
        df = pd.DataFrame({
            'ts_code': f'{600000+i}.SH',
            'trade_date': dates.strftime('%Y%m%d'),
            'open': prices + np.random.randn(n_days) * 0.1,
            'high': prices + abs(np.random.randn(n_days)) * 0.2,
            'low': prices - abs(np.random.randn(n_days)) * 0.2,
            'close': prices,
            'vol': np.random.randint(100000, 1000000, n_days)
        })
        data[f'{600000+i}.SH'] = df
    
    return data


def test_all_strategies():
    """测试所有策略"""
    print("="*70)
    print("🧪 策略全量测试")
    print("="*70)
    
    from strategies import (
        RSIStrategy, MACDStrategy, BollingerBandsStrategy,
        KDJStrategy, MomentumBreakoutStrategy, CombinedStrategy,
        MACrossVolumeStrategy
    )
    
    # 生成数据
    data_dict = generate_test_data(n_days=200, n_stocks=1)
    data = list(data_dict.values())[0]
    
    strategies = [
        ('RSI', RSIStrategy(period=14, oversold=30, overbought=70)),
        ('MACD', MACDStrategy(fast=12, slow=26, signal=9)),
        ('布林带', BollingerBandsStrategy(period=20, std_dev=2.0)),
        ('KDJ', KDJStrategy(n=9, m1=3, m2=3)),
        ('动量突破', MomentumBreakoutStrategy(lookback=20, volume_mult=2.0)),
        ('多因子共振', CombinedStrategy(ma_fast=5, ma_slow=20)),
        ('均线+量', MACrossVolumeStrategy(fast_period=10, slow_period=20)),
    ]
    
    results = []
    for name, strategy in strategies:
        signals = strategy.generate_signals(data)
        buy_signals = [s for s in signals if s.action == 'buy']
        sell_signals = [s for s in signals if s.action == 'sell']
        
        results.append({
            'name': name,
            'total': len(signals),
            'buy': len(buy_signals),
            'sell': len(sell_signals),
            'avg_confidence': np.mean([s.confidence for s in signals]) if signals else 0
        })
        
        print(f"\n✅ {name:12s} | 信号: {len(signals):2d} (买{len(buy_signals):2d}/卖{len(sell_signals):2d}) | 平均置信度: {results[-1]['avg_confidence']:.2f}")
        
        if signals:
            s = signals[0]
            print(f"   示例: [{s.action.upper()}] {s.reason[:50]}...")
    
    return results


def test_market_timing():
    """测试大盘择时"""
    print("\n" + "="*70)
    print("📊 大盘择时测试")
    print("="*70)
    
    from strategies import MarketTimingModule, MultiIndexTiming
    
    # 单指数择时
    timing = MarketTimingModule(index_code='000001.SH')
    signal = timing.analyze_market()
    
    print(f"\n✅ 上证指数择时:")
    print(f"   趋势: {signal.trend}")
    print(f"   趋势强度: {signal.trend_strength:.2f}")
    print(f"   允许做多: {signal.allow_long}")
    
    # 多指数择时
    multi = MultiIndexTiming()
    composite = multi.get_composite_signal()
    
    print(f"\n✅ 多指数综合择时:")
    print(f"   综合趋势: {composite['overall_trend']}")
    print(f"   一致性: {composite['consensus']:.2f}")
    print(f"   允许做多: {composite['allow_long']}")
    
    return signal, composite


def test_parameter_optimizer():
    """测试参数优化"""
    print("\n" + "="*70)
    print("🔧 参数优化测试")
    print("="*70)
    
    from strategies import ParameterOptimizer, ParameterSpace, MACDStrategy
    
    # 生成数据
    data_dict = generate_test_data(n_days=100, n_stocks=1)
    data = list(data_dict.values())[0]
    
    # 定义参数空间
    param_spaces = {
        'fast': ParameterSpace('fast', 'int', 8, 15),
        'slow': ParameterSpace('slow', 'int', 20, 30),
        'signal': ParameterSpace('signal', 'int', 7, 12)
    }
    
    # 简单的评分函数
    def simple_score(strategy, data):
        signals = strategy.generate_signals(data)
        if len(signals) < 2:
            return -np.inf
        return len(signals) * 0.1  # 简单评分：信号越多分越高
    
    optimizer = ParameterOptimizer(MACDStrategy, simple_score)
    
    print("\n⏳ 执行遗传算法优化 (小规模测试)...")
    result = optimizer.optimize(
        data, param_spaces, method='genetic',
        population_size=10, generations=5, verbose=False
    )
    
    print(f"\n✅ 优化完成:")
    print(f"   最佳参数: {result.best_params}")
    print(f"   最佳得分: {result.best_score:.4f}")
    print(f"   耗时: {result.optimization_time:.2f}秒")
    
    return result


def test_portfolio_engine():
    """测试策略组合引擎"""
    print("\n" + "="*70)
    print("🎯 策略组合引擎测试")
    print("="*70)
    
    from strategies import (
        PortfolioConfig, PortfolioManager,
        MACDStrategy, RSIStrategy, BollingerBandsStrategy
    )
    
    # 创建策略
    strategies = {
        'macd': MACDStrategy(fast=12, slow=26, signal=9),
        'rsi': RSIStrategy(period=14, oversold=30, overbought=70),
        'bollinger': BollingerBandsStrategy(period=20, std_dev=2.0)
    }
    
    # 配置组合
    config = PortfolioConfig(
        name="多因子组合",
        strategy_weights={'macd': 0.4, 'rsi': 0.3, 'bollinger': 0.3},
        signal_threshold=0.5,
        max_positions=5
    )
    
    # 创建管理器
    manager = PortfolioManager(config)
    for name, strategy in strategies.items():
        manager.add_strategy(name, strategy)
    manager.initialize()
    
    # 生成多股票数据
    data_dict = generate_test_data(n_days=150, n_stocks=3)
    
    # 生成组合信号
    signals = manager.generate_portfolio_signals(data_dict)
    
    print(f"\n✅ 组合信号生成:")
    print(f"   共生成 {len(signals)} 个信号")
    
    for s in signals[:3]:
        print(f"   [{s.action.upper()}] {s.ts_code} 置信度: {s.confidence:.2f}")
        print(f"   投票: {s.votes}")
    
    # 测试轮动
    print(f"\n⏳ 执行策略轮动...")
    for i in range(10):
        for name in strategies:
            manager.rotation_engine.update_performance(name, np.random.randn() * 0.01)
    
    new_weights = manager.rotation_engine.rotate(method='momentum')
    print(f"✅ 轮动后权重: {new_weights}")
    
    # 组合报告
    report = manager.get_portfolio_report()
    print(f"\n✅ 组合报告:")
    print(f"   名称: {report['config']['name']}")
    print(f"   策略数: {len(report['strategies'])}")
    
    return manager


def main():
    """主测试函数"""
    print("\n" + "🦞"*35)
    print("\n启动全量测试...\n")
    
    try:
        # 1. 测试所有策略
        strategy_results = test_all_strategies()
        
        # 2. 测试择时
        timing_signal, composite = test_market_timing()
        
        # 3. 测试参数优化
        opt_result = test_parameter_optimizer()
        
        # 4. 测试组合引擎
        portfolio = test_portfolio_engine()
        
        # 总结
        print("\n" + "="*70)
        print("📋 测试总结")
        print("="*70)
        
        total_signals = sum(r['total'] for r in strategy_results)
        print(f"\n✅ 所有测试通过!")
        print(f"   策略数量: {len(strategy_results)}")
        print(f"   总信号数: {total_signals}")
        print(f"   择时状态: {timing_signal.trend}")
        print(f"   优化得分: {opt_result.best_score:.4f}")
        print(f"   组合策略: {len(portfolio.strategies)}")
        
        print("\n" + "🦞"*35)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
