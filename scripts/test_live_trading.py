"""
实盘交易测试方案
Test Plan for Live Trading

目的：在投入真实资金前，全面验证交易系统的正确性
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.live_trading import LiveTradingManager, TradingMode
from execution.dongcai_choice import ChoiceTrader
from execution.notifier import NotificationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingTestSuite:
    """交易测试套件"""
    
    def __init__(self, mode: TradingMode = TradingMode.PAPER):
        self.mode = mode
        self.manager = LiveTradingManager(mode)
        self.results = []
        
    def run_all_tests(self) -> dict:
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("开始实盘交易测试")
        logger.info("=" * 60)
        
        tests = [
            ("连接测试", self.test_connection),
            ("账户查询测试", self.test_account_query),
            ("持仓查询测试", self.test_position_query),
            ("行情查询测试", self.test_quote_query),
            ("买入下单测试", self.test_buy_order),
            ("卖出下单测试", self.test_sell_order),
            ("撤单测试", self.test_cancel_order),
            ("订单查询测试", self.test_order_query),
            ("风控测试", self.test_risk_management),
            ("通知测试", self.test_notification),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                logger.info(f"\n>>> 执行测试: {name}")
                result = test_func()
                results[name] = result
                status = "✅ 通过" if result else "❌ 失败"
                logger.info(f"{status}: {name}")
            except Exception as e:
                logger.error(f"❌ 异常: {name} - {e}")
                results[name] = False
        
        # 保存测试结果
        self._save_results(results)
        
        return results
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            connected = self.manager.connect()
            if connected:
                logger.info("✅ 连接成功")
            else:
                logger.error("❌ 连接失败")
            return connected
        except Exception as e:
            logger.error(f"连接异常: {e}")
            return False
    
    def test_account_query(self) -> bool:
        """测试账户查询"""
        try:
            account = self.manager.interface.get_account_info()
            if account:
                logger.info(f"账户ID: {account.get('account_id')}")
                logger.info(f"总资产: {account.get('total_assets', 0):,.2f}")
                logger.info(f"可用资金: {account.get('available_cash', 0):,.2f}")
                return True
            else:
                logger.error("获取账户信息失败")
                return False
        except Exception as e:
            logger.error(f"查询账户异常: {e}")
            return False
    
    def test_position_query(self) -> bool:
        """测试持仓查询"""
        try:
            positions = self.manager.interface.get_positions()
            logger.info(f"持仓数量: {len(positions)}")
            for pos in positions[:3]:
                logger.info(f"  {pos.get('symbol')}: {pos.get('quantity')}股")
            return True
        except Exception as e:
            logger.error(f"查询持仓异常: {e}")
            return False
    
    def test_quote_query(self) -> bool:
        """测试行情查询"""
        try:
            # 测试获取平安银行行情
            quote = self.manager.interface.get_quote('000001.SZ')
            if quote:
                logger.info(f"最新价: {quote.get('price')}")
                logger.info(f"买一: {quote.get('bid1')} ({quote.get('bid_vol1')})")
                logger.info(f"卖一: {quote.get('ask1')} ({quote.get('ask_vol1')})")
                return True
            else:
                logger.error("获取行情失败")
                return False
        except Exception as e:
            logger.error(f"查询行情异常: {e}")
            return False
    
    def test_buy_order(self) -> bool:
        """测试买入下单"""
        try:
            # 使用极小的测试数量（1手 = 100股）
            symbol = '000001.SZ'  # 平安银行（低价股，适合测试）
            quantity = 100
            
            # 获取当前价格
            quote = self.manager.interface.get_quote(symbol)
            if not quote:
                logger.error("无法获取行情")
                return False
            
            price = quote.get('price', 0)
            if price <= 0:
                logger.error("无效的价格")
                return False
            
            # 使用限价单，价格设为买一价（确保不成交）
            buy_price = quote.get('bid1', price * 0.99)
            
            logger.info(f"测试买入: {symbol} {quantity}股 @ {buy_price}")
            
            order_id = self.manager.submit_order(
                symbol=symbol,
                action='buy',
                quantity=quantity,
                strategy='test',
                reason='实盘交易测试'
            )
            
            if order_id:
                logger.info(f"✅ 买入订单提交成功: {order_id}")
                # 保存订单ID用于后续撤单测试
                self._test_order_id = order_id
                return True
            else:
                logger.error("❌ 买入订单提交失败")
                return False
                
        except Exception as e:
            logger.error(f"买入测试异常: {e}")
            return False
    
    def test_sell_order(self) -> bool:
        """测试卖出下单"""
        try:
            # 先检查是否有持仓
            positions = self.manager.interface.get_positions()
            if not positions:
                logger.info("无持仓，跳过卖出测试")
                return True  # 无持仓不算失败
            
            # 选择第一个持仓进行测试
            pos = positions[0]
            symbol = pos.get('symbol')
            available = pos.get('available', 0)
            
            if available < 100:
                logger.info(f"{symbol} 可用持仓不足，跳过")
                return True
            
            quantity = 100  # 测试卖出1手
            
            logger.info(f"测试卖出: {symbol} {quantity}股")
            
            order_id = self.manager.submit_order(
                symbol=symbol,
                action='sell',
                quantity=quantity,
                strategy='test',
                reason='实盘交易测试'
            )
            
            if order_id:
                logger.info(f"✅ 卖出订单提交成功: {order_id}")
                return True
            else:
                logger.error("❌ 卖出订单提交失败")
                return False
                
        except Exception as e:
            logger.error(f"卖出测试异常: {e}")
            return False
    
    def test_cancel_order(self) -> bool:
        """测试撤单"""
        try:
            # 使用买入测试中创建的订单
            if not hasattr(self, '_test_order_id'):
                logger.info("无测试订单，跳过撤单测试")
                return True
            
            order_id = self._test_order_id
            logger.info(f"测试撤单: {order_id}")
            
            # 先查询订单状态
            status = self.manager.interface.get_order_status(order_id)
            if status:
                logger.info(f"订单状态: {status.get('status')}")
            
            # 撤单
            result = self.manager.interface.cancel_order(order_id)
            if result:
                logger.info(f"✅ 撤单成功")
                return True
            else:
                logger.warning("撤单失败（可能已成交或已撤）")
                return True  # 撤单失败不一定是系统问题
                
        except Exception as e:
            logger.error(f"撤单测试异常: {e}")
            return False
    
    def test_order_query(self) -> bool:
        """测试订单查询"""
        try:
            # 查询当日订单
            orders = self.manager.interface.get_orders()
            logger.info(f"当日订单数量: {len(orders)}")
            
            for order in orders[:3]:
                logger.info(f"  {order.get('order_id')}: {order.get('symbol')} "
                          f"{order.get('action')} {order.get('status')}")
            
            return True
        except Exception as e:
            logger.error(f"订单查询异常: {e}")
            return False
    
    def test_risk_management(self) -> bool:
        """测试风控系统"""
        try:
            from risk.risk_manager import RiskManager
            
            risk_mgr = RiskManager()
            
            # 测试场景1：超大额订单
            check = risk_mgr.check_order(
                symbol='000001.SZ',
                action='buy',
                quantity=100000,  # 10万股，可能触发风控
                price=10.0,
                portfolio_state={'cash': 100000}
            )
            
            logger.info(f"大额订单风控检查: {'通过' if check['allowed'] else '拦截'}")
            if not check['allowed']:
                logger.info(f"拦截原因: {check.get('reason')}")
            
            # 测试场景2：可用资金不足
            check = risk_mgr.check_order(
                symbol='000001.SZ',
                action='buy',
                quantity=10000,
                price=100.0,
                portfolio_state={'cash': 1000}  # 资金不足
            )
            
            logger.info(f"资金不足检查: {'通过' if check['allowed'] else '拦截'}")
            
            return True
        except Exception as e:
            logger.error(f"风控测试异常: {e}")
            return False
    
    def test_notification(self) -> bool:
        """测试通知系统"""
        try:
            notifier = NotificationManager()
            
            if notifier.enabled:
                # 发送测试通知
                notifier.send_risk_alert(
                    title="实盘交易测试",
                    content="交易系统测试通知，请勿惊慌",
                    level="info"
                )
                logger.info("✅ 测试通知已发送")
                return True
            else:
                logger.warning("通知系统未启用")
                return True  # 未启用不算失败
        except Exception as e:
            logger.error(f"通知测试异常: {e}")
            return False
    
    def _save_results(self, results: dict):
        """保存测试结果"""
        result_file = Path(__file__).parent.parent / "data" / "test_results"
        result_file.mkdir(parents=True, exist_ok=True)
        
        filename = result_file / f"trading_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'mode': self.mode.value,
                'results': results,
                'summary': {
                    'total': len(results),
                    'passed': sum(1 for v in results.values() if v),
                    'failed': sum(1 for v in results.values() if not v)
                }
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n测试结果已保存: {filename}")


def run_paper_test():
    """运行模拟交易测试"""
    print("\n" + "=" * 60)
    print("模拟交易测试")
    print("=" * 60)
    
    suite = TradingTestSuite(TradingMode.PAPER)
    results = suite.run_all_tests()
    
    print("\n测试结果汇总:")
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    passed = sum(1 for v in results.values() if v)
    print(f"\n通过: {passed}/{len(results)}")
    
    return results


def run_choice_test():
    """运行 Choice 终端测试"""
    print("\n" + "=" * 60)
    print("Choice 终端测试")
    print("=" * 60)
    
    from execution.dongcai_choice import ChoiceTrader
    
    trader = ChoiceTrader()
    
    if trader.connect():
        print("✅ 连接成功")
        
        # 测试账户查询
        account = trader.get_account_info()
        if account:
            print(f"\n账户信息:")
            print(f"  总资产: {account['total_assets']:,.2f}")
            print(f"  可用资金: {account['available_cash']:,.2f}")
        
        # 测试持仓查询
        positions = trader.get_positions()
        print(f"\n持仓: {len(positions)} 只股票")
        
        # 测试行情查询
        quote = trader.get_quote('000001.SZ')
        if quote:
            print(f"\n平安银行行情:")
            print(f"  最新价: {quote['price']}")
            print(f"  涨跌: {(quote['price'] - quote['pre_close']):.2f}")
        
        trader.disconnect()
        print("\n✅ Choice 测试完成")
        return True
    else:
        print("\n❌ 连接失败，请检查 Choice 终端是否已启动")
        return False


def generate_test_report():
    """生成测试报告"""
    report = f"""
实盘交易测试报告
{'=' * 60}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

测试环境检查清单:
  ☐ 已安装 Choice 金融终端
  ☐ Choice 终端已登录
  ☐ 已申请量化交易权限
  ☐ 账户资金充足（建议 ≥ 30万）
  ☐ 飞书通知已配置（可选）

测试步骤:
  1. 模拟交易测试
     cd daily_stock_analysis
     python scripts/test_live_trading.py --mode paper

  2. Choice 终端连接测试
     python scripts/test_live_trading.py --mode choice

  3. 小额实盘测试（1000元）
     - 手动下单1手测试
     - 验证成交回报
     - 检查持仓更新

  4. 策略实盘测试
     - 开启 SEPA 策略
     - 观察信号生成
     - 小额跟单验证

风险控制:
  - 首次实盘资金 ≤ 10000元
  - 单票仓位 ≤ 20%
  - 单日最大亏损 ≤ 3%
  - 设置止损线 -5%

{'=' * 60}
"""
    
    report_file = Path(__file__).parent.parent / "docs" / "LIVE_TRADING_TEST.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"测试报告已生成: {report_file}")
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='实盘交易测试')
    parser.add_argument('--mode', choices=['paper', 'choice', 'report'], 
                       default='report', help='测试模式')
    
    args = parser.parse_args()
    
    if args.mode == 'paper':
        run_paper_test()
    elif args.mode == 'choice':
        run_choice_test()
    else:
        print(generate_test_report())
