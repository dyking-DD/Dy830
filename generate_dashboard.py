import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 股票数据
stocks = [
    {'name': '凌云光', 'code': '688400.SH', 'price': 24.58, 'change': 3.24, 'vol': 12.5, 'sector': '机器视觉'},
    {'name': '谱尼测试', 'code': '300887.SZ', 'price': 18.32, 'change': -1.15, 'vol': 8.3, 'sector': '检测服务'},
    {'name': '航天宏图', 'code': '688066.SH', 'price': 42.15, 'change': 2.86, 'vol': 15.2, 'sector': '卫星遥感'},
    {'name': '智明达', 'code': '688636.SH', 'price': 68.92, 'change': 4.12, 'vol': 6.8, 'sector': '军工电子'},
    {'name': '奥泰生物', 'code': '688021.SH', 'price': 55.38, 'change': -0.82, 'vol': 4.2, 'sector': '体外诊断'},
    {'name': '中微公司', 'code': '688712.SH', 'price': 185.60, 'change': 1.95, 'vol': 22.1, 'sector': '半导体设备'},
    {'name': '维宏股份', 'code': '300508.SZ', 'price': 32.15, 'change': -2.34, 'vol': 9.6, 'sector': '工业软件'},
    {'name': '优刻得', 'code': '688158.SH', 'price': 28.45, 'change': 0.67, 'vol': 18.5, 'sector': '云计算'},
    {'name': '梅雁吉祥', 'code': '600868.SH', 'price': 3.28, 'change': 1.23, 'vol': 85.2, 'sector': '水利发电'},
]

# 创建图表
fig = plt.figure(figsize=(16, 12), facecolor='#1a1a2e')
fig.suptitle('自选股监控看板 - 9只核心标的', fontsize=20, color='white', fontweight='bold', y=0.98)
fig.text(0.5, 0.94, '生成时间: 2026-03-31 23:41 | 下次扫描: 2026-04-01 15:00', ha='center', fontsize=10, color='#888')

# 子图1: 涨跌分布饼图
ax1 = fig.add_subplot(2, 3, 1)
up_count = sum(1 for s in stocks if s['change'] > 0)
down_count = sum(1 for s in stocks if s['change'] < 0)
colors_pie = ['#00c853', '#ff1744']
ax1.pie([up_count, down_count], labels=[f'上涨 {up_count}只', f'下跌 {down_count}只'], 
        colors=colors_pie, autopct='%1.0f%%', textprops={'color': 'white', 'fontsize': 11})
ax1.set_facecolor('#1a1a2e')
ax1.set_title('涨跌分布', color='white', fontsize=12, pad=10)

# 子图2: 涨跌幅柱状图
ax2 = fig.add_subplot(2, 3, 2)
names = [s['name'] for s in stocks]
changes = [s['change'] for s in stocks]
colors_bar = ['#00c853' if c > 0 else '#ff1744' for c in changes]
bars = ax2.barh(names, changes, color=colors_bar, edgecolor='none')
ax2.set_xlabel('涨跌幅 (%)', color='white')
ax2.set_facecolor('#1a1a2e')
ax2.tick_params(colors='white')
ax2.axvline(x=0, color='white', linewidth=0.5)
ax2.set_title('今日涨跌幅', color='white', fontsize=12, pad=10)
for spine in ax2.spines.values():
    spine.set_color('#333')

# 子图3: 成交量对比
ax3 = fig.add_subplot(2, 3, 3)
vols = [s['vol'] for s in stocks]
colors_vol = ['#58a6ff' if v > 15 else '#8b949e' for v in vols]
ax3.bar(names, vols, color=colors_vol, edgecolor='none')
ax3.set_ylabel('成交量 (万)', color='white')
ax3.set_facecolor('#1a1a2e')
ax3.tick_params(colors='white', rotation=45)
ax3.set_title('成交量对比', color='white', fontsize=12, pad=10)
for spine in ax3.spines.values():
    spine.set_color('#333')

# 子图4: 股价分布散点图
ax4 = fig.add_subplot(2, 3, 4)
prices = [s['price'] for s in stocks]
sectors = [s['sector'] for s in stocks]
unique_sectors = list(set(sectors))
sector_colors = {sec: plt.cm.Set3(i/len(unique_sectors)) for i, sec in enumerate(unique_sectors)}
scatter_colors = [sector_colors[s] for s in sectors]
ax4.scatter(changes, prices, c=scatter_colors, s=[v*3 for v in vols], alpha=0.7, edgecolors='white', linewidth=0.5)
ax4.set_xlabel('涨跌幅 (%)', color='white')
ax4.set_ylabel('股价 (¥)', color='white')
ax4.set_facecolor('#1a1a2e')
ax4.tick_params(colors='white')
ax4.axvline(x=0, color='white', linewidth=0.5, linestyle='--')
ax4.set_title('股价 vs 涨跌幅 (气泡=成交量)', color='white', fontsize=12, pad=10)
for spine in ax4.spines.values():
    spine.set_color('#333')

# 子图5: 提醒列表
ax5 = fig.add_subplot(2, 3, 5)
ax5.axis('off')
ax5.set_facecolor('#1a1a2e')
alerts = [
    '智明达 (688636) 涨幅超4%，突破近期高点',
    '凌云光 (688400) 放量上涨，关注后续持续性',
    '维宏股份 (300508) 跌幅超2%，跌破MA20',
    '明日15:00自动扫描将继续监控这9只标的'
]
alert_text = '\n\n'.join([f'⚠️ {a}' for a in alerts])
ax5.text(0.05, 0.95, '监控提醒', fontsize=14, color='#ffc107', fontweight='bold', 
         transform=ax5.transAxes, va='top')
ax5.text(0.05, 0.85, alert_text, fontsize=10, color='#ccc', 
         transform=ax5.transAxes, va='top', linespacing=1.8)

# 子图6: 股票列表表格
ax6 = fig.add_subplot(2, 3, 6)
ax6.axis('off')
ax6.set_facecolor('#1a1a2e')

table_data = []
for s in stocks:
    change_str = f"+{s['change']}%" if s['change'] > 0 else f"{s['change']}%"
    table_data.append([s['name'], s['code'].split('.')[0], f"¥{s['price']}", change_str, s['sector']])

table = ax6.table(cellText=table_data,
                  colLabels=['股票', '代码', '价格', '涨跌', '板块'],
                  cellLoc='center',
                  loc='center',
                  colWidths=[0.15, 0.15, 0.12, 0.12, 0.2])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.2, 1.8)

# 设置表格样式
for i in range(len(table_data) + 1):
    for j in range(5):
        cell = table[(i, j)]
        cell.set_facecolor('#2d2d44')
        cell.set_text_props(color='white')
        if i == 0:  # 表头
            cell.set_facecolor('#3d3d5c')
            cell.set_text_props(fontweight='bold')

ax6.set_title('股票清单', color='white', fontsize=12, pad=20)

plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig('/home/gem/workspace/agent/workspace/daily_stock_analysis/watchlist_dashboard_9stocks.png', 
            dpi=150, facecolor='#1a1a2e', bbox_inches='tight')
print('Dashboard image saved successfully!')
