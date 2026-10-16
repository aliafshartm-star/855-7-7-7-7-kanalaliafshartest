"""
ارسال سیگنال — دو قالب جدا:
  🌱 ViaChart GROWTH
  🚀 ViaChart PUMP
"""
import os
import logging

from telegram import Bot, InputFile
from telegram.constants import ParseMode
from telegram.error import TimedOut, NetworkError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@aliafshartm2")
CHANNEL_HANDLE = os.environ.get("TELEGRAM_CHANNEL_HANDLE", "@aliafshartm2")


def _fmt(p):
    if p >= 1000:
        return f"${p:,.2f}"
    elif p >= 1:
        return f"${p:,.4f}"
    elif p >= 0.01:
        return f"${p:.4f}"
    else:
        return f"${p:.6f}"


def _pct(from_p, to_p):
    if from_p == 0:
        return "0.0%"
    change = ((to_p - from_p) / from_p) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def _full_name(symbol):
    mapping = {
        "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana",
        "BNB": "BNB", "XRP": "Ripple", "ADA": "Cardano",
        "DOGE": "Dogecoin", "AVAX": "Avalanche", "DOT": "Polkadot",
        "MATIC": "Polygon", "LINK": "Chainlink", "TON": "Toncoin",
        "NEAR": "Near", "ATOM": "Cosmos", "APT": "Aptos",
        "ARB": "Arbitrum", "OP": "Optimism", "SUI": "Sui",
        "INJ": "Injective", "TIA": "Celestia", "PEPE": "Pepe",
        "WIF": "dogwifhat", "FET": "Fetch.ai", "STRK": "Starknet",
    }
    return mapping.get(symbol, symbol)


# ═══════════════════════════════════════════
# 🌱 قالب GROWTH
# ═══════════════════════════════════════════

def build_growth_post(a):
    """ساخت پست سیگنال رشد"""
    symbol = a["symbol"].replace("USDT", "")
    full_name = _full_name(symbol)
    score = a["growth_score"]
    reasons = a.get("growth_reasons", [])
    forces = a.get("growth_forces", {})

    entry_low = a["growth_entry_low"]
    entry_high = a["growth_entry_high"]
    stop = a["growth_stop"]
    tp1 = a["growth_tp1"]
    tp2 = a["growth_tp2"]
    tp3 = a["growth_tp3"]

    tp1_prob = a.get("growth_tp1_prob", 0)
    tp2_prob = a.get("growth_tp2_prob", 0)
    prob_factors = a.get("growth_prob_factors", [])

    if score >= 85:
        tier = "TIER 1 🔥"
    elif score >= 75:
        tier = "TIER 2 🟢"
    else:
        tier = "TIER 3 🟡"

    reason_lines = ""
    for r in reasons[:5]:
        reason_lines += "🔹 " + r + "\n"
    if not reason_lines:
        reason_lines = "🔹 تحلیل تکنیکال\n"

    f1 = forces.get("Accumulation", 0)
    f2 = forces.get("Volume", 0)
    f3 = forces.get("Structure", 0)
    f4 = forces.get("Momentum", 0)
    f5 = forces.get("Context", 0)

    parts = []
    parts.append("🌱 <b>ViaChart GROWTH</b> | " + symbol + "/USDT")
    parts.append("")
    parts.append("🎯 امتیاز رشد: <b>" + str(score) + "/100</b> " + tier)
    parts.append("⏰ زمان: ۳-۱۴ روز")
    parts.append("")

    if tp1_prob and tp2_prob:
        parts.append("━━━━━━━━━━━━━━━")
        parts.append("🧠 <b>احتمال موفقیت</b>")
        parts.append("━━━━━━━━━━━━━━━")
        parts.append(f"📊 TP1: <b>~{tp1_prob}٪</b>")
        parts.append(f"📊 TP2: <b>~{tp2_prob}٪</b>")

        if prob_factors:
            parts.append("")
            parts.append("عوامل موثر:")
            for factor in prob_factors[:3]:
                parts.append("   • " + factor)

        parts.append("")
        parts.append("<i>⚠️ تخمینی — نه تضمین</i>")
        parts.append("")

    parts.append("━━━━━━━━━━━━━━━")
    parts.append("💰 <b>پلن معاملاتی</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("🎯 ورود: <b>" + _fmt(entry_low) + " - " + _fmt(entry_high) + "</b>")
    parts.append("")
    parts.append("✅ <b>اهداف:</b>")
    parts.append("   TP1: <b>" + _fmt(tp1) + "</b> (" + _pct(entry_high, tp1) + ")")
    parts.append("   TP2: <b>" + _fmt(tp2) + "</b> (" + _pct(entry_high, tp2) + ")")
    parts.append("   TP3: <b>" + _fmt(tp3) + "</b> (" + _pct(entry_high, tp3) + ")")
    parts.append("")
    parts.append("🛑 حد ضرر: <b>" + _fmt(stop) + "</b> (" + _pct(entry_high, stop) + ")")
    parts.append("")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("💡 <b>چرا این سیگنال؟</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append(reason_lines.rstrip())
    parts.append("")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("📊 <b>امتیاز ۵ نیرو</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("🌱 انباشت: " + str(f1) + "/25")
    parts.append("📈 حجم: " + str(f2) + "/20")
    parts.append("📊 ساختار: " + str(f3) + "/20")
    parts.append("🔥 مومنتوم: " + str(f4) + "/15")
    parts.append("🌊 بازار: " + str(f5) + "/20")
    parts.append("")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("🛡️ <b>مدیریت ریسک</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("• فقط اسپات (بدون اهرم)")
    parts.append("• حداکثر ۱٪ ریسک در هر معامله")
    parts.append("• بعد از TP1 حد ضرر رو به ورود بیار")
    parts.append("• صبر کن — رشد آرومه")
    parts.append("• توصیه مالی نیست — DYOR")
    parts.append("")
    parts.append("📢 " + CHANNEL_HANDLE)
    parts.append("")
    parts.append("#" + symbol + " #" + full_name + " #Growth #Crypto #Spot")

    return "\n".join(parts)


# ═══════════════════════════════════════════
# 🚀 قالب PUMP
# ═══════════════════════════════════════════

def build_pump_post(a):
    """ساخت پست سیگنال پامپ"""
    symbol = a["symbol"].replace("USDT", "")
    full_name = _full_name(symbol)
    score = a["pump_score"]
    reasons = a.get("pump_reasons", [])
    forces = a.get("pump_forces", {})

    entry_low = a["pump_entry_low"]
    entry_high = a["pump_entry_high"]
    stop = a["pump_stop"]
    tp1 = a["pump_tp1"]
    tp2 = a["pump_tp2"]
    tp3 = a["pump_tp3"]

    tp1_prob = a.get("pump_tp1_prob", 0)
    tp2_prob = a.get("pump_tp2_prob", 0)
    prob_factors = a.get("pump_prob_factors", [])

    if score >= 85:
        tier = "TIER 1 🔥"
    elif score >= 75:
        tier = "TIER 2 🟢"
    else:
        tier = "TIER 3 🟡"

    reason_lines = ""
    for r in reasons[:5]:
        reason_lines += "🔹 " + r + "\n"
    if not reason_lines:
        reason_lines = "🔹 تحلیل تکنیکال\n"

    f1 = forces.get("VolumeSpike", 0)
    f2 = forces.get("Breakout", 0)
    f3 = forces.get("Momentum", 0)
    f4 = forces.get("Social", 0)
    f5 = forces.get("Context", 0)

    parts = []
    parts.append("🚀 <b>ViaChart PUMP</b> | " + symbol + "/USDT")
    parts.append("")
    parts.append("🎯 امتیاز پامپ: <b>" + str(score) + "/100</b> " + tier)
    parts.append("⏰ زمان: ۱-۳ روز")
    parts.append("")
    parts.append("⚠️ <i>این سیگنال پرریسک‌تره — حجم کم وارد شو</i>")
    parts.append("")

    if tp1_prob and tp2_prob:
        parts.append("━━━━━━━━━━━━━━━")
        parts.append("🧠 <b>احتمال موفقیت</b>")
        parts.append("━━━━━━━━━━━━━━━")
        parts.append(f"📊 TP1: <b>~{tp1_prob}٪</b>")
        parts.append(f"📊 TP2: <b>~{tp2_prob}٪</b>")

        if prob_factors:
            parts.append("")
            parts.append("عوامل موثر:")
            for factor in prob_factors[:3]:
                parts.append("   • " + factor)

        parts.append("")
        parts.append("<i>⚠️ تخمینی — نه تضمین</i>")
        parts.append("")

    parts.append("━━━━━━━━━━━━━━━")
    parts.append("💰 <b>پلن معاملاتی</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("🎯 ورود: <b>" + _fmt(entry_low) + " - " + _fmt(entry_high) + "</b>")
    parts.append("")
    parts.append("✅ <b>اهداف:</b>")
    parts.append("   TP1: <b>" + _fmt(tp1) + "</b> (" + _pct(entry_high, tp1) + ")")
    parts.append("   TP2: <b>" + _fmt(tp2) + "</b> (" + _pct(entry_high, tp2) + ")")
    parts.append("   TP3: <b>" + _fmt(tp3) + "</b> (" + _pct(entry_high, tp3) + ")")
    parts.append("")
    parts.append("🛑 حد ضرر: <b>" + _fmt(stop) + "</b> (" + _pct(entry_high, stop) + ")")
    parts.append("")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("💡 <b>چرا این سیگنال؟</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append(reason_lines.rstrip())
    parts.append("")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("📊 <b>امتیاز ۵ نیرو</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("📈 Volume Spike: " + str(f1) + "/25")
    parts.append("📊 شکست: " + str(f2) + "/20")
    parts.append("🔥 مومنتوم: " + str(f3) + "/20")
    parts.append("💬 Hype: " + str(f4) + "/15")
    parts.append("🌊 بازار: " + str(f5) + "/20")
    parts.append("")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("🛡️ <b>مدیریت ریسک</b>")
    parts.append("━━━━━━━━━━━━━━━")
    parts.append("• فقط اسپات (بدون اهرم)")
    parts.append("• حداکثر ۰.۵٪ ریسک (کمتر از رشد)")
    parts.append("• سریع بخر، سریع بفروش")
    parts.append("• اگه TP1 خورد، بقیه رو بذار trail")
    parts.append("• پامپ سریع تموم میشه — حواس‌جمع باش")
    parts.append("• توصیه مالی نیست — DYOR")
    parts.append("")
    parts.append("📢 " + CHANNEL_HANDLE)
    parts.append("")
    parts.append("#" + symbol + " #" + full_name + " #Pump #Crypto #Spot")

    return "\n".join(parts)


# ═══════════════════════════════════════════
# ارسال
# ═══════════════════════════════════════════

async def send_post(text, chart_path=None, disable_notification=False):
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])

    try:
        if chart_path and os.path.exists(chart_path):
            caption = text if len(text) <= 1024 else text[:1020] + "..."
            with open(chart_path, "rb") as f:
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=InputFile(f),
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    disable_notification=disable_notification,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=30,
                )
            log.info("✅ پست با عکس ارسال شد")

            if len(text) > 1024:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=text[1024:],
                    parse_mode=ParseMode.HTML,
                    disable_notification=True,
                )
        else:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=text[:4096],
                parse_mode=ParseMode.HTML,
                disable_notification=disable_notification,
            )
            log.info("✅ پست متنی ارسال شد")
        return True
    except TimedOut:
        log.warning(f"⚠️ Timeout — رد شد")
        return False
    except NetworkError as e:
        log.error(f"❌ خطای شبکه: {e}")
        return False
    except Exception as e:
        log.error(f"❌ خطا: {e}")
        return False


async def post_growth_signal(analysis_data, chart_path=None):
    """ارسال سیگنال رشد"""
    log.info(f"📝 ساخت پست GROWTH برای {analysis_data['symbol']}...")
    post = build_growth_post(analysis_data)
    log.info(f"\n{post}\n")
    return await send_post(post, chart_path=chart_path)


async def post_pump_signal(analysis_data, chart_path=None):
    """ارسال سیگنال پامپ"""
    log.info(f"📝 ساخت پست PUMP برای {analysis_data['symbol']}...")
    post = build_pump_post(analysis_data)
    log.info(f"\n{post}\n")
    return await send_post(post, chart_path=chart_path)


# سازگاری
async def post_signal(analysis_data, chart_path=None):
    return await post_growth_signal(analysis_data, chart_path)