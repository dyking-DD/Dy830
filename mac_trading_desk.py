#!/usr/bin/env python3
"""
Mac类实盘交易系统 - 专业级行情展示
实时K线、买卖盘口、持仓盈亏
"""

import json
import os
import random
import webbrowser
import threading
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class StockQuote:
    """股票行情"""
    ts_code: str
    name: str
    price: float
    open_price: float
    high: float
    low: float
    prev_close: float
    volume: int
    turnover: float
    bid1: float
    bid1_vol: int
    ask1: float
    ask1_vol: int
    bid2: float
    bid2_vol: int
    ask2: float
    ask2_vol: int
    bid3: float
    bid3_vol: int
    ask3: float
    ask3_vol: int
    change_pct: float
    timestamp: str


class RealtimeMarket:
    """实时行情模拟器"""
    
    BASE_PRICES = {
        '600519.SH': 1680.0, '300750.SZ': 185.0, '000002.SZ': 15.2,
        '601318.SH': 45.8, '000858.SZ': 145.0, '002415.SZ': 32.6,
        '002594.SZ': 220.0, '000333.SZ': 58.0, '002714.SZ': 42.0,
        '600036.SH': 35.0, '601012.SH': 22.0, '000568.SZ': 78.5,
        '002352.SZ': 38.0, '601888.SH': 68.0, '000001.SZ': 10.5,
    }
    
    NAMES = {
        '600519.SH': '贵州茅台', '300750.SZ': '宁德时代', '000002.SZ': '万科A',
        '601318.SH': '中国平安', '000858.SZ': '五粮液', '002415.SZ': '海康威视',
        '002594.SZ': '比亚迪', '000333.SZ': '美的集团', '002714.SZ': '牧原股份',
        '600036.SH': '招商银行', '601012.SH': '隆基绿能', '000568.SZ': '泸州老窖',
        '002352.SZ': '顺丰控股', '601888.SH': '中国中免', '000001.SZ': '平安银行',
    }
    
    def __init__(self):
        self.quotes: Dict[str, StockQuote] = {}
        self.price_history: Dict[str, List[Dict]] = {code: [] for code in self.BASE_PRICES}
        self._init_quotes()
        self._start_price_simulation()
    
    def _init_quotes(self):
        """初始化行情"""
        for code, base_price in self.BASE_PRICES.items():
            change = random.uniform(-0.02, 0.02)
            price = base_price * (1 + change)
            self.quotes[code] = StockQuote(
                ts_code=code,
                name=self.NAMES[code],
                price=round(price, 2),
                open_price=round(base_price * random.uniform(0.995, 1.005), 2),
                high=round(price * 1.01, 2),
                low=round(price * 0.99, 2),
                prev_close=base_price,
                volume=random.randint(100000, 5000000),
                turnover=round(random.uniform(100000000, 5000000000), 2),
                bid1=round(price * 0.999, 2),
                bid1_vol=random.randint(100, 5000),
                ask1=round(price * 1.001, 2),
                ask1_vol=random.randint(100, 5000),
                bid2=round(price * 0.998, 2),
                bid2_vol=random.randint(100, 3000),
                ask2=round(price * 1.002, 2),
                ask2_vol=random.randint(100, 3000),
                bid3=round(price * 0.997, 2),
                bid3_vol=random.randint(100, 2000),
                ask3=round(price * 1.003, 2),
                ask3_vol=random.randint(100, 2000),
                change_pct=round(change * 100, 2),
                timestamp=datetime.now().strftime('%H:%M:%S')
            )
            
            # 初始化历史数据
            for i in range(60):
                t = datetime.now() - timedelta(minutes=60-i)
                p = base_price * (1 + random.uniform(-0.03, 0.03))
                self.price_history[code].append({
                    'time': t.strftime('%H:%M'),
                    'price': round(p, 2),
                    'volume': random.randint(1000, 50000)
                })
    
    def _start_price_simulation(self):
        """启动价格模拟线程"""
        def simulate():
            while True:
                time.sleep(2)
                for code in self.quotes:
                    quote = self.quotes[code]
                    # 随机波动
                    change = random.uniform(-0.001, 0.001)
                    new_price = round(quote.price * (1 + change), 2)
                    
                    # 更新五档盘口
                    spread = new_price * 0.001
                    quote.bid1 = round(new_price - spread * 0.5, 2)
                    quote.ask1 = round(new_price + spread * 0.5, 2)
                    quote.bid2 = round(quote.bid1 - spread, 2)
                    quote.ask2 = round(quote.ask1 + spread, 2)
                    quote.bid3 = round(quote.bid2 - spread, 2)
                    quote.ask3 = round(quote.ask2 + spread, 2)
                    
                    # 更新成交量
                    quote.volume += random.randint(100, 5000)
                    quote.price = new_price
                    quote.change_pct = round((new_price - quote.prev_close) / quote.prev_close * 100, 2)
                    quote.high = max(quote.high, new_price)
                    quote.low = min(quote.low, new_price)
                    quote.timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    # 更新历史
                    self.price_history[code].append({
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'price': new_price,
                        'volume': random.randint(1000, 50000)
                    })
                    if len(self.price_history[code]) > 240:
                        self.price_history[code].pop(0)
        
        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()
    
    def get_quote(self, code: str) -> StockQuote:
        return self.quotes.get(code)
    
    def get_all_quotes(self) -> List[StockQuote]:
        return list(self.quotes.values())
    
    def get_history(self, code: str) -> List[Dict]:
        return self.price_history.get(code, [])


class TradingAccount:
    """交易账户"""
    
    def __init__(self):
        self.initial_capital = 1000000.0
        self.cash = 100000.0
        self.positions = {}
        self._load_data()
    
    def _load_data(self):
        """加载账户数据"""
        data_file = "trading_account.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.cash = data.get('cash', self.initial_capital)
                for pos in data.get('positions', []):
                    self.positions[pos['ts_code']] = pos
    
    def get_portfolio_value(self, market: RealtimeMarket) -> Dict:
        """计算组合价值"""
        total_market_value = 0
        total_pnl = 0
        
        for code, pos in self.positions.items():
            quote = market.get_quote(code)
            if quote:
                market_value = quote.price * pos['volume']
                pnl = (quote.price - pos['avg_cost']) * pos['volume']
                total_market_value += market_value
                total_pnl += pnl
        
        total_assets = self.cash + total_market_value
        return {
            'total_assets': total_assets,
            'cash': self.cash,
            'market_value': total_market_value,
            'total_pnl': total_pnl,
            'return_pct': (total_assets - self.initial_capital) / self.initial_capital * 100
        }


# 全局实例
market = RealtimeMarket()
account = TradingAccount()


class TradingHandler(SimpleHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def do_GET(self):
        if self.path == '/api/quotes':
            self._send_json([asdict(q) for q in market.get_all_quotes()])
        elif self.path.startswith('/api/history/'):
            code = self.path.split('/')[-1]
            self._send_json(market.get_history(code))
        elif self.path == '/api/portfolio':
            self._send_json(account.get_portfolio_value(market))
        elif self.path == '/api/positions':
            self._send_positions()
        elif self.path == '/':
            self._send_index()
        else:
            super().do_GET()
    
    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_positions(self):
        positions = []
        for code, pos in account.positions.items():
            quote = market.get_quote(code)
            if quote:
                positions.append({
                    'ts_code': code,
                    'name': pos['name'],
                    'volume': pos['volume'],
                    'avg_cost': pos['avg_cost'],
                    'price': quote.price,
                    'market_value': quote.price * pos['volume'],
                    'pnl': (quote.price - pos['avg_cost']) * pos['volume'],
                    'pnl_pct': (quote.price - pos['avg_cost']) / pos['avg_cost'] * 100
                })
        self._send_json(positions)
    
    def _send_index(self):
        html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 Mac实盘交易系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
            color: #c9d1d9;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        /* Mac风格标题栏 */
        .titlebar {
            background: rgba(13, 17, 23, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid #30363d;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .titlebar .traffic-lights {
            display: flex;
            gap: 8px;
        }
        .traffic-light {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .close { background: #ff5f56; }
        .minimize { background: #ffbd2e; }
        .maximize { background: #27c93f; }
        .titlebar h1 {
            font-size: 15px;
            font-weight: 600;
            color: #fff;
        }
        .titlebar .time {
            font-size: 13px;
            color: #8b949e;
        }
        
        /* 主布局 */
        .main-container {
            display: grid;
            grid-template-columns: 1fr 320px;
            gap: 20px;
            padding: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        @media (max-width: 1200px) {
            .main-container { grid-template-columns: 1fr; }
        }
        
        /* 资产卡片 */
        .assets-bar {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }
        .asset-card {
            background: rgba(22, 27, 34, 0.8);
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 16px;
            transition: all 0.2s;
        }
        .asset-card:hover {
            border-color: #58a6ff;
            transform: translateY(-2px);
        }
        .asset-card .label {
            font-size: 12px;
            color: #8b949e;
            margin-bottom: 6px;
        }
        .asset-card .value {
            font-size: 24px;
            font-weight: 700;
            color: #fff;
            font-variant-numeric: tabular-nums;
        }
        .asset-card .change {
            font-size: 13px;
            margin-top: 4px;
            font-variant-numeric: tabular-nums;
        }
        .up { color: #3fb950; }
        .down { color: #f85149; }
        
        /* 面板 */
        .panel {
            background: rgba(22, 27, 34, 0.8);
            border: 1px solid #30363d;
            border-radius: 12px;
            overflow: hidden;
        }
        .panel-header {
            padding: 12px 16px;
            border-bottom: 1px solid #30363d;
            font-size: 13px;
            font-weight: 600;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .panel-content {
            padding: 16px;
        }
        
        /* 行情列表 */
        .quote-list {
            max-height: 600px;
            overflow-y: auto;
        }
        .quote-item {
            display: grid;
            grid-template-columns: 1fr auto auto;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid #21262d;
            cursor: pointer;
            transition: background 0.2s;
        }
        .quote-item:hover {
            background: rgba(88, 166, 255, 0.1);
        }
        .quote-item:last-child { border-bottom: none; }
        .quote-name {
            font-size: 14px;
            font-weight: 500;
        }
        .quote-code {
            font-size: 11px;
            color: #8b949e;
        }
        .quote-price {
            font-size: 15px;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
        }
        .quote-change {
            font-size: 13px;
            font-weight: 500;
            padding: 2px 8px;
            border-radius: 4px;
            font-variant-numeric: tabular-nums;
        }
        .quote-change.up {
            background: rgba(63, 185, 80, 0.15);
        }
        .quote-change.down {
            background: rgba(248, 81, 73, 0.15);
        }
        
        /* 盘口 */
        .order-book {
            font-size: 13px;
        }
        .book-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            padding: 4px 0;
            font-variant-numeric: tabular-nums;
        }
        .book-row.header {
            color: #8b949e;
            font-size: 11px;
            padding-bottom: 8px;
            border-bottom: 1px solid #21262d;
        }
        .ask { color: #f85149; }
        .bid { color: #3fb950; }
        .book-bar {
            height: 4px;
            background: #21262d;
            border-radius: 2px;
            margin-top: 2px;
            overflow: hidden;
        }
        .book-bar-fill {
            height: 100%;
            border-radius: 2px;
        }
        .book-bar-fill.ask { background: #f85149; }
        .book-bar-fill.bid { background: #3fb950; }
        
        /* K线区域 */
        .chart-container {
            height: 400px;
            position: relative;
        }
        
        /* 持仓表格 */
        .position-table {
            width: 100%;
            font-size: 13px;
            border-collapse: collapse;
        }
        .position-table th {
            text-align: left;
            padding: 10px 8px;
            color: #8b949e;
            font-weight: 500;
            border-bottom: 1px solid #30363d;
        }
        .position-table td {
            padding: 12px 8px;
            border-bottom: 1px solid #21262d;
        }
        .position-table tr:hover {
            background: rgba(88, 166, 255, 0.05);
        }
        .position-table .num {
            font-variant-numeric: tabular-nums;
        }
        
        /* 滚动条 */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0d1117;
        }
        ::-webkit-scrollbar-thumb {
            background: #30363d;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #484f58;
        }
        
        /* 选中状态 */
        .quote-item.active {
            background: rgba(88, 166, 255, 0.15);
            border-left: 3px solid #58a6ff;
        }
        
        /* 实时闪烁 */
        @keyframes flash-up {
            0%, 100% { background: transparent; }
            50% { background: rgba(63, 185, 80, 0.3); }
        }
        @keyframes flash-down {
            0%, 100% { background: transparent; }
            50% { background: rgba(248, 81, 73, 0.3); }
        }
        .flash-up { animation: flash-up 0.5s ease; }
        .flash-down { animation: flash-down 0.5s ease; }
    </style>
</head>
<body>
    <div class="titlebar">
        <div class="traffic-lights">
            <div class="traffic-light close"></div>
            <div class="traffic-light minimize"></div>
            <div class="traffic-light maximize"></div>
        </div>
        <h1>📈 Mac实盘交易系统</h1>
        <div class="time" id="clock">09:30:00</div>
    </div>
    
    <div style="padding: 20px; max-width: 1600px; margin: 0 auto;">
        <!-- 资产概览 -->
        <div class="assets-bar">
            <div class="asset-card">
                <div class="label">💰 总资产</div>
                <div class="value" id="totalAssets">¥0.00</div>
                <div class="change up" id="totalReturn">+0.00%</div>
            </div>
            <div class="asset-card">
                <div class="label">💵 可用资金</div>
                <div class="value" id="cash">¥0.00</div>
            </div>
            <div class="asset-card">
                <div class="label">📈 持仓市值</div>
                <div class="value" id="marketValue">¥0.00</div>
            </div>
            <div class="asset-card">
                <div class="label">📊 当日盈亏</div>
                <div class="value up" id="dailyPnl">+¥0.00</div>
                <div class="change up">+0.00%</div>
            </div>
        </div>
    </div>
    
    <div class="main-container">
        <!-- 左侧：行情和K线 -->
        <div class="left-panel">
            <div class="panel" style="margin-bottom: 20px;">
                <div class="panel-header">
                    📊 分时走势 - <span id="selectedStock">贵州茅台 600519.SH</span>
                </div>
                <div class="panel-content">
                    <div class="chart-container">
                        <canvas id="priceChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <div class="panel-header">📈 我的持仓</div>
                <div class="panel-content">
                    <table class="position-table">
                        <thead>
                            <tr>
                                <th>股票</th>
                                <th>持仓</th>
                                <th>成本</th>
                                <th>现价</th>
                                <th>市值</th>
                                <th>盈亏</th>
                            </tr>
                        </thead>
                        <tbody id="positionsBody">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- 右侧：自选和盘口 -->
        <div class="right-panel">
            <div class="panel" style="margin-bottom: 20px;">
                <div class="panel-header">⭐ 自选股</div>
                <div class="panel-content quote-list" id="quoteList">
                </div>
            </div>
            
            <div class="panel">
                <div class="panel-header">📋 五档盘口</div>
                <div class="panel-content order-book">
                    <div class="book-row header">
                        <span>档位</span>
                        <span>价格</span>
                        <span>数量</span>
                    </div>
                    <div id="orderBook">
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let selectedCode = '600519.SH';
        let priceChart = null;
        let historyData = [];
        
        // 初始化图表
        function initChart() {
            const ctx = document.getElementById('priceChart').getContext('2d');
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '价格',
                        data: [],
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88, 166, 255, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(13, 17, 23, 0.95)',
                            borderColor: '#30363d',
                            borderWidth: 1,
                            titleColor: '#c9d1d9',
                            bodyColor: '#c9d1d9',
                            callbacks: {
                                label: (ctx) => `价格: ¥${ctx.parsed.y.toFixed(2)}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: '#21262d' },
                            ticks: { color: '#8b949e', maxTicksLimit: 6 }
                        },
                        y: {
                            grid: { color: '#21262d' },
                            ticks: { color: '#8b949e' }
                        }
                    }
                }
            });
        }
        
        // 更新时钟
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString('zh-CN');
        }
        
        // 更新行情列表
        async function updateQuotes() {
            try {
                const res = await fetch('/api/quotes');
                const quotes = await res.json();
                
                const listEl = document.getElementById('quoteList');
                listEl.innerHTML = quotes.map(q => {
                    const isUp = q.change_pct >= 0;
                    const isSelected = q.ts_code === selectedCode ? 'active' : '';
                    return `
                        <div class="quote-item ${isSelected}" onclick="selectStock('${q.ts_code}', '${q.name}')">
                            <div>
                                <div class="quote-name">${q.name}</div>
                                <div class="quote-code">${q.ts_code}</div>
                            </div>
                            <div class="quote-price ${isUp ? 'up' : 'down'}">¥${q.price.toFixed(2)}</div>
                            <div class="quote-change ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${q.change_pct.toFixed(2)}%</div>
                        </div>
                    `;
                }).join('');
                
                // 更新盘口
                const selectedQuote = quotes.find(q => q.ts_code === selectedCode);
                if (selectedQuote) {
                    updateOrderBook(selectedQuote);
                }
            } catch (e) {
                console.error('Failed to fetch quotes:', e);
            }
        }
        
        // 更新盘口
        function updateOrderBook(quote) {
            const bookEl = document.getElementById('orderBook');
            const rows = [
                { label: '卖3', price: quote.ask3, vol: quote.ask3_vol, type: 'ask' },
                { label: '卖2', price: quote.ask2, vol: quote.ask2_vol, type: 'ask' },
                { label: '卖1', price: quote.ask1, vol: quote.ask1_vol, type: 'ask' },
                { label: '买1', price: quote.bid1, vol: quote.bid1_vol, type: 'bid' },
                { label: '买2', price: quote.bid2, vol: quote.bid2_vol, type: 'bid' },
                { label: '买3', price: quote.bid3, vol: quote.bid3_vol, type: 'bid' },
            ];
            
            const maxVol = Math.max(...rows.map(r => r.vol));
            
            bookEl.innerHTML = rows.map(r => `
                <div class="book-row">
                    <span class="${r.type}">${r.label}</span>
                    <span class="${r.type}">¥${r.price.toFixed(2)}</span>
                    <span>${r.vol}</span>
                </div>
                <div class="book-bar">
                    <div class="book-bar-fill ${r.type}" style="width: ${(r.vol / maxVol * 100).toFixed(0)}%"></div>
                </div>
            `).join('');
        }
        
        // 更新K线
        async function updateChart() {
            try {
                const res = await fetch(`/api/history/${selectedCode}`);
                historyData = await res.json();
                
                if (priceChart) {
                    priceChart.data.labels = historyData.map(d => d.time);
                    priceChart.data.datasets[0].data = historyData.map(d => d.price);
                    priceChart.update('none');
                }
            } catch (e) {
                console.error('Failed to fetch history:', e);
            }
        }
        
        // 更新持仓
        async function updatePositions() {
            try {
                const [portfolioRes, positionsRes] = await Promise.all([
                    fetch('/api/portfolio'),
                    fetch('/api/positions')
                ]);
                
                const portfolio = await portfolioRes.json();
                const positions = await positionsRes.json();
                
                // 更新资产卡片
                document.getElementById('totalAssets').textContent = `¥${portfolio.total_assets.toFixed(2)}`;
                document.getElementById('cash').textContent = `¥${portfolio.cash.toFixed(2)}`;
                document.getElementById('marketValue').textContent = `¥${portfolio.market_value.toFixed(2)}`;
                
                const returnEl = document.getElementById('totalReturn');
                returnEl.textContent = `${portfolio.return_pct >= 0 ? '+' : ''}${portfolio.return_pct.toFixed(2)}%`;
                returnEl.className = `change ${portfolio.return_pct >= 0 ? 'up' : 'down'}`;
                
                // 更新持仓表格
                document.getElementById('positionsBody').innerHTML = positions.map(p => {
                    const isUp = p.pnl >= 0;
                    return `
                        <tr>
                            <td>
                                <div>${p.name}</div>
                                <div style="font-size: 11px; color: #8b949e;">${p.ts_code}</div>
                            </td>
                            <td class="num">${p.volume}</td>
                            <td class="num">¥${p.avg_cost.toFixed(2)}</td>
                            <td class="num ${isUp ? 'up' : 'down'}">¥${p.price.toFixed(2)}</td>
                            <td class="num">¥${p.market_value.toFixed(0)}</td>
                            <td class="num ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}¥${p.pnl.toFixed(0)}</td>
                        </tr>
                    `;
                }).join('');
            } catch (e) {
                console.error('Failed to fetch positions:', e);
            }
        }
        
        // 选择股票
        function selectStock(code, name) {
            selectedCode = code;
            document.getElementById('selectedStock').textContent = `${name} ${code}`;
            updateChart();
            updateQuotes();
        }
        
        // 初始化
        function init() {
            initChart();
            updateClock();
            setInterval(updateClock, 1000);
            setInterval(updateQuotes, 1000);
            setInterval(updateChart, 2000);
            setInterval(updatePositions, 2000);
            updateQuotes();
            updateChart();
            updatePositions();
        }
        
        init();
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())


def start_server(port=8888):
    """启动服务器"""
    server = HTTPServer(('0.0.0.0', port), TradingHandler)
    print(f"🚀 Mac实盘交易系统已启动!")
    print(f"📊 访问地址: http://localhost:{port}")
    print(f"⏱️ 实时行情模拟中...")
    
    # 自动打开浏览器
    webbrowser.open(f'http://localhost:{port}')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 系统已关闭")
        server.shutdown()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Mac实盘交易系统')
    parser.add_argument('--port', type=int, default=8888, help='端口号')
    args = parser.parse_args()
    
    start_server(args.port)
