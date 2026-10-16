"""
Signal Brain v2 — تصمیم جدا برای:
  🌱 Growth
  🚀 Pump
"""
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 🌱 تصمیم رشد
# ═══════════════════════════════════════════

def should_send_growth(symbol, current_analysis, history):
    """تصمیم برای سیگنال رشد"""
    growth_history = [h for h in history if h.get("type") == "growth"]

    if not growth_history:
        return {
            "decision": "SEND",
            "reason": f"اولین Growth {symbol} (امتیاز {current_analysis['growth_score']})"
        }

    last = growth_history[-1]
    last_price = last.get("price_at_signal", 0)
    last_result = last.get("result", "")
    current_price = current_analysis["price"]

    if last_price > 0:
        change = ((current_price - last_price) / last_price) * 100
    else:
        change = 0

    # هنوز TP1 نخورده
    if not last_result or "OPEN" in last_result:
        return {
            "decision": "SKIP",
            "reason": f"Growth قبلی بازه ({change:+.1f}%) — صبر"
        }

    # TP خورد → بعد ۱۴ روز
    if "TP" in last_result:
        hours_ago = _hours_since(last.get("date"))
        if hours_ago >= 336:  # 14 روز
            return {
                "decision": "SEND",
                "reason": f"Growth قبلی موفق، {hours_ago/24:.0f} روز گذشته"
            }
        return {
            "decision": "SKIP",
            "reason": f"Growth قبلی موفق بود ({last_result})"
        }

    # Stop خورد → بعد ۷ روز
    if "STOP" in last_result:
        hours_ago = _hours_since(last.get("date"))
        if hours_ago >= 168 and current_analysis["growth_score"] >= 75:
            return {
                "decision": "SEND",
                "reason": f"ستاپ Growth جدید قوی ({current_analysis['growth_score']})"
            }
        return {
            "decision": "SKIP",
            "reason": "Growth قبلی Stop خورد"
        }

    return {"decision": "SKIP", "reason": "Growth قبلی موجوده"}


# ═══════════════════════════════════════════
# 🚀 تصمیم پامپ
# ═══════════════════════════════════════════

def should_send_pump(symbol, current_analysis, history):
    """تصمیم برای سیگنال پامپ"""
    pump_history = [h for h in history if h.get("type") == "pump"]

    if not pump_history:
        return {
            "decision": "SEND",
            "reason": f"اولین Pump {symbol} (امتیاز {current_analysis['pump_score']})"
        }

    last = pump_history[-1]
    last_price = last.get("price_at_signal", 0)
    last_result = last.get("result", "")
    current_price = current_analysis["price"]

    if last_price > 0:
        change = ((current_price - last_price) / last_price) * 100
    else:
        change = 0

    # هنوز TP1 نخورده
    if not last_result or "OPEN" in last_result:
        return {
            "decision": "SKIP",
            "reason": f"Pump قبلی بازه ({change:+.1f}%) — صبر"
        }

    # TP خورد → بعد ۷ روز
    if "TP" in last_result:
        hours_ago = _hours_since(last.get("date"))
        if hours_ago >= 168:
            return {
                "decision": "SEND",
                "reason": f"Pump قبلی موفق، {hours_ago/24:.0f} روز گذشته"
            }
        return {
            "decision": "SKIP",
            "reason": f"Pump قبلی موفق بود ({last_result})"
        }

    # Stop خورد → بعد ۴۸ ساعت
    if "STOP" in last_result:
        hours_ago = _hours_since(last.get("date"))
        if hours_ago >= 48 and current_analysis["pump_score"] >= 80:
            return {
                "decision": "SEND",
                "reason": f"Pump جدید قوی ({current_analysis['pump_score']})"
            }
        return {
            "decision": "SKIP",
            "reason": "Pump قبلی Stop خورد"
        }

    return {"decision": "SKIP", "reason": "Pump قبلی موجوده"}


def _hours_since(date_str):
    if not date_str:
        return 999
    try:
        dt = datetime.fromisoformat(date_str)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return 999


# سازگاری با کد قدیمی
def should_send(symbol, current_analysis, history):
    """پیش‌فرض: Growth"""
    return should_send_growth(symbol, current_analysis, history)


# ═══════════════════════════════════════════
# Tier ها
# ═══════════════════════════════════════════

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