#!/usr/bin/env python3
"""
创业板+科创板扫描器 - CYB+KCB Scanner

快捷扫描创业板(300xxx)和科创板(688xxx)股票
自动合并结果并发送通知

用法:
    python3 scripts/scan_cyb_kcb.py [--date YYYY-MM-DD] [--limit N]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from scripts.daily_scanner import DailyScanner
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='创业板+科创板扫描器')
    parser.add_argument('--date', type=str, help='扫描日期 (YYYY-MM-DD)，默认今天')
    parser.add_argument('--limit', type=int, default=1500, help='每板块限制数量')
    parser.add_argument('--webhook', type=str, help='飞书机器人Webhook地址')
    
    args = parser.parse_args()
    
    # 解析日期
    if args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        date = datetime.now()
    
    # 获取webhook
    webhook = args.webhook or os.environ.get('FEISHU_WEBHOOK', '')
    
    scanner = DailyScanner(webhook_url=webhook)
    
    logger.info("=" * 60)
    logger.info("创业板+科创板联合扫描")
    logger.info("=" * 60)
    
    # 扫描创业板
    logger.info("\n>>> 扫描创业板 (300xxx)")
    scanner.run(date, limit=args.limit, sector='cyb')
    
    # 扫描科创板
    logger.info("\n>>> 扫描科创板 (688xxx)")
    scanner.run(date, limit=args.limit, sector='kcb')
    
    logger.info("\n扫描完成！")


if __name__ == "__main__":
    main()
