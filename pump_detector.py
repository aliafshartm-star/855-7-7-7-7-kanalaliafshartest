"""
Pump Detector v5 — دو امتیاز جدا:
  🌱 Growth Score (0-100) — رشد پایدار
  🚀 Pump Score (0-100) — پامپ سریع
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


# ═══════════════════════════════════════════
# ابزارها
# ═══════════════════════════════════════════

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


# ═══════════════════════════════════════════
# کش‌ها
# ═══════════════════════════════════════════

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


# ═══════════════════════════════════════════
# 🌱 GROWTH SCORE (0-100)
# ═══════════════════════════════════════════

def detect_accumulation_phase(df):
    """فاز Accumulation — رنج فشرده قبل رشد"""
    score = 0
    reasons = []
    if len(df) < 90:
        return 0, reasons

    # رنج ۹۰ کندل (۱۵ روز)
    range_high = df["high"].tail(90).max()
    range_low = df["low"].tail(90).min()
    if range_low <= 0:
        return 0, reasons

    range_pct = (range_high - range_low) / range_low
    current = df["close"].iloc[-1]
    position = (current - range_low) / (range_high - range_low) if range_high > range_low else 0.5

    # ۱. رنج فشرده (۵-۲۰٪)
    if 0.05 <= range_pct <= 0.20:
        score += 10
        reasons.append(f"رنج فشرده ({range_pct*100:.1f}%) — آماده انفجار")
    elif range_pct < 0.05:
        score += 5
        reasons.append("رنج خیلی فشرده")
    elif range_pct > 0.35:
        score -= 5

    # ۲. قیمت تو میانه رنج
    if 0.35 <= position <= 0.65:
        score += 10
        reasons.append("قیمت در میانه رنج")
    elif position > 0.85:
        score -= 8
        reasons.append("نزدیک سقف رنج — خطر fake")
    elif position < 0.20:
        score += 5
        reasons.append("نزدیک کف رنج")

    # ۳. فاصله مناسب تا سقف
    distance_to_high = (range_high - current) / current if current > 0 else 0
    if 0.03 <= distance_to_high <= 0.15:
        score += 5
        reasons.append("فاصله مناسب تا سقف رنج")

    return min(25, max(0, score)), reasons


def detect_volume_pattern_growth(df):
    """الگوی حجم برای رشد — آروم ولی صعودی"""
    score = 0
    reasons = []
    if len(df) < 60:
        return 0, reasons

    vol_7d = df["volume"].tail(42).mean()
    vol_30d = df["volume"].tail(180).mean()

    # حجم آروم صعودی (نه spike)
    if vol_30d > 0:
        ratio = vol_7d / vol_30d
        if 1.15 <= ratio <= 1.8:
            score += 10
            reasons.append(f"حجم آروم صعودی ({ratio:.1f}x)")
        elif ratio > 2.5:
            score -= 5
        elif ratio < 0.8:
            score -= 3

    # OBV صعودی (تجمع پنهانی)
    obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    if len(obv) >= 20:
        obv_start = obv.iloc[-20]
        if obv_start != 0:
            obv_slope = (obv.iloc[-1] - obv_start) / abs(obv_start)
            if obv_slope > 0.05:
                score += 10
                reasons.append("OBV صعودی (تجمع پول)")

    return min(20, max(0, score)), reasons


def detect_structure_growth(df):
    """ساختار صعودی — Higher Lows + EMA"""
    score = 0
    reasons = []
    if len(df) < 60:
        return 0, reasons

    closes = df["close"]
    price = closes.iloc[-1]
    e20 = ema(closes, 20).iloc[-1]
    e50 = ema(closes, 50).iloc[-1]

    # EMA
    if price > e20 > e50:
        score += 10
        reasons.append("روند صعودی (EMA20 > EMA50)")
    elif price > e20:
        score += 5
        reasons.append("قیمت بالای EMA20")

    # Higher Lows
    swing_lows = find_swing_lows(df, lookback=5)
    if len(swing_lows) >= 3:
        last3 = swing_lows[-3:]
        if last3[0]["price"] < last3[1]["price"] < last3[2]["price"]:
            score += 10
            reasons.append("Higher Lows منظم")

    return min(20, max(0, score)), reasons


def detect_momentum_growth(df):
    """مومنتوم آروم — RSI میانه، MACD صعودی"""
    score = 0
    reasons = []
    if len(df) < 30:
        return 0, reasons

    closes = df["close"]

    # RSI میانه
    rsi_val = rsi(closes, 14).iloc[-1]
    if not np.isnan(rsi_val):
        if 45 <= rsi_val <= 60:
            score += 7
            reasons.append(f"RSI متعادل ({rsi_val:.0f})")
        elif 35 <= rsi_val < 45:
            score += 5
            reasons.append(f"RSI پایین ({rsi_val:.0f})")

    # MACD
    macd_line, signal_line, histogram = macd(closes)
    if len(histogram) >= 2:
        if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
            score += 8
            reasons.append("MACD کراس صعودی")
        elif histogram.iloc[-1] > 0:
            score += 3

    return min(15, max(0, score)), reasons


def detect_context_growth(df, symbol, btc_df=None):
    """Context — BTC، F&G، نقدینگی، RS"""
    score = 0
    reasons = []

    # BTC
    btc = get_btc_change()
    btc_change = btc["change"]
    if btc_change > 1:
        score += 5
        reasons.append(f"BTC مثبت ({btc_change:+.1f}%)")
    elif btc_change > -1:
        score += 3
    elif btc_change < -3:
        score -= 5

    # Fear & Greed
    fng = get_fng()
    if 25 <= fng <= 65:
        score += 3
    elif fng < 25:
        score += 5
    elif fng > 80:
        score -= 3

    # RS vs BTC
    if btc_df is not None and len(btc_df) >= 42 and len(df) >= 42:
        try:
            btc_change_7d = (btc_df["close"].iloc[-1] / btc_df["close"].iloc[-42]) - 1
            coin_change_7d = (df["close"].iloc[-1] / df["close"].iloc[-42]) - 1
            rs = coin_change_7d - btc_change_7d
            if rs > 0.05:
                score += 7
                reasons.append(f"RS vs BTC: +{rs*100:.1f}%")
            elif rs > 0.02:
                score += 3
        except Exception:
            pass

    return min(20, max(0, score)), reasons


def detect_growth_score(symbol, cg_id, df, ticker_info, btc_df=None):
    """امتیاز کامل رشد (0-100)"""
    forces = {}
    all_reasons = []

    s1, r1 = detect_accumulation_phase(df)
    forces["Accumulation"] = s1
    all_reasons.extend(r1)

    s2, r2 = detect_volume_pattern_growth(df)
    forces["Volume"] = s2
    all_reasons.extend(r2)

    s3, r3 = detect_structure_growth(df)
    forces["Structure"] = s3
    all_reasons.extend(r3)

    s4, r4 = detect_momentum_growth(df)
    forces["Momentum"] = s4
    all_reasons.extend(r4)

    s5, r5 = detect_context_growth(df, symbol, btc_df)
    forces["Context"] = s5
    all_reasons.extend(r5)

    total = sum(forces.values())

    return total, forces, all_reasons


# ═══════════════════════════════════════════
# 🚀 PUMP SCORE (0-100)
# ═══════════════════════════════════════════

def detect_volume_spike(df):
    """Volume Spike — نشانه پامپ"""
    score = 0
    reasons = []
    if len(df) < 20:
        return 0, reasons

    last_vol = df["volume"].iloc[-1]
    avg_vol = df["volume"].iloc[-20:-1].mean()

    if avg_vol > 0:
        ratio = last_vol / avg_vol
        if ratio >= 5.0:
            score += 20
            reasons.append(f"Volume Spike قوی ({ratio:.1f}x)")
        elif ratio >= 3.0:
            score += 15
            reasons.append(f"Volume Spike ({ratio:.1f}x)")
        elif ratio >= 2.0:
            score += 8
            reasons.append(f"حجم بالای میانگین ({ratio:.1f}x)")

    # کندل صعودی
    last = df.iloc[-1]
    if last["close"] > last["open"]:
        score += 5

    return min(25, score), reasons


def detect_breakout(df):
    """شکست مقاومت ۲۰ روزه"""
    score = 0
    reasons = []
    if len(df) < 40:
        return 0, reasons

    recent_high = df["high"].iloc[-40:-2].max()
    last_close = df["close"].iloc[-1]
    prev_close = df["close"].iloc[-2]

    # کندل قبلی بالای مقاومت بسته شده
    if prev_close > recent_high * 0.99:
        score += 10
        reasons.append("شکست مقاومت ۲۰ روزه")

    # ادامه داره
    if last_close > recent_high:
        score += 10
        reasons.append("بالای مقاومت پایدار")

    return min(20, score), reasons


def detect_momentum_pump(df):
    """مومنتوم قوی — RSI بالا ولی نه overbought"""
    score = 0
    reasons = []
    if len(df) < 30:
        return 0, reasons

    closes = df["close"]

    rsi_val = rsi(closes, 14).iloc[-1]
    if not np.isnan(rsi_val):
        if 55 <= rsi_val <= 70:
            score += 8
            reasons.append(f"RSI قوی ({rsi_val:.0f})")
        elif 70 < rsi_val <= 80:
            score += 3
        elif rsi_val > 85:
            score -= 10

    # MACD
    macd_line, signal_line, histogram = macd(closes)
    if len(histogram) >= 2:
        if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
            score += 7
            reasons.append("MACD کراس صعودی")
        elif histogram.iloc[-1] > histogram.iloc[-2] > 0:
            score += 5
            reasons.append("MACD صعودی")

    # Stochastic
    k, d = stochastic(df)
    if len(k) >= 1 and len(d) >= 1:
        k_last = k.iloc[-1]
        d_last = d.iloc[-1]
        if not np.isnan(k_last) and not np.isnan(d_last):
            if k_last < 30 and k_last > d_last:
                score += 5
                reasons.append("Stochastic سیگنال خرید")

    return min(20, max(0, score)), reasons


def detect_social_hype(symbol):
    """Hype و Trending"""
    score = 0
    reasons = []

    coin = symbol.replace("USDT", "").upper()
    trending = get_trending_coins()

    if coin in trending:
        score += 10
        reasons.append("ترند CoinGecko 🔥")
    else:
        score += 2

    # Buy Pressure
    try:
        url = f"{BINANCE_API}/klines"
        params = {"symbol": symbol, "interval": "4h", "limit": 6}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
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
                    score += 5
                    reasons.append(f"فشار خرید بالا ({buy_ratio:.0f}%)")
    except Exception:
        pass

    return min(15, score), reasons


def detect_context_pump(df, symbol, ticker_info):
    """Context پامپ — BTC، F&G، Liquidity"""
    score = 0
    reasons = []

    # BTC
    btc = get_btc_change()
    btc_change = btc["change"]
    if btc_change > 1:
        score += 8
        reasons.append(f"BTC صعودی ({btc_change:+.1f}%)")
    elif btc_change > -1:
        score += 5
    elif btc_change < -3:
        score -= 10

    # Fear & Greed
    fng = get_fng()
    if 30 <= fng <= 75:
        score += 5
    elif fng > 80:
        score -= 5
    elif fng < 25:
        score += 3

    # Liquidity
    volume_24h = ticker_info.get("volume_24h", 0)
    if volume_24h > 100_000_000:
        score += 7
        reasons.append("نقدینگی بالا")
    elif volume_24h > 50_000_000:
        score += 4

    return min(20, max(0, score)), reasons


def detect_pump_score(symbol, cg_id, df, ticker_info, btc_df=None):
    """امتیاز کامل پامپ (0-100)"""
    forces = {}
    all_reasons = []

    s1, r1 = detect_volume_spike(df)
    forces["VolumeSpike"] = s1
    all_reasons.extend(r1)

    s2, r2 = detect_breakout(df)
    forces["Breakout"] = s2
    all_reasons.extend(r2)

    s3, r3 = detect_momentum_pump(df)
    forces["Momentum"] = s3
    all_reasons.extend(r3)

    s4, r4 = detect_social_hype(symbol)
    forces["Social"] = s4
    all_reasons.extend(r4)

    s5, r5 = detect_context_pump(df, symbol, ticker_info)
    forces["Context"] = s5
    all_reasons.extend(r5)

    total = sum(forces.values())

    return total, forces, all_reasons


# ═══════════════════════════════════════════
# تحلیل کامل — هر دو امتیاز
# ═══════════════════════════════════════════

def analyze_coin(symbol, cg_id, df, ticker_info, btc_df=None):
    """تحلیل کامل — هر دو نوع سیگنال"""
    price = df["close"].iloc[-1]

    # 🌱 Growth
    growth_score, growth_forces, growth_reasons = detect_growth_score(
        symbol, cg_id, df, ticker_info, btc_df
    )

    # 🚀 Pump
    pump_score, pump_forces, pump_reasons = detect_pump_score(
        symbol, cg_id, df, ticker_info, btc_df
    )

    # تغییرات
    change_7d = 0
    if len(df) >= 42:
        change_7d = ((df["close"].iloc[-1] / df["close"].iloc[-42]) - 1) * 100

    # تارگت‌های Growth
    if symbol in ["BTCUSDT", "ETHUSDT"]:
        g_stop, g_tp1, g_tp2, g_tp3 = 0.03, 0.03, 0.06, 0.12
        p_stop, p_tp1, p_tp2, p_tp3 = 0.04, 0.05, 0.10, 0.20
    else:
        g_stop, g_tp1, g_tp2, g_tp3 = 0.05, 0.05, 0.10, 0.20
        p_stop, p_tp1, p_tp2, p_tp3 = 0.07, 0.10, 0.20, 0.40

    return {
        "symbol": symbol,
        "cg_id": cg_id,
        "price": float(price),
        "change_24h": ticker_info.get("change_24h", 0),
        "change_7d": float(change_7d),
        "volume_24h": ticker_info.get("volume_24h", 0),

        # 🌱 Growth
        "growth_score": growth_score,
        "growth_forces": growth_forces,
        "growth_reasons": growth_reasons,
        "growth_entry_low": round(price * 0.995, 8),
        "growth_entry_high": round(price * 1.005, 8),
        "growth_stop": round(price * (1 - g_stop), 8),
        "growth_tp1": round(price * (1 + g_tp1), 8),
        "growth_tp2": round(price * (1 + g_tp2), 8),
        "growth_tp3": round(price * (1 + g_tp3), 8),

        # 🚀 Pump
        "pump_score": pump_score,
        "pump_forces": pump_forces,
        "pump_reasons": pump_reasons,
        "pump_entry_low": round(price * 0.995, 8),
        "pump_entry_high": round(price * 1.005, 8),
        "pump_stop": round(price * (1 - p_stop), 8),
        "pump_tp1": round(price * (1 + p_tp1), 8),
        "pump_tp2": round(price * (1 + p_tp2), 8),
        "pump_tp3": round(price * (1 + p_tp3), 8),

        "atr": float(atr(df).iloc[-1]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════
# فیلترها
# ═══════════════════════════════════════════

def passes_growth_filters(coin):
    """فیلترهای Growth"""
    symbol = coin.get("symbol", "")
    base = symbol.replace("USDT", "")
    if base in STABLECOINS:
        return False

    if coin["volume_24h"] < 15_000_000:
        return False

    # Growth نمی‌خواد پامپ‌شده باشه
    if coin["change_24h"] > 5:
        return False
    if coin["change_24h"] < -15:
        return False
    if coin.get("change_7d", 0) > 20:
        return False

    return True


def passes_pump_filters(coin):
    """فیلترهای Pump"""
    symbol = coin.get("symbol", "")
    base = symbol.replace("USDT", "")
    if base in STABLECOINS:
        return False

    if coin["volume_24h"] < 20_000_000:
        return False

    # Pump می‌تونه پامپ‌شده باشه ولی نه خیلی زیاد
    if coin["change_24h"] > 12:
        return False
    if coin["change_24h"] < -10:
        return False
    if coin.get("change_7d", 0) > 35:
        return False

    return True


def get_growth_tier(score):
    if score >= 85:
        return "TIER 1"
    elif score >= 75:
        return "TIER 2"
    elif score >= 65:
        return "TIER 3"
    return "NO SIGNAL"


def get_pump_tier(score):
    if score >= 85:
        return "TIER 1"
    elif score >= 75:
        return "TIER 2"
    elif score >= 65:
        return "TIER 3"
    return "NO SIGNAL"