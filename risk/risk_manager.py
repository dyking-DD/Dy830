"""
风控管理器 - 量化交易系统核心风控模块

功能：
- 仓位控制（单票、板块、总仓位限制）
- 黑名单管理（ST股、退市股、停牌股）
- 熔断机制（日内最大回撤、总回撤限制）
- 交易频率控制
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import yaml
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    message: str
    risk_level: RiskLevel
    action: str = "allow"  # allow, block, warning


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int
    cost_price: float
    current_price: float
    market_value: float


class RiskManager:
    """
    风控管理器
    
    核心风控规则：
    1. 单票仓位限制（默认不超过总资金的10%）
    2. 板块集中度限制（默认单板块不超过30%）
    3. 总仓位限制（默认不超过80%）
    4. 日内回撤熔断（默认5%）
    5. 总回撤熔断（默认15%）
    6. 黑名单过滤
    """
    
    def __init__(self, config_path: str = "config/risk_config.yaml"):
        """
        初始化风控管理器
        
        Args:
            config_path: 风控配置文件路径
        """
        self.config = self._load_config(config_path)
        self.blacklist = set()
        self.daily_stats = {
            'date': None,
            'initial_equity': 0,
            'max_equity': 0,
            'min_equity': 0,
            'trade_count': 0,
            'last_trade_time': None
        }
        self.equity_history = []
        self.circuit_breaker_triggered = False
        self.circuit_breaker_end_time = None
        
        self._init_blacklist()
        logger.info("风控管理器初始化完成")
    
    def _load_config(self, config_path: str) -> Dict:
        """加载风控配置"""
        default_config = {
            # 仓位控制
            'max_position_per_stock': 0.10,  # 单票最大仓位 10%
            'max_position_per_sector': 0.30,  # 板块最大仓位 30%
            'max_total_position': 0.80,  # 总仓位上限 80%
            'min_cash_ratio': 0.10,  # 最小现金比例 10%
            
            # 熔断机制
            'daily_drawdown_limit': 0.05,  # 日内回撤限制 5%
            'total_drawdown_limit': 0.15,  # 总回撤限制 15%
            'circuit_breaker_duration_minutes': 30,  # 熔断冷却时间 30分钟
            
            # 交易频率
            'max_trades_per_day': 20,  # 日最大交易次数
            'min_trade_interval_seconds': 60,  # 最小交易间隔 60秒
            
            # 黑名单
            'auto_blacklist_st': True,  # 自动拉黑ST股
            'auto_blacklist_delisting': True,  # 自动拉黑退市股
            'blacklist_update_interval_days': 1,  # 黑名单更新间隔
            
            # 价格限制
            'max_order_price_deviation': 0.05,  # 下单价格偏离限制 5%
            'min_stock_price': 1.0,  # 最低股价 1元
            'max_stock_price': 1000.0,  # 最高股价 1000元
            
            # 流动性限制
            'min_daily_volume': 1000000,  # 最小日成交额 100万
            'min_market_cap': 1000000000,  # 最小市值 10亿
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    default_config.update(config)
                logger.info(f"已加载风控配置: {config_path}")
            except Exception as e:
                logger.warning(f"加载配置失败，使用默认配置: {e}")
        else:
            # 保存默认配置
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True)
            logger.info(f"已创建默认风控配置: {config_path}")
        
        return default_config
    
    def _init_blacklist(self):
        """初始化黑名单"""
        blacklist_path = "config/blacklist.txt"
        if os.path.exists(blacklist_path):
            with open(blacklist_path, 'r') as f:
                self.blacklist = set(line.strip() for line in f if line.strip())
            logger.info(f"已加载黑名单: {len(self.blacklist)} 只股票")
    
    def save_blacklist(self, path: str = "config/blacklist.txt"):
        """保存黑名单"""
        with open(path, 'w') as f:
            for symbol in sorted(self.blacklist):
                f.write(f"{symbol}\n")
        logger.info(f"黑名单已保存: {path}")
    
    def add_to_blacklist(self, symbol: str, reason: str = ""):
        """添加股票到黑名单"""
        self.blacklist.add(symbol)
        logger.info(f"添加黑名单: {symbol}, 原因: {reason}")
    
    def remove_from_blacklist(self, symbol: str):
        """从黑名单移除"""
        self.blacklist.discard(symbol)
        logger.info(f"移除黑名单: {symbol}")
    
    def check_order(self, 
                   symbol: str,
                   action: str,  # 'buy' or 'sell'
                   quantity: int,
                   price: float,
                   current_equity: float,
                   positions: Dict[str, Position],
                   sector_map: Optional[Dict[str, str]] = None) -> RiskCheckResult:
        """
        检查订单是否合规
        
        Args:
            symbol: 股票代码
            action: 买卖动作
            quantity: 数量
            price: 价格
            current_equity: 当前权益
            positions: 当前持仓
            sector_map: 股票板块映射
        
        Returns:
            RiskCheckResult: 检查结果
        """
        # 1. 检查熔断状态
        if self.circuit_breaker_triggered:
            if datetime.now() < self.circuit_breaker_end_time:
                return RiskCheckResult(
                    passed=False,
                    message=f"熔断中，剩余冷却时间: {(self.circuit_breaker_end_time - datetime.now()).seconds // 60} 分钟",
                    risk_level=RiskLevel.CRITICAL,
                    action="block"
                )
            else:
                self.circuit_breaker_triggered = False
                logger.info("熔断冷却结束，恢复正常交易")
        
        # 2. 检查黑名单
        if symbol in self.blacklist:
            return RiskCheckResult(
                passed=False,
                message=f"股票 {symbol} 在黑名单中",
                risk_level=RiskLevel.HIGH,
                action="block"
            )
        
        # 3. 检查交易频率
        if self.daily_stats['trade_count'] >= self.config['max_trades_per_day']:
            return RiskCheckResult(
                passed=False,
                message=f"今日交易次数已达上限 {self.config['max_trades_per_day']}",
                risk_level=RiskLevel.MEDIUM,
                action="block"
            )
        
        if self.daily_stats['last_trade_time']:
            elapsed = (datetime.now() - self.daily_stats['last_trade_time']).total_seconds()
            if elapsed < self.config['min_trade_interval_seconds']:
                return RiskCheckResult(
                    passed=False,
                    message=f"交易间隔过短，需等待 {self.config['min_trade_interval_seconds'] - int(elapsed)} 秒",
                    risk_level=RiskLevel.LOW,
                    action="block"
                )
        
        # 4. 买入特有检查
        if action == 'buy':
            return self._check_buy_order(symbol, quantity, price, current_equity, positions, sector_map)
        
        # 5. 卖出特有检查
        elif action == 'sell':
            return self._check_sell_order(symbol, quantity, price, positions)
        
        return RiskCheckResult(passed=True, message="检查通过", risk_level=RiskLevel.LOW)
    
    def _check_buy_order(self, symbol, quantity, price, current_equity, positions, sector_map):
        """检查买入订单"""
        order_value = quantity * price
        
        # 检查股价范围
        if price < self.config['min_stock_price']:
            return RiskCheckResult(
                passed=False,
                message=f"股价 {price} 低于最低限制 {self.config['min_stock_price']}",
                risk_level=RiskLevel.HIGH,
                action="block"
            )
        
        if price > self.config['max_stock_price']:
            return RiskCheckResult(
                passed=False,
                message=f"股价 {price} 高于最高限制 {self.config['max_stock_price']}",
                risk_level=RiskLevel.HIGH,
                action="block"
            )
        
        # 计算新持仓市值
        new_position_value = 0
        if symbol in positions:
            new_position_value = (positions[symbol].quantity + quantity) * price
        else:
            new_position_value = order_value
        
        # 检查单票仓位限制
        single_stock_ratio = new_position_value / current_equity
        if single_stock_ratio > self.config['max_position_per_stock']:
            max_allowed = int(current_equity * self.config['max_position_per_stock'] / price)
            return RiskCheckResult(
                passed=False,
                message=f"单票仓位将超过限制 ({single_stock_ratio:.2%} > {self.config['max_position_per_stock']:.2%}), 建议最多买入 {max_allowed} 股",
                risk_level=RiskLevel.HIGH,
                action="block"
            )
        
        # 检查板块集中度
        if sector_map and symbol in sector_map:
            sector = sector_map[symbol]
            sector_value = sum(
                pos.market_value for sym, pos in positions.items()
                if sym in sector_map and sector_map[sym] == sector
            )
            new_sector_ratio = (sector_value + order_value) / current_equity
            if new_sector_ratio > self.config['max_position_per_sector']:
                return RiskCheckResult(
                    passed=False,
                    message=f"板块 {sector} 仓位将超过限制 ({new_sector_ratio:.2%} > {self.config['max_position_per_sector']:.2%})",
                    risk_level=RiskLevel.MEDIUM,
                    action="block"
                )
        
        # 检查总仓位
        total_position_value = sum(pos.market_value for pos in positions.values()) + order_value
        total_ratio = total_position_value / current_equity
        if total_ratio > self.config['max_total_position']:
            return RiskCheckResult(
                passed=False,
                message=f"总仓位将超过限制 ({total_ratio:.2%} > {self.config['max_total_position']:.2%})",
                risk_level=RiskLevel.HIGH,
                action="block"
            )
        
        return RiskCheckResult(passed=True, message="买入检查通过", risk_level=RiskLevel.LOW)
    
    def _check_sell_order(self, symbol, quantity, price, positions):
        """检查卖出订单"""
        if symbol not in positions:
            return RiskCheckResult(
                passed=False,
                message=f"未持有股票 {symbol}",
                risk_level=RiskLevel.MEDIUM,
                action="block"
            )
        
        if positions[symbol].quantity < quantity:
            return RiskCheckResult(
                passed=False,
                message=f"持仓不足，当前持有 {positions[symbol].quantity} 股，试图卖出 {quantity} 股",
                risk_level=RiskLevel.MEDIUM,
                action="block"
            )
        
        return RiskCheckResult(passed=True, message="卖出检查通过", risk_level=RiskLevel.LOW)
    
    def update_equity(self, equity: float):
        """
        更新权益数据，检查回撤熔断
        
        Args:
            equity: 当前权益
        """
        today = datetime.now().date()
        
        # 新的一天，重置统计
        if self.daily_stats['date'] != today:
            self.daily_stats = {
                'date': today,
                'initial_equity': equity,
                'max_equity': equity,
                'min_equity': equity,
                'trade_count': 0,
                'last_trade_time': None
            }
            self.circuit_breaker_triggered = False
        
        # 更新当日最大/最小权益
        self.daily_stats['max_equity'] = max(self.daily_stats['max_equity'], equity)
        self.daily_stats['min_equity'] = min(self.daily_stats['min_equity'], equity)
        
        self.equity_history.append({
            'time': datetime.now(),
            'equity': equity
        })
        
        # 检查日内回撤熔断
        if self.daily_stats['max_equity'] > 0:
            daily_drawdown = (self.daily_stats['max_equity'] - equity) / self.daily_stats['max_equity']
            if daily_drawdown >= self.config['daily_drawdown_limit']:
                self._trigger_circuit_breaker(
                    f"日内回撤 {daily_drawdown:.2%} 超过限制 {self.config['daily_drawdown_limit']:.2%}"
                )
                return
        
        # 检查总回撤熔断
        if self.daily_stats['initial_equity'] > 0:
            total_drawdown = (self.daily_stats['initial_equity'] - equity) / self.daily_stats['initial_equity']
            if total_drawdown >= self.config['total_drawdown_limit']:
                self._trigger_circuit_breaker(
                    f"总回撤 {total_drawdown:.2%} 超过限制 {self.config['total_drawdown_limit']:.2%}"
                )
    
    def _trigger_circuit_breaker(self, reason: str):
        """触发熔断"""
        self.circuit_breaker_triggered = True
        self.circuit_breaker_end_time = datetime.now() + timedelta(
            minutes=self.config['circuit_breaker_duration_minutes']
        )
        logger.critical(f"⚠️ 熔断触发: {reason}, 冷却时间: {self.config['circuit_breaker_duration_minutes']} 分钟")
    
    def record_trade(self):
        """记录交易"""
        self.daily_stats['trade_count'] += 1
        self.daily_stats['last_trade_time'] = datetime.now()
    
    def is_blacklisted(self, symbol: str) -> bool:
        """检查股票是否在黑名单中"""
        return symbol in self.blacklist
    
    def get_risk_report(self) -> Dict:
        """获取风险报告"""
        return {
            'daily_stats': self.daily_stats,
            'circuit_breaker_active': self.circuit_breaker_triggered,
            'circuit_breaker_end_time': self.circuit_breaker_end_time,
            'blacklist_count': len(self.blacklist),
            'config': self.config
        }


class PositionSizer:
    """
    仓位计算器
    
    支持多种仓位计算方法：
    1. 固定比例法
    2. 波动率调整法（ATR）
    3. 凯利公式
    4. 风险平价
    """
    
    def __init__(self, risk_per_trade: float = 0.02):
        """
        Args:
            risk_per_trade: 单笔交易风险比例（默认2%）
        """
        self.risk_per_trade = risk_per_trade
    
    def fixed_ratio(self, equity: float, ratio: float = 0.10) -> float:
        """
        固定比例仓位
        
        Args:
            equity: 总资金
            ratio: 仓位比例
        
        Returns:
            目标仓位金额
        """
        return equity * ratio
    
    def atr_based(self, equity: float, atr: float, stop_loss_atr_multiple: float = 2.0) -> int:
        """
        基于ATR的仓位计算
        
        Args:
            equity: 总资金
            atr: 平均真实波幅
            stop_loss_atr_multiple: 止损ATR倍数
        
        Returns:
            建议持仓股数
        """
        risk_amount = equity * self.risk_per_trade
        stop_loss_distance = atr * stop_loss_atr_multiple
        
        if stop_loss_distance == 0:
            return 0
        
        position_size = int(risk_amount / stop_loss_distance)
        return max(0, position_size)
    
    def kelly_formula(self, equity: float, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        凯利公式计算最优仓位
        
        f* = (p*b - q) / b
        其中 p = 胜率, q = 败率, b = 盈亏比
        
        Args:
            equity: 总资金
            win_rate: 胜率 (0-1)
            avg_win: 平均盈利
            avg_loss: 平均亏损
        
        Returns:
            建议仓位金额
        """
        if avg_loss == 0 or win_rate >= 1:
            return 0
        
        b = avg_win / avg_loss  # 盈亏比
        q = 1 - win_rate
        
        kelly_fraction = (win_rate * b - q) / b
        
        # 使用半凯利（更保守）
        kelly_fraction = kelly_fraction * 0.5
        
        return max(0, equity * kelly_fraction)
    
    def risk_parity(self, equities: Dict[str, float], volatilities: Dict[str, float]) -> Dict[str, float]:
        """
        风险平价仓位分配
        
        Args:
            equities: 各资产可用资金
            volatilities: 各资产波动率
        
        Returns:
            各资产分配权重
        """
        inverse_vols = {k: 1/v if v > 0 else 0 for k, v in volatilities.items()}
        total_inverse_vol = sum(inverse_vols.values())
        
        if total_inverse_vol == 0:
            return {k: 0 for k in equities}
        
        weights = {k: v/total_inverse_vol for k, v in inverse_vols.items()}
        return weights


if __name__ == "__main__":
    # 测试风控管理器
    print("=" * 60)
    print("风控模块测试")
    print("=" * 60)
    
    # 初始化风控管理器
    rm = RiskManager()
    
    # 模拟持仓
    positions = {
        '000001.SZ': Position('000001.SZ', 1000, 10.0, 10.5, 10500),
        '000002.SZ': Position('000002.SZ', 500, 20.0, 21.0, 10500),
    }
    
    current_equity = 100000
    
    # 测试买入检查
    print("\n--- 买入检查测试 ---")
    result = rm.check_order('000001.SZ', 'buy', 10000, 10.0, current_equity, positions)
    print(f"买入10000股 000001.SZ @ 10.0: {result}")
    
    # 测试黑名单
    rm.add_to_blacklist('300001.SZ', '测试')
    result = rm.check_order('300001.SZ', 'buy', 100, 10.0, current_equity, positions)
    print(f"买入黑名单股票 300001.SZ: {result}")
    
    # 测试仓位计算器
    print("\n--- 仓位计算器测试 ---")
    sizer = PositionSizer(risk_per_trade=0.02)
    
    # 固定比例
    position = sizer.fixed_ratio(100000, 0.10)
    print(f"固定比例仓位 (10%): {position:,.2f}")
    
    # ATR仓位
    shares = sizer.atr_based(100000, atr=0.5, stop_loss_atr_multiple=2.0)
    print(f"ATR仓位 (ATR=0.5, 2倍止损): {shares} 股")
    
    # 凯利公式
    kelly_position = sizer.kelly_formula(100000, win_rate=0.55, avg_win=100, avg_loss=50)
    print(f"凯利公式仓位 (胜率55%, 盈亏比2:1): {kelly_position:,.2f}")
    
    print("\n" + "=" * 60)
    print("风控模块测试完成")
    print("=" * 60)

    def is_blacklisted(self, symbol: str) -> bool:
        """检查股票是否在黑名单中"""
        return symbol in self.blacklist

