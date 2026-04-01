"""
回测结果可视化模块
生成图表和报告
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class BacktestVisualizer:
    """回测结果可视化器"""
    
    def __init__(self, results: dict):
        """
        Args:
            results: 回测结果字典
        """
        self.results = results
        self.df = pd.DataFrame(results['daily_stats'])
        self.df['date'] = pd.to_datetime(self.df['date'])
        
    def plot_equity_curve(self, output_path: str = None):
        """绘制权益曲线"""
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # 权益曲线
        ax1 = axes[0]
        ax1.plot(self.df['date'], self.df['total_value'], label='Portfolio', linewidth=1.5)
        ax1.axhline(y=self.results['initial_capital'], color='gray', linestyle='--', alpha=0.5)
        ax1.set_ylabel('Total Value (CNY)')
        ax1.set_title(f"Backtest Results - {self.results['strategy']}\n" +
                      f"Total Return: {self.results['total_return']*100:.2f}%, " +
                      f"Sharpe: {self.results['sharpe_ratio']:.2f}, " +
                      f"Max DD: {self.results['max_drawdown']*100:.2f}%")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 回撤曲线
        ax2 = axes[1]
        self.df['cummax'] = self.df['total_value'].cummax()
        self.df['drawdown'] = (self.df['total_value'] - self.df['cummax']) / self.df['cummax']
        ax2.fill_between(self.df['date'], self.df['drawdown'] * 100, 0, 
                          color='red', alpha=0.3, label='Drawdown')
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Date')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"权益曲线已保存: {output_path}")
        
        return fig
    
    def plot_trade_history(self, output_path: str = None):
        """绘制交易历史"""
        if not self.results['trades']:
            logger.warning("无交易记录")
            return None
        
        trades_df = pd.DataFrame(self.results['trades'])
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制价格曲线
        ax.plot(self.df['date'], self.df['total_value'], label='Portfolio', alpha=0.7)
        
        # 标记买卖点
        buys = trades_df[trades_df['action'] == 'buy']
        sells = trades_df[trades_df['action'] == 'sell']
        
        ax.scatter(buys['date'], [self.results['initial_capital']] * len(buys), 
                   marker='^', color='green', s=100, label='Buy', zorder=5)
        ax.scatter(sells['date'], [self.results['initial_capital']] * len(sells), 
                   marker='v', color='red', s=100, label='Sell', zorder=5)
        
        ax.set_ylabel('Total Value (CNY)')
        ax.set_title('Trade History')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"交易历史图已保存: {output_path}")
        
        return fig
    
    def generate_report(self, output_path: str = None) -> str:
        """生成文字报告"""
        report = f"""
{'='*60}
          BACKTEST PERFORMANCE REPORT
{'='*60}

Strategy:       {self.results['strategy']}
Test Period:    {self.df['date'].min().strftime('%Y-%m-%d')} to {self.df['date'].max().strftime('%Y-%m-%d')}
Initial Capital: ¥{self.results['initial_capital']:,.2f}
Final Value:     ¥{self.results['final_value']:,.2f}

{'-'*60}
                    RETURNS
{'-'*60}
Total Return:       {self.results['total_return']*100:+.2f}%
Annual Return:      {self.results['annual_return']*100:+.2f}%
Annual Volatility:  {self.results['annual_volatility']*100:.2f}%
Sharpe Ratio:       {self.results['sharpe_ratio']:.2f}
Max Drawdown:       {self.results['max_drawdown']*100:.2f}%

{'-'*60}
                    TRADES
{'-'*60}
Total Trades:       {self.results['total_trades']}
Win Rate:           {self.results['win_rate']*100:.1f}%
Profit/Loss Ratio:  {self.results['profit_loss_ratio']:.2f}
Total Commission:   ¥{self.results['total_commission']:.2f}
Total Tax:          ¥{self.results['total_tax']:.2f}

{'='*60}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}
"""
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"报告已保存: {output_path}")
        
        return report
    
    def generate_all(self, output_dir: str = "backtest/results"):
        """生成所有图表和报告"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        strategy_name = self.results['strategy']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成权益曲线
        self.plot_equity_curve(output_dir / f"{strategy_name}_equity_{timestamp}.png")
        
        # 生成交易历史图
        self.plot_trade_history(output_dir / f"{strategy_name}_trades_{timestamp}.png")
        
        # 生成文字报告
        report = self.generate_report(output_dir / f"{strategy_name}_report_{timestamp}.txt")
        print(report)
        
        logger.info(f"所有可视化文件已保存到: {output_dir}")


if __name__ == "__main__":
    # 测试可视化
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # 加载回测结果
    result_file = Path("backtest/results").glob("*.json")
    result_file = list(result_file)
    
    if result_file:
        with open(result_file[0], 'r') as f:
            results = json.load(f)
        
        viz = BacktestVisualizer(results)
        viz.generate_all()
    else:
        print("没有找到回测结果文件")
