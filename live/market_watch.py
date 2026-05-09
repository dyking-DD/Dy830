#!/usr/bin/env python3
"""
TrendMatrix 盘中/盘后市场监控
实时扫描大盘 + 选股池信号，输出评分排名
"""
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, '/home/ubuntu/TrendMatrix')

# ===================== 选股池 =====================
STOCKS = {
    "sz.000977": ("浪潮信息", "core", "sz.000300"),
    "sz.002371": ("北方华创", "core", "sh.000300"),
    "sz.002837": ("英维克",   "core", "sh.000300"),
    "sh.603019": ("中科曙光", "core", "sh.000300"),
    "sh.688012": ("中微公司", "observe", "sh.000300"),
    "sz.300274": ("阳光电源", "observe", "sh.000300"),
}

# ===================== 数据获取 =====================
def get_kline(code: str, days: int = 30) -> pd.DataFrame:
    bs.login()
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"),
        frequency="d"
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
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["vol_ma5"] = df["volume"].rolling(5).mean()
    return df

# ===================== 评分 =====================
def score_stock(df: pd.DataFrame) -> dict:
    if len(df) < 12:
        return None
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    ma10 = curr["ma10"]
    vol_ma5 = curr["vol_ma5"]

    vol_ratio = curr["volume"] / vol_ma5 if vol_ma5 > 0 else 0
    close_vs_ma10 = (curr["close"] / ma10 - 1) * 100 if ma10 > 0 else 0
    trend_5d = (curr["close"] / df.iloc[-5]["close"] - 1) * 100 if len(df) >= 5 else 0
    trend_10d = (curr["close"] / df.iloc[-10]["close"] - 1) * 100 if len(df) >= 10 else 0

    score = 0
    notes = []

    # 基础：价格在MA10上方
    if curr["close"] > ma10:
        score += 3
    else:
        notes.append("MA10下方")

    # 放量
    if vol_ratio >= 1.5:
        score += 4
        notes.append(f"放量{vol_ratio:.1f}x")
    elif vol_ratio >= 1.2:
        score += 3
        notes.append(f"温和放量{vol_ratio:.1f}x")
    elif vol_ratio < 0.7:
        score -= 2
        notes.append("缩量")

    # 5日动量
    if trend_5d > 5:
        score += 3
        notes.append(f"5日+{trend_5d:.1f}%")
    elif trend_5d > 2:
        score += 2
        notes.append(f"5日+{trend_5d:.1f}%")
    elif trend_5d < -3:
        score -= 2
        notes.append(f"5日{trend_5d:.1f}%")

    # MA10远离度（不是追高）
    if close_vs_ma10 > 8:
        score -= 1
        notes.append("偏离MA10过大")
    elif close_vs_ma10 > 3:
        score += 1

    # 趋势完整性（价格在MA20上方）
    ma20 = curr["ma20"]
    if ma20 and curr["close"] > ma20:
        score += 1

    return {
        "close": curr["close"],
        "ma10": ma10,
        "ma20": ma20,
        "close_vs_ma10": close_vs_ma10,
        "vol_ratio": vol_ratio,
        "trend_5d": trend_5d,
        "trend_10d": trend_10d,
        "score": score,
        "notes": notes,
    }

# ===================== 主程序 =====================
def run_watch():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  TrendMatrix 市场监控  {today}")
    print(f"{'='*60}")

    # 大盘
    mkt = get_kline("sh.000300", 30)
    if mkt.empty:
        print("[错误] 无法获取大盘数据")
        return

    mkt_curr = mkt.iloc[-1]
    mkt_prev = mkt.iloc[-2]
    mkt_vol_ratio = mkt_curr["volume"] / mkt_curr["vol_ma5"] if mkt_curr["vol_ma5"] > 0 else 0
    mkt_trend = (mkt_curr["close"] / mkt.iloc[-5]["close"] - 1) * 100 if len(mkt) >= 5 else 0

    mkt_ma10_ok = mkt_curr["close"] > mkt_curr["ma10"]
    mkt_ma20_ok = mkt_curr["close"] > mkt_curr["ma20"]
    mkt_score = 0
    mkt_status = "🟢 多头" if mkt_ma10_ok and mkt_ma20_ok else ("🟡 震荡" if mkt_ma10_ok else "🔴 空头")

    print(f"\n大盘: 沪深300 {mkt_curr['close']:.2f}")
    print(f"  MA10 {mkt_curr['ma10']:.2f}  {'✓' if mkt_ma10_ok else '✗'}")
    print(f"  MA20 {mkt_curr['ma20']:.2f}  {'✓' if mkt_ma20_ok else '✗'}")
    print(f"  5日涨跌: {mkt_trend:+.2f}%")
    print(f"  放量: {mkt_vol_ratio:.2f}x {'↑' if mkt_vol_ratio > 1 else '↓'}")
    print(f"  状态: {mkt_status}")

    # 选股池
    print(f"\n{'='*60}")
    print(f"{'名称':<10} {'收盘':>8} {'MA10偏离':>9} {'放量':>6} {'5日':>8} {'10日':>8} {'评分':>5} {'信号'}")
    print("-" * 75)

    results = []
    for code, (name, pos_type, _) in STOCKS.items():
        df = get_kline(code, 30)
        if df.empty or len(df) < 12:
            continue
        s = score_stock(df)
        if s is None:
            continue
        results.append((name, pos_type, s))

    results.sort(key=lambda x: x[2]["score"], reverse=True)

    market_ok = mkt_ma10_ok

    for name, pos_type, s in results:
        pos_label = "●" if pos_type == "core" else "○"
        notes_str = " ".join(s["notes"]) if s["notes"] else "正常"
        status = "🟢" if s["score"] >= 7 else ("🟡" if s["score"] >= 4 else "🔴")
        enter = "✅ 入场信号" if (s["score"] >= 7 and market_ok) else ""
        print(f"{pos_label}{name:<9} {s['close']:>8.2f} {s['close_vs_ma10']:>+8.1f}% {s['vol_ratio']:>5.2f}x {s['trend_5d']:>+7.1f}% {s['trend_10d']:>+7.1f}% {s['score']:>5d} {status} {notes_str} {enter}")

    # 建议
    print(f"\n{'='*60}")
    print("【操作建议】")
    if not market_ok:
        print("大盘在MA10下方 → 观望，不开新仓")
    else:
        strong = [n for n, _, s in results if s["score"] >= 7]
        weak = [n for n, _, s in results if s["score"] < 4]
        if strong:
            print(f"重点关注: {', '.join(strong)}")
        if weak:
            print(f"走弱观察: {', '.join(weak)}")
        if not strong and not weak:
            print("选股池无明显信号，维持现状")

    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_watch()
