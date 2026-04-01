#!/usr/bin/env python3
"""
每日扫描器 - Daily Scanner

功能：
- 每日收盘后扫描全市场股票
- 运行策略生成交易信号
- 执行模拟交易
- 生成每日报告
- 发送飞书通知（可选）

运行方式:
    python3 scripts/daily_scanner.py [--date YYYY-MM-DD] [--webhook URL] [--watchlist] [--sector SECTOR]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.akshare_fetcher import AkShareFetcher
from execution.paper_trading import PaperTradingEngine, OrderType
from execution.notifier import NotificationManager
from risk import RiskManager, PositionSizer
from strategies.examples import MACrossVolumeStrategy, RSIStrategy


class DailyScanner:
    """每日扫描器"""
    
    def __init__(self, webhook_url: str = None):
        self.fetcher = AkShareFetcher()
        self.engine = PaperTradingEngine()
        self.risk_manager = RiskManager()
        self.sizer = PositionSizer(risk_per_trade=0.02)
        self.notifier = NotificationManager(webhook_url=webhook_url)
        
        # 加载策略
        self.strategies = [
            MACrossVolumeStrategy(),
            RSIStrategy()
        ]
        
        logger.info("每日扫描器初始化完成")
    
    def load_watchlist(self, watchlist_file: str = "config/watchlist.txt") -> List[str]:
        """
        加载自选股票列表
        
        Args:
            watchlist_file: 自选列表文件路径
            
        Returns:
            股票代码列表
        """
        if not os.path.exists(watchlist_file):
            logger.warning(f"自选列表文件不存在: {watchlist_file}")
            return []
        
        symbols = []
        with open(watchlist_file, 'r') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 提取股票代码（处理空格等）
                symbol = line.split()[0] if ' ' in line else line
                if symbol:
                    symbols.append(symbol)
        
        logger.info(f"从 {watchlist_file} 加载 {len(symbols)} 只自选股票")
        return symbols
    
    def filter_by_sector(self, symbols: List[str], sector: str) -> List[str]:
        """
        按板块筛选股票
        
        Args:
            symbols: 股票代码列表
            sector: 板块名称 (cyb=创业板, kcb=科创板, sz=深证主板, sh=上证主板)
            
        Returns:
            筛选后的股票代码列表
        """
        sector_patterns = {
            'cyb': lambda s: s.startswith('300') and s.endswith('.SZ'),  # 创业板
            'kcb': lambda s: s.startswith('688') and s.endswith('.SH'),  # 科创板
            'sz': lambda s: s.endswith('.SZ'),  # 深证（含主板、中小板、创业板）
            'sh': lambda s: s.endswith('.SH'),  # 上证（含主板、科创板）
        }
        
        if sector not in sector_patterns:
            logger.warning(f"未知板块: {sector}，返回全部")
            return symbols
        
        filtered = [s for s in symbols if sector_patterns[sector](s)]
        logger.info(f"板块筛选 [{sector}]: {len(filtered)}/{len(symbols)} 只")
        return filtered
    
    def get_stock_universe(self, sector: Optional[str] = None, 
                          watchlist_only: bool = False,
                          watchlist_file: str = "config/watchlist.txt") -> List[str]:
        """
        获取股票池
        
        Args:
            sector: 板块筛选 (cyb/kcb/sz/sh)
            watchlist_only: 是否只使用自选列表
            watchlist_file: 自选列表文件路径
            
        Returns:
            股票代码列表（排除ST、退市等）
        """
        # 如果使用自选列表
        if watchlist_only:
            symbols = self.load_watchlist(watchlist_file)
        else:
            # 获取全市场股票
            logger.info("获取股票池...")
            df = self.fetcher.get_stock_list()
            
            if df is None or df.empty:
                logger.error("获取股票列表失败")
                return []
            
            symbols = df['ts_code'].tolist()
        
        # 板块筛选
        if sector:
            symbols = self.filter_by_sector(symbols, sector)
        
        # 排除黑名单
        filtered = [s for s in symbols if not self.risk_manager.is_blacklisted(s)]
        
        logger.info(f"股票池: {len(filtered)} 只（排除 {len(symbols) - len(filtered)} 只黑名单）")
        return filtered
    
    def scan_stock(self, symbol: str, date: datetime) -> Dict:
        """
        扫描单只股票
        
        Args:
            symbol: 股票代码
            date: 扫描日期
        
        Returns:
            扫描结果
        """
        try:
            # 获取历史数据（需要足够计算均线）
            code = symbol.split('.')[0]
            df = self.fetcher.get_daily_data(code, start_date=(date - timedelta(days=120)).strftime('%Y%m%d'))
            
            if df is None or len(df) < 60:
                return None
            
            # 计算技术指标
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            
            # 计算ATR
            df['TR'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['ATR14'] = df['TR'].rolling(window=14).mean()
            
            # 获取最新数据
            latest = df.iloc[-1]
            current_price = latest['close']
            
            # 生成信号
            signals = []
            
            # 策略1: 双均线金叉
            if latest['MA5'] > latest['MA20'] and df['MA5'].iloc[-2] <= df['MA20'].iloc[-2]:
                signals.append({
                    'symbol': symbol,
                    'action': 'buy',
                    'price': current_price,
                    'reason': 'MA5上穿MA20金叉',
                    'strength': 0.7
                })
            elif latest['MA5'] < latest['MA20'] and df['MA5'].iloc[-2] >= df['MA20'].iloc[-2]:
                signals.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'price': current_price,
                    'reason': 'MA5下穿MA20死叉',
                    'strength': 0.7
                })
            
            # 策略2: RSI超卖反弹
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            latest_rsi = df['RSI'].iloc[-1]
            if latest_rsi < 30:
                signals.append({
                    'symbol': symbol,
                    'action': 'buy',
                    'price': current_price,
                    'reason': f'RSI超卖({latest_rsi:.1f})',
                    'strength': 0.6
                })
            elif latest_rsi > 70:
                signals.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'price': current_price,
                    'reason': f'RSI超买({latest_rsi:.1f})',
                    'strength': 0.6
                })
            
            return {
                'symbol': symbol,
                'price': current_price,
                'atr': latest['ATR14'],
                'ma5': latest['MA5'],
                'ma20': latest['MA20'],
                'rsi': latest_rsi,
                'vol': latest['vol'],
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"扫描 {symbol} 失败: {e}")
            return None
    
    def execute_signals(self, signals: List[Dict]):
        """
        执行交易信号
        
        Args:
            signals: 交易信号列表
        """
        if not signals:
            logger.info("无交易信号")
            return
        
        logger.info(f"处理 {len(signals)} 个交易信号...")
        
        # 按强度排序，优先处理强信号
        signals = sorted(signals, key=lambda x: x['strength'], reverse=True)
        
        executed_count = 0
        for signal in signals:
            symbol = signal['symbol']
            action = signal['action']
            price = signal['price']
            reason = signal.get('reason', '')
            
            # 风控检查
            from risk.risk_manager import Position as RiskPosition
            positions = {
                k: RiskPosition(k, v.quantity, v.avg_price, v.current_price, v.market_value)
                for k, v in self.engine.positions.items()
            }
            
            result = self.risk_manager.check_order(
                symbol, action, 100, price, self.engine.equity, positions
            )
            
            if not result.passed:
                logger.warning(f"风控拦截 {symbol}: {result.message}")
                self.notifier.send_risk_alert(
                    f"风控拦截: {symbol}",
                    result.message,
                    "warning"
                )
                continue
            
            # 计算仓位
            # 使用ATR计算建议仓位
            atr = signal.get('atr', price * 0.02)  # 默认2%波动
            suggested_shares = self.sizer.atr_based(self.engine.equity, atr, 2.0)
            
            # 限制单票仓位
            max_shares = int(self.engine.equity * self.risk_manager.config['max_position_per_stock'] / price)
            shares = min(suggested_shares, max_shares)
            
            # 最少买入100股
            if action == 'buy' and shares < 100:
                logger.info(f"{symbol} 建议仓位不足100股，跳过")
                continue
            
            # 执行交易
            order = self.engine.submit_order(
                symbol=symbol,
                action=action,
                quantity=shares,
                order_type=OrderType.MARKET,
                current_price=price
            )
            
            if order.status.value == 'filled':
                logger.info(f"✓ 执行 {action.upper()} {symbol} {shares}股 @ {price:.2f}")
                self.risk_manager.record_trade()
                executed_count += 1
                
                # 发送交易通知
                self.notifier.send_trade_alert(
                    symbol=symbol,
                    action=action,
                    quantity=shares,
                    price=price,
                    reason=reason
                )
            else:
                logger.warning(f"✗ 订单被拒绝: {order.reason}")
        
        logger.info(f"执行完成: {executed_count}/{len(signals)} 个信号")
    
    def run(self, date: datetime = None, limit: int = 100,
            sector: Optional[str] = None,
            watchlist_only: bool = False):
        """
        运行每日扫描
        
        Args:
            date: 扫描日期，默认今天
            limit: 限制扫描股票数量（用于测试）
            sector: 板块筛选 (cyb=创业板, kcb=科创板)
            watchlist_only: 是否只扫描自选列表
        """
        if date is None:
            date = datetime.now()
        
        # 显示扫描范围
        scope_desc = []
        if watchlist_only:
            scope_desc.append("自选列表")
        if sector:
            sector_names = {'cyb': '创业板', 'kcb': '科创板', 'sz': '深证', 'sh': '上证'}
            scope_desc.append(sector_names.get(sector, sector))
        scope_str = ' + '.join(scope_desc) if scope_desc else '全市场'
        
        logger.info(f"{'='*60}")
        logger.info(f"开始每日扫描 - {date.strftime('%Y-%m-%d')} [{scope_str}]")
        logger.info(f"{'='*60}")
        
        # 1. 获取股票池
        symbols = self.get_stock_universe(sector=sector, watchlist_only=watchlist_only)[:limit]
        
        if not symbols:
            logger.error("股票池为空，终止扫描")
            self.notifier.send_risk_alert("扫描失败", f"[{scope_str}] 股票池为空", "error")
            return
        
        # 2. 扫描每只股票
        all_signals = []
        for i, symbol in enumerate(symbols):
            if (i + 1) % 50 == 0 or (i + 1) == len(symbols):
                logger.info(f"扫描进度: {i+1}/{len(symbols)}")
            
            result = self.scan_stock(symbol, date)
            if result and result['signals']:
                all_signals.extend(result['signals'])
        
        logger.info(f"扫描完成，发现 {len(all_signals)} 个交易信号")
        
        # 3. 执行交易信号
        self.execute_signals(all_signals)
        
        # 4. 记录每日快照
        self.engine.record_daily_snapshot(date)
        
        # 5. 生成报告
        report = self.engine.generate_daily_report(date)
        print("\n" + report)
        
        # 保存报告
        report_file = f"logs/daily_report_{date.strftime('%Y%m%d')}.txt"
        os.makedirs("logs", exist_ok=True)
        with open(report_file, 'w') as f:
            f.write(report)
        logger.info(f"报告已保存: {report_file}")
        
        # 6. 发送飞书通知
        self.notifier.send_daily_report(report, date)
        
        return report


def main():
    parser = argparse.ArgumentParser(description='每日股票扫描器')
    parser.add_argument('--date', type=str, help='扫描日期 (YYYY-MM-DD)，默认今天')
    parser.add_argument('--limit', type=int, default=1000, help='限制扫描股票数量')
    parser.add_argument('--webhook', type=str, help='飞书机器人Webhook地址')
    parser.add_argument('--sector', type=str, choices=['cyb', 'kcb', 'sz', 'sh'],
                       help='板块筛选: cyb=创业板, kcb=科创板, sz=深证, sh=上证')
    parser.add_argument('--watchlist', action='store_true',
                       help='只扫描自选列表(config/watchlist.txt)')
    parser.add_argument('--cyb-kcb', action='store_true',
                       help='扫描创业板+科创板（快捷方式）')
    
    args = parser.parse_args()
    
    # 解析日期
    if args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        date = datetime.now()
    
    # 优先使用命令行传入的webhook，否则使用环境变量
    webhook = args.webhook or os.environ.get('FEISHU_WEBHOOK', '')
    
    # 处理快捷方式 --cyb-kcb
    sector = args.sector
    if args.cyb_kcb:
        # 创业板+科创板需要两次扫描，这里先以创业板为例，实际可以扩展
        logger.info("创业板+科创板扫描模式")
        # 暂时只扫描创业板，用户可以运行两次
        sector = 'cyb'
    
    # 运行扫描
    scanner = DailyScanner(webhook_url=webhook)
    scanner.run(date, limit=args.limit, sector=sector, watchlist_only=args.watchlist)


if __name__ == "__main__":
    main()
