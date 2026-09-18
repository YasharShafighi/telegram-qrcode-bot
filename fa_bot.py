import io
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# 🔑 توکن ربات خود را اینجا بگذارید
TOKEN = "توکن_خودت_را_اینجا_بگذار"


# ---------- کیبورد اصلی ----------
def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔗 لینک سایت", callback_data="link"),
         InlineKeyboardButton("📝 متن ساده", callback_data="text")],
        [InlineKeyboardButton("📞 شماره تلفن", callback_data="phone"),
         InlineKeyboardButton("📧 ایمیل", callback_data="email")],
        [InlineKeyboardButton("💬 پیامک", callback_data="sms"),
         InlineKeyboardButton("📶 وای‌فای", callback_data="wifi")],
        [InlineKeyboardButton("👤 مخاطب", callback_data="contact"),
         InlineKeyboardButton("📍 موقعیت", callback_data="location")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------- استارت ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = (
        "سلام! 👋\n"
        "من ربات سازنده **QRCode** هستم.\n\n"
        "نوع QR مورد نظرت را انتخاب کن:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")


# ---------- هندل دکمه‌ها ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    # لغو
    if choice == "cancel":
        context.user_data.clear()
        await query.edit_message_text("لغو شد. یک گزینه انتخاب کن:", reply_markup=main_keyboard())
        return

    context.user_data["type"] = choice

    prompts = {
        "link":     "🔗 آدرس سایت را بفرست:\n(مثال: zoomit.ir)",
        "text":     "📝 متن دلخواه را بفرست:",
        "phone":    "📞 شماره تلفن را بفرست:\n(با کد کشور، مثال: +989121234567)",
        "email":    "📧 ایمیل را بفرست:\n(مثال: test@gmail.com)",
        "sms":      "💬 شماره را بفرست:\n(با کد کشور)",
        "wifi":     "📶 نام وای‌فای (SSID) را بفرست:",
        "contact":  "👤 نام مخاطب را بفرست:",
        "location": "📍 مختصات را بفرست:\n(مثال: 35.6892,51.3890)",
    }

    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="cancel")]])
    await query.edit_message_text(prompts[choice], reply_markup=cancel_kb)


# ---------- ساخت QR در حافظه ----------
def make_qr_image(data, fill="black", back="white"):
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill, back_color=back)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# ---------- ارسال QR ----------
async def send_qr(update: Update, data, caption):
    try:
        buffer = make_qr_image(data)
        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        await update.message.reply_photo(
            photo=buffer,
            filename=f"QR_{time_str}.png",
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
    finally:
        context_clear(update)
        await update.message.reply_text("یکی دیگر بسازیم؟", reply_markup=main_keyboard())


def context_clear(update):
    pass  # برای پاک کردن user_data دسترسی نداریم، در handle_message انجام می‌دهیم


# ---------- مدیریت پیام‌های متنی ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    qr_type = context.user_data.get("type")

    if not qr_type:
        await update.message.reply_text(
            "اول یک گزینه از منو انتخاب کن:",
            reply_markup=main_keyboard()
        )
        return

    # ---------- مرحله دوم وای‌فای: رمز ----------
    if qr_type == "wifi" and "wifi_ssid" not in context.user_data:
        context.user_data["wifi_ssid"] = text
        await update.message.reply_text("🔒 رمز وای‌فای را بفرست (اگر ندارد بنویس `nopass`):")
        return

    if qr_type == "wifi" and "wifi_pass" not in context.user_data:
        ssid = context.user_data["wifi_ssid"]
        password = text if text != "nopass" else ""
        security = "nopass" if password == "" else "WPA"
        data = f"WIFI:T:{security};S:{ssid};P:{password};;"
        caption = f"📶 وای‌فای: `{ssid}`"
        context.user_data.clear()
        await send_qr(update, data, caption)
        return

    # ---------- مرحله دوم مخاطب: فامیل ----------
    if qr_type == "contact" and "contact_first" not in context.user_data:
        context.user_data["contact_first"] = text
        await update.message.reply_text("👤 فامیل مخاطب را بفرست:")
        return

    if qr_type == "contact" and "contact_last" not in context.user_data:
        context.user_data["contact_last"] = text
        await update.message.reply_text("📞 شماره تلفن مخاطب را بفرست:")
        return

    if qr_type == "contact" and "contact_phone" not in context.user_data:
        first = context.user_data["contact_first"]
        last = context.user_data["contact_last"]
        data = (
            "BEGIN:VCARD\nVERSION:3.0\n"
            f"N:{last};{first}\n"
            f"FN:{first} {last}\n"
            f"TEL:{text}\n"
            "END:VCARD"
        )
        caption = f"👤 مخاطب: {first} {last}"
        context.user_data.clear()
        await send_qr(update, data, caption)
        return

    # ---------- انواع دیگر ----------
    if qr_type == "link":
        url = text
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        data = url
        caption = f"🔗 لینک:\n`{url}`"

    elif qr_type == "text":
        data = text
        caption = f"📝 متن: `{text[:50]}`"

    elif qr_type == "phone":
        data = f"tel:{text}"
        caption = f"📞 تلفن: `{text}`"

    elif qr_type == "email":
        data = f"mailto:{text}"
        caption = f"📧 ایمیل: `{text}`"

    elif qr_type == "sms":
        data = f"SMSTO:{text}:"
        caption = f"💬 پیامک به: `{text}`"

    elif qr_type == "location":
        data = f"geo:{text}"
        caption = f"📍 موقعیت: `{text}`"

    else:
        await update.message.reply_text("❌ نوع نامعتبر. دوباره انتخاب کن:", reply_markup=main_keyboard())
        context.user_data.clear()
        return

    context.user_data.clear()
    await send_qr(update, data, caption)


# ---------- اجرا ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 ربات روشن شد...")
    app.run_polling()


if __name__ == "__main__":
    main()