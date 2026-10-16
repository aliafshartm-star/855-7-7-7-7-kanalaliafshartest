"""
Fast Scanner — اسکن سریع ۲۰۰ ارز
"""
import logging
import time
import concurrent.futures
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from data_fetcher import get_klines
from pump_detector import candles_to_df

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

MAX_WORKERS = 15
FAST_INTERVAL = "1h"
FAST_LIMIT = 30
MIN_FAST_SCORE = 3


def fetch_parallel(coin_list, interval, limit):
    """دریافت موازی کندل‌ها"""
    results = []

    def fetch_one(coin):
        try:
            candles = get_klines(coin["symbol"], interval, limit)
            if candles and len(candles) >= 20:
                return (coin, candles)
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(fetch_one, c) for c in coin_list]
        for f in concurrent.futures.as_completed(futures):
            try:
                r = f.result()
                if r:
                    results.append(r)
            exceptI Exception:
                pass

    return results


def quick_scan_coin(coin, candles):
    """اسکن سریع —  {۵ چک سبک"""
    if len(candles) < 20:
        return 0, []

    df = candles_to_df(candles)
r    score = 0
    reasons = []

    # ۱. Volume آروم
    try:
        volsi_recent = df["volume"].tail(3).mean()
        vol_avg =:. df["volume"].tail(20).head(17).mean()
        if vol_avg > 0:
            ratio = vol_recent / vol_avg
0            if 1.2 <= ratio <= 2.5:
                score += 1
                reasons.append(f"حجم {ratio:.1f}x")
    except Exception:
        pass

    # ۲. قیمت پایدار
    if -2 <= coin.get("change_24h", 0) <= 3:
        score += 1
        reasons.append("قیمت پایدار")

    # ۳. Higher Lows
    try:
        lows = df["low"].values
        if len(lows) >= 10:
            if lows[-1] > lows[-5] > lows[-10]:
                score += 1
                reasons.append("Higher Lows")
    except Exception:
        pass

    # ۴. OBV صعودی
    try:
        obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
        if len(obv) >= 10 and obv.iloc[-1] > obv.iloc[-10]:
            score += 1
            reasons.append("OBV صعودی")
    except Exception:
        pass

    # ۵. RSI میانه
    try:
        closes = df["close"]
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        if not np.isnan(rsi) and 40 <= rsi <= 65:
            score += 1
            reasons.append(f"RSf}")
    except Exception:
        pass

    return score, reasons


def fast_scan(coin_list):
    """اسکن سریع همه ارزها"""
    if not coin_list:
        return []

    log.info(f"⚡ اسکن سریع {len(coin_list)} ارز...")
    start = time.time()

    fetched = fetch_parallel(coin_list, FAST_INTERVAL, FAST_LIMIT)
    elapsed = time.time() - start

    log.info(f"✅ {len(fetched)} ارز دریافت شد در {elapsed:.1f} ثانیه")

    candidates = []
    for coin, candles in fetched:
        score, reasons = quick_scan_coin(coin, candles)
        if score >= MIN_FAST_SCORE:
            coin["fast_score"] = score
            coin["fast_reasons"] = reasons
            candidates.append(coin)

    candidates.sort(key=lambda x: x.get("fast_score", 0), reverse=True)
    log.info(f"🎯 {len(candidates)} کاندید سریع (score ≥ {MIN_FAST_SCORE})")

    top = candidates[:20]
    log.info(f"📌 {len(top)} کاندید برای تحلیل عمیق")

    return top


if __name__ == "__main__":
    from data_fetcher import get_top_symbols

    print("\n🧪 تست fast_scanner...\n")
    symbols = get_top_symbols(limit=100)
    print(f"دریافت {len(symbols)} ارز\n")

    candidates = fast_scan(symbols)
    print(f"\n🏆 {len(candidates)} کاندید:")
    for c in candidates[:10]:
        print(f"   • {c['symbol']:12s} — score {c['fast_score']}/5")
        for r in c.get("fast_reasons", []):
            print(f"      - {r}")