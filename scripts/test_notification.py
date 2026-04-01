#!/usr/bin/env python3
"""
测试飞书通知功能

用法:
    python3 scripts/test_notification.py
    python3 scripts/test_notification.py --webhook https://open.feishu.cn/...
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from execution.notifier import NotificationManager


def main():
    parser = argparse.ArgumentParser(description='测试飞书通知')
    parser.add_argument('--webhook', type=str, help='飞书Webhook地址')
    args = parser.parse_args()
    
    # 获取webhook
    webhook = args.webhook or os.environ.get('FEISHU_WEBHOOK', '')
    
    if not webhook:
        print("❌ 未配置Webhook地址")
        print("")
        print("配置方式：")
        print("1. 环境变量: export FEISHU_WEBHOOK=https://open.feishu.cn/...")
        print("2. 命令行: python3 scripts/test_notification.py --webhook https://...")
        print("3. 交互配置: bash scripts/setup_feishu.sh")
        return
    
    print("🦞 量化交易通知测试")
    print("=" * 50)
    print(f"Webhook: {webhook[:50]}...")
    print("")
    
    notifier = NotificationManager(webhook_url=webhook)
    
    # 测试1: 交易信号
    print("📤 测试1: 发送交易信号...")
    notifier.send_trade_alert(
        symbol="000001.SZ",
        action="buy",
        quantity=1000,
        price=10.5,
        reason="MA5金叉MA20"
    )
    print("   完成\n")
    
    # 测试2: 风控告警
    print("📤 测试2: 发送风控告警...")
    notifier.send_risk_alert(
        title="熔断触发",
        content="日内回撤超过5%，交易已暂停30分钟",
        level="warning"
    )
    print("   完成\n")
    
    # 测试3: 每日报告
    print("📤 测试3: 发送每日报告...")
    test_report = """
【账户概览】
初始资金: 100,000.00
当前现金: 90,020.55
总资产:   100,005.00
累计盈亏: +5.00 (+0.01%)
持仓数量: 1 只
现金比例: 90.0%

【持仓明细】
688710.SH: 151股 @ 66.06 (市值9,974.45)

【今日成交】 (1笔)
🟢 BUY 688710.SH 151股 @ 66.06
   原因: MA5上穿MA20金叉

【交易信号】 (2个)
- 688710.SH: 买入 (RSI超卖)
   ⚠️ 风控拦截: 交易间隔过短
"""
    notifier.send_daily_report(test_report)
    print("   完成\n")
    
    print("=" * 50)
    print("✅ 测试完成！请检查飞书群聊是否收到消息。")
    print("")
    print("如果未收到，请检查：")
    print("1. Webhook地址是否正确")
    print("2. 机器人在群聊中是否正常")
    print("3. 网络连接是否正常")


if __name__ == "__main__":
    main()
