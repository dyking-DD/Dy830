#!/usr/bin/env python3
"""
每日量化扫描 - 自动运行策略并推送飞书
Daily Quant Scan - Run strategies and send Feishu notifications

数据库集成版本 - 自动记录信号和绩效
"""
import sys
sys.path.insert(0, '/home/gem/workspace/agent/workspace/daily_stock_analysis')

import argparse
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
from dataclasses import dataclass
import logging

from config import Config
from strategies.portfolio import PortfolioManager
from strategies import (
    RSIStrategy, MACDStrategy, BollingerBandsStrategy,
    MomentumBreakoutStrategy as MomentumStrategy,
    CombinedStrategy,
    MarketTimingModule
)
from utils.akshare_fetcher import AkShareFetcher
from utils.trading_db import TradingDB, Trade, Position

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyQuantScanner:
    """每日量化扫描器"""
    
    def __init__(self, config_path: str = None, mode: str = 'paper', enable_db: bool = True):
        """
        初始化扫描器
        
        Args:
            config_path: 配置文件路径
            mode: 运行模式 ('paper'=模拟, 'live'=实盘)
            enable_db: 是否启用数据库记录
        """
        self.config = Config(config_path) if config_path else Config()
        self.fetcher = AkShareFetcher()
        self.portfolio = PortfolioManager(self.config.to_portfolio_config())
        self.market_timing = MarketTimingModule()
        self.mode = mode
        self.enable_db = enable_db
        
        # 初始化数据库
        if enable_db:
            try:
                self.db = TradingDB()
                logger.info("数据库连接成功")
            except Exception as e:
                logger.warning(f"数据库连接失败: {e}, 将使用内存模式")
                self.db = None
        else:
            self.db = None
        
        # 加载自选股
        self.watchlist = self._load_watchlist()
        
        # 模拟账户状态
        self.initial_capital = 100000  # 初始资金10万
        self.current_cash = self.initial_capital
        self.current_positions = {}  # {ts_code: {'volume': x, 'avg_cost': y}}
        self._load_portfolio_state()
        
        # 初始化策略
        self._init_strategies()
    
    def _init_strategies(self):
        """初始化策略并添加到组合管理器"""
        strategies = {
            'rsi': RSIStrategy(period=14, oversold=30, overbought=70),
            'macd': MACDStrategy(fast=12, slow=26, signal=9),
            'bollinger': BollingerBandsStrategy(period=20, std_dev=2.0),
            'momentum': MomentumStrategy(),
            'combined': CombinedStrategy()
        }
        
        for name, strategy in strategies.items():
            self.portfolio.add_strategy(name, strategy)
        
        self.portfolio.initialize()
        logger.info(f"已初始化 {len(strategies)} 个策略")
    
    def _load_watchlist(self) -> List[str]:
        """加载自选股列表"""
        watchlist_path = "config/watchlist.json"
        if os.path.exists(watchlist_path):
            with open(watchlist_path, 'r') as f:
                data = json.load(f)
                return data.get('stocks', [])
        return []
    
    def _load_portfolio_state(self):
        """从数据库加载持仓状态"""
        if not self.db:
            return
        
        try:
            positions = self.db.get_positions()
            for _, pos in positions.iterrows():
                self.current_positions[pos['ts_code']] = {
                    'volume': pos['volume'],
                    'avg_cost': pos['avg_cost'],
                    'strategy': pos.get('strategy', 'unknown')
                }
            
            # 计算当前现金
            total_position_value = 0
            for ts_code, pos in self.current_positions.items():
                try:
                    df = self.fetcher.get_daily_data(ts_code, 
                        start_date=(datetime.now() - timedelta(days=5)).strftime('%Y%m%d'),
                        end_date=datetime.now().strftime('%Y%m%d'))
                    if df is not None and not df.empty:
                        current_price = df['close'].iloc[-1]
                        total_position_value += current_price * pos['volume']
                except:
                    total_position_value += pos['avg_cost'] * pos['volume']
            
            # 获取最新账户快照
            summary = self.db.get_performance_summary()
            if summary and summary.get('total_assets', 0) > 0:
                self.current_cash = summary['cash_balance']
            else:
                self.current_cash = self.initial_capital - total_position_value
                
            logger.info(f"加载持仓: {len(self.current_positions)} 只, 现金: ¥{self.current_cash:,.2f}")
        except Exception as e:
            logger.warning(f"加载持仓状态失败: {e}")
    
    def add_to_watchlist(self, stocks: List[str]):
        """添加股票到自选股"""
        for stock in stocks:
            if stock not in self.watchlist:
                self.watchlist.append(stock)
                logger.info(f"添加自选股: {stock}")
        
        # 保存
        os.makedirs("config", exist_ok=True)
        with open("config/watchlist.json", 'w') as f:
            json.dump({'stocks': self.watchlist}, f, indent=2)
    
    def remove_from_watchlist(self, stocks: List[str]):
        """从自选股移除股票"""
        for stock in stocks:
            if stock in self.watchlist:
                self.watchlist.remove(stock)
                logger.info(f"移除自选股: {stock}")
        
        # 保存
        with open("config/watchlist.json", 'w') as f:
            json.dump({'stocks': self.watchlist}, f, indent=2)
    
    def get_stock_universe(self, include_watchlist: bool = True) -> List[str]:
        """获取股票池"""
        stocks = set()
        
        # 添加自选股
        if include_watchlist:
            stocks.update(self.watchlist)
        
        # 获取A股全市场 (限制数量避免API限制)
        try:
            import akshare as ak
            # 获取沪深A股
            stock_zh = ak.stock_zh_a_spot_em()
            # 选取市值前50的股票 + 自选股
            top_stocks = stock_zh.nlargest(50, '总市值')['代码'].tolist()
            stocks.update(top_stocks)
        except Exception as e:
            logger.warning(f"获取股票列表失败: {e}")
        
        return list(stocks)
    
    def _simulate_trade(self, signal):
        """
        模拟交易执行
        记录到数据库但不实际下单(实盘前测试用)
        """
        if not self.db:
            return None
        
        try:
            ts_code = signal.ts_code
            action = signal.action
            price = signal.price if hasattr(signal, 'price') and signal.price else 0
            
            # 默认每单金额不超过总资金的10%
            max_position_value = self.initial_capital * 0.1
            
            if action == 'buy':
                # 检查是否已有持仓
                if ts_code in self.current_positions:
                    logger.info(f"已持有 {ts_code}，跳过买入")
                    return None
                
                # 计算可买数量(100股整数倍)
                max_shares = int(max_position_value / price / 100) * 100
                if max_shares < 100:
                    logger.warning(f"资金不足，无法买入 {ts_code}")
                    return None
                
                # 模拟成交
                volume = min(max_shares, 1000)  # 最多1000股
                cost = price * volume
                
                if cost > self.current_cash:
                    logger.warning(f"现金不足，无法买入 {ts_code}")
                    return None
                
                # 更新现金和持仓
                self.current_cash -= cost
                strategy_name = signal.reasons[0] if hasattr(signal, 'reasons') and signal.reasons else 'unknown'
                self.current_positions[ts_code] = {
                    'volume': volume,
                    'avg_cost': price,
                    'strategy': strategy_name
                }
                
                # 记录交易
                trade = Trade(
                    ts_code=ts_code,
                    trade_date=datetime.now().strftime('%Y-%m-%d'),
                    action='buy',
                    price=price,
                    volume=volume,
                    strategy=strategy_name,
                    confidence=signal.confidence if hasattr(signal, 'confidence') else 0.5,
                    notes=f"模拟买入 - 信号置信度{signal.confidence:.2f}" if hasattr(signal, 'confidence') else "模拟买入"
                )
                trade_id = self.db.record_trade(trade)
                
                # 更新持仓
                position = Position(
                    ts_code=ts_code,
                    volume=volume,
                    avg_cost=price,
                    current_price=price,
                    strategy=strategy_name,
                    open_date=datetime.now().strftime('%Y-%m-%d')
                )
                self.db.update_position(position)
                
                logger.info(f"模拟买入 {ts_code}: {volume}股 @ {price:.2f}, 花费{cost:.2f}")
                return trade_id
                
            elif action == 'sell':
                # 检查是否有持仓
                if ts_code not in self.current_positions:
                    logger.info(f"未持有 {ts_code}，跳过卖出")
                    return None
                
                pos = self.current_positions[ts_code]
                volume = pos['volume']
                avg_cost = pos['avg_cost']
                
                # 计算盈亏
                revenue = price * volume
                pnl = (price - avg_cost) * volume
                
                # 更新现金
                self.current_cash += revenue
                del self.current_positions[ts_code]
                
                # 记录交易
                trade = Trade(
                    ts_code=ts_code,
                    trade_date=datetime.now().strftime('%Y-%m-%d'),
                    action='sell',
                    price=price,
                    volume=volume,
                    strategy=pos.get('strategy', 'unknown'),
                    confidence=signal.confidence if hasattr(signal, 'confidence') else 0.5,
                    notes=f"模拟卖出 - 盈亏: {pnl:.2f}"
                )
                trade_id = self.db.record_trade(trade)
                
                # 清空持仓
                self.db.close_position(ts_code)
                
                logger.info(f"模拟卖出 {ts_code}: {volume}股 @ {price:.2f}, 收入{revenue:.2f}, 盈亏{pnl:.2f}")
                return trade_id
                
        except Exception as e:
            logger.error(f"模拟交易失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _record_account_snapshot(self):
        """记录账户快照"""
        if not self.db:
            return
        
        try:
            # 计算持仓市值
            position_value = 0
            for ts_code, pos in self.current_positions.items():
                # 获取最新价格
                try:
                    df = self.fetcher.get_daily_data(ts_code, 
                        start_date=(datetime.now() - timedelta(days=5)).strftime('%Y%m%d'),
                        end_date=datetime.now().strftime('%Y%m%d'))
                    if df is not None and not df.empty:
                        current_price = df['close'].iloc[-1]
                        position_value += current_price * pos['volume']
                        
                        # 更新持仓当前价格
                        position = Position(
                            ts_code=ts_code,
                            volume=pos['volume'],
                            avg_cost=pos['avg_cost'],
                            current_price=current_price,
                            strategy=pos.get('strategy'),
                            open_date=None
                        )
                        self.db.update_position(position)
                except Exception as e:
                    logger.warning(f"获取 {ts_code} 最新价格失败: {e}")
                    position_value += pos['avg_cost'] * pos['volume']
            
            total_assets = self.current_cash + position_value
            
            # 获取昨日总资产计算当日盈亏
            try:
                yesterday_assets = self.db.get_performance_summary()['total_assets']
                day_pnl = total_assets - yesterday_assets if yesterday_assets > 0 else 0
            except:
                day_pnl = 0
            
            self.db.record_snapshot(
                total_assets=total_assets,
                cash_balance=self.current_cash,
                position_value=position_value,
                day_pnl=day_pnl
            )
            
            logger.info(f"账户快照: 总资产={total_assets:.2f}, 现金={self.current_cash:.2f}, 持仓={position_value:.2f}")
            
        except Exception as e:
            logger.error(f"记录账户快照失败: {e}")
    
    def scan_stocks(self, stock_list: List[str] = None, include_watchlist: bool = True,
                    simulate_trades: bool = False) -> Dict:
        """扫描股票生成信号"""
        if stock_list is None:
            stock_list = self.get_stock_universe(include_watchlist=include_watchlist)
        
        logger.info(f"开始扫描 {len(stock_list)} 只股票...")
        
        # 获取市场择时信号
        market_signal = self.market_timing.analyze_market()
        logger.info(f"市场择时: {market_signal.trend}, 允许做多: {market_signal.allow_long}")
        
        # 获取数据并生成信号
        all_data = {}
        all_signals = []
        watchlist_signals = []
        executed_trades = []
        
        for ts_code in stock_list[:20]:  # 限制扫描数量避免API限制
            try:
                # 获取近60天数据
                end_date = datetime.now()
                start_date = end_date - timedelta(days=70)
                df = self.fetcher.get_daily_data(
                    ts_code,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
                if df is not None and len(df) >= 30:
                    all_data[ts_code] = df
                    
                    # 生成信号
                    signals = self.portfolio.voting_engine.aggregate_signals(df)
                    all_signals.extend(signals)
                    
                    # 记录自选股信号
                    if ts_code in self.watchlist and signals:
                        watchlist_signals.extend(signals)
                    
                    # 模拟交易(如果启用)
                    if simulate_trades and signals:
                        for signal in signals:
                            if signal.confidence >= 0.6:  # 高置信度信号才执行
                                trade_id = self._simulate_trade(signal)
                                if trade_id:
                                    executed_trades.append({
                                        'ts_code': ts_code,
                                        'action': signal.action,
                                        'trade_id': trade_id
                                    })
            except Exception as e:
                logger.warning(f"获取 {ts_code} 数据失败: {e}")
        
        # 排序并筛选
        all_signals.sort(key=lambda x: x.confidence, reverse=True)
        top_signals = all_signals[:self.portfolio.config.max_positions]
        
        # 自选股信号单独整理
        watchlist_signals.sort(key=lambda x: x.confidence, reverse=True)
        
        # 根据市场择时过滤
        if not market_signal.allow_long:
            logger.warning("市场状态不佳，过滤买入信号")
            top_signals = [s for s in top_signals if s.action != 'buy']
            watchlist_signals = [s for s in watchlist_signals if s.action != 'buy']
        
        # 记录账户快照
        if self.enable_db:
            self._record_account_snapshot()
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'market_trend': market_signal.trend,
            'market_allow_long': market_signal.allow_long,
            'total_scanned': len(stock_list),
            'total_signals': len(all_signals),
            'top_signals': top_signals,
            'watchlist_signals': watchlist_signals,
            'watchlist_count': len(self.watchlist),
            'portfolio_weights': self.portfolio.voting_engine.weights if self.portfolio.voting_engine else {},
            'executed_trades': executed_trades,
            'current_cash': self.current_cash,
            'current_positions': len(self.current_positions)
        }
    
    def format_report(self, result: Dict) -> str:
        """格式化报告"""
        lines = []
        lines.append("📊 每日量化扫描报告")
        lines.append(f"扫描日期: {result['date']}")
        lines.append(f"市场状态: {result['market_trend']} {'✅' if result['market_allow_long'] else '⚠️'}")
        lines.append(f"扫描股票: {result['total_scanned']} 只 (自选股 {result['watchlist_count']})")
        lines.append(f"生成信号: {result['total_signals']} 个")
        lines.append(f"模拟持仓: {result['current_positions']} 只, 现金: ¥{result['current_cash']:,.2f}")
        lines.append("")
        
        # 自选股信号单独展示
        if result['watchlist_signals']:
            lines.append(f"⭐ 自选股信号 ({len(result['watchlist_signals'])}):")
            for i, signal in enumerate(result['watchlist_signals'][:5], 1):
                emoji = "🟢" if signal.action == 'buy' else "🔴" if signal.action == 'sell' else "⚪"
                lines.append(f"{i}. {emoji} [{signal.action.upper()}] {signal.ts_code} (置信度: {signal.confidence:.2f})")
            lines.append("")
        
        # 已执行交易
        if result['executed_trades']:
            lines.append(f"💰 模拟交易执行 ({len(result['executed_trades'])}):")
            for trade in result['executed_trades'][:5]:
                emoji = "🟢" if trade['action'] == 'buy' else "🔴"
                lines.append(f"  {emoji} {trade['action'].upper()} {trade['ts_code']} (ID: {trade['trade_id']})")
            lines.append("")
        
        if result['top_signals']:
            lines.append(f"🎯 Top {len(result['top_signals'])} 信号:")
            lines.append("")
            
            for i, signal in enumerate(result['top_signals'], 1):
                emoji = "🟢" if signal.action == 'buy' else "🔴" if signal.action == 'sell' else "⚪"
                star = "⭐" if signal.ts_code in self.watchlist else "  "
                lines.append(f"{i}. {star} {emoji} [{signal.action.upper()}] {signal.ts_code}")
                lines.append(f"   置信度: {signal.confidence:.2f}")
                reasons = signal.reasons if hasattr(signal, 'reasons') else []
                lines.append(f"   原因: {', '.join(reasons[:2]) if reasons else 'N/A'}")
                lines.append("")
        else:
            lines.append("📝 今日无符合条件的信号")
        
        lines.append("---")
        lines.append("策略权重:")
        weights = result['portfolio_weights']
        for name, weight in weights.items():
            lines.append(f"  {name}: {weight:.2%}")
        
        # 添加数据库链接
        if self.enable_db:
            lines.append("")
            lines.append("📁 数据已记录到数据库，可执行以下命令查看:")
            lines.append("  python -c \"from utils.trading_db import TradingDB; db=TradingDB(); print(db.get_performance_summary())\"")
            lines.append("  python scripts/generate_report.py")
        
        return '\n'.join(lines)
    
    def save_report(self, content: str, date_str: str):
        """保存报告到文件"""
        report_dir = "/home/gem/workspace/agent/workspace/daily_stock_analysis/reports"
        os.makedirs(report_dir, exist_ok=True)
        report_file = f"{report_dir}/scan_{date_str}.txt"
        with open(report_file, 'w') as f:
            f.write(content)
        logger.info(f"报告已保存: {report_file}")
        return report_file
    
    def run(self, save_report_file: bool = True, include_watchlist: bool = True,
            simulate_trades: bool = False) -> Dict:
        """执行完整扫描流程"""
        logger.info("="*60)
        logger.info("启动每日量化扫描")
        logger.info(f"模式: {self.mode}, 数据库: {'启用' if self.enable_db else '禁用'}")
        logger.info("="*60)
        
        # 执行扫描
        result = self.scan_stocks(
            include_watchlist=include_watchlist,
            simulate_trades=simulate_trades
        )
        
        # 格式化报告
        report = self.format_report(result)
        logger.info("\n" + report)
        
        # 保存报告
        if save_report_file:
            self.save_report(report, result['date'])
        
        # 生成可视化报告(如果启用数据库)
        if self.enable_db and save_report_file:
            try:
                from scripts.generate_report import generate_performance_report
                report_path = generate_performance_report(
                    db_path='database/trading.db',
                    output_dir='reports'
                )
                logger.info(f"可视化报告已生成: {report_path}")
            except Exception as e:
                logger.warning(f"生成可视化报告失败: {e}")
        
        logger.info("扫描完成")
        return result


def main():
    parser = argparse.ArgumentParser(description='每日量化扫描')
    parser.add_argument('--no-watchlist', action='store_true',
                       help='不包含自选股扫描')
    parser.add_argument('--add-watchlist', nargs='+',
                       help='添加股票到自选股 (例如: 000001.SZ 600519.SH)')
    parser.add_argument('--remove-watchlist', nargs='+',
                       help='从自选股移除股票')
    parser.add_argument('--list-watchlist', action='store_true',
                       help='列出自选股')
    parser.add_argument('--no-db', action='store_true',
                       help='禁用数据库记录')
    parser.add_argument('--simulate', action='store_true',
                       help='启用模拟交易(根据信号自动执行模拟买卖)')
    parser.add_argument('--mode', default='paper', choices=['paper', 'live'],
                       help='交易模式: paper=模拟, live=实盘')
    
    args = parser.parse_args()
    
    scanner = DailyQuantScanner(
        mode=args.mode,
        enable_db=not args.no_db
    )
    
    # 管理自选股
    if args.add_watchlist:
        scanner.add_to_watchlist(args.add_watchlist)
        return 0
    
    if args.remove_watchlist:
        scanner.remove_from_watchlist(args.remove_watchlist)
        return 0
    
    if args.list_watchlist:
        print(f"自选股列表 ({len(scanner.watchlist)} 只):")
        for code in scanner.watchlist:
            print(f"  - {code}")
        return 0
    
    # 执行扫描
    result = scanner.run(
        include_watchlist=not args.no_watchlist,
        simulate_trades=args.simulate
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
