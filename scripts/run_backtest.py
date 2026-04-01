#!/usr/bin/env python3
"""
回测示例脚本
运行单股票策略回测
"""
import sys
from pathlib import Path
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.akshare_fetcher import AkShareFetcher
from strategies.examples import MACrossVolumeStrategy, RSIStrategy, get_strategy
from backtest.engine import BacktestEngine


def main():
    """运行回测示例"""
    print("=" * 60)
    print("A股量化回测示例")
    print("=" * 60)
    
    # 获取数据
    print("\n📊 下载股票数据...")
    fetcher = AkShareFetcher()
    
    # 使用平安银行(000001)作为示例
    stock_code = "000001"
    df = fetcher.get_daily_data(stock_code, start_date="20230101")
    
    if df.empty:
        print("❌ 数据获取失败")
        return
    
    print(f"✅ 获取到 {len(df)} 条日线数据 (2023-01 至 2026-03)")
    
    # 选择策略
    print("\n📈 选择策略:")
    print("1. MA_Cross_Volume (双均线+成交量)")
    print("2. RSI (相对强弱)")
    
    # 默认使用双均线策略
    strategy = MACrossVolumeStrategy(
        fast_period=10,
        slow_period=20,
        stop_loss=0.05,
        take_profit=0.10
    )
    
    print(f"\n🎯 使用策略: {strategy.name}")
    print(f"   - 快均线: {strategy.fast_period}日")
    print(f"   - 慢均线: {strategy.slow_period}日")
    print(f"   - 止损: {strategy.stop_loss*100}%")
    print(f"   - 止盈: {strategy.take_profit*100}%")
    
    # 运行回测
    print("\n🚀 开始回测...")
    engine = BacktestEngine(
        initial_capital=100000,  # 10万初始资金
        commission_rate=0.0003,  # 万3佣金
        slippage=0.001,          # 千1滑点
        max_position_per_stock=0.2  # 单票最大20%
    )
    
    results = engine.run_backtest(strategy, df)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("📊 回测结果")
    print("=" * 60)
    print(f"初始资金:     ¥{results['initial_capital']:,.2f}")
    print(f"最终资产:     ¥{results['final_value']:,.2f}")
    print(f"总收益率:     {results['total_return']*100:+.2f}%")
    print(f"年化收益率:   {results['annual_return']*100:+.2f}%")
    print(f"年化波动率:   {results['annual_volatility']*100:.2f}%")
    print(f"夏普比率:     {results['sharpe_ratio']:.2f}")
    print(f"最大回撤:     {results['max_drawdown']*100:.2f}%")
    print(f"交易次数:     {results['total_trades']}次")
    print(f"总手续费:     ¥{results['total_commission']:.2f}")
    print(f"总印花税:     ¥{results['total_tax']:.2f}")
    print("=" * 60)
    
    # 保存结果
    output_file = f"backtest/results/{strategy.name}_{stock_code}.json"
    engine.save_results(results, output_file)
    
    print(f"\n💾 详细结果已保存: {output_file}")
    print("\n提示: 可以修改策略参数或换其他股票测试")


if __name__ == "__main__":
    main()
