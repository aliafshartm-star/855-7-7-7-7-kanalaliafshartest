"""
Signal History v2 — ذخیره با نوع (growth/pump)
"""
import os
import json
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

HISTORY_FILE = "state/signal_history.json"
os.makedirs("state", exist_ok=True)


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_growth_signal(symbol, analysis):
    """ذخیره سیگنال Growth"""
    history = load_history()
    if symbol not in history:
        history[symbol] = []

    record = {
        "type": "growth",
        "date": datetime.now(timezone.utc).isoformat(),
        "price_at_signal": analysis["price"],
        "score": analysis["growth_score"],
        "entry_low": analysis["growth_entry_low"],
        "entry_high": analysis["growth_entry_high"],
        "stop": analysis["growth_stop"],
        "tp1": analysis["growth_tp1"],
        "tp2": analysis["growth_tp2"],
        "tp3": analysis["growth_tp3"],
        "forces": analysis.get("growth_forces", {}),
        "reasons": analysis.get("growth_reasons", []),
        "result": "OPEN",
        "result_price": None,
        "result_date": None,
    }

    history[symbol].append(record)
    save_history(history)
    return record


def add_pump_signal(symbol, analysis):
    """ذخیره سیگنال Pump"""
    history = load_history()
    if symbol not in history:
        history[symbol] = []

    record = {
        "type": "pump",
        "date": datetime.now(timezone.utc).isoformat(),
        "price_at_signal": analysis["price"],
        "score": analysis["pump_score"],
        "entry_low": analysis["pump_entry_low"],
        "entry_high": analysis["pump_entry_high"],
        "stop": analysis["pump_stop"],
        "tp1": analysis["pump_tp1"],
        "tp2": analysis["pump_tp2"],
        "tp3": analysis["pump_tp3"],
        "forces": analysis.get("pump_forces", {}),
        "reasons": analysis.get("pump_reasons", []),
        "result": "OPEN",
        "result_price": None,
        "result_date": None,
    }

    history[symbol].append(record)
    save_history(history)
    return record


def get_all_signals(symbol):
    history = load_history()
    return history.get(symbol, [])


def update_result(symbol, current_price):
    """آپدیت وضعیت همه سیگنال‌های باز"""
    history = load_history()
    signals = history.get(symbol, [])
    if not signals:
        return None

    updated = False
    for last in signals:
        if "OPEN" not in (last.get("result") or "OPEN"):
            continue

        tp1 = last.get("tp1", 0)
        tp2 = last.get("tp2", 0)
        tp3 = last.get("tp3", 0)
        stop = last.get("stop", 0)
        entry = last.get("price_at_signal", 0)

        if current_price >= tp3:
            last["result"] = "TP3_HIT"
        elif current_price >= tp2:
            last["result"] = "TP2_HIT"
        elif current_price >= tp1:
            last["result"] = "TP1_HIT"
        elif current_price <= stop:
            last["result"] = "STOPPED"
        else:
            change = ((current_price - entry) / entry) * 100 if entry > 0 else 0
            last["result"] = f"OPEN ({change:+.1f}%)"

        if "OPEN (" not in last["result"]:
            last["result_price"] = current_price
            last["result_date"] = datetime.now(timezone.utc).isoformat()
            updated = True

    if updated:
        save_history(history)
    return signals


# سازگاری با کد قدیمی
def add_signal(symbol, analysis):
    """پیش‌فرض: Growth"""
    return add_growth_signal(symbol, analysis)