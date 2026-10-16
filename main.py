"""
ViaChart Agent v6 — Fast Scanner + Deep Analysis
"""
import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from data_fetcher import get_top_symbols, get_klines
from fast_scanner import fast_scan
from pump_detector import (
    candles_to_df, analyze_coin, passes_growth_filters, passes_pump_filters,
    atr as atr_calc, get_btc_change, get_fng
)
from chart_generator import generate_chart
from telegram_poster import post_growth_signal, post_pump_signal
from_prob signal_history import (
    add_growth_signal, add_pump_signal, get_all_signals, update_result
)
from signal_brain import should_s
end_growth, should_send_pump
from probability_engine import (
    estimate_growth_probability, estimate_pump_probability
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

STATE_FILE = "state/last_s           ent.json"
os.makedirs("state", exist_ok=True)

MIN_GROWTH_SCORE = 50
MIN_PUMP_SCORE = 30

COOLDOWN_GROWTH_HOURS = 24
COOLDOWN_PUMP_HOURS = 48

INTERVAL = "4h"
KLINE_LIMIT = 200
SEND_DELAY = 20


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"growth_sent": {}, "pump_sent": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_on_cooldown(state, symbol, sig_type):
    key = f"{sig_type}_sent"
    last_time = state.get(key, {}).get(symbol)
    if not last_time:
        return False
    try:
        last_dt = datetime.fromisoformat(last_time)
        hours = COOLDOWN_GROWTH_HOURS if sig_type == "growth" else COOLDOWN_PUMP_HOURS
        if datetime.now(timezone.utc) - last_dt < timedelta(hours=hours):
            return True
    except Exception:
        pass
    return False


def mark_sent(state, symbol, sig_type):
    key = f"{sig_type}_sent"
    if key not in state:
        state[key] = {}
    state[key][symbol] = datetime.now(timezone.utc).isoformat()


def deep_analyze(candidates, btc_df):
    """تحلیل عمیق فقط کاندیدهای Fast Scanner"""
    log.info(f"🔍 تحلیل عمیق {len(candidates)} ارز...")
    results = []

    for i, coin in enumerate(candidates, 1):
        symbol = coin["symbol"]
        try:
            candles = get_klines(symbol, INTERVAL, KLINE_LIMIT)
            if not candles or len(candles) < 90:
                continue

            df = candles_to_df(candles)
            cg_id = symbol.replace("USDT", "").lower()
            analysis = analyze_coin(symbol, cg_id, df, coin, btc_df=btc_df)
            analysis["fast_score"] = coin.get("fast_score", 0)
            analysis["fast_reasons"] = coin.get("fast_reasons", [])
            results.append(analysis)

            if i % 5 == 0:
                log.info(f"   ... {i}/{len(candidates)}")

            time.sleep(0.08)
        except Exception as e:
            log.warning(f"   ⚠️ {symbol}: {str(e)[:60]}")
            continue

    return results


async def process_growth_signals(all_results, state):
    log.info("\n" + "=" * 50)
    log.info("🌱 بررسی سیگنال‌های GROWTH")
    log.info("=" * 50)

    passed = [r for r in all_results if passes_growth_filters(r)]
    passed.sort(key=lambda x: x["growth_score"], reverse=True)

    log.info(f"📋 {len(passed)} ارز از Growth filters گذشت")
    log.info(f"\n📊 TOP 10 Growth Score (آستانه: {MIN_GROWTH_SCORE}):")
    for r in passed[:10]:
        log.info(f"   • {r['symbol']:12s} — {r['growth_score']:3d}/100")

    candidates = [r for r in passed if r["growth_score"] >= MIN_GROWTH_SCORE]
    log.info(f"\n🎯 {len(candidates)} ارز Growth ≥ {MIN_GROWTH_SCORE}")

    if not candidates:
        return 0

    sent = 0
    for pick in candidates:
        symbol = pick["symbol"]

        if is_on_cooldown(state, symbol, "growth"):
            log.info(f"   ⏳ {symbol} در cooldown")
            continue

        history = get_all_signals(symbol)
        update_result(symbol, pick["price"])
        history = get_all_signals(symbol)

        decision = should_send_growth(symbol, pick, history)
        log.info(f"   🎯 {symbol}: {decision['decision']} — {decision['reason']}")

        if decision["decision"] != "SEND":
            continue

        candles = get_klines(symbol, INTERVAL, KLINE_LIMIT)
        if candles:
            df_full = candles_to_df(candles)
            atr_val = atr_calc(df_full).iloc[-1]
            btc_chg = get_btc_change()["change"]
            fg = get_fng()

            tp1_prob, tp2_prob, factors = estimate_growth_probability(
                pick, df_full, atr_val, btc_chg, fg
            )
            pick["growth_tp1_prob"] = tp1_prob
            pick["growth_tp2_prob"] = tp2 pick["growth_prob_factors"] = factors
            log.info(f"   🧠 احتمال: TP1 {tp1_prob}٪ | TP2 {tp2_prob}٪")

        try:
            chart = generate_chart(symbol, INTERVAL, 150, score_data=pick)
            ok = await post_growth_signal(pick, chart)

            if ok:
                add_growth_signal(symbol, pick)
                mark_sent(state, symbol, "growth")
                save_state(state)
                sent += 1
                log.info(f"   ✅ ارسال Growth")
                await asyncio.sleep(SEND_DELAY)
        except Exception as e:
            log.error(f"   ❌ {symbol}: {e}")

    return sent


async def process_pump_signals(all_results, state):
    log.info("\n" + "=" * 50)
    log.info("🚀 بررسی سیگنال‌های PUMP")
    log.info("=" * 50)

    passed = [r for r in all_results if passes_pump_filters(r)]
    passed.sort(key=lambda x: x["pump_score"], reverse=True)

    log.info(f"📋 {len(passed)} ارز از Pump filters گذشت")
    log.info(f"\n📊 TOP 10 Pump Score (آستانه: {MIN_PUMP_SCORE}):")
    for r in passed[:10]:
        log.info(f"   • {r['symbol']:12s} — {r['pump_score']:3d}/100")

    candidates = [r for r in passed if r["pump_score"] >= MIN_PUMP_SCORE]
    log.info(f"\n🎯 {len(candidates)} ارز Pump ≥ {MIN_PUMP_SCORE}")

    if not candidates:
        return 0

    sent = 0
    for pick in candidates:
        symbol = pick["symbol"]

        if is_on_cooldown(state, symbol, "pump"):
            log.info(f"   ⏳ {symbol} در cooldown")
            continue

        history = get_all_signals(symbol)
        update_result(symbol, pick["price"])
        history = get_all_signals(symbol)

        decision = should_send_pump(symbol, pick, history)
        log.info(f"   🎯 {symbol}: {decision['decision']} — {decision['reason']}")

        if decision["decision"] != "SEND":
            continue

        candles = get_klines(symbol, INTERVAL, KLINE_LIMIT)
        if candles:
            df_full = candles_to_df(candles)
            atr_val = atr_calc(df_full).iloc[-1]
            btc_chg = get_btc_change()["change"]
            fg = get_fng()

            tp1_prob, tp2_prob, factors = estimate_pump_probability(
                pick, df_full, atr_val, btc_chg, fg
            )
            pick["pump_tp1_prob"] = tp1_prob
            pick["pump_tp2_prob"] = tp2_prob
            pick["pump_prob_factors"] = factors
            log.info(f"   🧠 احتمال: TP1 {tp1_prob}٪ | TP2 {tp2_prob}٪")

        try:
            chart = generate_chart(symbol, INTERVAL, 150, score_data=pick)
            ok = await post_pump_signal(pick, chart)

            if ok:
                add_pump_signal(symbol, pick)
                mark_sent(state, symbol, "pump")
                save_state(state)
                sent += 1
                log.info(f"   ✅ ارسال Pump")
                await asyncio.sleep(SEND_DELAY)
        except Exception as e:
            log.error(f"   ❌ {symbol}: {e}")

    return sent


async def run():
    start_time = time.time()

    log.info("=" * 50)
    log.info("🚀 ViaChart Agent v6 — Fast Scanner")
    log.info("=" * 50)

    # ۱. دریافت ۲۰۰ ارز
    all_symbols = get_top_symbols(limit=200)
    if not all_symbols:
        log.error("❌ ارزی دریافت نشد")
        return
    log.info(f"📥 {len(all_symbols)} ارز دریافت شد")

    # ۲. Fast Scan (موازی)
    candidates = fast_scan(all_symbols)
    if not candidates:
        log.warning("⚠️ هیچ کاندیدی پیدا نشد")
        return

    # ۳. BTC candles برای RS
    btc_candles = get_klines("BTCUSDT", INTERVAL, KLINE_LIMIT)
    btc_df = candles_to_df(btc_candles) if btc_candles else None

    # ۴. تحلیل عمیق
    all_results = deep_analyze(candidates, btc_df)
    if not all_results:
        log.warning("⚠️ هیچ ارزی تحلیل نشد")
        return

    # ۵. پردازش سیگنال‌ها
    state = load_state()
    growth_sent = await process_growth_signals(all_results, state)
    pump_sent = await process_pump_signals(all_results, state)

    elapsed = time.time() - start_time

    log.info(f"\n{'=' * 50}")
    log.info(f"✅ جمع: {growth_sent} Growth + {pump_sent} Pump")
    log.info(f"⏱️ زمان کل: {elapsed:.1f} ثانیه")
    log.info(f"{'=' * 50}")


def main():
    log.info("🎬 ViaChart Agent v6")
    try:
        asyncio.run(run())
        log.info("🎉 اجرا تمام شد")
    except Exception as e:
        log.error(f"❌ خطای کلی: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()