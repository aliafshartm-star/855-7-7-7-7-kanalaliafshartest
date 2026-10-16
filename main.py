"""
ViaChart Agent v4 — ۷ نیرو
"""
import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from data_fetcher import get_top_symbols, get_klines
from pump_detector import (
    candles_to_df, analyze_coin, passes_filters, get_signal_tier
)
from chart_generator import generate_chart
from telegram_poster import post_signal
from signal_history import add_signal, get_all_signals, update_result
from signal_brain import should_send

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

STATE_FILE = "state/last_sent.json"
os.makedirs("state", exist_ok=True)

MIN_SCORE = 60
COOLDOWN_HOURS = 24
TOP_SCAN = 200
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
    return {"last_sent": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_on_cooldown(state, symbol):
    last_time = state["last_sent"].get(symbol)
    if not last_time:
        return False
    try:
        last_dt = datetime.fromisoformat(last_time)
        if datetime.now(timezone.utc) - last_dt < timedelta(hours=COOLDOWN_HOURS):
            return True
    except Exception:
        pass
    return False


def mark_sent(state, symbol):
    state["last_sent"][symbol] = datetime.now(timezone.utc).isoformat()


def analyze_all(limit=TOP_SCAN):
    log.info(f"📊 تحلیل {limit} ارز...")

    btc_candles = get_klines("BTCUSDT", INTERVAL, KLINE_LIMIT)
    btc_df = candles_to_df(btc_candles) if btc_candles else None

    symbols = get_top_symbols(limit=limit)
    if not symbols:
        log.error("❌ هیچ ارزی دریافت نشد")
        return []

    results = []
    for i, coin in enumerate(symbols, 1):
        symbol = coin["symbol"]
        try:
            candles = get_klines(symbol, INTERVAL, KLINE_LIMIT)
            if not candles or len(candles) < 60:
                continue

            df = candles_to_df(candles)
            cg_id = symbol.replace("USDT", "").lower()
            analysis = analyze_coin(symbol, cg_id, df, coin, btc_df=btc_df)
            results.append(analysis)

            if i % 20 == 0:
                log.info(f"   ... {i}/{len(symbols)}")

            time.sleep(0.08)
        except Exception as e:
            log.warning(f"   ⚠️ {symbol}: {str(e)[:60]}")
            continue

    return results


async def run():
    log.info("=" * 50)
    log.info("🚀 ViaChart Agent v4 — ۷ نیرو")
    log.info("=" * 50)

    all_results = analyze_all()
    if not all_results:
        log.warning("⚠️ هیچ ارزی تحلیل نشد")
        return

    passed = [r for r in all_results if passes_filters(r)]
    log.info(f"✅ {len(passed)} ارز از فیلترها گذشت")

    candidates = [r for r in passed if r["score"] >= MIN_SCORE]
    candidates.sort(key=lambda x: x["score"], reverse=True)

    log.info(f"🎯 {len(candidates)} ارز امتیاز ≥ {MIN_SCORE}")

    if not candidates:
        log.info("😐 هیچ سیگنالی نبود")
        return

    log.info(f"\n🏆 کاندیداها:")
    for r in candidates[:10]:
        log.info(f"   • {r['symbol']:12s} — {r['score']:3d}/140")

    state = load_state()
    sent = 0

    for pick in candidates:
        symbol = pick["symbol"]
        log.info(f"\n🧠 بررسی {symbol}...")

        history = get_all_signals(symbol)
        if history:
            update_result(symbol, pick["price"])
            history = get_all_signals(symbol)

        decision = should_send(symbol, pick, history)
        log.info(f"   🎯 Signal Brain: {decision['decision']} — {decision['reason']}")

        if decision["decision"] != "SEND":
            log.info(f"   ⏭️ رد شد")
            continue

        log.info(f"   📤 ارسال...")
        try:
            chart = generate_chart(symbol, INTERVAL, 150, score_data=pick)
            ok = await post_signal(pick, chart)

            if ok:
                add_signal(symbol, pick)
                mark_sent(state, symbol)
                save_state(state)
                sent += 1
                log.info(f"   ✅ ارسال موفق")
                await asyncio.sleep(SEND_DELAY)
        except Exception as e:
            log.error(f"   ❌ {symbol}: {e}")

    log.info(f"\n✅ {sent} سیگنال ارسال شد")


def main():
    log.info("🎬 ViaChart Agent v4")
    try:
        asyncio.run(run())
        log.info("🎉 اجرا تمام شد")
    except Exception as e:
        log.error(f"❌ خطای کلی: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()