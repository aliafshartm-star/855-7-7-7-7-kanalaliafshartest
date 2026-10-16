"""
Probability Engine v2 — احتمال جدا برای:
  🌱 Growth Signal
  🚀 Pump Signal
بر اساس داده‌های واقعی بازار
"""
import numpy as np
import logging

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 🌱 احتمال موفقیت سیگنال رشد
# ═══════════════════════════════════════════

def estimate_growth_probability(coin, df, atr_value, btc_change=0.0, fng=50):
    """
    محاسبه احتمال TP1 و TP2 برای سیگنال رشد

    Returns:
        tp1_prob, tp2_prob, factors
    """
    price = coin["price"]
    tp1 = coin["growth_tp1"]
    tp2 = coin["growth_tp2"]
    score = coin["growth_score"]
    forces = coin["growth_forces"]

    # ۱. فاصله TP از قیمت (نسبت به ATR)
    tp1_dist_pct = (tp1 - price) / price
    tp2_dist_pct = (tp2 - price) / price
    atr_pct = atr_value / price if price > 0 else 0.05

    tp1_atr_ratio = tp1_dist_pct / atr_pct if atr_pct > 0 else 10
    tp2_atr_ratio = tp2_dist_pct / atr_pct if atr_pct > 0 else 10

    # TP1 نزدیک = احتمال بالا
    if tp1_atr_ratio <= 1.5:
        tp1_dist_score = 25
    elif tp1_atr_ratio <= 2.5:
        tp1_dist_score = 18
    elif tp1_atr_ratio <= 3.5:
        tp1_dist_score = 10
    else:
        tp1_dist_score = 3

    if tp2_atr_ratio <= 2.5:
        tp2_dist_score = 20
    elif tp2_atr_ratio <= 4:
        tp2_dist_score = 12
    else:
        tp2_dist_score = 5

    # ۲. Accumulation (وزن بالا برای Growth)
    accum_score = forces.get("Accumulation", 0)
    if accum_score >= 20:
        accum_bonus = 15
    elif accum_score >= 15:
        accum_bonus = 10
    elif accum_score >= 10:
        accum_bonus = 5
    else:
        accum_bonus = 0

    # ۳. Structure
    structure_score = forces.get("Structure", 0)
    if structure_score >= 15:
        structure_bonus = 12
    elif structure_score >= 10:
        structure_bonus = 8
    elif structure_score >= 5:
        structure_bonus = 4
    else:
        structure_bonus = 0

    # ۴. Volume (آروم، نه spike)
    vol_score = forces.get("Volume", 0)
    if vol_score >= 15:
        vol_bonus = 10
    elif vol_score >= 10:
        vol_bonus = 6
    elif vol_score >= 5:
        vol_bonus = 3
    else:
        vol_bonus = 0

    # ۵. Momentum آروم
    mom_score = forces.get("Momentum", 0)
    if mom_score >= 12:
        mom_bonus = 8
    elif mom_score >= 8:
        mom_bonus = 5
    elif mom_score >= 5:
        mom_bonus = 2
    else:
        mom_bonus = 0

    # ۶. Context
    ctx_score = forces.get("Context", 0)
    if ctx_score >= 15:
        ctx_bonus = 10
    elif ctx_score >= 10:
        ctx_bonus = 6
    elif ctx_score >= 5:
        ctx_bonus = 2
    else:
        ctx_bonus = 0

    # ۷. BTC bias
    if btc_change > 2:
        btc_bonus = 8
    elif btc_change > 0.5:
        btc_bonus = 4
    elif btc_change > -1:
        btc_bonus = 0
    elif btc_change > -3:
        btc_bonus = -10
    else:
        btc_bonus = -25

    # ۸. Fear & Greed
    if 25 <= fng <= 65:
        fng_bonus = 5
    elif fng < 25:
        fng_bonus = 8
    elif fng > 80:
        fng_bonus = -8
    else:
        fng_bonus = 0

    # محاسبه
    base_tp1 = 55  # پایه بالاتر چون Growth پایدارتره
    base_tp2 = 35

    tp1_factors = tp1_dist_score + accum_bonus + structure_bonus + vol_bonus + mom_bonus
    tp2_factors = tp2_dist_score + accum_bonus + structure_bonus + vol_bonus + mom_bonus

    global_factors = ctx_bonus + btc_bonus + fng_bonus

    tp1_prob = base_tp1 + tp1_factors + global_factors
    tp2_prob = base_tp2 + tp2_factors + global_factors

    tp1_prob = max(10, min(92, tp1_prob))
    tp2_prob = max(10, min(85, tp2_prob))

    if tp2_prob >= tp1_prob:
        tp2_prob = tp1_prob - 12

    # عوامل
    factors = []
    if tp1_atr_ratio <= 2:
        factors.append(f"TP نزدیک ({tp1_atr_ratio:.1f}x ATR)")
    if accum_score >= 15:
        factors.append("Accumulation قوی")
    if structure_score >= 12:
        factors.append("ساختار صعودی")
    if vol_score >= 12:
        factors.append("حجم صعودی")
    if btc_change > 1:
        factors.append("BTC صعودی")
    elif btc_change < -2:
        factors.append("BTC نزولی")

    return round(tp1_prob), round(tp2_prob), factors


# ═══════════════════════════════════════════
# 🚀 احتمال موفقیت سیگنال پامپ
# ═══════════════════════════════════════════

def estimate_pump_probability(coin, df, atr_value, btc_change=0.0, fng=50):
    """
    محاسبه احتمال TP1 و TP2 برای سیگنال پامپ

    Returns:
        tp1_prob, tp2_prob, factors
    """
    price = coin["price"]
    tp1 = coin["pump_tp1"]
    tp2 = coin["pump_tp2"]
    score = coin["pump_score"]
    forces = coin["pump_forces"]

    # ۱. فاصله TP (پامپ TP دورتره)
    tp1_dist_pct = (tp1 - price) / price
    tp2_dist_pct = (tp2 - price) / price
    atr_pct = atr_value / price if price > 0 else 0.05

    tp1_atr_ratio = tp1_dist_pct / atr_pct if atr_pct > 0 else 10
    tp2_atr_ratio = tp2_dist_pct / atr_pct if atr_pct > 0 else 10

    if tp1_atr_ratio <= 2.0:
        tp1_dist_score = 25
    elif tp1_atr_ratio <= 3.5:
        tp1_dist_score = 15
    elif tp1_atr_ratio <= 5:
        tp1_dist_score = 8
    else:
        tp1_dist_score = 2

    if tp2_atr_ratio <= 4:
        tp2_dist_score = 18
    elif tp2_atr_ratio <= 6:
        tp2_dist_score = 10
    else:
        tp2_dist_score = 3

    # ۲. Volume Spike (وزن بالا)
    vs_score = forces.get("VolumeSpike", 0)
    if vs_score >= 20:
        vs_bonus = 15
    elif vs_score >= 15:
        vs_bonus = 10
    elif vs_score >= 10:
        vs_bonus = 5
    else:
        vs_bonus = 0

    # ۳. Breakout
    breakout_score = forces.get("Breakout", 0)
    if breakout_score >= 15:
        breakout_bonus = 12
    elif breakout_score >= 10:
        breakout_bonus = 8
    elif breakout_score >= 5:
        breakout_bonus = 4
    else:
        breakout_bonus = 0

    # ۴. Momentum
    mom_score = forces.get("Momentum", 0)
    if mom_score >= 15:
        mom_bonus = 10
    elif mom_score >= 10:
        mom_bonus = 6
    elif mom_score >= 5:
        mom_bonus = 2
    else:
        mom_bonus = 0

    # ۵. Social
    social_score = forces.get("Social", 0)
    if social_score >= 12:
        social_bonus = 8
    elif social_score >= 8:
        social_bonus = 5
    elif social_score >= 4:
        social_bonus = 2
    else:
        social_bonus = 0

    # ۶. Context
    ctx_score = forces.get("Context", 0)
    if ctx_score >= 15:
        ctx_bonus = 8
    elif ctx_score >= 10:
        ctx_bonus = 5
    elif ctx_score >= 5:
        ctx_bonus = 2
    else:
        ctx_bonus = 0

    # ۷. BTC bias (برای پامپ حیاتی‌تر)
    if btc_change > 2:
        btc_bonus = 12
    elif btc_change > 0.5:
        btc_bonus = 5
    elif btc_change > -1:
        btc_bonus = 0
    elif btc_change > -3:
        btc_bonus = -15
    else:
        btc_bonus = -30

    # ۸. Fear & Greed (پامپ تو F&G پایین بهتره)
    if fng < 30:
        fng_bonus = 8
    elif fng < 60:
        fng_bonus = 3
    elif fng > 80:
        fng_bonus = -10
    else:
        fng_bonus = 0

    # محاسبه (پامپ پایه کمتره)
    base_tp1 = 45
    base_tp2 = 25

    tp1_factors = tp1_dist_score + vs_bonus + breakout_bonus + mom_bonus + social_bonus
    tp2_factors = tp2_dist_score + vs_bonus + breakout_bonus + mom_bonus + social_bonus

    global_factors = ctx_bonus + btc_bonus + fng_bonus

    tp1_prob = base_tp1 + tp1_factors + global_factors
    tp2_prob = base_tp2 + tp2_factors + global_factors

    tp1_prob = max(10, min(88, tp1_prob))
    tp2_prob = max(5, min(80, tp2_prob))

    if tp2_prob >= tp1_prob:
        tp2_prob = tp1_prob - 15

    # عوامل
    factors = []
    if vs_score >= 15:
        factors.append("Volume Spike قوی")
    if breakout_score >= 12:
        factors.append("Breakout تأیید شده")
    if mom_score >= 12:
        factors.append("مومنتوم قوی")
    if social_score >= 10:
        factors.append("Hype بالا")
    if btc_change > 1:
        factors.append("BTC صعودی")
    elif btc_change < -2:
        factors.append("BTC نزولی — خطر")

    return round(tp1_prob), round(tp2_prob), factors


# ═══════════════════════════════════════════
# تابع قدیمی (برای سازگاری)
# ═══════════════════════════════════════════

def estimate_probability(analysis, df, atr_value, btc_change=0.0, fng=50):
    """سازگاری با کد قدیمی — از Growth استفاده می‌کنه"""
    return estimate_growth_probability(analysis, df, atr_value, btc_change, fng)