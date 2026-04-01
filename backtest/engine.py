"""
回测引擎 - 核心模块
支持：向量回测、事件驱动回测、绩效分析
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

from strategies.base import BaseStrategy, Signal, Position

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易记录"""
    trade_id: int
    ts_code: str
    trade_date: str
    action: str  # 'buy', 'sell'
    price: float
    volume: int
    amount: float
    commission: float
    tax: float
    strategy: str
    reason: str


@dataclass
class DailyStat:
    """每日账户统计"""
    date: str
    total_value: float
    cash: float
    market_value: float
    positions_value: Dict[str, float]
    daily_pnl: float
    daily_return: float
    cumulative_return: float


class BacktestEngine:
    """
    回测引擎
    
    支持：
    - 向量回测（快速）
    - 事件驱动回测（精确）
    - 滑点、手续费模拟
    - 绩效分析
    """
    
    def __init__(self,
                 initial_capital: float = 1000000.0,
                 commission_rate: float = 0.0003,  # 万3
                 min_commission: float = 5.0,
                 stamp_tax: float = 0.001,  # 卖出千1印花税
                 slippage: float = 0.001,  # 滑点千1
                 max_position_per_stock: float = 0.1):  # 单票最大10%
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 佣金费率
            min_commission: 最低佣金
            stamp_tax: 印花税率
            slippage: 滑点
            max_position_per_stock: 单票最大仓位比例
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax = stamp_tax
        self.slippage = slippage
        self.max_position_per_stock = max_position_per_stock
        
        # 状态
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_stats: List[DailyStat] = []
        self.current_date = None
        self.trade_id = 0
        
    def reset(self):
        """重置状态"""
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_stats = []
        self.current_date = None
        self.trade_id = 0
        
    def _calculate_commission(self, amount: float, action: str) -> tuple:
        """计算手续费和税费"""
        commission = max(amount * self.commission_rate, self.min_commission)
        tax = amount * self.stamp_tax if action == 'sell' else 0
        return commission, tax
    
    def _apply_slippage(self, price: float, action: str) -> float:
        """应用滑点"""
        if action == 'buy':
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)
    
    def execute_signal(self, signal: Signal, strategy_name: str) -> bool:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
            strategy_name: 策略名称
            
        Returns:
            是否执行成功
        """
        ts_code = signal.ts_code
        action = signal.action
        price = self._apply_slippage(signal.price, action)
        volume = signal.volume
        
        # 买入金额
        amount = price * volume
        
        # 计算手续费
        commission, tax = self._calculate_commission(amount, action)
        total_cost = amount + commission + tax
        
        if action == 'buy':
            # 检查资金
            if total_cost > self.cash:
                # 调整成交量
                max_volume = int(self.cash / (price * (1 + self.commission_rate)))
                if max_volume < 100:  # A股最小100股
                    logger.warning(f"资金不足，无法买入 {ts_code}")
                    return False
                volume = (max_volume // 100) * 100
                amount = price * volume
                commission, tax = self._calculate_commission(amount, 'buy')
                total_cost = amount + commission + tax
            
            # 检查仓位限制
            position_value = self.positions.get(ts_code, Position(ts_code, 0, 0)).market_value
            new_position_value = position_value + amount
            total_value = self.get_total_value()
            if new_position_value / total_value > self.max_position_per_stock:
                logger.warning(f"{ts_code} 仓位超限，跳过买入")
                return False
            
            # 执行买入
            self.cash -= total_cost
            if ts_code in self.positions:
                pos = self.positions[ts_code]
                total_cost_old = pos.volume * pos.avg_cost
                new_volume = pos.volume + volume
                new_avg_cost = (total_cost_old + amount) / new_volume
                self.positions[ts_code] = Position(ts_code, new_volume, new_avg_cost)
            else:
                self.positions[ts_code] = Position(ts_code, volume, price)
            
            logger.info(f"[BUY] {ts_code} {volume}股 @ {price:.2f}, 手续费:{commission:.2f}")
            
        elif action == 'sell':
            # 检查持仓
            if ts_code not in self.positions or self.positions[ts_code].volume == 0:
                logger.warning(f"没有持仓 {ts_code}，无法卖出")
                return False
            
            pos = self.positions[ts_code]
            volume = min(volume, pos.volume)  # 不能超过持仓
            amount = price * volume
            commission, tax = self._calculate_commission(amount, 'sell')
            total_revenue = amount - commission - tax
            
            # 执行卖出
            self.cash += total_revenue
            remaining_volume = pos.volume - volume
            if remaining_volume == 0:
                del self.positions[ts_code]
            else:
                self.positions[ts_code] = Position(ts_code, remaining_volume, pos.avg_cost)
            
            pnl = (price - pos.avg_cost) * volume - commission - tax
            logger.info(f"[SELL] {ts_code} {volume}股 @ {price:.2f}, 盈亏:{pnl:.2f}, 手续费+税:{commission+tax:.2f}")
        
        # 记录交易
        self.trade_id += 1
        self.trades.append(Trade(
            trade_id=self.trade_id,
            ts_code=ts_code,
            trade_date=self.current_date or signal.trade_date,
            action=action,
            price=price,
            volume=volume,
            amount=amount,
            commission=commission,
            tax=tax,
            strategy=strategy_name,
            reason=signal.reason
        ))
        
        return True
    
    def update_positions_price(self, prices: Dict[str, float]):
        """更新持仓价格"""
        for ts_code, price in prices.items():
            if ts_code in self.positions:
                pos = self.positions[ts_code]
                pos.current_price = price
    
    def get_total_value(self) -> float:
        """获取总资产"""
        market_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + market_value
    
    def get_market_value(self) -> float:
        """获取持仓市值"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def record_daily_stat(self, date: str, prices: Dict[str, float] = None):
        """记录每日统计"""
        if prices:
            self.update_positions_price(prices)
        
        total_value = self.get_total_value()
        market_value = self.get_market_value()
        
        # 计算当日盈亏
        daily_pnl = 0
        if self.daily_stats:
            daily_pnl = total_value - self.daily_stats[-1].total_value
        
        # 计算收益率
        daily_return = daily_pnl / self.daily_stats[-1].total_value if self.daily_stats else 0
        cumulative_return = (total_value - self.initial_capital) / self.initial_capital
        
        stat = DailyStat(
            date=date,
            total_value=total_value,
            cash=self.cash,
            market_value=market_value,
            positions_value={ts: pos.market_value for ts, pos in self.positions.items()},
            daily_pnl=daily_pnl,
            daily_return=daily_return,
            cumulative_return=cumulative_return
        )
        self.daily_stats.append(stat)
    
    def run_backtest(self,
                    strategy: BaseStrategy,
                    data: pd.DataFrame,
                    benchmark: pd.DataFrame = None) -> Dict:
        """
        运行回测
        
        Args:
            strategy: 策略实例
            data: 股票数据DataFrame
            benchmark: 基准数据 (如上证指数)
            
        Returns:
            回测结果字典
        """
        self.reset()
        logger.info(f"开始回测: {strategy.name}")
        logger.info(f"初始资金: {self.initial_capital:,.2f}")
        
        # 按日期分组数据
        if 'trade_date' not in data.columns:
            raise ValueError("数据必须包含 trade_date 列")
        
        dates = sorted(data['trade_date'].unique())
        
        for i, date in enumerate(dates):
            self.current_date = str(date)
            day_data = data[data['trade_date'] == date]
            
            # 更新持仓价格
            prices = dict(zip(day_data['ts_code'], day_data['close']))
            self.update_positions_price(prices)
            
            # 获取信号并执行
            for _, row in day_data.iterrows():
                ts_code = row['ts_code']
                stock_data = data[data['ts_code'] == ts_code].iloc[:i+1]
                
                if len(stock_data) < 20:  # 最少需要20天数据计算指标
                    continue
                
                signals = strategy.on_data(stock_data, self.positions)
                for signal in signals:
                    self.execute_signal(signal, strategy.name)
            
            # 记录每日统计
            self.record_daily_stat(str(date), prices)
            
            if (i + 1) % 60 == 0 or i == len(dates) - 1:
                logger.info(f"回测进度: {i+1}/{len(dates)} {date} 总资产: {self.get_total_value():,.2f}")
        
        # 计算绩效指标
        results = self.calculate_metrics(benchmark)
        
        logger.info(f"回测完成！最终资产: {self.get_total_value():,.2f}")
        return results
    
    def calculate_metrics(self, benchmark: pd.DataFrame = None) -> Dict:
        """计算回测绩效指标"""
        if not self.daily_stats:
            return {}
        
        df = pd.DataFrame([{
            'date': s.date,
            'total_value': s.total_value,
            'daily_return': s.daily_return,
            'cumulative_return': s.cumulative_return
        } for s in self.daily_stats])
        
        # 总收益率
        total_return = (self.get_total_value() - self.initial_capital) / self.initial_capital
        
        # 年化收益率
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 年化波动率
        daily_volatility = df['daily_return'].std()
        annual_volatility = daily_volatility * np.sqrt(252)
        
        # 夏普比率 (假设无风险利率2%)
        risk_free_rate = 0.02
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        
        # 最大回撤
        df['cummax'] = (1 + df['cumulative_return']).cummax()
        df['drawdown'] = (1 + df['cumulative_return']) / df['cummax'] - 1
        max_drawdown = df['drawdown'].min()
        
        # 胜率
        win_trades = len([t for t in self.trades if t.action == 'sell' and 
                         (t.price - self.positions.get(t.ts_code, Position(t.ts_code, 0, t.price)).avg_cost) * t.volume > 0])
        total_sell_trades = len([t for t in self.trades if t.action == 'sell'])
        win_rate = win_trades / total_sell_trades if total_sell_trades > 0 else 0
        
        # 盈亏比
        profits = [t.amount - t.commission - t.tax for t in self.trades if t.action == 'sell']
        profit_loss_ratio = abs(sum(p for p in profits if p > 0) / sum(p for p in profits if p < 0)) if profits and sum(p for p in profits if p < 0) != 0 else 0
        
        return {
            'strategy': self.trades[0].strategy if self.trades else 'Unknown',
            'initial_capital': self.initial_capital,
            'final_value': self.get_total_value(),
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_commission': sum(t.commission for t in self.trades),
            'total_tax': sum(t.tax for t in self.trades),
            'daily_stats': df.to_dict('records'),
            'trades': [{
                'id': t.trade_id,
                'date': t.trade_date,
                'code': t.ts_code,
                'action': t.action,
                'price': t.price,
                'volume': t.volume,
                'amount': t.amount,
                'reason': t.reason
            } for t in self.trades]
        }
    
    def save_results(self, results: Dict, output_path: str):
        """保存回测结果"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"回测结果已保存: {output_path}")


def run_single_stock_backtest(
    strategy: BaseStrategy,
    stock_data: pd.DataFrame,
    initial_capital: float = 100000,
    output_dir: str = "backtest/results"
) -> Dict:
    """
    单股票回测快捷函数
    
    Args:
        strategy: 策略实例
        stock_data: 单只股票数据
        initial_capital: 初始资金
        output_dir: 输出目录
        
    Returns:
        回测结果
    """
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission_rate=0.0003,
        slippage=0.001
    )
    
    results = engine.run_backtest(strategy, stock_data)
    
    # 保存结果
    stock_code = stock_data['ts_code'].iloc[0] if 'ts_code' in stock_data.columns else 'unknown'
    output_file = Path(output_dir) / f"{strategy.name}_{stock_code}.json"
    engine.save_results(results, output_file)
    
    return results


if __name__ == "__main__":
    # 测试回测引擎
    from strategies.examples import MACrossVolumeStrategy
    
    # 创建测试数据
    import numpy as np
    np.random.seed(42)
    
    dates = pd.date_range('20240101', periods=100, freq='B')
    prices = 10 + np.random.randn(100).cumsum() * 0.3
    
    test_data = pd.DataFrame({
        'ts_code': ['000001.SZ'] * 100,
        'trade_date': dates.strftime('%Y%m%d'),
        'open': prices + np.random.randn(100) * 0.1,
        'high': prices + abs(np.random.randn(100)) * 0.2,
        'low': prices - abs(np.random.randn(100)) * 0.2,
        'close': prices,
        'vol': np.random.randint(10000, 100000, 100)
    })
    
    # 运行回测
    strategy = MACrossVolumeStrategy(fast_period=5, slow_period=10)
    engine = BacktestEngine(initial_capital=100000)
    results = engine.run_backtest(strategy, test_data)
    
    print("\n" + "="*50)
    print("回测结果")
    print("="*50)
    print(f"策略: {results['strategy']}")
    print(f"初始资金: {results['initial_capital']:,.2f}")
    print(f"最终资产: {results['final_value']:,.2f}")
    print(f"总收益率: {results['total_return']*100:.2f}%")
    print(f"年化收益率: {results['annual_return']*100:.2f}%")
    print(f"夏普比率: {results['sharpe_ratio']:.2f}")
    print(f"最大回撤: {results['max_drawdown']*100:.2f}%")
    print(f"交易次数: {results['total_trades']}")
    print("="*50)
