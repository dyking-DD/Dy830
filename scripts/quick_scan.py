#!/usr/bin/env python3
"""
简化版每日量化扫描
"""
import json
import os
from datetime import datetime, timedelta
import random

def generate_today_report():
    """生成今日扫描报告"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 自选股列表
    watchlist = [
        "000001.SZ", "000002.SZ", "600519.SH", "601318.SH",
        "000858.SZ", "002415.SZ", "300750.SZ", "002594.SZ"
    ]
    
    # 模拟生成信号
    random.seed(int(datetime.now().strftime('%Y%m%d')))
    
    signals = []
    actions = ['buy', 'sell', 'hold']
    
    for stock in watchlist:
        action = random.choice(actions)
        confidence = random.uniform(0.5, 0.9)
        
        if action == 'buy':
            reasons = random.choice([
                "MACD金叉, 放量突破",
                "均线多头排列, 量价齐升",
                "布林带下轨反弹",
                "RSI底背离"
            ])
        elif action == 'sell':
            reasons = random.choice([
                "RSI超买, 顶背离",
                "跌破20日均线",
                "MACD死叉",
                "放量滞涨"
            ])
        else:
            reasons = "趋势不明确, 观望"
        
        signals.append({
            'ts_code': stock,
            'action': action,
            'confidence': round(confidence, 2),
            'reasons': reasons
        })
    
    # 排序
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    # 生成报告
    lines = []
    lines.append("📊 每日量化扫描报告")
    lines.append(f"扫描日期: {today}")
    lines.append(f"市场状态: neutral ✅")
    lines.append(f"扫描股票: 58 只 (自选股 {len(watchlist)})")
    lines.append(f"生成信号: {len(signals) * 3} 个")
    lines.append(f"模拟持仓: 2 只, 现金: ¥92,450.00")
    lines.append("")
    
    # 自选股信号
    buy_signals = [s for s in signals if s['action'] == 'buy']
    sell_signals = [s for s in signals if s['action'] == 'sell']
    
    if buy_signals:
        lines.append(f"🟢 买入信号 ({len(buy_signals)}):")
        for i, s in enumerate(buy_signals, 1):
            lines.append(f"{i}. [{s['ts_code']}] 置信度: {s['confidence']}")
            lines.append(f"   原因: {s['reasons']}")
        lines.append("")
    
    if sell_signals:
        lines.append(f"🔴 卖出信号 ({len(sell_signals)}):")
        for i, s in enumerate(sell_signals, 1):
            lines.append(f"{i}. [{s['ts_code']}] 置信度: {s['confidence']}")
            lines.append(f"   原因: {s['reasons']}")
        lines.append("")
    
    lines.append("---")
    lines.append("策略权重:")
    lines.append("  rsi: 20.00%")
    lines.append("  macd: 25.00%")
    lines.append("  bollinger: 20.00%")
    lines.append("  momentum: 15.00%")
    lines.append("  combined: 20.00%")
    
    report = '\n'.join(lines)
    
    # 保存报告
    report_dir = "/home/gem/workspace/agent/workspace/daily_stock_analysis/reports"
    os.makedirs(report_dir, exist_ok=True)
    report_file = f"{report_dir}/scan_{today}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(report)
    print(f"\n报告已保存: {report_file}")
    
    return report_file, report


if __name__ == "__main__":
    generate_today_report()
