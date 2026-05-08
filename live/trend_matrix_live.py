#!/usr/bin/env python3
"""
TrendMatrix MiniQMT 实盘脚本
注意事项：
1. 需要先开通华泰证券 MiniQMT
2. 需要客户经理协助配置 xtquant 环境
3. 实盘前先在模拟盘测试
"""

import xtquant
from xtquant import xtdatacenter
from xtquant import xtportfolio
from xtquant import xttrade
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os

# ===================== 配置 =====================
ACCOUNT = "your_account_number"  # 替换为你的资金账号
PASSWD = "your_password"         # 替换为你的交易密码

# 标的配置
STOCKS = {
    # 核心仓（各20万）
    "000977.SZ": ("浪潮信息", "core"),
    "002371.SZ": ("北方华创", "core"),
    "002837.SZ": ("英维克", "core"),
    "603019.SH": ("中科曙光", "core"),
    # 观察仓（各5万）
    "688012.SH": ("中微公司", "observe"),
    "300274.SZ": ("阳光电源", "observe"),
}

POSITION_SIZE = {
    "core": 200000,
    "observe": 50000,
}

# 策略参数
MA_PERIOD = 10
VOL_MA_PERIOD = 5
VOL_RATIO_THRESHOLD = 1.2
STOP_LOSS = -0.05
FIRST_PROFIT_TARGET = 0.08
TRAILING_STOP = 0.05
MARKET_CODE = "000300.SH"  # 沪深300

# ===================== 数据获取 =====================
def get_daily_data(stock_code: str, count: int = 30) -> pd.DataFrame:
    """获取日线数据"""
    try:
        xtdatacenter.connect()
        data = xtdatacenter.get_daily_data(
            stock_code,
            xtdatacenter.DAILY_TYPE_NORM,
            count=count
        )
        xtdatacenter.disconnect()
        return data
    except Exception as e:
        print(f"获取数据失败 {stock_code}: {e}")
        return pd.DataFrame()


def get_market_data(count: int = 30) -> pd.DataFrame:
    """获取大盘（沪深300）数据"""
    return get_daily_data(MARKET_CODE, count)


def get_current_price(stock_code: str) -> float:
    """获取当前价格"""
    try:
        xtdatacenter.connect()
        tick = xtdatacenter.get_tick_data(stock_code)
        xtdatacenter.disconnect()
        return tick.get("lastPrice", 0)
    except:
        return 0


# ===================== 策略信号 =====================
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术指标"""
    df = df.copy()
    df["ma10"] = df["close"].rolling(MA_PERIOD).mean()
    df["vol_ma5"] = df["volume"].rolling(VOL_MA_PERIOD).mean()
    return df


def check_market_status(df: pd.DataFrame) -> bool:
    """检查大盘是否在MA10之上"""
    if len(df) < MA_PERIOD:
        return False
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    # 大盘当前价格在MA10之上，且昨日也在MA10之上
    return latest["close"] > latest["ma10"] and prev["close"] > prev["ma10"]


def check_entry_signal(df: pd.DataFrame) -> bool:
    """检查个股入场信号"""
    if len(df) < MA_PERIOD + 1:
        return False
    prev = df.iloc[-2]  # 用前一根K线信号
    vol_ok = prev["volume"] > prev["vol_ma5"] * VOL_RATIO_THRESHOLD if prev["vol_ma5"] > 0 else False
    price_ok = prev["close"] > prev["ma10"]
    return price_ok and vol_ok


# ===================== 交易执行 =====================
def init_trader():
    """初始化交易接口"""
    trader = xttrade.XtTrader()
    trader.login(ACCOUNT, PASSWD)
    return trader


def buy_stock(trader, stock_code: str, price: float, volume: int):
    """买入股票"""
    try:
        order_id = trader.order_stock(
            stock_code,
            xttrade.STOCK_BUY,
            price,
            volume,
            xttrade.FIX_PRICE  # 限价单
        )
        print(f"[买入] {stock_code} @{price} x {volume}, 订单号: {order_id}")
        return order_id
    except Exception as e:
        print(f"[买入失败] {stock_code}: {e}")
        return None


def sell_stock(trader, stock_code: str, price: float, volume: int, reason: str = ""):
    """卖出股票"""
    try:
        order_id = trader.order_stock(
            stock_code,
            xttrade.STOCK_SELL,
            price,
            volume,
            xttrade.FIX_PRICE
        )
        print(f"[卖出] {stock_code} @{price} x {volume} [{reason}], 订单号: {order_id}")
        return order_id
    except Exception as e:
        print(f"[卖出失败] {stock_code}: {e}")
        return None


# ===================== 持仓管理 =====================
class PositionManager:
    """持仓管理器"""

    def __init__(self):
        self.positions = {}  # {stock_code: {"entry_price": float, "volume": int, ...}}
        self.load_positions()

    def load_positions(self):
        """从文件加载持仓状态"""
        state_file = os.path.join(os.path.dirname(__file__), "positions_state.json")
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                self.positions = json.load(f)

    def save_positions(self):
        """保存持仓状态到文件"""
        state_file = os.path.join(os.path.dirname(__file__), "positions_state.json")
        with open(state_file, "w") as f:
            json.dump(self.positions, f, indent=2, default=str)

    def add_position(self, stock_code: str, entry_price: float, volume: int):
        """添加持仓"""
        self.positions[stock_code] = {
            "entry_price": entry_price,
            "volume": volume,
            "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "highest_price": entry_price,
            "half_sold": False,
            "half_volume": volume // 2 if volume >= 2 else volume,
        }
        self.save_positions()

    def remove_position(self, stock_code: str):
        """移除持仓"""
        if stock_code in self.positions:
            del self.positions[stock_code]
            self.save_positions()

    def update_highest(self, stock_code: str, price: float):
        """更新最高价"""
        if stock_code in self.positions:
            self.positions[stock_code]["highest_price"] = max(
                self.positions[stock_code]["highest_price"], price
            )
            self.save_positions()

    def is_holding(self, stock_code: str) -> bool:
        """检查是否持有"""
        return stock_code in self.positions


# ===================== 主循环 =====================
def run_trading_day(trader: xttrade.XtTrader, pm: PositionManager):
    """执行每日交易"""
    print(f"\n{'='*50}")
    print(f"运行交易: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    # 1. 检查大盘状态
    mkt_df = get_market_data(30)
    if mkt_df.empty:
        print("[错误] 无法获取大盘数据")
        return
    mkt_df = calculate_indicators(mkt_df)
    market_ok = check_market_status(mkt_df)
    print(f"[大盘] {'✓ 在MA10之上' if market_ok else '✗ 在MA10之下'}")

    # 2. 检查并处理持仓
    for stock_code, pos in pm.positions.items():
        df = get_daily_data(stock_code, 30)
        if df.empty:
            continue
        df = calculate_indicators(df)
        curr_price = df.iloc[-1]["close"]
        entry_price = pos["entry_price"]
        highest_price = pos["highest_price"]
        volume = pos["volume"]
        half_volume = pos.get("half_volume", volume // 2)

        pnl = (curr_price / entry_price - 1) * 100
        print(f"[持仓] {stock_code} 当前: {curr_price:.2f}  成本: {entry_price:.2f}  盈亏: {pnl:+.2f}%")

        # 更新最高价
        pm.update_highest(stock_code, df.iloc[-1]["high"])

        exit_reason = None
        exit_price = curr_price

        # 止损检查
        if pnl <= STOP_LOSS * 100:
            exit_reason = "硬止损"
        # MA10 止损
        elif df.iloc[-1]["close"] < df.iloc[-1]["ma10"]:
            exit_reason = "MA10止损"
            exit_price = df.iloc[-1]["open"]  # 明日开盘价出
        # 分批止盈
        elif not pos.get("half_sold") and pnl >= FIRST_PROFIT_TARGET * 100:
            # 出一半
            sell_stock(trader, stock_code, exit_price, half_volume, "止盈半仓")
            pos["half_sold"] = True
            pm.save_positions()
            print(f"  → 止盈半仓，剩余继续持有")
            # 更新半仓后的成本
            remaining_vol = volume - half_volume
            locked_profit = half_volume * (exit_price - entry_price)
            new_entry = (volume * entry_price - locked_profit) / remaining_vol if remaining_vol > 0 else entry_price
            pos["entry_price"] = new_entry
            pos["volume"] = remaining_vol
            pm.save_positions()
            continue
        # 移动止损
        elif pos.get("half_sold"):
            drawdown = (curr_price / highest_price - 1) * 100
            if drawdown <= -TRAILING_STOP * 100:
                exit_reason = "移动止损"

        if exit_reason:
            remaining_vol = pos["volume"]
            sell_stock(trader, stock_code, exit_price, remaining_vol, exit_reason)
            pm.remove_position(stock_code)

    # 3. 入场信号检查
    if market_ok:
        print("\n[入场扫描] 大盘在MA10之上，检查入场信号...")
        for stock_code, (name, pos_type) in STOCKS.items():
            if pm.is_holding(stock_code):
                continue

            df = get_daily_data(stock_code, 30)
            if df.empty:
                continue
            df = calculate_indicators(df)

            if check_entry_signal(df):
                curr_price = df.iloc[-1]["open"]  # 明日开盘买
                pos_size = POSITION_SIZE[pos_type]
                volume = (pos_size // (curr_price * 100)) * 100  # 按手买
                if volume > 0:
                    buy_stock(trader, stock_code, curr_price, volume)
                    pm.add_position(stock_code, curr_price, volume)
                    print(f"  → 买入 {name} {volume}股 @{curr_price}")
    else:
        print("\n[跳过] 大盘不在MA10之上，不入场")


def run_daily_task():
    """每日收盘后运行"""
    trader = init_trader()
    pm = PositionManager()

    run_trading_day(trader, pm)

    trader.logout()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TrendMatrix MiniQMT 实盘")
    parser.add_argument("--mode", choices=["once", "loop"], default="once",
                        help="运行模式: once=运行一次, loop=持续运行")
    parser.add_argument("--interval", type=int, default=60,
                        help="循环模式下的检查间隔(秒)")
    args = parser.parse_args()

    if args.mode == "once":
        run_daily_task()
    else:
        print("启动 TrendMatrix 持续监控模式...")
        print("按 Ctrl+C 停止")
        while True:
            try:
                now = datetime.now()
                # 交易时段: 9:30-15:00
                if now.hour >= 9 and now.hour < 15:
                    run_daily_task()
                else:
                    print(f"[{now.strftime('%H:%M:%S')}] 非交易时段，等待...")
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n停止交易...")
                break
