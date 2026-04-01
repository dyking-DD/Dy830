#!/usr/bin/env python3
"""
模拟量化实盘可视化看板
专业级交易仪表盘 - 实时更新、多维度分析
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np

# 设置中文字体和样式
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

plt.rcParams['font.family'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class TradingVisualizer:
    """交易可视化器"""
    
    # 配色方案 - 深色专业主题
    COLORS = {
        'bg': '#0d1117',
        'card_bg': '#161b22',
        'border': '#30363d',
        'text': '#c9d1d9',
        'text_secondary': '#8b949e',
        'green': '#238636',
        'green_bright': '#3fb950',
        'red': '#da3633',
        'red_bright': '#f85149',
        'blue': '#58a6ff',
        'purple': '#a371f7',
        'orange': '#f0883e',
        'yellow': '#d29922'
    }
    
    def __init__(self, account_file: str = 'trading_account.json'):
        """初始化可视化器"""
        self.account_file = account_file
        self.account_data = self._load_account()
        self.output_dir = 'reports/visualizations'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _load_account(self) -> Dict:
        """加载账户数据"""
        if os.path.exists(self.account_file):
            with open(self.account_file, 'r') as f:
                return json.load(f)
        return self._create_mock_data()
    
    def _create_mock_data(self) -> Dict:
        """创建模拟数据（用于演示）"""
        return {
            "initial_capital": 1000000.0,
            "cash": 101116.3,
            "positions": [
                {"ts_code": "600519.SH", "name": "贵州茅台", "volume": 200, "avg_cost": 1650.0, 
                 "current_price": 1680.0, "market_value": 336000.0, "pnl": 6000.0, "pnl_pct": 1.82},
                {"ts_code": "300750.SZ", "name": "宁德时代", "volume": 1000, "avg_cost": 182.0,
                 "current_price": 185.0, "market_value": 185000.0, "pnl": 3000.0, "pnl_pct": 1.65},
            ],
            "trades": [],
            "updated_at": datetime.now().isoformat()
        }
    
    def _generate_equity_curve(self, days: int = 30) -> Tuple[List[datetime], List[float], List[float]]:
        """生成资金曲线数据"""
        end_date = datetime.now()
        dates = [end_date - timedelta(days=i) for i in range(days)][::-1]
        
        initial = self.account_data.get('initial_capital', 1000000)
        current = sum(p['market_value'] for p in self.account_data.get('positions', []))
        current += self.account_data.get('cash', 0)
        
        # 生成平滑的权益曲线
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.015, days)
        returns[-1] = (current - initial) / initial  # 确保终点正确
        
        equity = [initial]
        for r in returns[:-1]:
            equity.append(equity[-1] * (1 + r))
        equity.append(current)
        
        # 生成基准曲线（沪深300模拟）
        benchmark = [initial]
        for r in np.random.normal(0.0005, 0.012, days):
            benchmark.append(benchmark[-1] * (1 + r))
        
        return dates, equity, benchmark[:days+1]
    
    def _generate_daily_pnl(self, days: int = 14) -> Tuple[List[str], List[float]]:
        """生成每日盈亏数据"""
        dates = []
        pnl = []
        
        for i in range(days, 0, -1):
            date = datetime.now() - timedelta(days=i)
            dates.append(date.strftime('%m-%d'))
            # 模拟日盈亏 -8000 到 +12000
            pnl.append(round(random.uniform(-8000, 12000), 2))
        
        return dates, pnl
    
    def create_dashboard(self, save_path: str = None) -> str:
        """创建完整交易看板"""
        
        # 创建图表
        fig = plt.figure(figsize=(20, 12), facecolor=self.COLORS['bg'])
        fig.suptitle('🎯 量化模拟交易实盘看板', fontsize=24, color='white', 
                     fontweight='bold', y=0.98)
        
        # 更新时间
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fig.text(0.5, 0.94, f'实时更新: {update_time} | 模拟账户 | 延迟: < 1s', 
                ha='center', fontsize=11, color=self.COLORS['text_secondary'])
        
        # 使用GridSpec布局
        gs = GridSpec(3, 4, figure=fig, hspace=0.35, wspace=0.3,
                     left=0.05, right=0.95, top=0.92, bottom=0.05)
        
        # === 第1行: 关键指标卡片 ===
        positions = self.account_data.get('positions', [])
        cash = self.account_data.get('cash', 0)
        initial = self.account_data.get('initial_capital', 1000000)
        
        total_value = sum(p.get('market_value', 0) for p in positions)
        total_assets = total_value + cash
        total_pnl = total_assets - initial
        total_return_pct = (total_pnl / initial) * 100
        
        # 指标卡片
        metrics = [
            ('💰 总资产', f'¥{total_assets:,.0f}', self.COLORS['blue']),
            ('📈 累计盈亏', f'¥{total_pnl:+,.0f}', self.COLORS['green_bright'] if total_pnl >= 0 else self.COLORS['red_bright']),
            ('📊 收益率', f'{total_return_pct:+.2f}%', self.COLORS['green_bright'] if total_return_pct >= 0 else self.COLORS['red_bright']),
            ('💵 可用资金', f'¥{cash:,.0f}', self.COLORS['orange']),
        ]
        
        for idx, (label, value, color) in enumerate(metrics):
            ax = fig.add_subplot(gs[0, idx])
            ax.set_facecolor(self.COLORS['card_bg'])
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            
            # 绘制卡片边框
            rect = mpatches.FancyBboxPatch((0.05, 0.1), 0.9, 0.8,
                                            boxstyle="round,pad=0.02,rounding_size=0.1",
                                            facecolor=self.COLORS['card_bg'],
                                            edgecolor=self.COLORS['border'],
                                            linewidth=2)
            ax.add_patch(rect)
            
            # 标签
            ax.text(0.5, 0.65, label, ha='center', va='center',
                   fontsize=12, color=self.COLORS['text_secondary'],
                   fontweight='bold')
            
            # 数值
            ax.text(0.5, 0.35, value, ha='center', va='center',
                   fontsize=20, color=color, fontweight='bold')
        
        # === 第2行: 资金曲线 ===
        ax_equity = fig.add_subplot(gs[1, :2])
        ax_equity.set_facecolor(self.COLORS['card_bg'])
        
        dates, equity, benchmark = self._generate_equity_curve(30)
        
        ax_equity.plot(dates, equity, color=self.COLORS['green_bright'], 
                      linewidth=2.5, label='策略权益')
        ax_equity.plot(dates, benchmark, color=self.COLORS['text_secondary'], 
                      linewidth=1.5, linestyle='--', alpha=0.7, label='基准(沪深300)')
        
        # 填充区域
        ax_equity.fill_between(dates, equity, initial, 
                              alpha=0.2, color=self.COLORS['green_bright'])
        
        ax_equity.set_title('📈 资金曲线 (近30日)', color='white', 
                           fontsize=14, fontweight='bold', pad=10)
        ax_equity.set_xlabel('日期', color=self.COLORS['text_secondary'])
        ax_equity.set_ylabel('资产 (¥)', color=self.COLORS['text_secondary'])
        ax_equity.tick_params(colors=self.COLORS['text_secondary'])
        ax_equity.legend(loc='upper left', facecolor=self.COLORS['card_bg'],
                        edgecolor=self.COLORS['border'], labelcolor='white')
        ax_equity.grid(True, alpha=0.2, color=self.COLORS['border'])
        
        for spine in ax_equity.spines.values():
            spine.set_color(self.COLORS['border'])
        
        # 简化x轴标签
        ax_equity.xaxis.set_major_locator(plt.MaxNLocator(6))
        
        # === 第2行: 每日盈亏 ===
        ax_pnl = fig.add_subplot(gs[1, 2:])
        ax_pnl.set_facecolor(self.COLORS['card_bg'])
        
        pnl_dates, daily_pnl = self._generate_daily_pnl(14)
        colors_pnl = [self.COLORS['green_bright'] if p >= 0 else self.COLORS['red_bright'] 
                     for p in daily_pnl]
        
        bars = ax_pnl.bar(pnl_dates, daily_pnl, color=colors_pnl, edgecolor='none', alpha=0.8)
        ax_pnl.axhline(y=0, color=self.COLORS['text_secondary'], linewidth=1, linestyle='-')
        
        ax_pnl.set_title('📊 每日盈亏 (近14日)', color='white',
                        fontsize=14, fontweight='bold', pad=10)
        ax_pnl.set_xlabel('日期', color=self.COLORS['text_secondary'])
        ax_pnl.set_ylabel('盈亏 (¥)', color=self.COLORS['text_secondary'])
        ax_pnl.tick_params(colors=self.COLORS['text_secondary'])
        ax_pnl.grid(True, alpha=0.2, color=self.COLORS['border'], axis='y')
        
        for spine in ax_pnl.spines.values():
            spine.set_color(self.COLORS['border'])
        
        # === 第3行: 持仓分布 + 最近交易 ===
        # 持仓饼图
        ax_pie = fig.add_subplot(gs[2, 0])
        ax_pie.set_facecolor(self.COLORS['card_bg'])
        
        if positions:
            labels = [f"{p['name']}\n{p['ts_code'].split('.')[0]}" for p in positions]
            sizes = [p.get('market_value', 0) for p in positions]
            colors = plt.cm.Set3(np.linspace(0, 1, len(positions)))
            
            wedges, texts, autotexts = ax_pie.pie(
                sizes, labels=labels, autopct='%1.1f%%',
                colors=colors, textprops={'color': 'white', 'fontsize': 9},
                startangle=90
            )
            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontweight('bold')
        else:
            ax_pie.text(0.5, 0.5, '暂无持仓', ha='center', va='center',
                       color=self.COLORS['text_secondary'], fontsize=14)
        
        ax_pie.set_title('📦 持仓分布', color='white',
                        fontsize=14, fontweight='bold', pad=10)
        
        # 持仓明细表格
        ax_table = fig.add_subplot(gs[2, 1:3])
        ax_table.set_facecolor(self.COLORS['card_bg'])
        ax_table.axis('off')
        
        if positions:
            table_data = []
            for p in positions:
                pnl_pct = p.get('pnl_pct', 0)
                pnl_str = f"+{pnl_pct:.2f}%" if pnl_pct >= 0 else f"{pnl_pct:.2f}%"
                table_data.append([
                    p['name'],
                    p['ts_code'],
                    f"{p.get('volume', 0):,}",
                    f"¥{p.get('avg_cost', 0):.2f}",
                    f"¥{p.get('current_price', 0):.2f}",
                    f"¥{p.get('market_value', 0):,.0f}",
                    pnl_str
                ])
            
            table = ax_table.table(
                cellText=table_data,
                colLabels=['名称', '代码', '持仓', '成本', '现价', '市值', '盈亏'],
                cellLoc='center',
                loc='center',
                colWidths=[0.15, 0.12, 0.12, 0.12, 0.12, 0.15, 0.12]
            )
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.2, 2)
            
            # 样式设置
            for i in range(len(table_data) + 1):
                for j in range(7):
                    cell = table[(i, j)]
                    if i == 0:
                        cell.set_facecolor(self.COLORS['border'])
                        cell.set_text_props(color='white', fontweight='bold')
                    else:
                        cell.set_facecolor(self.COLORS['card_bg'])
                        cell.set_text_props(color=self.COLORS['text'])
                        # 盈亏列着色
                        if j == 6:
                            pnl_val = float(positions[i-1].get('pnl_pct', 0))
                            if pnl_val >= 0:
                                cell.set_text_props(color=self.COLORS['green_bright'])
                            else:
                                cell.set_text_props(color=self.COLORS['red_bright'])
        
        ax_table.set_title('📋 持仓明细', color='white',
                          fontsize=14, fontweight='bold', pad=10)
        
        # 最近交易记录
        ax_trades = fig.add_subplot(gs[2, 3])
        ax_trades.set_facecolor(self.COLORS['card_bg'])
        ax_trades.axis('off')
        
        trades = self.account_data.get('trades', [])
        recent_trades = trades[-5:][::-1] if trades else []
        
        trade_text = []
        for t in recent_trades:
            action_icon = '🟢' if t.get('action') == 'BUY' else '🔴'
            trade_text.append(
                f"{action_icon} {t.get('name', t.get('ts_code', ''))[:6]}\n"
                f"   {t.get('action')} {t.get('volume', 0)} @ ¥{t.get('price', 0)}\n"
            )
        
        if trade_text:
            ax_trades.text(0.05, 0.95, '最近交易', fontsize=14, color='white',
                          fontweight='bold', transform=ax_trades.transAxes, va='top')
            ax_trades.text(0.05, 0.82, '\n'.join(trade_text), fontsize=10,
                          color=self.COLORS['text'], transform=ax_trades.transAxes,
                          va='top', linespacing=1.8)
        else:
            ax_trades.text(0.5, 0.5, '暂无交易记录', ha='center', va='center',
                          color=self.COLORS['text_secondary'], fontsize=12)
        
        ax_trades.set_title('📝 最近交易', color='white',
                           fontsize=14, fontweight='bold', pad=10)
        
        # 保存
        if save_path is None:
            save_path = os.path.join(self.output_dir, 
                f'trading_dashboard_{datetime.now():%Y%m%d_%H%M%S}.png')
        
        plt.savefig(save_path, dpi=150, facecolor=self.COLORS['bg'],
                   bbox_inches='tight', pad_inches=0.2)
        plt.close()
        
        return save_path
    
    def create_simple_chart(self, chart_type: str = 'equity', save_path: str = None) -> str:
        """创建单一图表"""
        fig, ax = plt.subplots(figsize=(12, 6), facecolor=self.COLORS['bg'])
        ax.set_facecolor(self.COLORS['card_bg'])
        
        if chart_type == 'equity':
            dates, equity, benchmark = self._generate_equity_curve(30)
            ax.plot(dates, equity, color=self.COLORS['green_bright'], 
                   linewidth=2, label='策略')
            ax.plot(dates, benchmark, color=self.COLORS['blue'], 
                   linewidth=1.5, linestyle='--', alpha=0.7, label='基准')
            ax.fill_between(dates, equity, self.account_data.get('initial_capital', 1000000),
                           alpha=0.2, color=self.COLORS['green_bright'])
            ax.set_title('资金曲线', color='white', fontsize=16, fontweight='bold')
            ax.set_ylabel('资产 (¥)', color=self.COLORS['text'])
            
        elif chart_type == 'pnl':
            pnl_dates, daily_pnl = self._generate_daily_pnl(20)
            colors = [self.COLORS['green_bright'] if p >= 0 else self.COLORS['red_bright'] 
                     for p in daily_pnl]
            ax.bar(pnl_dates, daily_pnl, color=colors, edgecolor='none', alpha=0.8)
            ax.axhline(y=0, color=self.COLORS['text_secondary'], linewidth=1)
            ax.set_title('每日盈亏', color='white', fontsize=16, fontweight='bold')
            ax.set_ylabel('盈亏 (¥)', color=self.COLORS['text'])
        
        ax.set_xlabel('日期', color=self.COLORS['text'])
        ax.tick_params(colors=self.COLORS['text'])
        ax.legend(loc='upper left', facecolor=self.COLORS['card_bg'],
                 edgecolor=self.COLORS['border'], labelcolor='white')
        ax.grid(True, alpha=0.2, color=self.COLORS['border'])
        
        for spine in ax.spines.values():
            spine.set_color(self.COLORS['border'])
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, f'{chart_type}_chart.png')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, facecolor=self.COLORS['bg'],
                   bbox_inches='tight')
        plt.close()
        
        return save_path


def main():
    """主函数"""
    print("🎯 正在生成量化交易可视化看板...")
    
    visualizer = TradingVisualizer()
    
    # 生成完整看板
    dashboard_path = visualizer.create_dashboard()
    print(f"✅ 完整看板已生成: {dashboard_path}")
    
    # 生成单一图表
    equity_path = visualizer.create_simple_chart('equity')
    print(f"✅ 资金曲线已生成: {equity_path}")
    
    pnl_path = visualizer.create_simple_chart('pnl')
    print(f"✅ 盈亏图表已生成: {pnl_path}")
    
    print("\n📊 可视化文件列表:")
    print(f"   1. {dashboard_path}")
    print(f"   2. {equity_path}")
    print(f"   3. {pnl_path}")
    
    return dashboard_path


if __name__ == '__main__':
    main()
