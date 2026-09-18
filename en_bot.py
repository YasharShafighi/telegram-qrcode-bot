import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Replace with your own bot token (or load it from an environment variable)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# QR type definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QRType:
    """Metadata describing a QR code category."""

    key: str
    button_label: str
    prompt: str


QR_TYPES: dict[str, QRType] = {
    "link":     QRType("link",     "🔗 Website link",  "Send the website URL:\n(e.g. example.com)"),
    "text":     QRType("text",     "📝 Plain text",    "Send the text you want to encode:"),
    "phone":    QRType("phone",    "📞 Phone number",  "Send the phone number:\n(e.g. +14155552671)"),
    "email":    QRType("email",    "📧 Email address", "Send the email address:\n(e.g. user@example.com)"),
    "sms":      QRType("sms",      "💬 SMS",           "Send the recipient's phone number:"),
    "wifi":     QRType("wifi",     "📶 Wi-Fi",         "Send the Wi-Fi network name (SSID):"),
    "contact":  QRType("contact",  "👤 Contact",       "Send the contact's first name:"),
    "location": QRType("location", "📍 Location",      "Send the coordinates:\n(e.g. 37.7749,-122.4194)"),
}


def build_main_keyboard() -> InlineKeyboardMarkup:
    """Return the main menu keyboard with all QR type options."""
    buttons = [
        InlineKeyboardButton(qr_type.button_label, callback_data=qr_type.key)
        for qr_type in QR_TYPES.values()
    ]
    # Arrange buttons in rows of two
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def build_cancel_keyboard() -> InlineKeyboardMarkup:
    """Return a single-button 'Cancel' keyboard."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    )


# ---------------------------------------------------------------------------
# QR rendering
# ---------------------------------------------------------------------------

def generate_qr_image(data: str, fill_color: str = "black", back_color: str = "white") -> io.BytesIO:
    """Generate a QR code image and return it as an in-memory PNG buffer."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    image = qr.make_image(fill_color=fill_color, back_color=back_color)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command and display the main menu."""
    context.user_data.clear()

    text = (
        "👋 Welcome!\n"
        "I'm a *QR Code Generator* bot.\n\n"
        "Choose the type of QR code you'd like to create:"
    )

    if update.message:
        await update.message.reply_text(
            text, reply_markup=build_main_keyboard(), parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=build_main_keyboard(), parse_mode="Markdown"
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all inline button callbacks."""
    query = update.callback_query
    await query.answer()
    choice = query.data

    # --- Cancel flow ---
    if choice == "cancel":
        context.user_data.clear()
        await query.edit_message_text(
            "Cancelled. Please choose an option:",
            reply_markup=build_main_keyboard(),
        )
        return

    # --- Unknown choice ---
    qr_type = QR_TYPES.get(choice)
    if qr_type is None:
        await query.edit_message_text(
            "❌ Invalid option. Please try again.",
            reply_markup=build_main_keyboard(),
        )
        return

    context.user_data["type"] = qr_type.key
    await query.edit_message_text(qr_type.prompt, reply_markup=build_cancel_keyboard())


# ---------------------------------------------------------------------------
# QR payload builders
# ---------------------------------------------------------------------------

def _build_wifi_payload(ssid: str, password: str) -> str:
    security = "nopass" if not password else "WPA"
    return f"WIFI:T:{security};S:{ssid};P:{password};;"


def _build_vcard(first: str, last: str, phone: str) -> str:
    return (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        f"N:{last};{first}\n"
        f"FN:{first} {last}\n"
        f"TEL:{phone}\n"
        "END:VCARD"
    )


def _normalize_url(value: str) -> str:
    if not value.startswith(("http://", "https://")):
        return f"https://{value}"
    return value


# Registry of simple single-input payload builders (type -> (builder, caption builder))
SIMPLE_BUILDERS: dict[str, tuple[Callable[[str], str], Callable[[str], str]]] = {
    "link": (
        _normalize_url,
        lambda v: f"🔗 Link:\n`{_normalize_url(v)}`",
    ),
    "text": (
        lambda v: v,
        lambda v: f"📝 Text: `{v[:50]}`",
    ),
    "phone": (
        lambda v: f"tel:{v}",
        lambda v: f"📞 Phone: `{v}`",
    ),
    "email": (
        lambda v: f"mailto:{v}",
        lambda v: f"📧 Email: `{v}`",
    ),
    "sms": (
        lambda v: f"SMSTO:{v}:",
        lambda v: f"💬 SMS to: `{v}`",
    ),
    "location": (
        lambda v: f"geo:{v}",
        lambda v: f"📍 Location: `{v}`",
    ),
}


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------

async def _send_qr(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, caption: str) -> None:
    """Send the generated QR code to the user and reset the conversation state."""
    try:
        buffer = generate_qr_image(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await update.message.reply_photo(
            photo=buffer,
            filename=f"qr_{timestamp}.png",
            caption=caption,
            parse_mode="Markdown",
        )
    except Exception as exc:  # noqa: BLE001 — surface any error to the user
        logger.exception("Failed to generate QR code")
        await update.message.reply_text(f"❌ Error: {exc}")
    finally:
        context.user_data.clear()
        await update.message.reply_text(
            "Would you like to create another one?",
            reply_markup=build_main_keyboard(),
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process the user's text input according to the selected QR type."""
    text = update.message.text.strip()
    qr_type = context.user_data.get("type")

    if not qr_type:
        await update.message.reply_text(
            "Please select an option from the menu first:",
            reply_markup=build_main_keyboard(),
        )
        return

    # ----- Multi-step flow: Wi-Fi (SSID -> password) -----
    if qr_type == "wifi":
        if "wifi_ssid" not in context.user_data:
            context.user_data["wifi_ssid"] = text
            await update.message.reply_text(
                "🔒 Send the Wi-Fi password (or `nopass` if it's open):",
                parse_mode="Markdown",
            )
            return

        ssid = context.user_data["wifi_ssid"]
        password = "" if text.lower() == "nopass" else text
        payload = _build_wifi_payload(ssid, password)
        await _send_qr(update, context, payload, f"📶 Wi-Fi: `{ssid}`")
        return

    # ----- Multi-step flow: Contact (first -> last -> phone) -----
    if qr_type == "contact":
        if "contact_first" not in context.user_data:
            context.user_data["contact_first"] = text
            await update.message.reply_text("Send the contact's last name:")
            return

        if "contact_last" not in context.user_data:
            context.user_data["contact_last"] = text
            await update.message.reply_text("Send the contact's phone number:")
            return

        first = context.user_data["contact_first"]
        last = context.user_data["contact_last"]
        payload = _build_vcard(first, last, text)
        await _send_qr(update, context, payload, f"👤 Contact: {first} {last}")
        return

    # ----- Single-step flows -----
    builder = SIMPLE_BUILDERS.get(qr_type)
    if builder is None:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Invalid type. Please choose again:",
            reply_markup=build_main_keyboard(),
        )
        return

    payload_builder, caption_builder = builder
    payload = payload_builder(text)
    caption = caption_builder(text)
    await _send_qr(update, context, payload, caption)


# ---------------------------------------------------------------------------
# Application bootstrap
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point: build and start the Telegram bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("🤖 Bot is up and running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()