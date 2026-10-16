"""
Pump Detector v4 — ۷ نیرو
"""
import logging
import time
from datetime import datetime, timezone

import requests
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

BINANCE_API = "https://data-api.binance.vision/api/v3"
COINGECKO_API = "https://api.coingecko.com/api/v3"

STABLECOINS = ["USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP", "USTC", "USDD", "PYUSD"]


def candles_to_df(candles):
    df = pd.DataFrame(candles)
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df = df.set_index("time")
    return df


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def adx_calc(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    plus_dm = h.diff().where((h.diff() > -l.diff()) & (h.diff() > 0), 0)
    minus_dm = (-l.diff()).where((-l.diff() > h.diff()) & (-l.diff() > 0), 0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_val = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr_val
    minus_di = 100 * minus_dm.rolling(period).mean() / atr_val
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(period).mean()


def stochastic(df, k_period=14, d_period=3):
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d


def find_swing_lows(df, lookback=5):
    lows = []
    l = df["low"].values
    for i in range(lookback, len(df) - lookback):
        if l[i] == min(l[i - lookback:i + lookback + 1]):
            lows.append({"index": i, "price": l[i]})
    return lows


_cache = {
    "trending": {"data": None, "time": 0},
    "btc": {"data": None, "time": 0},
    "fng": {"data": None, "time": 0},
    "dominance": {"data": None, "time": 0},
}


def get_trending_coins():
    now = time.time()
    if _cache["trending"]["data"] and (now - _cache["trending"]["time"]) < 1800:
        return _cache["trending"]["data"]
    try:
        r = requests.get(f"{COINGECKO_API}/search/trending", timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        result = [c["item"]["symbol"].upper() for c in data.get("coins", [])]
        _cache["trending"]["data"] = result
        _cache["trending"]["time"] = now
        return result
    except Exception:
        return []


def get_btc_change():
    now = time.time()
    if _cache["btc"]["data"] and (now - _cache["btc"]["time"]) < 300:
        return _cache["btc"]["data"]
    try:
        url = f"{BINANCE_API}/ticker/24hr"
        r = requests.get(url, params={"symbol": "BTCUSDT"}, timeout=10)
        if r.status_code != 200:
            return {"change": 0, "price": 0}
        data = r.json()
        result = {"change": float(data["priceChangePercent"]), "price": float(data["lastPrice"])}
        _cache["btc"]["data"] = result
        _cache["btc"]["time"] = now
        return result
    except Exception:
        return {"change": 0, "price": 0}


def get_fng():
    now = time.time()
    if _cache["fng"]["data"] and (now - _cache["fng"]["time"]) < 3600:
        return _cache["fng"]["data"]
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        data = r.json()
        result = int(data["data"][0]["value"])
        _cache["fng"]["data"] = result
        _cache["fng"]["time"] = now
        return result
    except Exception:
        return 50


def get_btc_dominance():
    now = time.time()
    if _cache["dominance"]["data"] and (now - _cache["dominance"]["time"]) < 1800:
        return _cache["dominance"]["data"]
    try:
        r = requests.get(f"{COINGECKO_API}/global", timeout=10)
        data = r.json()
        result = float(data["data"]["market_cap_percentage"]["btc"])
        _cache["dominance"]["data"] = result
        _cache["dominance"]["time"] = now
        return result
    except Exception:
        return 50.0


def detect_volume_accumulation(df):
    score = 0
    reasons = []
    if len(df) < 60:
        return 0, reasons

    vol_7d = df["volume"].tail(42).mean()
    vol_30d = df["volume"].tail(180).mean()
    if vol_30d > 0:
        ratio = vol_7d / vol_30d
        if ratio > 1.5:
            score += 6
            reasons.append(f"حجم ۷ روزه {ratio:.1f}x میانگین")
        elif ratio > 1.2:
            score += 4
            reasons.append(f"حجم در حال افزایش ({ratio:.1f}x)")

    obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    obv_tail = obv.tail(20)
    if obv_tail.iloc[0] != 0:
        obv_slope = (obv_tail.iloc[-1] - obv_tail.iloc[0]) / abs(obv_tail.iloc[0])
        if obv_slope > 0.1:
            score += 5
            reasons.append("OBV صعودی (تجمع پول)")

    swing_lows = find_swing_lows(df, lookback=5)
    if len(swing_lows) >= 3:
        last3 = swing_lows[-3:]
        if last3[0]["price"] < last3[1]["price"] < last3[2]["price"]:
            score += 5
            reasons.append("Higher Lows صعودی")

    recent_low = df["low"].tail(5).min()
    prev_low = df["low"].tail(30).head(25).min()
    if prev_low > 0 and recent_low > prev_low * 1.01:
        score += 4
        reasons.append("کف‌های اخیر بالاتر")

    return min(20, score), reasons


def detect_trend_strength(df, symbol, btc_df=None):
    score = 0
    reasons = []
    if len(df) < 60:
        return 0, reasons

    closes = df["close"]
    price = closes.iloc[-1]
    e20 = ema(closes, 20).iloc[-1]
    e50 = ema(closes, 50).iloc[-1]

    if price > e20 > e50:
        score += 6
        reasons.append("روند صعودی (EMA20 > EMA50)")
    elif price > e20:
        score += 3
        reasons.append("قیمت بالای EMA20")

    adx_val = adx_calc(df, 14).iloc[-1]
    if not np.isnan(adx_val):
        if adx_val > 30:
            score += 5
            reasons.append(f"ADX قوی ({adx_val:.0f})")
        elif adx_val > 25:
            score += 3
            reasons.append(f"ADX متوسط ({adx_val:.0f})")

    if btc_df is not None and len(btc_df) >= 42 and len(df) >= 42:
        try:
            btc_change = (btc_df["close"].iloc[-1] / btc_df["close"].iloc[-42]) - 1
            coin_change = (df["close"].iloc[-1] / df["close"].iloc[-42]) - 1
            rs = coin_change - btc_change
            if rs > 0.10:
                score += 6
                reasons.append(f"RS vs BTC: +{rs*100:.1f}%")
            elif rs > 0.03:
                score += 4
                reasons.append(f"RS vs BTC: +{rs*100:.1f}%")
            elif rs < -0.05:
                score -= 3
        except Exception:
            pass

    if len(df) >= 42:
        change_7d = (closes.iloc[-1] / closes.iloc[-42]) - 1
        if change_7d > 0.10:
            score += 3
        elif change_7d > 0.03:
            score += 2

    return max(0, min(20, score)), reasons


def detect_momentum(df):
    score = 0
    reasons = []
    if len(df) < 30:
        return 0, reasons

    closes = df["close"]

    rsi_val = rsi(closes, 14).iloc[-1]
    if not np.isnan(rsi_val):
        if 45 <= rsi_val <= 65:
            score += 4
            reasons.append(f"RSI متعادل ({rsi_val:.0f})")
        elif 30 <= rsi_val < 45:
            score += 6
            reasons.append(f"RSI پایین ({rsi_val:.0f})")

    macd_line, signal_line, histogram = macd(closes)
    if len(histogram) >= 2:
        if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
            score += 5
            reasons.append("MACD کراس صعودی")
        elif histogram.iloc[-1] > 0:
            score += 2
            reasons.append("MACD مثبت")

    k, d = stochastic(df)
    if len(k) >= 1 and len(d) >= 1:
        k_last = k.iloc[-1]
        d_last = d.iloc[-1]
        if not np.isnan(k_last) and not np.isnan(d_last):
            if k_last < 25 and k_last > d_last:
                score += 5
                reasons.append("Stochastic — سیگنال خرید")
            elif k_last > 75 and k_last < d_last:
                score -= 3

    return max(0, min(20, score)), reasons


def detect_market_regime():
    score = 0
    reasons = []

    btc = get_btc_change()
    change = btc["change"]

    if change > 1:
        score += 6
        reasons.append(f"BTC مثبت ({change:+.1f}%)")
    elif change > -1:
        score += 4
        reasons.append(f"BTC پایدار ({change:+.1f}%)")
    elif change > -3:
        score += 2
    else:
        score -= 4
        reasons.append(f"BTC نزولی ({change:+.1f}%)")

    fng = get_fng()
    if 25 <= fng <= 65:
        score += 5
        reasons.append(f"Fear & Greed: {fng}")
    elif fng < 25:
        score += 7
        reasons.append(f"F&G: {fng} (فرصت)")
    elif fng > 80:
        score -= 2

    dom = get_btc_dominance()
    if dom < 50:
        score += 5
        reasons.append(f"BTC Dom پایین ({dom:.1f}%) — آلتseason")
    elif dom > 60:
        score -= 2

    return max(0, min(20, score)), reasons


def detect_liquidity(symbol, volume_24h):
    score = 0
    reasons = []

    if volume_24h > 100_000_000:
        score += 10
        reasons.append("نقدینگی بسیار بالا (>$100M)")
    elif volume_24h > 50_000_000:
        score += 8
        reasons.append("نقدینگی بالا (>$50M)")
    elif volume_24h > 20_000_000:
        score += 5
        reasons.append("نقدینگی متوسط (>$20M)")
    else:
        score += 2

    try:
        url = f"{BINANCE_API}/ticker/bookTicker"
        r = requests.get(url, params={"symbol": symbol}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            bid = float(data.get("bidPrice", 0))
            ask = float(data.get("askPrice", 0))
            if bid > 0 and ask > 0:
                spread = (ask - bid) / bid * 100
                if spread < 0.05:
                    score += 10
                    reasons.append(f"اسپرد بسیار کم ({spread:.3f}%)")
                elif spread < 0.15:
                    score += 6
                    reasons.append(f"اسپرد کم ({spread:.3f}%)")
                else:
                    score -= 3
    except Exception:
        pass

    return max(0, min(20, score)), reasons


def detect_buy_sell_pressure(symbol):
    score = 0
    reasons = []

    try:
        url = f"{BINANCE_API}/klines"
        params = {"symbol": symbol, "interval": "4h", "limit": 6}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return 5, ["داده فشار خرید/فروش موجود نیست"]

        data = r.json()
        total_buy = 0
        total_sell = 0

        for candle in data:
            taker_buy = float(candle[9])
            total_volume = float(candle[5])
            total_buy += taker_buy
            total_sell += (total_volume - taker_buy)

        if total_buy + total_sell > 0:
            buy_ratio = total_buy / (total_buy + total_sell) * 100

            if buy_ratio > 60:
                score += 15
                reasons.append(f"فشار خرید قوی ({buy_ratio:.0f}%)")
            elif buy_ratio > 55:
                score += 10
                reasons.append(f"فشار خرید ({buy_ratio:.0f}%)")
            elif buy_ratio > 50:
                score += 5
                reasons.append(f"فشار خرید ملایم ({buy_ratio:.0f}%)")
            elif buy_ratio < 40:
                score -= 5
                reasons.append(f"فشار فروش ({buy_ratio:.0f}%)")
    except Exception as e:
        log.warning(f"Buy/Sell pressure error: {e}")
        return 5, []

    return max(0, min(20, score)), reasons


def detect_trending(symbol):
    score = 0
    reasons = []

    coin = symbol.replace("USDT", "").upper()
    trending = get_trending_coins()

    if coin in trending:
        score += 15
        reasons.append("ترند CoinGecko")
    else:
        score += 3

    return max(0, min(20, score)), reasons


def analyze_coin(symbol, cg_id, df, ticker_info, btc_df=None):
    forces = {}
    all_reasons = []

    s1, r1 = detect_volume_accumulation(df)
    forces["Volume"] = s1
    all_reasons.extend(r1)

    s2, r2 = detect_trend_strength(df, symbol, btc_df)
    forces["Trend"] = s2
    all_reasons.extend(r2)

    s3, r3 = detect_momentum(df)
    forces["Momentum"] = s3
    all_reasons.extend(r3)

    s4, r4 = detect_market_regime()
    forces["Regime"] = s4
    all_reasons.extend(r4)

    s5, r5 = detect_liquidity(symbol, ticker_info.get("volume_24h", 0))
    forces["Liquidity"] = s5
    all_reasons.extend(r5)

    s6, r6 = detect_buy_sell_pressure(symbol)
    forces["BuyPressure"] = s6
    all_reasons.extend(r6)

    s7, r7 = detect_trending(symbol)
    forces["Trending"] = s7
    all_reasons.extend(r7)

    total = sum(forces.values())

    price = df["close"].iloc[-1]
    atr_val = atr(df).iloc[-1]

    # تارگت‌های پویا
    if symbol in ["BTCUSDT", "ETHUSDT"]:
        stop_pct = 0.03    # -3%
        tp1_pct = 0.03     # +3%
        tp2_pct = 0.06     # +6%
    else:
        stop_pct = 0.05    # -5%
        tp1_pct = 0.05     # +5%
        tp2_pct = 0.10     # +10%

    entry_low = price * 0.995
    entry_high = price * 1.005
    stop = price * (1 - stop_pct)
    tp1 = price * (1 + tp1_pct)
    tp2 = price * (1 + tp2_pct)
    tp3 = tp2  # حذف شد

    change_7d = 0
    if len(df) >= 42:
        change_7d = ((df["close"].iloc[-1] / df["close"].iloc[-42]) - 1) * 100

    return {
        "symbol": symbol,
        "cg_id": cg_id,
        "price": float(price),
        "change_24h": ticker_info.get("change_24h", 0),
        "change_7d": float(change_7d),
        "volume_24h": ticker_info.get("volume_24h", 0),
        "score": total,
        "forces": forces,
        "reasons": all_reasons,
        "entry_low": round(entry_low, 8),
        "entry_high": round(entry_high, 8),
        "stop": round(stop, 8),
        "tp1": round(tp1, 8),
        "tp2": round(tp2, 8),
        "tp3": round(tp3, 8),
        "atr": float(atr_val),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def passes_filters(coin):
    symbol = coin.get("symbol", "")
    base = symbol.replace("USDT", "")
    if base in STABLECOINS:
        return False

    if coin["volume_24h"] < 15_000_000:
        return False
    if coin["change_24h"] > 5:
        return False
    if coin["change_24h"] < -15:
        return False
    if coin.get("change_7d", 0) > 30:
        return False

    entry_mid = (coin["entry_low"] + coin["entry_high"]) / 2
    risk = (entry_mid - coin["stop"]) / entry_mid
    reward = (coin["tp1"] - entry_mid) / entry_mid
    if risk > 0 and (reward / risk) < 0.9:
        return False

    return True


def get_signal_tier(score):
    if score >= 110:
        return "TIER 1"
    elif score >= 95:
        return "TIER 2"
    elif score >= 80:
        return "TIER 3"
    return "NO SIGNAL"