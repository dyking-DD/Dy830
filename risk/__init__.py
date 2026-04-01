"""
风控模块 (Risk Module)

提供量化交易系统的全面风控功能，包括：
- 仓位管理：单票、板块、总仓位限制
- 黑名单管理：ST股、退市股、停牌股自动过滤
- 熔断机制：日内回撤、总回撤限制
- 仓位计算：ATR、凯利公式、风险平价

使用示例:
    from risk import RiskManager, PositionSizer, BlacklistManager
    
    # 初始化风控管理器
    rm = RiskManager('config/risk_config.yaml')
    
    # 检查订单合规性
    result = rm.check_order('000001.SZ', 'buy', 1000, 10.0, 100000, positions)
    if result.passed:
        print("订单合规，可以执行")
    else:
        print(f"订单被拦截: {result.message}")
    
    # 仓位计算
    sizer = PositionSizer(risk_per_trade=0.02)
    shares = sizer.atr_based(100000, atr=0.5)
    print(f"建议买入: {shares} 股")
    
    # 黑名单管理
    bl = BlacklistManager()
    bl.update_all()
    print(f"黑名单数量: {len(bl.get_all_blacklist())}")
"""

from .risk_manager import RiskManager, PositionSizer, RiskCheckResult, RiskLevel, Position
from .blacklist_manager import BlacklistManager

__all__ = [
    'RiskManager',
    'PositionSizer', 
    'BlacklistManager',
    'RiskCheckResult',
    'RiskLevel',
    'Position',
]
