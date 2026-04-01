#!/usr/bin/env python3
"""
量化交易模拟视频可视化生成器 - 使用显式字体
生成动态视频展示：资产变化、交易点位、收益曲线、持仓变化
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import FancyBboxPatch, Circle
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties

# 显式加载中文字体
CHINESE_FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

# 颜色主题
COLORS = {
    'bg': '#0a0a0a',
    'grid': '#1a1a1a',
    'text': '#e0e0e0',
    'accent': '#00d4ff',
    'buy': '#00ff88',
    'sell': '#ff4444',
    'profit': '#00ff88',
    'loss': '#ff4444',
    'neutral': '#888888',
    'card_bg': '#1a1a2e',
    'gold': '#ffd700'
}

class TradingVideoGenerator:
    def __init__(self, trading_account_path: str, account_history_path: str = None):
        """初始化视频生成器"""
        self.chinese_font = FontProperties(fname=CHINESE_FONT_PATH)
        self.load_data(trading_account_path, account_history_path)
        self.setup_style()
        
    def load_data(self, account_path: str, history_path: str = None):
        """加载交易数据"""
        with open(account_path, 'r') as f:
            self.account_data = json.load(f)
        
        self.trades = self.account_data.get('trades', [])
        self.positions = self.account_data.get('positions', [])
        self.initial_capital = self.account_data.get('initial_capital', 1000000)
        
        self.history = None
        if history_path and Path(history_path).exists():
            self.history = pd.read_csv(history_path)
            self.history['trade_date'] = pd.to_datetime(self.history['trade_date'])
        
        self.build_timeline()
    
    def build_timeline(self):
        """构建交易时间线"""
        timeline = []
        current_positions = {}
        current_cash = self.initial_capital
        
        for trade in self.trades:
            ts_code = trade['ts_code']
            action = trade['action']
            volume = trade['volume']
            price = trade['price']
            amount = trade['amount']
            fee = trade['fee']
            timestamp = trade['timestamp']
            
            if action == 'BUY':
                current_cash -= (amount + fee)
                if ts_code in current_positions:
                    pos = current_positions[ts_code]
                    total_volume = pos['volume'] + volume
                    total_cost = pos['cost'] + amount
                    current_positions[ts_code] = {
                        'volume': total_volume,
                        'cost': total_cost,
                        'avg_price': total_cost / total_volume
                    }
                else:
                    current_positions[ts_code] = {
                        'volume': volume,
                        'cost': amount,
                        'avg_price': price
                    }
            else:  # SELL
                current_cash += (amount - fee)
                if ts_code in current_positions:
                    pos = current_positions[ts_code]
                    pos['volume'] -= volume
                    if pos['volume'] <= 0:
                        del current_positions[ts_code]
            
            position_value = sum(p['volume'] * p['avg_price'] for p in current_positions.values())
            total_assets = current_cash + position_value
            
            timeline.append({
                'timestamp': timestamp,
                'trade': trade,
                'cash': current_cash,
                'position_value': position_value,
                'total_assets': total_assets,
                'positions': current_positions.copy(),
                'position_count': len(current_positions)
            })
        
        self.timeline = timeline
        if timeline:
            self.max_assets = max(t['total_assets'] for t in timeline)
            self.min_assets = min(t['total_assets'] for t in timeline)
        else:
            self.max_assets = self.min_assets = self.initial_capital
        
    def setup_style(self):
        """设置可视化样式"""
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(16, 10), facecolor=COLORS['bg'])
        self.fig.suptitle('量化交易模拟可视化', fontsize=20, color=COLORS['gold'], 
                         fontweight='bold', y=0.98, fontproperties=self.chinese_font)
        
        gs = self.fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3, 
                                   left=0.05, right=0.95, top=0.93, bottom=0.05)
        
        self.ax_assets = self.fig.add_subplot(gs[0, :2])
        self.ax_assets.set_facecolor(COLORS['bg'])
        self.ax_assets.set_title('资产变化曲线', fontsize=14, color=COLORS['accent'], 
                                pad=10, fontproperties=self.chinese_font)
        
        self.ax_trades = self.fig.add_subplot(gs[0, 2])
        self.ax_trades.set_facecolor(COLORS['card_bg'])
        self.ax_trades.axis('off')
        self.ax_trades.set_title('最新交易', fontsize=14, color=COLORS['accent'], 
                                pad=10, fontproperties=self.chinese_font)
        
        self.ax_positions = self.fig.add_subplot(gs[1, 0])
        self.ax_positions.set_facecolor(COLORS['bg'])
        self.ax_positions.set_title('持仓分布', fontsize=14, color=COLORS['accent'], 
                                   pad=10, fontproperties=self.chinese_font)
        
        self.ax_metrics = self.fig.add_subplot(gs[1, 1])
        self.ax_metrics.set_facecolor(COLORS['card_bg'])
        self.ax_metrics.axis('off')
        self.ax_metrics.set_title('收益指标', fontsize=14, color=COLORS['accent'], 
                                 pad=10, fontproperties=self.chinese_font)
        
        self.ax_stats = self.fig.add_subplot(gs[1, 2])
        self.ax_stats.set_facecolor(COLORS['card_bg'])
        self.ax_stats.axis('off')
        self.ax_stats.set_title('交易统计', fontsize=14, color=COLORS['accent'], 
                               pad=10, fontproperties=self.chinese_font)
        
        self.ax_timeline = self.fig.add_subplot(gs[2, :])
        self.ax_timeline.set_facecolor(COLORS['bg'])
        self.ax_timeline.set_title('交易时间线', fontsize=14, color=COLORS['accent'], 
                                  pad=10, fontproperties=self.chinese_font)
        
    def format_money(self, amount):
        """格式化金额"""
        if amount >= 10000:
            return f'{amount/10000:.2f}万'
        return f'{amount:,.2f}'
    
    def update(self, frame):
        """更新动画帧"""
        if not self.timeline or frame >= len(self.timeline):
            return []
        
        data = self.timeline[frame]
        
        # 1. 更新资产曲线
        self.ax_assets.clear()
        self.ax_assets.set_facecolor(COLORS['bg'])
        
        dates = [datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00')) 
                for t in self.timeline[:frame+1]]
        assets = [t['total_assets'] for t in self.timeline[:frame+1]]
        
        self.ax_assets.plot(dates, assets, color=COLORS['accent'], linewidth=2)
        self.ax_assets.fill_between(dates, assets, self.initial_capital, 
                                    alpha=0.3, color=COLORS['accent'])
        self.ax_assets.axhline(y=self.initial_capital, color=COLORS['neutral'], 
                              linestyle='--', alpha=0.5, label='初始资金')
        
        if dates:
            self.ax_assets.scatter([dates[-1]], [assets[-1]], 
                                  color=COLORS['gold'], s=100, zorder=5)
        
        self.ax_assets.set_ylabel('资产总值', color=COLORS['text'], fontproperties=self.chinese_font)
        self.ax_assets.tick_params(colors=COLORS['text'])
        self.ax_assets.legend(loc='upper left', prop=self.chinese_font)
        self.ax_assets.grid(True, alpha=0.2, color=COLORS['grid'])
        
        # 2. 更新交易面板
        self.ax_trades.clear()
        self.ax_trades.set_facecolor(COLORS['card_bg'])
        self.ax_trades.axis('off')
        self.ax_trades.set_title('最新交易', fontsize=14, color=COLORS['accent'], 
                                pad=10, fontproperties=self.chinese_font)
        
        trade = data['trade']
        color = COLORS['buy'] if trade['action'] == 'BUY' else COLORS['sell']
        action_text = '买入' if trade['action'] == 'BUY' else '卖出'
        
        self.ax_trades.text(0.5, 0.8, action_text, ha='center', va='center',
                           fontsize=18, fontweight='bold', color=color,
                           transform=self.ax_trades.transAxes, fontproperties=self.chinese_font)
        self.ax_trades.text(0.5, 0.6, trade['name'], ha='center', va='center',
                           fontsize=14, color=COLORS['text'],
                           transform=self.ax_trades.transAxes, fontproperties=self.chinese_font)
        self.ax_trades.text(0.5, 0.45, trade['ts_code'], ha='center', va='center',
                           fontsize=10, color=COLORS['neutral'],
                           transform=self.ax_trades.transAxes)
        self.ax_trades.text(0.5, 0.25, f"{trade['volume']}股 @ ¥{trade['price']:.2f}", 
                           ha='center', va='center',
                           fontsize=12, color=COLORS['text'],
                           transform=self.ax_trades.transAxes, fontproperties=self.chinese_font)
        self.ax_trades.text(0.5, 0.1, f"金额: ¥{self.format_money(trade['amount'])}", 
                           ha='center', va='center',
                           fontsize=10, color=COLORS['neutral'],
                           transform=self.ax_trades.transAxes, fontproperties=self.chinese_font)
        
        # 3. 更新持仓分布
        self.ax_positions.clear()
        self.ax_positions.set_facecolor(COLORS['bg'])
        self.ax_positions.set_title('持仓分布', fontsize=14, color=COLORS['accent'], 
                                   pad=10, fontproperties=self.chinese_font)
        
        if data['positions']:
            positions = data['positions']
            labels = [f"{k.split('.')[0]}" for k in positions.keys()]
            sizes = [p['volume'] * p['avg_price'] for p in positions.values()]
            colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(sizes)))
            
            wedges, texts, autotexts = self.ax_positions.pie(
                sizes, labels=labels, colors=colors,
                autopct='%1.1f%%', startangle=90,
                textprops={'color': COLORS['text'], 'fontsize': 8}
            )
            for text in texts:
                text.set_fontproperties(self.chinese_font)
            for autotext in autotexts:
                autotext.set_fontproperties(self.chinese_font)
        else:
            self.ax_positions.text(0.5, 0.5, '无持仓', ha='center', va='center',
                                  fontsize=14, color=COLORS['neutral'],
                                  transform=self.ax_positions.transAxes, fontproperties=self.chinese_font)
        
        # 4. 更新收益指标
        self.ax_metrics.clear()
        self.ax_metrics.set_facecolor(COLORS['card_bg'])
        self.ax_metrics.axis('off')
        self.ax_metrics.set_title('收益指标', fontsize=14, color=COLORS['accent'], 
                                 pad=10, fontproperties=self.chinese_font)
        
        pnl = data['total_assets'] - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100
        color = COLORS['profit'] if pnl >= 0 else COLORS['loss']
        
        self.ax_metrics.text(0.5, 0.75, f"{pnl:+.0f}", ha='center', va='center',
                            fontsize=28, fontweight='bold', color=color,
                            transform=self.ax_metrics.transAxes)
        self.ax_metrics.text(0.5, 0.5, f"{pnl_pct:+.2f}%", ha='center', va='center',
                            fontsize=16, color=color,
                            transform=self.ax_metrics.transAxes)
        self.ax_metrics.text(0.5, 0.25, '累计盈亏', ha='center', va='center',
                            fontsize=10, color=COLORS['neutral'],
                            transform=self.ax_metrics.transAxes, fontproperties=self.chinese_font)
        
        # 5. 更新交易统计
        self.ax_stats.clear()
        self.ax_stats.set_facecolor(COLORS['card_bg'])
        self.ax_stats.axis('off')
        self.ax_stats.set_title('交易统计', fontsize=14, color=COLORS['accent'], 
                               pad=10, fontproperties=self.chinese_font)
        
        buy_count = sum(1 for t in self.timeline[:frame+1] if t['trade']['action'] == 'BUY')
        sell_count = frame + 1 - buy_count
        
        stats_text = f"总交易: {frame+1}\n买入: {buy_count}\n卖出: {sell_count}\n持仓: {data['position_count']}"
        self.ax_stats.text(0.5, 0.5, stats_text, ha='center', va='center',
                          fontsize=12, color=COLORS['text'],
                          transform=self.ax_stats.transAxes,
                          linespacing=1.5, fontproperties=self.chinese_font)
        
        # 6. 更新交易时间线
        self.ax_timeline.clear()
        self.ax_timeline.set_facecolor(COLORS['bg'])
        self.ax_timeline.set_title('交易时间线', fontsize=14, color=COLORS['accent'], 
                                  pad=10, fontproperties=self.chinese_font)
        
        for i, t in enumerate(self.timeline[:frame+1]):
            trade_time = datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00'))
            color = COLORS['buy'] if t['trade']['action'] == 'BUY' else COLORS['sell']
            marker = '^' if t['trade']['action'] == 'BUY' else 'v'
            
            self.ax_timeline.scatter(trade_time, i, c=color, s=100, marker=marker, zorder=3)
        
        self.ax_timeline.set_xlabel('时间', color=COLORS['text'], fontproperties=self.chinese_font)
        self.ax_timeline.set_ylabel('交易序号', color=COLORS['text'], fontproperties=self.chinese_font)
        self.ax_timeline.tick_params(colors=COLORS['text'])
        self.ax_timeline.grid(True, alpha=0.2, color=COLORS['grid'])
        
        # 添加图例
        buy_patch = mpatches.Patch(color=COLORS['buy'], label='买入')
        sell_patch = mpatches.Patch(color=COLORS['sell'], label='卖出')
        legend = self.ax_timeline.legend(handles=[buy_patch, sell_patch], loc='upper left')
        for text in legend.get_texts():
            text.set_fontproperties(self.chinese_font)
        
        # 更新窗口标题
        title = f'量化交易模拟可视化 | 交易 #{frame+1}/{len(self.timeline)} | 资产: ¥{self.format_money(data["total_assets"])}'
        self.fig.suptitle(title, fontsize=16, color=COLORS['gold'], 
                         fontweight='bold', y=0.98, fontproperties=self.chinese_font)
        
        return []
    
    def generate(self, output_path: str, fps: int = 2, dpi: int = 100):
        """生成视频"""
        if not self.timeline:
            print("没有交易数据，无法生成视频")
            return
        
        print(f"开始生成视频，共 {len(self.timeline)} 帧...")
        
        anim = animation.FuncAnimation(
            self.fig, self.update, frames=len(self.timeline),
            interval=1000//fps, blit=False, repeat=False
        )
        
        writer = animation.FFMpegWriter(fps=fps, metadata=dict(artist='Lobster Trader'),
                                       bitrate=5000)
        anim.save(output_path, writer=writer, dpi=dpi)
        
        print(f"视频已保存: {output_path}")
        plt.close()


def main():
    """主函数"""
    base_path = Path('/home/gem/workspace/agent/workspace/daily_stock_analysis')
    
    account_path = base_path / 'trading_account.json'
    history_path = base_path / 'reports' / 'account_history.csv'
    output_path = base_path / 'reports' / 'trading_simulation.mp4'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    generator = TradingVideoGenerator(str(account_path), str(history_path))
    generator.generate(str(output_path), fps=1, dpi=120)
    
    print(f"\n量化交易模拟视频已生成！")
    print(f"视频路径: {output_path}")
    print(f"交易笔数: {len(generator.trades)}")
    if generator.timeline:
        final_assets = generator.timeline[-1]['total_assets']
        pnl = final_assets - generator.initial_capital
        print(f"最终资产: ¥{generator.format_money(final_assets)}")
        print(f"累计盈亏: {pnl:+.0f} ({pnl/generator.initial_capital*100:+.2f}%)")
    else:
        print("最终资产: N/A")


if __name__ == '__main__':
    main()
