"""
TrendMatrix 策略核心模块
V3: 大盘择时 + MA10入场 + 分批止盈 + 移动止损
"""

import baostock as bs
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")


# ===================== 配置 =====================
# 标的配置：(baostock代码, 名称, 仓位类型)
STOCKS = {
    # 核心仓（各20万）
    "sz.000977": ("浪潮信息", "core"),
    "sz.002371": ("北方华创", "core"),
    "sz.002837": ("英维克", "core"),
    "sh.603019": ("中科曙光", "core"),
    # 观察仓（各5万）
    "sh.688012": ("中微公司", "observe"),
    "sz.300274": ("阳光电源", "observe"),
}

POSITION_SIZE = {
    "core": 200000,      # 核心仓 20万
    "observe": 50000,     # 观察仓 5万
}

# 策略参数
MA_PERIOD = 10           # MA周期
VOL_MA_PERIOD = 5        # 成交量均线周期
VOL_RATIO_THRESHOLD = 1.2 # 放量倍数阈值
STOP_LOSS = -0.05         # 硬止损 -5%
FIRST_PROFIT_TARGET = 0.08  # 第一批止盈 +8%
TRAILING_STOP = 0.05     # 移动止损 5%
START_DATE = "2025-01-01"
END_DATE = "2025-04-30"


# ===================== 数据获取 =====================
def get_stock_data(code: str, start: str, end: str) -> pd.DataFrame:
    """获取单只股票历史数据"""
    bs.login()
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=start, end_date=end, frequency="d"
    )
    data = []
    while rs.error_code == "0" and rs.next():
        data.append(rs.get_row_data())
    bs.logout()

    df = pd.DataFrame(data, columns=["date","open","high","low","close","volume"])
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=["close"])
    if len(df) == 0:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 计算指标
    df["ma10"] = df["close"].rolling(MA_PERIOD).mean()
    df["vol_ma5"] = df["volume"].rolling(VOL_MA_PERIOD).mean()

    return df


def get_market_data(start: str, end: str) -> pd.DataFrame:
    """获取沪深300大盘数据"""
    bs.login()
    rs = bs.query_history_k_data_plus(
        "sh.000300", "date,open,high,low,close,volume",
        start_date=start, end_date=end, frequency="d"
    )
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


# ===================== 策略信号 =====================
def check_entry_signal(prev_row: pd.Series) -> bool:
    """检查入场信号"""
    # 放量 > 1.2倍
    vol_ok = prev_row["volume"] > prev_row["vol_ma5"] * VOL_RATIO_THRESHOLD if prev_row["vol_ma5"] > 0 else False
    # 价格在 MA10 之上
    price_ok = prev_row["close"] > prev_row["ma10"]
    return price_ok and vol_ok


def check_exit_signals(position: dict, curr_row: pd.Series) -> dict:
    """
    检查出场信号
    返回: {"exit": bool, "reason": str, "exit_price": float}
    """
    entry_price = position["entry_price"]
    highest_price = position["highest_price"]
    half_sold = position.get("half_sold", False)

    pnl = (curr_row["close"] / entry_price - 1)

    # 1. 硬止损 -5%
    if pnl <= STOP_LOSS:
        return {"exit": True, "reason": "硬止损", "exit_price": curr_row["close"]}

    # 2. MA10 止损
    if curr_row["close"] < curr_row["ma10"]:
        return {"exit": True, "reason": "MA10止损", "exit_price": curr_row["open"]}

    # 3. 分批止盈：第一批 +8%
    if not half_sold and pnl >= FIRST_PROFIT_TARGET:
        return {"exit": True, "reason": "止盈半仓", "exit_price": curr_row["close"], "half": True}

    # 4. 移动止损：最高点回撤 5%（且已出完半仓）
    if half_sold:
        drawdown = (curr_row["close"] / highest_price - 1)
        if drawdown <= -TRAILING_STOP:
            return {"exit": True, "reason": "移动止损", "exit_price": curr_row["close"]}

    return {"exit": False}


# ===================== 回测引擎 =====================
def run_backtest():
    """运行完整回测"""
    print("=" * 70)
    print("TrendMatrix V3 回测")
    print("大盘择时 + MA10入场 + 分批止盈 + 移动止损")
    print("=" * 70)

    # 获取大盘数据
    print("\n[1] 获取大盘数据...")
    market = get_market_data(START_DATE, END_DATE)
    print(f"    大盘数据: {len(market)} 条")

    # 获取个股数据
    print("\n[2] 获取个股数据...")
    stock_data = {}
    for code, (name, pos_type) in STOCKS.items():
        df = get_stock_data(code, START_DATE, END_DATE)
        stock_data[name] = df
        print(f"    {name}: {len(df)} 条")

    # 合并大盘数据到个股（按日期对齐）
    for name in stock_data:
        stock_data[name] = stock_data[name].merge(
            market[["date", "close", "ma10"]],
            on="date",
            suffixes=("", "_mkt")
        )

    # 回测
    results = {}

    for code, (name, pos_type) in STOCKS.items():
        df = stock_data[name]
        init_cap = 50000
        capital = init_cap
        position = None
        trades = []
        cooldown = 0  # 出场后冷却 Bar 数（防立即重新入场）

        for i in range(MA_PERIOD, len(df)):
            row = df.iloc[i]
            if cooldown > 0:
                cooldown -= 1

            # 大盘不在 MA10 上，跳过（大盘择时）
            if row["close_mkt"] <= row["ma10_mkt"]:
                if position is not None:
                    # 大盘破 MA10，强制离场
                    exit_info = {
                        "exit_date": row["date"],
                        "exit_price": row["open"],
                        "pnl": (row["open"] / position["entry_price"] - 1) * 100,
                        "reason": "大盘破MA10",
                        "max_return": position["max_return"]
                    }
                    capital = capital * (1 + exit_info["pnl"] / 100)
                    trades.append(exit_info)
                    position = None
                    cooldown = 3  # 强制出场后冷却3根
                continue

            if position is None:
                # cooldown 未结束，禁止入场
                if cooldown > 0:
                    continue
                prev = df.iloc[i - 1]
                if check_entry_signal(prev):
                    position = {
                        "entry_price": row["open"],
                        "entry_date": row["date"],
                        "highest_price": row["open"],
                        "max_return": 0,
                        "half_sold": False,
                    }
            else:
                # 更新最高价
                position["highest_price"] = max(position["highest_price"], row["high"])
                # 计算当前最大盈利
                curr_pnl = (row["close"] / position["entry_price"] - 1) * 100
                position["max_return"] = max(position["max_return"], curr_pnl)

                # 检查出场
                exit_info = check_exit_signals(position, row)
                if exit_info["exit"]:
                    exit_price = exit_info["exit_price"]
                    pnl = (exit_price / position["entry_price"] - 1) * 100
                    capital = capital * (1 + pnl / 100)
                    trade = {
                        "exit_date": row["date"],
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "reason": exit_info["reason"],
                        "max_return": position["max_return"]
                    }
                    trades.append(trade)

                    # 分批止盈：出半仓，保留半仓跑移动止损
                    if exit_info.get("half"):
                        locked_capital = init_cap * 0.5 * (1 + pnl / 100)
                        capital = locked_capital + init_cap * 0.5
                        position["half_sold"] = True
                        # 不清position，保留半仓继续跑；不出 cooldown，继续持
                    else:
                        position = None
                        cooldown = 3  # 全仓退出后冷却3根

        # 最后仍未卖出，按最后收盘结算
        if position is not None:
            last = df.iloc[-1]
            pnl = (last["close"] / position["entry_price"] - 1) * 100
            capital = capital * (1 + pnl / 100)
            trades.append({
                "exit_date": last["date"],
                "exit_price": last["close"],
                "pnl": pnl,
                "reason": "期末结算",
                "max_return": position["max_return"],
                "final": True
            })

        final_return = (capital / 50000 - 1) * 100
        results[name] = {
            "final": capital,
            "return": final_return,
            "trades": trades,
            "wins": sum(1 for t in trades if t["pnl"] > 0),
            "total": len(trades),
            "max_return": max([t["max_return"] for t in trades], default=0),
            "max_loss": min([t["pnl"] for t in trades], default=0),
            "pos_type": pos_type,
            "pos_size": POSITION_SIZE[pos_type],
        }

    return results


def print_results(results: dict):
    """打印回测结果"""
    sorted_results = sorted(results.items(), key=lambda x: x[1]["return"], reverse=True)

    total_capital = sum(r["pos_size"] for _, r in results.items())
    total_final = sum(r["final"] / 50000 * r["pos_size"] for _, r in results.items())

    print("\n" + "=" * 70)
    for name, r in sorted_results:
        flag = "★" if r["return"] > 0 else " "
        pos_label = "[核心]" if r["pos_type"] == "core" else "[观察]"
        print(f"\n[{flag}] {name} {pos_label}: 50000 -> {r['final']:.0f}  {r['return']:+.2f}%")
        print(f"    胜率: {r['wins']}/{r['total']}笔  |  最大赚: {r['max_return']:.1f}%  |  最大亏: {r['max_loss']:.1f}%")
        for t in r["trades"]:
            final_mark = " FINAL" if t.get("final") else ""
            print(f"    → {t['exit_date'].strftime('%Y-%m-%d')} @{t['exit_price']:.2f}  {t['pnl']:+.2f}%  [{t['reason']}]{final_mark}")

    print("\n" + "=" * 70)
    print(f"\n总本金: {total_capital/10000:.0f}万")
    print(f"总资金: {total_final/10000:.0f}万")
    total_return = (total_final / total_capital - 1) * 100
    print(f"总收益率: {total_return:+.2f}%")

    months = 4
    monthly = ((total_final / total_capital) ** (1/months) - 1) * 100
    annual = ((total_final / total_capital) ** (12/months) - 1) * 100
    print(f"月化收益率: {monthly:+.2f}%")
    print(f"年化收益率: {annual:+.2f}%")
    print(f"沪深300同期: -1.30%")
    print(f"超额年化: {annual - (-1.30 * 12/4):+.2f}%")
    print("=" * 70)

    # 板块统计
    print("\n【板块统计】")
    core = {n: r for n, r in results.items()}
    avg = sum(r["return"] for r in core.values()) / len(core)
    print(f"  核心仓平均: {avg:+.2f}%")

    # 盈亏统计
    wins = sum(1 for r in results.values() if r["return"] > 0)
    print(f"\n盈利标的: {wins}/{len(results)}")


if __name__ == "__main__":
    results = run_backtest()
    print_results(results)
