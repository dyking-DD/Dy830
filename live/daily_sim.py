#!/usr/bin/env python3
"""
TrendMatrix 每日模拟实盘脚本
每天16:00自动运行，跟踪模拟持仓和交易信号
"""

import baostock as bs
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import sys

sys.path.insert(0, '/home/ubuntu/TrendMatrix')
from strategy.core import (
    STOCKS, POSITION_SIZE, MA_PERIOD, VOL_MA_PERIOD,
    VOL_RATIO_THRESHOLD, STOP_LOSS, FIRST_PROFIT_TARGET, TRAILING_STOP
)

STATE_FILE = "/home/ubuntu/TrendMatrix/live/sim_positions.json"

# ===================== 数据获取 =====================
def get_data(code: str, count: int = 30) -> pd.DataFrame:
    bs.login()
    rs = bs.query_history_k_data_plus(code, "date,open,high,low,close,volume",
        start_date=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"), frequency="d")
    data = []
    while rs.error_code == "0" and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    df = pd.DataFrame(data, columns=["date","open","high","low","close","volume"])
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=["close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["ma10"] = df["close"].rolling(MA_PERIOD).mean()
    df["vol_ma5"] = df["volume"].rolling(VOL_MA_PERIOD).mean()
    return df

# ===================== 状态管理 =====================
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"positions": {}, "cash": 100000, "history": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

# ===================== 每日分析 =====================
def run_daily_analysis():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"TrendMatrix 每日模拟实盘")
    print(f"日期: {today}")
    print(f"{'='*60}")

    state = load_state()
    positions = state["positions"]
    cash = state["cash"]

    # 获取大盘数据
    mkt = get_data("sh.000300", 30)
    if mkt.empty or len(mkt) < MA_PERIOD:
        print("[错误] 无法获取大盘数据")
        return

    latest_mkt = mkt.iloc[-1]
    prev_mkt = mkt.iloc[-2]
    market_ok = latest_mkt["close"] > latest_mkt["ma10"] and prev_mkt["close"] > prev_mkt["ma10"]
    print(f"\n[大盘] 沪深300: {latest_mkt['close']:.2f}  MA10: {latest_mkt['ma10']:.2f}")
    print(f"      {'✓ 在MA10之上' if market_ok else '✗ 在MA10之下'}")

    # 处理现有持仓
    print(f"\n[持仓] 当前现金: {cash:.2f}")
    closed_trades = []

    for code, (name, pos_type) in STOCKS.items():
        if code not in positions:
            continue

        pos = positions[code]
        df = get_data(code, 30)
        if df.empty:
            continue

        curr = df.iloc[-1]
        entry_price = pos["entry_price"]
        highest = pos.get("highest_price", entry_price)
        volume = pos["volume"]
        half_sold = pos.get("half_sold", False)

        # 更新最高价
        pos["highest_price"] = max(highest, curr["high"])

        pnl = (curr["close"] / entry_price - 1) * 100
        print(f"  {name}: {curr['close']:.2f} ({pnl:+.2f}%)")

        exit_reason = None
        exit_price = curr["close"]

        # 出场检查
        if pnl <= STOP_LOSS * 100:
            exit_reason = "硬止损"
        elif curr["close"] < curr["ma10"]:
            exit_reason = "MA10止损"
            exit_price = curr["open"]
        elif not half_sold and pnl >= FIRST_PROFIT_TARGET * 100:
            # 半仓止盈
            half_vol = volume // 2
            half_profit = half_vol * (exit_price - entry_price)
            cash += half_profit
            pos["volume"] = volume - half_vol
            pos["half_sold"] = True
            print(f"    → 止盈半仓，现金: {cash:.2f}")
            closed_trades.append({"name": name, "reason": "止盈半仓", "pnl": (exit_price/entry_price-1)*100})
            continue
        elif half_sold:
            drawdown = (curr["close"] / pos["highest_price"] - 1) * 100
            if drawdown <= -TRAILING_STOP * 100:
                exit_reason = "移动止损"

        if exit_reason:
            profit = pos["volume"] * (exit_price - entry_price)
            cash += profit
            print(f"    → {exit_reason} @{exit_price:.2f}, 现金: {cash:.2f}")
            closed_trades.append({"name": name, "reason": exit_reason, "pnl": pnl})
            del positions[code]

    # 入场信号检查
    new_positions = []
    if market_ok:
        print(f"\n[入场扫描] 大盘在MA10之上，检查信号...")
        for code, (name, pos_type) in STOCKS.items():
            if code in positions:
                continue
            df = get_data(code, 30)
            if df.empty or len(df) < MA_PERIOD + 1:
                continue

            prev = df.iloc[-2]
            vol_ok = prev["volume"] > prev["vol_ma5"] * VOL_RATIO_THRESHOLD if prev["vol_ma5"] > 0 else False
            price_ok = prev["close"] > prev["ma10"]

            if price_ok and vol_ok:
                curr_price = df.iloc[-1]["open"]
                pos_size = POSITION_SIZE[pos_type]
                buy_vol = (pos_size // (curr_price * 100)) * 100
                if buy_vol > 0 and cash >= buy_vol * curr_price:
                    cost = buy_vol * curr_price
                    cash -= cost
                    positions[code] = {
                        "name": name,
                        "entry_price": curr_price,
                        "volume": buy_vol,
                        "entry_date": datetime.now().strftime("%Y-%m-%d"),
                        "highest_price": curr_price,
                        "half_sold": False,
                        "pos_type": pos_type
                    }
                    new_positions.append(name)
                    print(f"  → 买入 {name} {buy_vol}股 @{curr_price:.2f}, 现金: {cash:.2f}")

    # 保存状态
    state["cash"] = cash
    state["positions"] = positions
    save_state(state)

    # 汇总
    print(f"\n{'='*60}")
    print(f"[汇总] 日期: {today}")
    print(f"  现金: {cash:.2f}")
    print(f"  持仓: {len(positions)}只")
    for code, pos in positions.items():
        pnl = (df.iloc[-1]["close"] / pos["entry_price"] - 1) * 100 if code in [c for c, _ in STOCKS.items()] else 0
        print(f"    {pos['name']}: {pos['entry_price']:.2f} x {pos['volume']}股")
    print(f"{'='*60}")

if __name__ == "__main__":
    run_daily_analysis()
