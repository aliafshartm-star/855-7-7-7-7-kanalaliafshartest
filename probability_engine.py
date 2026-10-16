"""
Probability Engine — محاسبه احتمال واقعی TP1/TP2
بر اساس داده‌های بازار، نه هاردکد
"""
import numpy as np
import logging

log = logging.getLogger(__name__)


def estimate_probability(analysis, df, atr_value, btc_change=0.0, fng=50):
    """
    محاسبه احتمال TP1 و TP2 بر اساس داده‌های واقعی

    پارامترها:
    - analysis: dict خروجی analyze_coin
    - df: DataFrame کندل‌ها
    - atr_value: ATR فعلی
    - btc_change: تغییر 24h بیت‌کوین
    - fng: Fear & Greed Index

    Returns:
    - tp1_prob: احتمال TP1 (0-100)
    - tp2_prob: احتمال TP2 (0-100)
    - factors: لیست عوامل موثر
    """
    price = analysis["price"]
    tp1 = analysis["tp1"]
    tp2 = analysis["tp2"]
    stop = analysis["stop"]
    score = analysis["score"]
    forces = analysis["forces"]

    # ═══════════════════════════════════════════
    # ۱. فاصله TP از قیمت (نسبت به ATR)
    # ═══════════════════════════════════════════
    tp1_dist_pct = (tp1 - price) / price
    tp2_dist_pct = (tp2 - price) / price
    atr_pct = atr_value / price if price > 0 else 0.05

    tp1_atr_ratio = tp1_dist_pct / atr_pct if atr_pct > 0 else 10
    tp2_atr_ratio = tp2_dist_pct / atr_pct if atr_pct > 0 else 10

    # هرچی TP نزدیک‌تر به ATR، احتمال بیشتر
    # 1.5 ATR = راحت / 5 ATR = سخت
    if tp1_atr_ratio <= 1.5:
        tp1_dist_score = 25
    elif tp1_atr_ratio <= 2.5:
        tp1_dist_score = 18
    elif tp1_atr_ratio <= 3.5:
        tp1_dist_score = 10
    elif tp1_atr_ratio <= 5:
        tp1_dist_score = 3
    else:
        tp1_dist_score = 0

    if tp2_atr_ratio <= 2.5:
        tp2_dist_score = 20
    elif tp2_atr_ratio <= 4:
        tp2_dist_score = 12
    elif tp2_atr_ratio <= 6:
        tp2_dist_score = 5
    else:
        tp2_dist_score = 0

    # ═══════════════════════════════════════════
    # ۲. قدرت روند (ADX + EMA)
    # ═══════════════════════════════════════════
    trend_score = forces.get("Trend", 0)
    if trend_score >= 15:
        trend_bonus = 15
    elif trend_score >= 10:
        trend_bonus = 10
    elif trend_score >= 5:
        trend_bonus = 5
    else:
        trend_bonus = 0

    # ═══════════════════════════════════════════
    # ۳. Momentum (RSI + MACD)
    # ═══════════════════════════════════════════
    momentum_score = forces.get("Momentum", 0)
    if momentum_score >= 12:
        momentum_bonus = 10
    elif momentum_score >= 8:
        momentum_bonus = 6
    elif momentum_score >= 5:
        momentum_bonus = 3
    else:
        momentum_bonus = 0

    # ═══════════════════════════════════════════
    # ۴. فشار خرید (Buy Pressure)
    # ═══════════════════════════════════════════
    buy_pressure = forces.get("BuyPressure", 0)
    if buy_pressure >= 12:
        bp_bonus = 8
    elif buy_pressure >= 8:
        bp_bonus = 5
    elif buy_pressure >= 5:
        bp_bonus = 2
    else:
        bp_bonus = 0

    # ═══════════════════════════════════════════
    # ۵. وضعیت بازار (Regime)
    # ═══════════════════════════════════════════
    regime_score = forces.get("Regime", 0)
    if regime_score >= 15:
        regime_bonus = 10
    elif regime_score >= 10:
        regime_bonus = 5
    elif regime_score >= 5:
        regime_bonus = 0
    else:
        regime_bonus = -10  # بازار خرابه

    # ═══════════════════════════════════════════
    # ۶. حجم (Volume)
    # ═══════════════════════════════════════════
    vol_score = forces.get("Volume", 0)
    if vol_score >= 15:
        vol_bonus = 8
    elif vol_score >= 10:
        vol_bonus = 4
    elif vol_score >= 5:
        vol_bonus = 2
    else:
        vol_bonus = 0

    # ═══════════════════════════════════════════
    # ۷. بایاس BTC (سنگین)
    # ═══════════════════════════════════════════
    if btc_change > 2:
        btc_bonus = 10
    elif btc_change > 0.5:
        btc_bonus = 5
    elif btc_change > -1:
        btc_bonus = 0
    elif btc_change > -3:
        btc_bonus = -10
    else:
        btc_bonus = -25  # BTC ریخته، احتمال کم

    # ═══════════════════════════════════════════
    # ۸. Fear & Greed
    # ═══════════════════════════════════════════
    if 25 <= fng <= 65:
        fng_bonus = 5
    elif fng < 25:
        fng_bonus = 8
    elif fng > 80:
        fng_bonus = -8
    else:
        fng_bonus = 0

    # ═══════════════════════════════════════════
    # محاسبه احتمال نهایی
    # ═══════════════════════════════════════════
    # پایه ۴۵٪
    base_tp1 = 45
    base_tp2 = 30

    # عوامل موثر
    tp1_factors = (
        tp1_dist_score +  # فاصله ATR
        trend_bonus +
        momentum_bonus +
        bp_bonus +
        vol_bonus
    )

    tp2_factors = (
        tp2_dist_score +
        trend_bonus +
        momentum_bonus +
        bp_bonus +
        vol_bonus
    )

    # BTC و Regime و FNG
    global_factors = regime_bonus + btc_bonus + fng_bonus

    tp1_prob = base_tp1 + tp1_factors + global_factors
    tp2_prob = base_tp2 + tp2_factors + global_factors

    # محدودیت (5-90)
    tp1_prob = max(5, min(90, tp1_prob))
    tp2_prob = max(5, min(85, tp2_prob))

    # TP2 همیشه کمتر از TP1
    if tp2_prob >= tp1_prob:
        tp2_prob = tp1_prob - 15

    # ═══════════════════════════════════════════
    # دلایل
    # ═══════════════════════════════════════════
    factors = []

    if tp1_atr_ratio <= 2:
        factors.append(f"TP نزدیک ({tp1_atr_ratio:.1f}x ATR)")
    elif tp1_atr_ratio > 4:
        factors.append(f"TP دور ({tp1_atr_ratio:.1f}x ATR)")

    if trend_score >= 12:
        factors.append("روند قوی")
    if momentum_score >= 10:
        factors.append("مومنتوم قوی")
    if buy_pressure >= 10:
        factors.append("فشار خرید بالا")
    if btc_change > 1:
        factors.append("BTC صعودی")
    elif btc_change < -2:
        factors.append("BTC نزولی")

    return round(tp1_prob), round(tp2_prob), factors