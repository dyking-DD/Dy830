#!/usr/bin/env python3
"""
马克·米勒维尼 SEPA策略扫描器
严格按照《股票魔法师》标准筛选

用法:
    python3 scripts/scan_minervini.py [--watchlist] [--limit N] [--min-score 60]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from datetime import datetime
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from strategies.minervini_sepa import MinerviniSEPAScreener, MinerviniSEPAStrategy
from utils.akshare_fetcher import AkShareFetcher
from execution.notifier import NotificationManager


def load_watchlist(watchlist_file: str = "config/watchlist.txt") -> List[str]:
    """加载自选列表"""
    if not os.path.exists(watchlist_file):
        return []
    
    symbols = []
    with open(watchlist_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            symbol = line.split()[0] if ' ' in line else line
            if symbol:
                symbols.append(symbol)
    return symbols


def format_result(result) -> str:
    """格式化筛选结果"""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"📊 {result.ts_code} {result.name}")
    lines.append(f"{'='*60}")
    
    if result.passed:
        lines.append(f"✅ 通过SEPA筛选 | 综合评分: {result.score:.1f}/100")
        lines.append("")
        lines.append("【基本面指标】")
        lines.append(f"  营收增长(YoY): {result.details.get('revenue_growth_yoy', 0)*100:.1f}% (要求>25%)")
        lines.append(f"  净利润增长(YoY): {result.details.get('profit_growth_yoy', 0)*100:.1f}% (要求>30%)")
        lines.append(f"  净利润增长(QoQ): {result.details.get('profit_growth_qoq', 0)*100:.1f}% (要求>0%)")
        lines.append(f"  ROE: {result.details.get('roe', 0)*100:.1f}% (要求>15%)")
        lines.append(f"  3年CAGR: {result.details.get('profit_cagr_3y', 0)*100:.1f}% (要求>20%)")
        lines.append("")
        lines.append("【技术面指标】")
        lines.append(f"  当前价格: ¥{result.details.get('price', 0):.2f}")
        lines.append(f"  MA50: ¥{result.details.get('ma50', 0):.2f}")
        lines.append(f"  MA150: ¥{result.details.get('ma150', 0):.2f}")
        lines.append(f"  10日均量: {result.details.get('vol_ma10', 0):.0f}")
        lines.append(f"  120日均量: {result.details.get('vol_ma120', 0):.0f}")
        lines.append(f"  成交量放大: {'是' if result.details.get('volume_expanding') else '否'}")
    else:
        lines.append(f"❌ 未通过: {result.fail_reason}")
    
    lines.append(f"{'='*60}\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='马克·米勒维尼 SEPA策略扫描器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SEPA筛选条件 (《股票魔法师》标准):
  1. 排除ST股票和次新股(<1年)
  2. 营收同比增长 > 25%
  3. 净利润同比增长 > 30% 且环比为正
  4. 股价 > MA50 且 > MA150
  5. 10日成交量 > 120日成交量
  6. ROE > 15%
  7. 3年净利润CAGR > 20%
        """
    )
    parser.add_argument('--watchlist', action='store_true',
                       help='只扫描自选列表(config/watchlist.txt)')
    parser.add_argument('--limit', type=int, default=100,
                       help='扫描股票数量上限')
    parser.add_argument('--min-score', type=float, default=60.0,
                       help='最低评分要求 (默认60)')
    parser.add_argument('--webhook', type=str,
                       help='飞书Webhook地址')
    parser.add_argument('--notify', action='store_true',
                       help='发送飞书通知')
    parser.add_argument('--sector', type=str, choices=['cyb', 'kcb', 'all'],
                       default='all', help='板块筛选')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🎯 马克·米勒维尼 SEPA策略扫描器")
    print("   (基于《股票魔法师》标准)")
    print("=" * 70)
    print()
    
    # 初始化
    screener = MinerviniSEPAScreener()
    strategy = MinerviniSEPAStrategy()
    fetcher = AkShareFetcher()
    
    webhook = args.webhook or os.environ.get('FEISHU_WEBHOOK', '')
    notifier = NotificationManager(webhook_url=webhook) if args.notify and webhook else None
    
    # 获取股票列表
    if args.watchlist:
        symbols = load_watchlist()
        print(f"📋 从自选列表加载 {len(symbols)} 只股票")
    else:
        print("📋 获取市场股票列表...")
        df = fetcher.get_stock_list()
        
        if args.sector == 'cyb':
            symbols = [s for s in df['ts_code'].tolist() if s.startswith('300')]
        elif args.sector == 'kcb':
            symbols = [s for s in df['ts_code'].tolist() if s.startswith('688')]
        else:
            symbols = df['ts_code'].tolist()
        
        symbols = symbols[:args.limit]
        print(f"📋 获取到 {len(symbols)} 只股票")
    
    print(f"🎯 开始SEPA筛选 (最低评分: {args.min_score})...")
    print("-" * 70)
    
    # 执行筛选
    passed_results, all_results = screener.screen_batch(
        symbols, 
        min_score=args.min_score
    )
    
    # 显示结果
    print(f"\n✅ SEPA筛选完成: {len(passed_results)}/{len(symbols)} 只股票通过")
    print()
    
    if passed_results:
        print("🏆 通过筛选的股票 (按评分排序):")
        print()
        
        for i, result in enumerate(passed_results[:10], 1):  # 显示前10只
            print(format_result(result))
            
            # 分析VCP形态
            symbol = result.ts_code.split('.')[0]
            df = fetcher.get_daily_data(symbol, start_date='20240901')
            if not df.empty and len(df) > 50:
                vcp = strategy.analyze_vcp_pattern(df)
                if vcp['is_vcp']:
                    print(f"  🔥 检测到VCP形态! 评分: {vcp['score']}")
                    print(f"     距52周高点: {vcp['price_vs_52w_high']:.1f}%")
        
        # 发送飞书通知
        if notifier:
            message = f"🎯 SEPA策略扫描完成\n\n"
            message += f"扫描范围: {len(symbols)}只股票\n"
            message += f"通过筛选: {len(passed_results)}只\n\n"
            message += "🏆 前5名:\n"
            for r in passed_results[:5]:
                message += f"• {r.ts_code} (评分{r.score:.0f})\n"
            
            notifier.send_daily_report(message, datetime.now())
            print("📱 飞书通知已发送")
    else:
        print("❌ 没有股票通过SEPA筛选")
        print()
        print("可能原因:")
        print("  - 当前市场环境不佳")
        print("  - 筛选条件过于严格")
        print("  - 数据获取不完整")
    
    # 保存详细报告
    report_file = f"logs/sepa_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    os.makedirs("logs", exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write("马克·米勒维尼 SEPA策略扫描报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"扫描股票: {len(symbols)}只\n")
        f.write(f"通过筛选: {len(passed_results)}只\n")
        f.write(f"最低评分: {args.min_score}\n")
        f.write("="*70 + "\n\n")
        
        for result in passed_results:
            f.write(format_result(result))
    
    print(f"📄 详细报告已保存: {report_file}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
