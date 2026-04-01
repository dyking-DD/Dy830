#!/usr/bin/env python3
"""
🎯 Mac本地模拟交易系统
启动命令: python3 trading_server.py
然后在浏览器打开: http://localhost:8080
"""

import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from aiohttp import web
import aiohttp_cors

# ============ 数据模型 ============

@dataclass
class Position:
    """持仓"""
    ts_code: str
    name: str
    volume: int
    avg_cost: float
    current_price: float
    market_value: float
    pnl: float
    pnl_pct: float
    open_date: str

@dataclass  
class Trade:
    """交易记录"""
    trade_id: str
    ts_code: str
    name: str
    action: str  # BUY/SELL
    price: float
    volume: int
    amount: float
    fee: float
    timestamp: str
    pnl: float = 0

# 股票名称映射
STOCK_NAMES = {
    '600519.SH': '贵州茅台', '300750.SZ': '宁德时代', '000002.SZ': '万科A',
    '601318.SH': '中国平安', '000858.SZ': '五粮液', '002415.SZ': '海康威视',
    '002594.SZ': '比亚迪', '000333.SZ': '美的集团', '002714.SZ': '牧原股份',
    '600036.SH': '招商银行', '601012.SH': '隆基绿能', '000568.SZ': '泸州老窖',
    '002352.SZ': '顺丰控股', '601888.SH': '中国中免', '000001.SZ': '平安银行',
    '600276.SH': '恒瑞医药', '000063.SZ': '中兴通讯', '601398.SH': '工商银行',
    '601288.SH': '农业银行', '600028.SH': '中国石化',
}

# 基础价格（模拟用）
BASE_PRICES = {
    '600519.SH': 1680, '300750.SZ': 185, '000002.SZ': 15.2,
    '601318.SH': 45.8, '000858.SZ': 145, '002415.SZ': 32.6,
    '002594.SZ': 220, '000333.SZ': 58, '002714.SZ': 42,
    '600036.SH': 35, '601012.SH': 22, '000568.SZ': 168,
    '002352.SZ': 52, '601888.SH': 85, '000001.SZ': 10.5,
    '600276.SH': 48, '000063.SZ': 28, '601398.SH': 5.2,
    '601288.SH': 4.3, '600028.SH': 6.1,
}

class TradingSystem:
    """交易系统核心"""
    
    def __init__(self, data_file: str = 'trading_account.json'):
        self.data_file = data_file
        self.initial_capital = 1000000.0
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.commission_rate = 0.0003
        self.min_commission = 5.0
        self.tax_rate = 0.001
        
        self._load_data()
    
    def _load_data(self):
        """加载账户数据"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.initial_capital = data.get('initial_capital', 1000000.0)
                self.cash = data.get('cash', self.initial_capital)
                
                # 恢复持仓
                for pos_data in data.get('positions', []):
                    pos = Position(**pos_data)
                    self.positions[pos.ts_code] = pos
                
                # 恢复交易记录
                for trade_data in data.get('trades', []):
                    self.trades.append(Trade(**trade_data))
    
    def _save_data(self):
        """保存账户数据"""
        data = {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': [asdict(p) for p in self.positions.values()],
            'trades': [asdict(t) for t in self.trades[-100:]],
            'updated_at': datetime.now().isoformat()
        }
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def get_stock_name(self, ts_code: str) -> str:
        return STOCK_NAMES.get(ts_code, ts_code)
    
    def get_current_price(self, ts_code: str) -> float:
        """获取当前价格（模拟实时波动）"""
        base = BASE_PRICES.get(ts_code, 50.0)
        change = random.uniform(-0.005, 0.005)  # ±0.5% 波动
        return round(base * (1 + change), 2)
    
    def calculate_fees(self, amount: float, action: str) -> float:
        commission = max(amount * self.commission_rate, self.min_commission)
        tax = amount * self.tax_rate if action == 'SELL' else 0
        return round(commission + tax, 2)
    
    def buy(self, ts_code: str, volume: int) -> Dict:
        """买入股票"""
        if volume < 100 or volume % 100 != 0:
            return {'success': False, 'error': '数量必须是100的整数倍'}
        
        current_price = self.get_current_price(ts_code)
        amount = current_price * volume
        fee = self.calculate_fees(amount, 'BUY')
        total_cost = amount + fee
        
        if total_cost > self.cash:
            return {'success': False, 'error': f'资金不足 (需要¥{total_cost:,.2f}, 可用¥{self.cash:,.2f})'}
        
        self.cash -= total_cost
        name = self.get_stock_name(ts_code)
        
        if ts_code in self.positions:
            # 加仓
            pos = self.positions[ts_code]
            total_volume = pos.volume + volume
            total_cost_basis = pos.avg_cost * pos.volume + current_price * volume
            pos.avg_cost = round(total_cost_basis / total_volume, 2)
            pos.volume = total_volume
            pos.current_price = current_price
        else:
            # 新建仓
            self.positions[ts_code] = Position(
                ts_code=ts_code, name=name, volume=volume,
                avg_cost=current_price, current_price=current_price,
                market_value=amount, pnl=0, pnl_pct=0,
                open_date=datetime.now().strftime('%Y-%m-%d')
            )
        
        # 记录交易
        trade = Trade(
            trade_id=f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}",
            ts_code=ts_code, name=name, action='BUY',
            price=current_price, volume=volume, amount=amount,
            fee=fee, timestamp=datetime.now().isoformat()
        )
        self.trades.append(trade)
        self._save_data()
        
        return {
            'success': True,
            'trade': asdict(trade),
            'remaining_cash': self.cash
        }
    
    def sell(self, ts_code: str, volume: int) -> Dict:
        """卖出股票"""
        if ts_code not in self.positions:
            return {'success': False, 'error': f'未持有 {ts_code}'}
        
        pos = self.positions[ts_code]
        sell_volume = min(volume, pos.volume)
        
        if sell_volume < 100:
            return {'success': False, 'error': '卖出数量至少100股'}
        
        current_price = self.get_current_price(ts_code)
        amount = current_price * sell_volume
        fee = self.calculate_fees(amount, 'SELL')
        net_amount = amount - fee
        
        # 计算盈亏
        cost_basis = pos.avg_cost * sell_volume
        pnl = amount - cost_basis - fee
        pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
        
        self.cash += net_amount
        pos.volume -= sell_volume
        
        if pos.volume == 0:
            del self.positions[ts_code]
        else:
            pos.current_price = current_price
        
        # 记录交易
        trade = Trade(
            trade_id=f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}",
            ts_code=ts_code, name=pos.name, action='SELL',
            price=current_price, volume=sell_volume, amount=amount,
            fee=fee, timestamp=datetime.now().isoformat(),
            pnl=round(pnl, 2)
        )
        self.trades.append(trade)
        self._save_data()
        
        return {
            'success': True,
            'trade': asdict(trade),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'remaining_cash': self.cash
        }
    
    def update_prices(self):
        """更新所有持仓价格"""
        for ts_code, pos in self.positions.items():
            current_price = self.get_current_price(ts_code)
            pos.current_price = current_price
            pos.market_value = round(current_price * pos.volume, 2)
            pos.pnl = round((current_price - pos.avg_cost) * pos.volume, 2)
            pos.pnl_pct = round((current_price - pos.avg_cost) / pos.avg_cost * 100, 2)
    
    def get_portfolio(self) -> Dict:
        """获取投资组合数据"""
        self.update_prices()
        
        total_market_value = sum(p.market_value for p in self.positions.values())
        total_pnl = sum(p.pnl for p in self.positions.values())
        total_assets = self.cash + total_market_value
        
        return {
            'initial_capital': self.initial_capital,
            'total_assets': round(total_assets, 2),
            'cash': round(self.cash, 2),
            'market_value': round(total_market_value, 2),
            'total_pnl': round(total_pnl, 2),
            'total_return_pct': round((total_assets - self.initial_capital) / self.initial_capital * 100, 2),
            'daily_pnl': round(random.uniform(-5000, 8000), 2),
            'position_count': len(self.positions),
            'positions': [asdict(p) for p in self.positions.values()],
            'trades': [asdict(t) for t in self.trades[-20:][::-1]],
            'updated_at': datetime.now().isoformat()
        }

# ============ HTTP服务器 ============

class TradingServer:
    """交易HTTP服务器"""
    
    def __init__(self, trading_system: TradingSystem):
        self.trading = trading_system
        self.app = web.Application()
        self._setup_routes()
        self._setup_cors()
    
    def _setup_routes(self):
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/api/portfolio', self.portfolio_handler)
        self.app.router.add_post('/api/buy', self.buy_handler)
        self.app.router.add_post('/api/sell', self.sell_handler)
        self.app.router.add_get('/api/prices', self.prices_handler)
    
    def _setup_cors(self):
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def index_handler(self, request):
        """主页 - 返回交易界面HTML"""
        html_content = self._get_html_content()
        return web.Response(text=html_content, content_type='text/html')
    
    async def portfolio_handler(self, request):
        """获取投资组合数据"""
        portfolio = self.trading.get_portfolio()
        return web.json_response(portfolio)
    
    async def buy_handler(self, request):
        """买入股票"""
        try:
            data = await request.json()
            ts_code = data.get('ts_code')
            volume = int(data.get('volume', 0))
            
            if not ts_code or volume <= 0:
                return web.json_response({'success': False, 'error': '参数错误'})
            
            result = self.trading.buy(ts_code, volume)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({'success': False, 'error': str(e)})
    
    async def sell_handler(self, request):
        """卖出股票"""
        try:
            data = await request.json()
            ts_code = data.get('ts_code')
            volume = int(data.get('volume', 0))
            
            if not ts_code or volume <= 0:
                return web.json_response({'success': False, 'error': '参数错误'})
            
            result = self.trading.sell(ts_code, volume)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({'success': False, 'error': str(e)})
    
    async def prices_handler(self, request):
        """获取实时价格"""
        prices = {}
        for code in STOCK_NAMES.keys():
            prices[code] = {
                'price': self.trading.get_current_price(code),
                'name': STOCK_NAMES[code]
            }
        return web.json_response(prices)
    
    def _get_html_content(self) -> str:
        """获取HTML界面内容"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Mac模拟交易盘</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f1419 0%, #161b22 50%, #0d1117 100%);
            min-height: 100vh;
            color: #c9d1d9;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        /* 头部 */
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #30363d;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; background: linear-gradient(90deg, #58a6ff, #a371f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header .subtitle { color: #8b949e; font-size: 1rem; }
        
        /* 资产卡片 */
        .assets-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .asset-card {
            background: rgba(22, 27, 34, 0.8);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid #30363d;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .asset-card:hover { transform: translateY(-4px); border-color: #58a6ff; box-shadow: 0 8px 32px rgba(88, 166, 255, 0.1); }
        .asset-card .label { color: #8b949e; font-size: 0.9rem; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .asset-card .value { font-size: 1.9rem; font-weight: 700; color: #f0f6fc; }
        .asset-card .change { font-size: 0.95rem; margin-top: 6px; font-weight: 600; }
        .positive { color: #3fb950; }
        .negative { color: #f85149; }
        
        /* 图表区域 */
        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }
        @media (max-width: 1024px) { .charts-grid { grid-template-columns: 1fr; } }
        
        .chart-card {
            background: rgba(22, 27, 34, 0.8);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid #30363d;
        }
        .chart-card h3 { margin-bottom: 16px; font-size: 1.1rem; color: #f0f6fc; }
        
        /* 交易区 */
        .section {
            background: rgba(22, 27, 34, 0.8);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #30363d;
        }
        .section h2 { margin-bottom: 20px; font-size: 1.2rem; color: #f0f6fc; display: flex; align-items: center; gap: 8px; }
        
        /* 快速交易 */
        .quick-trade {
            display: grid;
            grid-template-columns: 2fr 1fr auto auto;
            gap: 12px;
            align-items: end;
        }
        @media (max-width: 768px) { .quick-trade { grid-template-columns: 1fr; } }
        
        select, input {
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px solid #30363d;
            background: #0d1117;
            color: #f0f6fc;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        select:focus, input:focus { border-color: #58a6ff; }
        
        .btn {
            padding: 14px 28px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .btn:active { transform: translateY(0); }
        .btn-buy { background: linear-gradient(135deg, #238636, #2ea043); color: white; }
        .btn-sell { background: linear-gradient(135deg, #da3633, #f85149); color: white; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        /* 表格 */
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 14px 12px; text-align: left; border-bottom: 1px solid #21262d; }
        th { color: #8b949e; font-weight: 500; font-size: 0.85rem; text-transform: uppercase; }
        td { font-size: 0.95rem; color: #c9d1d9; }
        tr:hover { background: rgba(48, 54, 61, 0.3); }
        
        /* Toast 提示 */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 12px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            transform: translateX(400px);
            transition: transform 0.3s ease;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .toast.show { transform: translateX(0); }
        .toast.success { background: linear-gradient(135deg, #238636, #2ea043); }
        .toast.error { background: linear-gradient(135deg, #da3633, #f85149); }
        .toast.info { background: linear-gradient(135deg, #1f6feb, #58a6ff); }
        
        /* 加载动画 */
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        /* 实时价格标签 */
        .price-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .price-up { background: rgba(47, 129, 83, 0.2); color: #3fb950; }
        .price-down { background: rgba(248, 81, 73, 0.2); color: #f85149; }
        
        /* 状态指示器 */
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            color: #8b949e;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #3fb950;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Mac模拟交易盘</h1>
            <div class="subtitle">
                <span class="status-indicator"><span class="status-dot"></span> 系统在线</span>
                · 初始资金 ¥1,000,000 · 本地数据自动保存
            </div>
        </div>
        
        <!-- 资产概览 -->
        <div class="assets-grid">
            <div class="asset-card">
                <div class="label">💰 总资产</div>
                <div class="value" id="totalAssets">--</div>
                <div class="change" id="totalReturn">--</div>
            </div>
            <div class="asset-card">
                <div class="label">💵 可用现金</div>
                <div class="value" id="cash">--</div>
            </div>
            <div class="asset-card">
                <div class="label">📈 持仓市值</div>
                <div class="value" id="marketValue">--</div>
            </div>
            <div class="asset-card">
                <div class="label">📊 浮动盈亏</div>
                <div class="value" id="totalPnl">--</div>
            </div>
        </div>
        
        <!-- 图表区域 -->
        <div class="charts-grid">
            <div class="chart-card">
                <h3>📈 资金曲线</h3>
                <canvas id="equityChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>📦 持仓分布</h3>
                <canvas id="positionChart"></canvas>
            </div>
        </div>
        
        <!-- 快速交易 -->
        <div class="section">
            <h2>⚡ 快速交易</h2>
            <div class="quick-trade">
                <select id="stockSelect">
                    <option value="">选择股票...</option>
                </select>
                <input type="number" id="tradeVolume" placeholder="数量 (100的倍数)" min="100" step="100">
                <button class="btn btn-buy" onclick="executeTrade('buy')" id="buyBtn">
                    <span>🟢 买入</span>
                </button>
                <button class="btn btn-sell" onclick="executeTrade('sell')" id="sellBtn">
                    <span>🔴 卖出</span>
                </button>
            </div>
        </div>
        
        <!-- 持仓明细 -->
        <div class="section">
            <h2>📋 持仓明细</h2>
            <table>
                <thead>
                    <tr>
                        <th>股票</th>
                        <th>持仓</th>
                        <th>成本</th>
                        <th>现价</th>
                        <th>市值</th>
                        <th>盈亏</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="positionsTable">
                    <tr><td colspan="7" style="text-align:center;color:#666;">加载中...</td></tr>
                </tbody>
            </table>
        </div>
        
        <!-- 最近交易 -->
        <div class="section">
            <h2>📝 最近交易记录</h2>
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>股票</th>
                        <th>操作</th>
                        <th>价格</th>
                        <th>数量</th>
                        <th>金额</th>
                        <th>手续费</th>
                    </tr>
                </thead>
                <tbody id="tradesTable">
                    <tr><td colspan="7" style="text-align:center;color:#666;">暂无交易记录</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        // 股票列表
        const STOCKS = {
            '600519.SH': '贵州茅台', '300750.SZ': '宁德时代', '000002.SZ': '万科A',
            '601318.SH': '中国平安', '000858.SZ': '五粮液', '002415.SZ': '海康威视',
            '002594.SZ': '比亚迪', '000333.SZ': '美的集团', '002714.SZ': '牧原股份',
            '600036.SH': '招商银行', '601012.SH': '隆基绿能', '000568.SZ': '泸州老窖',
            '002352.SZ': '顺丰控股', '601888.SH': '中国中免', '000001.SZ': '平安银行',
            '600276.SH': '恒瑞医药', '000063.SZ': '中兴通讯', '601398.SH': '工商银行',
            '601288.SH': '农业银行', '600028.SH': '中国石化',
        };
        
        let portfolio = null;
        let equityChart = null;
        let positionChart = null;
        
        // 初始化
        function init() {
            // 填充股票选择器
            const select = document.getElementById('stockSelect');
            for (const [code, name] of Object.entries(STOCKS)) {
                const option = document.createElement('option');
                option.value = code;
                option.textContent = `${code} ${name}`;
                select.appendChild(option);
            }
            
            // 加载数据
            loadPortfolio();
            
            // 定时刷新
            setInterval(loadPortfolio, 5000);
        }
        
        // 加载投资组合数据
        async function loadPortfolio() {
            try {
                const response = await fetch('/api/portfolio');
                portfolio = await response.json();
                updateUI(portfolio);
            } catch (error) {
                showToast('数据加载失败: ' + error.message, 'error');
            }
        }
        
        // 更新界面
        function updateUI(data) {
            // 资产卡片
            document.getElementById('totalAssets').textContent = formatMoney(data.total_assets);
            document.getElementById('cash').textContent = formatMoney(data.cash);
            document.getElementById('marketValue').textContent = formatMoney(data.market_value);
            document.getElementById('totalPnl').textContent = formatMoney(data.total_pnl, true);
            document.getElementById('totalPnl').className = data.total_pnl >= 0 ? 'value positive' : 'value negative';
            
            const returnEl = document.getElementById('totalReturn');
            returnEl.textContent = `${data.total_return_pct >= 0 ? '+' : ''}${data.total_return_pct}%`;
            returnEl.className = data.total_return_pct >= 0 ? 'change positive' : 'change negative';
            
            // 持仓表格
            updatePositionsTable(data.positions);
            
            // 交易记录
            updateTradesTable(data.trades);
            
            // 图表
            updateCharts(data);
        }
        
        // 更新持仓表格
        function updatePositionsTable(positions) {
            const tbody = document.getElementById('positionsTable');
            if (!positions || positions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#666;">暂无持仓</td></tr>';
                return;
            }
            
            tbody.innerHTML = positions.map(p => `
                <tr>
                    <td><strong>${p.name}</strong><br><small style="color:#666;">${p.ts_code}</small></td>
                    <td>${p.volume.toLocaleString()}</td>
                    <td>¥${p.avg_cost.toFixed(2)}</td>
                    <td><span class="price-tag ${p.pnl >= 0 ? 'price-up' : 'price-down'}">¥${p.current_price.toFixed(2)}</span></td>
                    <td>¥${p.market_value.toLocaleString()}</td>
                    <td class="${p.pnl >= 0 ? 'positive' : 'negative'}">${p.pnl >= 0 ? '+' : ''}¥${p.pnl.toLocaleString()}</td>
                    <td><button class="btn btn-sell" onclick="quickSell('${p.ts_code}', ${p.volume})" style="padding:8px 16px;font-size:0.85rem;">卖出</button></td>
                </tr>
            `).join('');
        }
        
        // 更新交易记录表格
        function updateTradesTable(trades) {
            const tbody = document.getElementById('tradesTable');
            if (!trades || trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#666;">暂无交易记录</td></tr>';
                return;
            }
            
            tbody.innerHTML = trades.slice(0, 10).map(t => {
                const time = new Date(t.timestamp).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
                return `
                    <tr>
                        <td>${time}</td>
                        <td>${t.name}</td>
                        <td class="${t.action === 'BUY' ? 'positive' : 'negative'}">${t.action === 'BUY' ? '🟢 买入' : '🔴 卖出'}</td>
                        <td>¥${t.price.toFixed(2)}</td>
                        <td>${t.volume.toLocaleString()}</td>
                        <td>¥${t.amount.toLocaleString()}</td>
                        <td>¥${t.fee.toFixed(2)}</td>
                    </tr>
                `;
            }).join('');
        }
        
        // 更新图表
        function updateCharts(data) {
            // 资金曲线（模拟历史数据）
            const ctx1 = document.getElementById('equityChart').getContext('2d');
            if (equityChart) equityChart.destroy();
            
            const labels = [];
            const equityData = [];
            let equity = data.initial_capital;
            
            for (let i = 30; i >= 0; i--) {
                const date = new Date();
                date.setDate(date.getDate() - i);
                labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
                
                // 模拟历史曲线，最后一天是实际值
                if (i === 0) {
                    equityData.push(data.total_assets);
                } else {
                    equity = equity * (1 + (Math.random() - 0.4) * 0.02);
                    equityData.push(equity);
                }
            }
            
            equityChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '总资产',
                        data: equityData,
                        borderColor: '#3fb950',
                        backgroundColor: 'rgba(63, 185, 80, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            grid: { color: '#21262d' },
                            ticks: { color: '#8b949e', callback: v => '¥' + (v/10000).toFixed(0) + '万' }
                        },
                        x: { grid: { display: false }, ticks: { color: '#8b949e', maxTicksLimit: 6 } }
                    }
                }
            });
            
            // 持仓分布饼图
            const ctx2 = document.getElementById('positionChart').getContext('2d');
            if (positionChart) positionChart.destroy();
            
            if (data.positions && data.positions.length > 0) {
                positionChart = new Chart(ctx2, {
                    type: 'doughnut',
                    data: {
                        labels: data.positions.map(p => p.name),
                        datasets: [{
                            data: data.positions.map(p => p.market_value),
                            backgroundColor: ['#58a6ff', '#a371f7', '#3fb950', '#f85149', '#d29922', '#f0883e']
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { position: 'right', labels: { color: '#c9d1d9' } }
                        }
                    }
                });
            }
        }
        
        // 执行交易
        async function executeTrade(action) {
            const stock = document.getElementById('stockSelect').value;
            const volume = parseInt(document.getElementById('tradeVolume').value);
            
            if (!stock) { showToast('请选择股票', 'error'); return; }
            if (!volume || volume < 100 || volume % 100 !== 0) {
                showToast('请输入有效的数量（100的整数倍）', 'error'); return;
            }
            
            const btn = document.getElementById(action + 'Btn');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div>';
            
            try {
                const response = await fetch(`/api/${action}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ts_code: stock, volume: volume })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`${action === 'buy' ? '买入' : '卖出'}成功！`, 'success');
                    document.getElementById('tradeVolume').value = '';
                    loadPortfolio();
                } else {
                    showToast(result.error || '交易失败', 'error');
                }
            } catch (error) {
                showToast('交易请求失败: ' + error.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<span>${action === 'buy' ? '🟢 买入' : '🔴 卖出'}</span>`;
            }
        }
        
        // 快速卖出
        function quickSell(stockCode, maxVolume) {
            document.getElementById('stockSelect').value = stockCode;
            document.getElementById('tradeVolume').value = maxVolume;
            document.getElementById('tradeVolume').focus();
            showToast(`已选择 ${STOCKS[stockCode]}，输入数量后点击卖出`, 'info');
        }
        
        // 格式化金额
        function formatMoney(value, showSign = false) {
            if (value === undefined || value === null) return '--';
            const sign = showSign && value > 0 ? '+' : '';
            return sign + '¥' + value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        
        // Toast 提示
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = `toast ${type}`;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
        
        // 启动
        init();
    </script>
</body>
</html>'''
    
    def run(self, host='0.0.0.0', port=8080):
        """启动服务器"""
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🎯 Mac模拟交易盘                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║   启动成功！请在浏览器打开:                                   ║
║                                                              ║
║   ➜ http://localhost:{port}                                    ║
║                                                              ║
║   功能：                                                     ║
║   • 实时资金曲线 + 持仓分布图表                              ║
║   • 买入/卖出股票（100股倍数）                               ║
║   • 持仓明细 + 交易记录                                      ║
║   • 数据自动保存到 trading_account.json                      ║
║                                                              ║
║   快捷键：                                                   ║
║   • Cmd+W 关闭窗口                                           ║
║   • Cmd+R 刷新数据                                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
        web.run_app(self.app, host=host, port=port)


# ============ 主程序 ============

if __name__ == '__main__':
    # 创建交易系统
    trading_system = TradingSystem()
    
    # 创建并启动服务器
    server = TradingServer(trading_system)
    server.run(port=8080)
