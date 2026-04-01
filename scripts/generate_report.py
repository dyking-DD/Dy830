#!/usr/bin/env python3
"""
策略绩效可视化报告生成器
使用 matplotlib 生成专业图表
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

def generate_performance_report(db_path='trading.db', output_dir='reports'):
    """生成策略绩效报告"""
    
    os.makedirs(output_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    
    # 创建综合报告图
    fig = plt.figure(figsize=(16, 12))
    
    # 1. 累计收益曲线
    ax1 = plt.subplot(2, 3, 1)
    df_snap = pd.read_sql('SELECT * FROM account_snapshot ORDER BY trade_date', conn)
    df_snap['trade_date'] = pd.to_datetime(df_snap['trade_date'])
    ax1.plot(df_snap['trade_date'], df_snap['cumulative_pnl'], 'g-', linewidth=2, marker='o')
    ax1.fill_between(df_snap['trade_date'], df_snap['cumulative_pnl'], alpha=0.3, color='green')
    ax1.set_title('Cumulative P&L', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('P&L (CNY)')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # 2. 每日盈亏
    ax2 = plt.subplot(2, 3, 2)
    colors = ['green' if x > 0 else 'red' for x in df_snap['day_pnl']]
    ax2.bar(df_snap['trade_date'], df_snap['day_pnl'], color=colors, alpha=0.7)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('Daily P&L', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('P&L (CNY)')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # 3. 资产配置饼图
    ax3 = plt.subplot(2, 3, 3)
    latest = df_snap.iloc[-1]
    sizes = [latest['cash_balance'], latest['position_value']]
    labels = [f'Cash\n¥{latest["cash_balance"]:,.0f}', f'Positions\n¥{latest["position_value"]:,.0f}']
    colors_pie = ['#3498db', '#e74c3c']
    explode = (0.05, 0)
    ax3.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', 
            startangle=90, explode=explode, shadow=True)
    ax3.set_title(f'Asset Allocation\nTotal: ¥{latest["total_assets"]:,.0f}', 
                  fontsize=12, fontweight='bold')
    
    # 4. 策略胜率对比
    ax4 = plt.subplot(2, 3, 4)
    df_perf = pd.read_sql('''
        SELECT strategy, 
               SUM(win_count) as wins, 
               SUM(loss_count) as losses,
               SUM(net_pnl) as total_pnl
        FROM strategy_performance 
        GROUP BY strategy
    ''', conn)
    
    x = range(len(df_perf))
    width = 0.35
    ax4.bar([i - width/2 for i in x], df_perf['wins'], width, label='Wins', color='green', alpha=0.7)
    ax4.bar([i + width/2 for i in x], df_perf['losses'], width, label='Losses', color='red', alpha=0.7)
    ax4.set_title('Strategy Win/Loss Count', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Strategy')
    ax4.set_ylabel('Count')
    ax4.set_xticks(x)
    ax4.set_xticklabels(df_perf['strategy'], rotation=45, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. 策略盈亏对比
    ax5 = plt.subplot(2, 3, 5)
    colors_bar = ['green' if x > 0 else 'red' for x in df_perf['total_pnl']]
    bars = ax5.bar(df_perf['strategy'], df_perf['total_pnl'], color=colors_bar, alpha=0.7)
    ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax5.set_title('Strategy P&L', fontsize=12, fontweight='bold')
    ax5.set_xlabel('Strategy')
    ax5.set_ylabel('P&L (CNY)')
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right')
    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'¥{height:,.0f}', ha='center', va='bottom' if height > 0 else 'top',
                fontsize=9)
    
    # 6. 关键指标摘要
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    total_trades = pd.read_sql('SELECT COUNT(*) as cnt FROM trades', conn).iloc[0]['cnt']
    win_trades = pd.read_sql("SELECT COUNT(*) as cnt FROM trades WHERE action='sell'", conn).iloc[0]['cnt']
    total_pnl = latest['cumulative_pnl']
    return_rate = (total_pnl / 100000) * 100
    
    summary_text = f"""
    ╔══════════════════════════════════╗
    ║     PERFORMANCE SUMMARY          ║
    ╠══════════════════════════════════╣
    ║  Total Trades:     {total_trades:>10}      ║
    ║  Closed Trades:    {win_trades:>10}      ║
    ║  Total P&L:        ¥{total_pnl:>10,.0f}      ║
    ║  Return Rate:      {return_rate:>10.2f}%      ║
    ║  Total Assets:     ¥{latest['total_assets']:>10,.0f}      ║
    ║  Cash:             ¥{latest['cash_balance']:>10,.0f}      ║
    ║  Positions:        ¥{latest['position_value']:>10,.0f}      ║
    ╚══════════════════════════════════╝
    """
    ax6.text(0.5, 0.5, summary_text, transform=ax6.transAxes,
             fontsize=11, verticalalignment='center', horizontalalignment='center',
             fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('Quant Trading Performance Report', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # 保存报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'{output_dir}/performance_report_{timestamp}.png'
    plt.savefig(report_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # 同时生成 CSV 数据文件
    df_snap.to_csv(f'{output_dir}/account_history.csv', index=False)
    df_perf.to_csv(f'{output_dir}/strategy_performance.csv', index=False)
    
    conn.close()
    
    return report_path

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    report_path = generate_performance_report()
    print(f"✅ 报告已生成: {report_path}")
