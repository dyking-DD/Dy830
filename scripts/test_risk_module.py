#!/usr/bin/env python3
"""
风控模块测试与演示脚本

运行: python3 scripts/test_risk_module.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk import RiskManager, PositionSizer, BlacklistManager, RiskLevel

def test_risk_manager():
    """测试风控管理器"""
    print("\n" + "="*60)
    print("测试 1: 风控管理器 (RiskManager)")
    print("="*60)
    
    # 初始化
    rm = RiskManager("config/risk_config.yaml")
    print(f"✓ 风控管理器初始化完成")
    print(f"  - 单票仓位限制: {rm.config['max_position_per_stock']:.0%}")
    print(f"  - 板块仓位限制: {rm.config['max_position_per_sector']:.0%}")
    print(f"  - 日内回撤熔断: {rm.config['daily_drawdown_limit']:.1%}")
    print(f"  - 总回撤熔断: {rm.config['total_drawdown_limit']:.1%}")
    
    # 模拟持仓
    from risk.risk_manager import Position
    positions = {
        '000001.SZ': Position('000001.SZ', 1000, 10.0, 10.5, 10500),
    }
    current_equity = 100000
    
    # 测试买入 - 正常情况
    print("\n--- 买入检查测试 ---")
    result = rm.check_order('000002.SZ', 'buy', 1000, 10.0, current_equity, positions)
    print(f"买入 000002.SZ 1000股 @ 10.0: {'✓ 通过' if result.passed else '✗ 拦截'}")
    if not result.passed:
        print(f"  原因: {result.message}")
    
    # 测试买入 - 超限
    result = rm.check_order('000003.SZ', 'buy', 20000, 10.0, current_equity, positions)
    print(f"买入 000003.SZ 20000股 @ 10.0: {'✓ 通过' if result.passed else '✗ 拦截'}")
    if not result.passed:
        print(f"  原因: {result.message}")
    
    # 测试黑名单
    rm.add_to_blacklist('300001.SZ', '测试')
    result = rm.check_order('300001.SZ', 'buy', 100, 10.0, current_equity, positions)
    print(f"买入黑名单股票 300001.SZ: {'✓ 通过' if result.passed else '✗ 拦截'}")
    if not result.passed:
        print(f"  原因: {result.message}")
    
    # 测试卖出
    print("\n--- 卖出检查测试 ---")
    result = rm.check_order('000001.SZ', 'sell', 500, 10.5, current_equity, positions)
    print(f"卖出 000001.SZ 500股: {'✓ 通过' if result.passed else '✗ 拦截'}")
    
    result = rm.check_order('000001.SZ', 'sell', 2000, 10.5, current_equity, positions)
    print(f"卖出 000001.SZ 2000股 (超限): {'✓ 通过' if result.passed else '✗ 拦截'}")
    if not result.passed:
        print(f"  原因: {result.message}")
    
    # 测试熔断机制
    print("\n--- 熔断机制测试 ---")
    rm.update_equity(100000)  # 初始权益
    rm.daily_stats['max_equity'] = 100000
    rm.update_equity(94000)   # 触发日内回撤 6%
    print(f"权益 100000 -> 94000 (回撤6%): {'✓ 熔断' if rm.circuit_breaker_triggered else '✗ 未熔断'}")
    
    if rm.circuit_breaker_triggered:
        result = rm.check_order('000004.SZ', 'buy', 100, 10.0, 94000, positions)
        print(f"熔断期间买入: {'✓ 通过' if result.passed else '✗ 拦截'}")
        if not result.passed:
            print(f"  原因: {result.message}")

def test_position_sizer():
    """测试仓位计算器"""
    print("\n" + "="*60)
    print("测试 2: 仓位计算器 (PositionSizer)")
    print("="*60)
    
    sizer = PositionSizer(risk_per_trade=0.02)
    equity = 100000
    
    # 固定比例
    print("\n--- 固定比例法 ---")
    position = sizer.fixed_ratio(equity, 0.10)
    print(f"10% 固定比例: {position:,.2f} 元")
    
    position = sizer.fixed_ratio(equity, 0.20)
    print(f"20% 固定比例: {position:,.2f} 元")
    
    # ATR仓位
    print("\n--- ATR仓位法 ---")
    shares = sizer.atr_based(equity, atr=0.5, stop_loss_atr_multiple=2.0)
    print(f"ATR=0.5, 2倍止损: {shares} 股")
    print(f"  (风险金额: {equity * 0.02:,.2f} 元, 止损距离: 1.0 元)")
    
    shares = sizer.atr_based(equity, atr=1.0, stop_loss_atr_multiple=2.0)
    print(f"ATR=1.0, 2倍止损: {shares} 股")
    
    # 凯利公式
    print("\n--- 凯利公式 ---")
    kelly = sizer.kelly_formula(equity, win_rate=0.55, avg_win=100, avg_loss=50)
    print(f"胜率55%, 盈亏比2:1: {kelly:,.2f} 元")
    print(f"  (凯利分数: {kelly/equity:.2%})")
    
    kelly = sizer.kelly_formula(equity, win_rate=0.60, avg_win=150, avg_loss=50)
    print(f"胜率60%, 盈亏比3:1: {kelly:,.2f} 元")
    
    # 风险平价
    print("\n--- 风险平价 ---")
    equities = {'stock_a': 100000, 'stock_b': 100000, 'stock_c': 100000}
    volatilities = {'stock_a': 0.15, 'stock_b': 0.25, 'stock_c': 0.20}
    weights = sizer.risk_parity(equities, volatilities)
    print("波动率: A=15%, B=25%, C=20%")
    for name, weight in weights.items():
        print(f"  {name}: {weight:.2%}")

def test_blacklist_manager():
    """测试黑名单管理器"""
    print("\n" + "="*60)
    print("测试 3: 黑名单管理器 (BlacklistManager)")
    print("="*60)
    
    bl = BlacklistManager("config")
    
    # 更新ST股票（不检查停牌，节省测试时间）
    print("\n--- 更新ST股票 ---")
    try:
        st_stocks = bl.update_st_stocks()
        print(f"✓ 已更新ST股票: {len(st_stocks)} 只")
        if st_stocks:
            print(f"  示例: {', '.join(list(st_stocks)[:3])}")
    except Exception as e:
        print(f"⚠ 更新ST股票失败: {e}")
    
    # 手动添加
    print("\n--- 手动黑名单 ---")
    bl.add_manual('000001.SZ', '测试用途')
    bl.add_manual('000002.SZ', '测试用途')
    print(f"✓ 手动添加 2 只股票到黑名单")
    
    # 获取完整黑名单
    all_blacklist = bl.get_all_blacklist()
    print(f"\n--- 黑名单统计 ---")
    categories = bl.get_blacklist_by_category()
    for category, symbols in categories.items():
        print(f"  {category}: {len(symbols)} 只")
    print(f"  总计: {len(all_blacklist)} 只")
    
    # 检查是否在黑名单
    print("\n--- 黑名单检查 ---")
    test_symbols = ['000001.SZ', '600519.SH', '300750.SZ']
    for symbol in test_symbols:
        is_bl = bl.is_blacklisted(symbol)
        reason = bl.get_blacklist_reason(symbol) if is_bl else ""
        status = "✗ 在黑名单" if is_bl else "✓ 正常"
        print(f"  {symbol}: {status} {f'({reason})' if reason else ''}")
    
    # 保存
    bl._save_cache()
    print("\n✓ 黑名单已保存到 config/blacklist_cache.json")

def test_integration():
    """测试集成场景"""
    print("\n" + "="*60)
    print("测试 4: 集成场景测试")
    print("="*60)
    
    # 初始化所有组件
    rm = RiskManager("config/risk_config.yaml")
    sizer = PositionSizer(risk_per_trade=0.02)
    
    print("\n场景: 用户想要买入一只股票")
    print("-" * 40)
    
    # 模拟参数
    equity = 100000
    symbol = '000001.SZ'
    current_price = 10.0
    atr = 0.5
    
    # 1. 检查是否在黑名单
    if rm.is_blacklisted(symbol):
        print(f"✗ {symbol} 在黑名单中，拒绝交易")
        return
    print(f"✓ {symbol} 不在黑名单")
    
    # 2. 计算建议仓位
    suggested_shares = sizer.atr_based(equity, atr, 2.0)
    suggested_value = suggested_shares * current_price
    print(f"✓ ATR建议仓位: {suggested_shares} 股 (约 {suggested_value:,.2f} 元)")
    
    # 3. 检查风控限制
    from risk.risk_manager import Position
    positions = {}
    
    result = rm.check_order(symbol, 'buy', suggested_shares, current_price, equity, positions)
    if result.passed:
        print(f"✓ 风控检查通过")
        print(f"\n✅ 可以执行买入: {symbol} {suggested_shares}股 @ {current_price}")
    else:
        print(f"✗ 风控拦截: {result.message}")
        
        # 尝试调整数量
        max_shares = int(equity * rm.config['max_position_per_stock'] / current_price)
        print(f"\n尝试调整至最大允许仓位: {max_shares} 股")
        result = rm.check_order(symbol, 'buy', max_shares, current_price, equity, positions)
        if result.passed:
            print(f"✅ 调整后可以执行: {symbol} {max_shares}股 @ {current_price}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("风控模块全面测试")
    print("="*60)
    
    try:
        test_risk_manager()
    except Exception as e:
        print(f"风控管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_position_sizer()
    except Exception as e:
        print(f"仓位计算器测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_blacklist_manager()
    except Exception as e:
        print(f"黑名单管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_integration()
    except Exception as e:
        print(f"集成测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60)
