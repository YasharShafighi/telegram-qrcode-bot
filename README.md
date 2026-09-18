# 🤖telegram-qrcode-bot 

A simple yet complete Telegram bot for generating all kinds of QR codes, supporting links, text, phone numbers, emails, SMS, Wi-Fi, contacts, and locations.

---

## ✨ Features

- 🔗 **Website link QR** (automatically prefixes `https://`)
- 📝 **Plain text**
- 📞 **Phone number**
- 📧 **Email**
- 💬 **SMS**
- 📶 **Wi-Fi network** (SSID + password)
- 👤 **Contact** (vCard)
- 📍 **Location** (Latitude,Longitude)
- 🎨 High quality with error correction level **H** (up to 30% damage tolerance)
- 📋 Inline menu with glass buttons
- ❌ Cancel option at every step

---

## 🚀 Installation & Setup

### 1) Prerequisites

- Python 3.9 or higher
- A Telegram bot token (explained below)

### 2) Install libraries

```bash
pip install python-telegram-bot qrcode[pil] pillow
```

### Configure the token

In `bot.py`, replace the following line with your own token:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```

### Run

```bash
python bot.py
```

If everything is set up correctly, you'll see in the logs:

```
🤖 Bot is up and running...
```

---

## 🎓 How to Build a Telegram Bot from Scratch

### Step 1: Create a bot with BotFather

1. In Telegram, search for and open **@BotFather**.
2. Send the `/newbot` command.
3. Choose a **name** for your bot (e.g., `My QR Bot`).
4. Choose a **username** that ends in `bot` (e.g., `my_qr_generator_bot`).
5. BotFather will give you a **token** like this:

   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567
   ```

6. Copy this token and paste it into the code. Never make it public!

---