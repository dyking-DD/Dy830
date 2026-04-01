#!/usr/bin/env python3
"""
飞书Bot交易命令处理器
支持: 买入、卖出、查看持仓、查询价格
"""

import json
import re
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trading_cli import TradingAccount

class FeishuTradingBot:
    """飞书交易Bot"""
    
    def __init__(self):
        self.account = TradingAccount()
    
    def parse_command(self, message: str) -> dict:
        """解析用户消息"""
        msg = message.strip().upper()
        
        # 买入命令: 买入 600519.SH 100股 / 买 茅台 200 / BUY 600519 100
        buy_patterns = [
            r'(?:买入|买|BUY)\s+(\d{6}(?:\.SZ|\.SH)?)\s*(\d+)?\s*(?:股|手)?',
            r'(?:买入|买|BUY)\s+([\u4e00-\u9fa5]+)\s*(\d+)?\s*(?:股|手)?',
        ]
        
        # 卖出命令: 卖出 600519.SH 100股 / 卖 茅台 50% / SELL 600519
        sell_patterns = [
            r'(?:卖出|卖|SELL)\s+(\d{6}(?:\.SZ|\.SH)?)\s*(\d+|\d+%)?\s*(?:股|手)?',
            r'(?:卖出|卖|SELL)\s+([\u4e00-\u9fa5]+)\s*(\d+|\d+%)?\s*(?:股|手)?',
        ]
        
        # 查询命令
        if any(kw in msg for kw in ['持仓', '账户', '资产', 'STATUS', 'PORTFOLIO', '查']):
            return {'action': 'status'}
        
        if any(kw in msg for kw in ['价格', '行情', 'PRICE', 'QUOTE']):
            return {'action': 'prices'}
        
        # 匹配买入
        for pattern in buy_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                code = match.group(1)
                amount = match.group(2)
                return {
                    'action': 'buy',
                    'code': self._normalize_code(code),
                    'amount': amount
                }
        
        # 匹配卖出
        for pattern in sell_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                code = match.group(1)
                amount = match.group(2)
                return {
                    'action': 'sell',
                    'code': self._normalize_code(code),
                    'amount': amount
                }
        
        return {'action': 'unknown', 'message': message}
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        # 处理中文名称
        name_map = {
            '茅台': '600519.SH', '贵州茅台': '600519.SH',
            '宁德': '300750.SZ', '宁德时代': '300750.SZ',
            '万科': '000002.SZ', '万科A': '000002.SZ',
            '平安': '601318.SH', '中国平安': '601318.SH',
            '五粮液': '000858.SZ',
            '海康': '002415.SZ', '海康威视': '002415.SZ',
            '比亚迪': '002594.SZ',
            '美的': '000333.SZ', '美的集团': '000333.SZ',
            '牧原': '002714.SZ', '牧原股份': '002714.SZ',
            '招行': '600036.SH', '招商银行': '600036.SH',
            '隆基': '601012.SH', '隆基绿能': '601012.SH',
            '老窖': '000568.SZ', '泸州老窖': '000568.SZ',
            '顺丰': '002352.SZ', '顺丰控股': '002352.SZ',
            '中免': '601888.SH', '中国中免': '601888.SH',
            '平安银行': '000001.SZ', '平银': '000001.SZ',
        }
        
        if code in name_map:
            return name_map[code]
        
        # 处理纯数字代码
        if code.isdigit():
            if code.startswith('6'):
                return f"{code}.SH"
            else:
                return f"{code}.SZ"
        
        return code
    
    def execute(self, command: dict) -> str:
        """执行命令并返回飞书消息格式"""
        action = command.get('action')
        
        if action == 'status':
            return self._format_status()
        
        elif action == 'prices':
            return self._format_prices()
        
        elif action == 'buy':
            return self._execute_buy(command['code'], command.get('amount'))
        
        elif action == 'sell':
            return self._execute_sell(command['code'], command.get('amount'))
        
        else:
            return self._format_help()
    
    def _format_status(self) -> str:
        """格式化账户状态"""
        summary = self.account.get_portfolio_summary()
        
        pnl_emoji = "🟢" if summary['total_pnl'] >= 0 else "🔴"
        daily_emoji = "🟢" if summary['daily_pnl'] >= 0 else "🔴"
        
        lines = [
            "## 💰 账户概览",
            "",
            f"**总资产**: ¥{summary['total_assets']:,.2f}",
            f"**可用现金**: ¥{summary['cash']:,.2f}",
            f"**持仓市值**: ¥{summary['market_value']:,.2f}",
            f"{pnl_emoji} **累计盈亏**: ¥{summary['total_pnl']:+,.2f} ({summary['total_return_pct']:+.2f}%)",
            f"{daily_emoji} **当日盈亏**: ¥{summary['daily_pnl']:+,.2f}",
            f"**持仓数量**: {summary['position_count']} 只",
            "",
        ]
        
        # 持仓明细
        if self.account.positions:
            lines.append("### 📈 持仓明细")
            lines.append("")
            lines.append("| 股票 | 持仓 | 成本 | 现价 | 市值 | 盈亏 |")
            lines.append("|------|------|------|------|------|------|")
            
            for pos in sorted(self.account.positions.values(), 
                            key=lambda x: x.market_value, reverse=True):
                pnl_str = f"{'🟢' if pos.pnl >= 0 else '🔴'} ¥{pos.pnl:+.0f}"
                lines.append(f"| {pos.name} | {pos.volume} | ¥{pos.avg_cost:.2f} | ¥{pos.current_price:.2f} | ¥{pos.market_value:,.0f} | {pnl_str} |")
            
            lines.append("")
        
        # 最近交易
        if self.account.trades:
            lines.append("### 📝 最近交易")
            lines.append("")
            lines.append("| 时间 | 股票 | 操作 | 价格 | 数量 | 金额 |")
            lines.append("|------|------|------|------|------|------|")
            
            for trade in reversed(self.account.trades[-5:]):
                time_str = trade.timestamp[11:16] if len(trade.timestamp) > 16 else trade.timestamp[:16]
                action_emoji = "🟢" if trade.action == 'BUY' else "🔴"
                action_str = "买入" if trade.action == 'BUY' else "卖出"
                lines.append(f"| {time_str} | {trade.name} | {action_emoji}{action_str} | ¥{trade.price:.2f} | {trade.volume} | ¥{trade.amount:,.0f} |")
        
        return '\n'.join(lines)
    
    def _format_prices(self) -> str:
        """格式化行情"""
        lines = [
            "## 📊 自选行情",
            "",
            "| 股票 | 代码 | 最新价 | 涨跌 |",
            "|------|------|--------|------|"
        ]
        
        watchlist = [
            ('600519.SH', '贵州茅台'), ('300750.SZ', '宁德时代'),
            ('000002.SZ', '万科A'), ('601318.SH', '中国平安'),
            ('000858.SZ', '五粮液'), ('002415.SZ', '海康威视'),
            ('002594.SZ', '比亚迪'), ('000333.SZ', '美的集团'),
        ]
        
        for code, name in watchlist:
            price = self.account.get_current_price(code)
            base = self.account.BASE_PRICES.get(code, price)
            change = (price - base) / base * 100
            emoji = "🟢" if change >= 0 else "🔴"
            lines.append(f"| {name} | {code} | ¥{price:.2f} | {emoji} {change:+.2f}% |")
        
        return '\n'.join(lines)
    
    def _execute_buy(self, code: str, amount: str = None) -> str:
        """执行买入"""
        # 解析数量
        volume = None
        percent = None
        
        if amount:
            if '%' in amount:
                percent = float(amount.replace('%', '')) / 100
            else:
                volume = int(amount)
        
        # 执行买入
        result = self.account.buy(code, volume=volume, percent=percent)
        
        if result['success']:
            trade = result['trade']
            return f"""## ✅ 买入成功

**{trade['name']}** ({trade['ts_code']})
- 数量: {trade['volume']}股
- 价格: ¥{trade['price']:.2f}
- 金额: ¥{trade['amount']:,.2f}
- 费用: ¥{trade['fee']:.2f}
- 剩余现金: ¥{result['remaining_cash']:,.2f}
"""
        else:
            return f"## ❌ 买入失败\n\n{result['error']}"
    
    def _execute_sell(self, code: str, amount: str = None) -> str:
        """执行卖出"""
        # 解析数量
        volume = None
        percent = None
        
        if amount:
            if '%' in amount:
                percent = float(amount.replace('%', ''))
            else:
                volume = int(amount)
        
        # 执行卖出
        result = self.account.sell(code, volume=volume, percent=percent)
        
        if result['success']:
            trade = result['trade']
            pnl_emoji = "🟢" if result['pnl'] >= 0 else "🔴"
            return f"""## ✅ 卖出成功

**{trade['name']}** ({trade['ts_code']})
- 数量: {trade['volume']}股
- 价格: ¥{trade['price']:.2f}
- 金额: ¥{trade['amount']:,.2f}
- 盈亏: {pnl_emoji} ¥{result['pnl']:+.2f} ({result['pnl_pct']:+.2f}%)
- 剩余现金: ¥{result['remaining_cash']:,.2f}
"""
        else:
            return f"## ❌ 卖出失败\n\n{result['error']}"
    
    def _format_help(self) -> str:
        """格式化帮助信息"""
        return """## 🎯 交易Bot使用指南

### 查看账户
- `持仓`、`账户`、`资产`

### 查询行情
- `价格`、`行情`

### 买入股票
- `买入 600519.SH 100` - 买入100股
- `买 茅台 200` - 买入200股茅台
- `买入 宁德时代 20%` - 用20%资金买入

### 卖出股票
- `卖出 600519.SH 100` - 卖出100股
- `卖 万科 50%` - 卖出一半持仓
- `卖出 中国平安` - 全部卖出

### 支持的股票
茅台、宁德、万科、平安、五粮液、海康、比亚迪、美的、牧原、招行、隆基、老窖、顺丰、中免、平安银行
"""


def process_message(message: str) -> str:
    """处理飞书消息并返回回复"""
    bot = FeishuTradingBot()
    command = bot.parse_command(message)
    return bot.execute(command)


if __name__ == "__main__":
    # 测试模式
    if len(sys.argv) > 1:
        test_msg = ' '.join(sys.argv[1:])
        print(process_message(test_msg))
    else:
        # 交互模式
        print("🎯 飞书交易Bot测试模式")
        print("输入命令 (或 'quit' 退出):")
        while True:
            try:
                msg = input("> ").strip()
                if msg.lower() in ['quit', 'exit', 'q']:
                    break
                if msg:
                    print(process_message(msg))
                    print()
            except EOFError:
                break
