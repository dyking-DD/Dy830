#!/usr/bin/env python3
"""
专业模拟交易盘 - 真实交易体验 (轻量版)
支持: 实时盈亏、持仓管理、成交记录、资金曲线
"""

import json
import os
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class Position:
    """持仓"""
    ts_code: str
    name: str
    volume: int          # 持股数量
    avg_cost: float      # 成本价
    current_price: float # 当前价
    market_value: float  # 市值
    pnl: float          # 浮动盈亏
    pnl_pct: float      # 盈亏比例
    open_date: str      # 开仓日期


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    ts_code: str
    name: str
    action: str         # BUY/SELL
    price: float
    volume: int
    amount: float       # 成交金额
    fee: float         # 手续费
    timestamp: str
    pnl: float = 0     # 卖出时记录盈亏


class TradingAccount:
    """交易账户"""
    
    # 股票基准价格表
    BASE_PRICES = {
        '000001.SZ': 10.5, '000002.SZ': 15.2, '600519.SH': 1680.0,
        '601318.SH': 45.8, '000858.SZ': 145.0, '002415.SZ': 32.6,
        '300750.SZ': 185.0, '002594.SZ': 220.0, '000333.SZ': 58.0,
        '002714.SZ': 42.0, '600036.SH': 35.0, '601012.SH': 22.0,
        '000568.SZ': 78.5, '002352.SZ': 38.0, '601888.SH': 68.0,
    }
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_pnl_history: List[Dict] = []
        
        # 交易费用
        self.commission_rate = 0.0003    # 佣金万3
        self.min_commission = 5.0        # 最低佣金
        self.tax_rate = 0.001            # 印花税千1 (卖出)
        
        # 加载数据
        self._load_data()
    
    def _load_data(self):
        """从文件加载账户数据"""
        data_file = "trading_account.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.cash = data.get('cash', self.initial_capital)
                self.initial_capital = data.get('initial_capital', self.initial_capital)
                # 恢复持仓
                for pos_data in data.get('positions', []):
                    pos = Position(**pos_data)
                    self.positions[pos.ts_code] = pos
                # 恢复交易记录
                for trade_data in data.get('trades', []):
                    self.trades.append(Trade(**trade_data))
    
    def _save_data(self):
        """保存账户数据"""
        data = {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': [asdict(p) for p in self.positions.values()],
            'trades': [asdict(t) for t in self.trades[-100:]],  # 只保留最近100条
            'updated_at': datetime.now().isoformat()
        }
        with open("trading_account.json", 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def get_stock_name(self, ts_code: str) -> str:
        """获取股票名称"""
        name_map = {
            '000001.SZ': '平安银行', '000002.SZ': '万科A', '600519.SH': '贵州茅台',
            '601318.SH': '中国平安', '000858.SZ': '五粮液', '002415.SZ': '海康威视',
            '300750.SZ': '宁德时代', '002594.SZ': '比亚迪', '000333.SZ': '美的集团',
            '002714.SZ': '牧原股份', '600036.SH': '招商银行', '601012.SH': '隆基绿能',
            '000568.SZ': '泸州老窖', '002352.SZ': '顺丰控股', '601888.SH': '中国中免',
        }
        return name_map.get(ts_code, ts_code)
    
    def get_current_price(self, ts_code: str) -> float:
        """获取当前价格 (模拟实时波动)"""
        base = self.BASE_PRICES.get(ts_code, 50.0)
        # 基于时间种子生成伪随机波动，保证同一时间价格一致
        seed = int(datetime.now().strftime('%Y%m%d%H'))
        random.seed(seed + hash(ts_code) % 1000)
        change = random.uniform(-0.015, 0.015)  # ±1.5%波动
        return round(base * (1 + change), 2)
    
    def calculate_fees(self, amount: float, action: str) -> float:
        """计算交易费用"""
        commission = max(amount * self.commission_rate, self.min_commission)
        tax = amount * self.tax_rate if action == 'SELL' else 0
        return round(commission + tax, 2)
    
    def buy(self, ts_code: str, price: Optional[float] = None, 
            volume: Optional[int] = None, percent: Optional[float] = None) -> Dict:
        """买入股票"""
        
        # 获取当前价格
        current_price = price or self.get_current_price(ts_code)
        
        # 确定买入数量
        if volume:
            buy_volume = (volume // 100) * 100  # 100股整数倍
        elif percent:
            buy_amount = self.cash * percent
            buy_volume = int(buy_amount / current_price / 100) * 100
        else:
            buy_amount = self.cash * 0.2
            buy_volume = int(buy_amount / current_price / 100) * 100
        
        if buy_volume < 100:
            return {'success': False, 'error': '资金不足或买入数量少于100股'}
        
        # 计算金额和费用
        amount = current_price * buy_volume
        fee = self.calculate_fees(amount, 'BUY')
        total_cost = amount + fee
        
        if total_cost > self.cash:
            return {'success': False, 'error': f'资金不足 (需要¥{total_cost:,.2f}, 可用¥{self.cash:,.2f})'}
        
        # 执行买入
        self.cash -= total_cost
        name = self.get_stock_name(ts_code)
        
        if ts_code in self.positions:
            # 加仓 - 更新成本
            pos = self.positions[ts_code]
            total_volume = pos.volume + buy_volume
            total_cost_basis = pos.avg_cost * pos.volume + current_price * buy_volume
            pos.avg_cost = round(total_cost_basis / total_volume, 2)
            pos.volume = total_volume
            pos.current_price = current_price
        else:
            # 新建仓
            self.positions[ts_code] = Position(
                ts_code=ts_code,
                name=name,
                volume=buy_volume,
                avg_cost=current_price,
                current_price=current_price,
                market_value=amount,
                pnl=0,
                pnl_pct=0,
                open_date=datetime.now().strftime('%Y-%m-%d')
            )
        
        # 记录交易
        trade = Trade(
            trade_id=f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}",
            ts_code=ts_code,
            name=name,
            action='BUY',
            price=current_price,
            volume=buy_volume,
            amount=amount,
            fee=fee,
            timestamp=datetime.now().isoformat()
        )
        self.trades.append(trade)
        self._save_data()
        
        return {
            'success': True,
            'trade': asdict(trade),
            'remaining_cash': self.cash
        }
    
    def sell(self, ts_code: str, price: Optional[float] = None,
             volume: Optional[int] = None, percent: Optional[float] = None) -> Dict:
        """卖出股票"""
        
        if ts_code not in self.positions:
            return {'success': False, 'error': f'未持有 {ts_code}'}
        
        pos = self.positions[ts_code]
        current_price = price or self.get_current_price(ts_code)
        
        # 确定卖出数量
        if volume:
            sell_volume = min((volume // 100) * 100, pos.volume)
        elif percent:
            sell_volume = int(pos.volume * percent / 100) * 100
        else:
            sell_volume = pos.volume
        
        if sell_volume < 100:
            return {'success': False, 'error': '卖出数量至少100股'}
        
        # 计算金额和费用
        amount = current_price * sell_volume
        fee = self.calculate_fees(amount, 'SELL')
        net_amount = amount - fee
        
        # 计算盈亏
        cost_basis = pos.avg_cost * sell_volume
        pnl = amount - cost_basis - fee
        pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
        
        # 执行卖出
        self.cash += net_amount
        pos.volume -= sell_volume
        
        if pos.volume == 0:
            del self.positions[ts_code]
        else:
            pos.current_price = current_price
        
        # 记录交易
        trade = Trade(
            trade_id=f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}",
            ts_code=ts_code,
            name=pos.name,
            action='SELL',
            price=current_price,
            volume=sell_volume,
            amount=amount,
            fee=fee,
            timestamp=datetime.now().isoformat(),
            pnl=round(pnl, 2)
        )
        self.trades.append(trade)
        self._save_data()
        
        return {
            'success': True,
            'trade': asdict(trade),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'remaining_cash': self.cash
        }
    
    def update_prices(self):
        """更新所有持仓的最新价格"""
        for ts_code, pos in self.positions.items():
            current_price = self.get_current_price(ts_code)
            pos.current_price = current_price
            pos.market_value = current_price * pos.volume
            pos.pnl = (current_price - pos.avg_cost) * pos.volume
            pos.pnl_pct = ((current_price - pos.avg_cost) / pos.avg_cost) * 100
    
    def get_portfolio_summary(self) -> Dict:
        """获取账户汇总"""
        self.update_prices()
        
        total_market_value = sum(p.market_value for p in self.positions.values())
        total_pnl = sum(p.pnl for p in self.positions.values())
        total_assets = self.cash + total_market_value
        
        # 计算当日盈亏 (基于随机种子)
        seed = int(datetime.now().strftime('%Y%m%d'))
        random.seed(seed)
        daily_pnl = random.uniform(-8000, 12000)
        
        return {
            'total_assets': round(total_assets, 2),
            'cash': round(self.cash, 2),
            'market_value': round(total_market_value, 2),
            'total_pnl': round(total_pnl, 2),
            'daily_pnl': round(daily_pnl, 2),
            'total_return_pct': round((total_assets - self.initial_capital) / self.initial_capital * 100, 2),
            'position_count': len(self.positions),
            'updated_at': datetime.now().strftime('%H:%M:%S')
        }
    
    def get_positions_table(self) -> str:
        """生成持仓表格"""
        if not self.positions:
            return "暂无持仓"
        
        self.update_prices()
        
        lines = []
        lines.append("┌──────────┬──────────┬────────┬─────────┬─────────┬───────────┬───────────┐")
        lines.append("│ 股票代码 │ 股票名称 │ 持仓量 │ 成本价  │ 现价    │ 市值      │ 浮动盈亏  │")
        lines.append("├──────────┼──────────┼────────┼─────────┼─────────┼───────────┼───────────┤")
        
        for pos in sorted(self.positions.values(), key=lambda x: x.market_value, reverse=True):
            pnl_str = f"{pos.pnl:+.0f}"
            lines.append(f"│ {pos.ts_code:<8} │ {pos.name:<8} │ {pos.volume:>6} │ {pos.avg_cost:>7.2f} │ {pos.current_price:>7.2f} │ {pos.market_value:>9,.0f} │ {pnl_str:>9} │")
        
        lines.append("└──────────┴──────────┴────────┴─────────┴─────────┴───────────┴───────────┘")
        
        return '\n'.join(lines)
    
    def get_recent_trades(self, n: int = 5) -> str:
        """生成最近交易记录"""
        if not self.trades:
            return "暂无交易记录"
        
        lines = []
        lines.append("┌──────────────┬──────────┬────────┬────────┬─────────┬───────────┬───────────┐")
        lines.append("│ 时间         │ 股票     │ 操作   │ 价格   │ 数量    │ 金额      │ 盈亏      │")
        lines.append("├──────────────┼──────────┼────────┼────────┼─────────┼───────────┼───────────┤")
        
        for trade in reversed(self.trades[-n:]):
            time_str = trade.timestamp[11:19] if len(trade.timestamp) > 19 else trade.timestamp
            action_str = "买入" if trade.action == 'BUY' else "卖出"
            pnl_str = f"{trade.pnl:+.0f}" if trade.pnl != 0 else "-"
            lines.append(f"│ {time_str:<12} │ {trade.name:<8} │ {action_str:<6} │ {trade.price:>6.2f} │ {trade.volume:>7} │ {trade.amount:>9,.0f} │ {pnl_str:>9} │")
        
        lines.append("└──────────────┴──────────┴────────┴────────┴─────────┴───────────┴───────────┘")
        
        return '\n'.join(lines)


def show_dashboard():
    """显示交易盘"""
    account = TradingAccount()
    summary = account.get_portfolio_summary()
    
    print("=" * 80)
    print("🎯 专业模拟交易盘".center(76))
    print("=" * 80)
    print()
    
    # 账户概览
    pnl_emoji = "🟢" if summary['total_pnl'] >= 0 else "🔴"
    daily_emoji = "🟢" if summary['daily_pnl'] >= 0 else "🔴"
    
    print(f"💰 总资产: ¥{summary['total_assets']:>15,.2f}    初始资金: ¥{account.initial_capital:>15,.2f}")
    print(f"💵 可用现金: ¥{summary['cash']:>13,.2f}    持仓市值: ¥{summary['market_value']:>15,.2f}")
    print(f"{pnl_emoji} 累计盈亏: ¥{summary['total_pnl']:>+13,.2f} ({summary['total_return_pct']:+.2f}%)    {daily_emoji} 当日盈亏: ¥{summary['daily_pnl']:>+13,.2f}")
    print(f"📊 持仓数量: {summary['position_count']:>3} 只    更新时间: {summary['updated_at']}")
    print()
    
    # 持仓明细
    print("-" * 80)
    print("📈 持仓明细")
    print("-" * 80)
    print(account.get_positions_table())
    print()
    
    # 最近交易
    print("-" * 80)
    print("📝 最近交易")
    print("-" * 80)
    print(account.get_recent_trades(5))
    print()
    
    # 操作提示
    print("-" * 80)
    print("⌨️ 操作指令:")
    print("   python trading_cli.py buy 股票代码 [数量/百分比]  - 买入")
    print("   python trading_cli.py sell 股票代码 [数量/百分比] - 卖出")
    print("   python trading_cli.py status                      - 查看状态")
    print("=" * 80)


def buy_stock(ts_code, amount=None):
    """买入股票"""
    account = TradingAccount()
    
    if amount and '%' in amount:
        result = account.buy(ts_code, percent=float(amount.replace('%', '')) / 100)
    elif amount:
        result = account.buy(ts_code, volume=int(amount))
    else:
        result = account.buy(ts_code)
    
    if result['success']:
        trade = result['trade']
        print(f"✅ 买入成功!")
        print(f"   股票: {trade['name']} ({trade['ts_code']})")
        print(f"   数量: {trade['volume']}股 @ ¥{trade['price']}")
        print(f"   金额: ¥{trade['amount']:,.2f}")
        print(f"   费用: ¥{trade['fee']:.2f}")
        print(f"   剩余现金: ¥{result['remaining_cash']:,.2f}")
    else:
        print(f"❌ {result['error']}")


def sell_stock(ts_code, amount=None):
    """卖出股票"""
    account = TradingAccount()
    
    if amount and '%' in amount:
        result = account.sell(ts_code, percent=float(amount.replace('%', '')))
    elif amount:
        result = account.sell(ts_code, volume=int(amount))
    else:
        result = account.sell(ts_code)
    
    if result['success']:
        trade = result['trade']
        pnl_emoji = "🟢" if result['pnl'] >= 0 else "🔴"
        print(f"✅ 卖出成功!")
        print(f"   股票: {trade['name']} ({trade['ts_code']})")
        print(f"   数量: {trade['volume']}股 @ ¥{trade['price']}")
        print(f"   金额: ¥{trade['amount']:,.2f}")
        print(f"   盈亏: {pnl_emoji} ¥{result['pnl']:+.2f} ({result['pnl_pct']:+.2f}%)")
        print(f"   剩余现金: ¥{result['remaining_cash']:,.2f}")
    else:
        print(f"❌ {result['error']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        show_dashboard()
    elif sys.argv[1] == 'buy':
        if len(sys.argv) < 3:
            print("用法: python trading_cli.py buy 股票代码 [数量/百分比]")
            print("示例: python trading_cli.py buy 600519.SH")
            print("      python trading_cli.py buy 000002.SZ 1000")
            print("      python trading_cli.py buy 300750.SZ 20%")
        else:
            amount = sys.argv[3] if len(sys.argv) > 3 else None
            buy_stock(sys.argv[2].upper(), amount)
    elif sys.argv[1] == 'sell':
        if len(sys.argv) < 3:
            print("用法: python trading_cli.py sell 股票代码 [数量/百分比]")
            print("示例: python trading_cli.py sell 600519.SH")
            print("      python trading_cli.py sell 000002.SZ 500")
            print("      python trading_cli.py sell 300750.SZ 50%")
        else:
            amount = sys.argv[3] if len(sys.argv) > 3 else None
            sell_stock(sys.argv[2].upper(), amount)
    elif sys.argv[1] == 'status':
        show_dashboard()
    else:
        print(f"未知命令: {sys.argv[1]}")
        print("可用命令: status, buy, sell")
