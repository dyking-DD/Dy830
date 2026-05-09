#!/usr/bin/env python3
"""
TrendMatrix 板块轮动分析（轻量版）
减少API调用次数，批量获取数据
"""
import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/home/ubuntu/TrendMatrix')

# 选股池 + 板块归属
STOCKS = {
    "sz.000977": ("浪潮信息", "算力基建"),
    "sz.002371": ("北方华创", "半导体"),
    "sz.002837": ("英维克",   "液冷散热"),
    "sh.603019": ("中科曙光", "算力基建"),
    "sh.688012": ("中微公司", "半导体"),
    "sz.300274": ("阳光电源", "储能"),
}

def fetch_kline(code: str, days: int = 30) -> pd.DataFrame:
    bs.login()
    rs = bs.query_history_k_data_plus(
        code, "date,close,volume",
        start_date=(datetime.now() - timedelta(days=days+15)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"),
        frequency="d"
    )
    data = []
    while rs.error_code == "0" and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    df = pd.DataFrame(data, columns=["date","close","volume"])
    for col in ["close","volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    return df

def run():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*65}")
    print(f"  TrendMatrix 板块轮动  {today}")
    print(f"{'='*65}")

    # 获取大盘数据
    mkt = fetch_kline("sh.000300", 25)
    if len(mkt) < 20:
        print("大盘数据不足")
        return
    mkt["ma10"] = mkt["close"].rolling(10).mean()
    mkt["ret20"] = mkt["close"].pct_change(20) * 100
    mkt_latest = mkt.iloc[-1]
    market_ret_20d = mkt_latest["ret20"] if not pd.isna(mkt_latest["ret20"]) else 0
    market_ma10_status = "🟢" if mkt_latest["close"] > mkt_latest["ma10"] else "🔴"

    print(f"\n大盘: 沪深300 {mkt_latest['close']:.2f}  {market_ma10_status}MA10 {mkt_latest['ma10']:.2f}")
    print(f"大盘20日涨跌: {market_ret_20d:+.2f}%")

    # 获取所有个股数据
    stock_data = {}
    for code in STOCKS:
        df = fetch_kline(code, 25)
        if len(df) >= 20:
            df["ma5"] = df["close"].rolling(5).mean()
            df["ret20"] = df["close"].pct_change(20) * 100
            df["vol_ma5"] = df["volume"].rolling(5).mean()
            vol_r = df["volume"].iloc[-1] / df["vol_ma5"].iloc[-1] if df["vol_ma5"].iloc[-1] > 0 else 1
            stock_data[code] = {
                "name": STOCKS[code][0],
                "sector": STOCKS[code][1],
                "close": df["close"].iloc[-1],
                "ret20": df["ret20"].iloc[-1] if not pd.isna(df["ret20"].iloc[-1]) else 0,
                "vol_ratio": vol_r,
                "above_ma5": df["close"].iloc[-1] > df["ma5"].iloc[-1],
            }

    # 按板块汇总
    sectors = {}
    for code, d in stock_data.items():
        sec = d["sector"]
        if sec not in sectors:
            sectors[sec] = {"rets": [], "vols": [], "stocks": []}
        sectors[sec]["rets"].append(d["ret20"])
        sectors[sec]["vols"].append(d["vol_ratio"])
        sectors[sec]["stocks"].append(d["name"])

    # 评分
    print(f"\n{'='*65}")
    print(f"{'板块':<10} {'20日涨跌':>10} {'量能':>8} {'成分股':>12} {'评分':>5} {'信号'}")
    print("-" * 65)

    sector_results = []
    for sec, d in sectors.items():
        avg_ret = np.mean(d["rets"])
        avg_vol = np.mean(d["vols"])
        beat = sum(1 for r in d["rets"] if r > market_ret_20d)

        score = 0
        if avg_ret > 8: score += 4
        elif avg_ret > 4: score += 3
        elif avg_ret > 0: score += 1
        else: score -= 2

        if avg_vol > 1.4: score += 3
        elif avg_vol > 1.15: score += 2
        elif avg_vol < 0.75: score -= 2

        if beat >= len(d["rets"]) * 0.7 and len(d["rets"]) >= 2: score += 2
        elif beat <= len(d["rets"]) * 0.3 and len(d["rets"]) >= 2: score -= 1

        emoji = "🟢" if score >= 7 else ("🟡" if score >= 4 else "🔴")
        vol_str = f"{avg_vol:.2f}x"
        stocks_str = "/".join(d["stocks"][:2])
        notes = []
        if avg_ret > 4: notes.append(f"+{avg_ret:.1f}%")
        if avg_vol > 1.3: notes.append(f"放量{avg_vol:.1f}x")
        if beat >= len(d["rets"]) * 0.7: notes.append("集体跑赢")
        note_str = " ".join(notes) if notes else "正常"

        print(f"{sec:<10} {avg_ret:>+9.1f}% {vol_str:>8} {stocks_str:>12} {score:>5d} {emoji} {note_str}")
        sector_results.append((sec, score, avg_ret, avg_vol, d["stocks"]))

    sector_results.sort(key=lambda x: x[1], reverse=True)

    # 大盘MA10结论
    print(f"\n大盘MA10: {market_ma10_status} {'→ 可做多' if market_ma10_status=='🟢' else '→ 观望'}")

    # 结论
    print(f"\n{'='*65}")
    print("【板块轮动结论】")
    strong = [x for x in sector_results if x[1] >= 7]
    mid = [x for x in sector_results if 4 <= x[1] < 7]
    weak = [x for x in sector_results if x[1] < 4]

    if strong:
        print(f"强势: {', '.join([x[0] for x in strong])}")
    if mid:
        print(f"震荡: {', '.join([x[0] for x in mid])}")
    if weak:
        print(f"弱势: {', '.join([x[0] for x in weak])}")

    print(f"\n{'='*65}")
    print("【选股池调整建议】")
    if strong:
        print("核心仓重点:")
        for s, sc, r, v, names in strong[:3]:
            print(f"  ★ {s}({','.join(names)}): 20日{r:+.1f}%")
    if mid:
        print("观察仓:")
        for s, sc, r, v, names in mid[:2]:
            print(f"  ○ {s}: 20日{r:+.1f}%")
    if weak:
        print("回避:")
        for s, sc, r, v, names in weak:
            print(f"  ✗ {s}: 20日{r:+.1f}%")

    print(f"\n{'='*65}")

if __name__ == "__main__":
    run()
