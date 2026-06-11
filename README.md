# 🛍️ Trendy K Telegram Bot

A Telegram bot for **Trendy K Store** that lets customers browse products, view categories, and generate purchase vouchers — powered by Google Sheets as a live product database.

---

## ✨ Features

- 📦 **Browse Products** — Browse products by brand/category with pagination
- 🧾 **Open Voucher** — Generate a PDF voucher for purchases
- 📊 **Google Sheets Integration** — Product catalogue and customer data pulled live from Google Sheets
- 🔄 **Auto-restart** — Configured to restart on failure when deployed on Railway

---

## 🗂️ Project Structure

```
TrendyKTelegramBot/
├── bot.py              # Main entry point & command/callback handlers
├── voucher_flow.py     # Conversation flow for voucher creation
├── voucher_pdf.py      # PDF generation for vouchers
├── sheets_service.py   # Google Sheets API integration
├── fonts/              # Custom fonts used in PDF generation
├── requirements.txt    # Python dependencies
├── Procfile            # Railway process config
├── railway.json        # Railway build & deploy settings
├── runtime.txt         # Python version pin
└── .env                # Local environment variables (not committed)
```

---

## 🚀 Getting Started (Local)

### 1. Prerequisites

- Python 3.12+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- A Google Cloud Service Account with Sheets API access

### 2. Clone the Repository

```bash
git clone https://github.com/kyawyea92/TrendyKTelegramBot.git
cd TrendyKTelegramBot
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example below into a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

GOOGLE_SERVICE_ACCOUNT_EMAIL=your-service-account@project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_CUSTOMER_SHEET_ID=your_customer_sheet_id
```

### 6. Run the Bot

```bash
python bot.py
```

Send `/start` to your bot on Telegram to begin.

---

## 🌐 Deploy on Railway

### 1. Push to GitHub

Make sure your code is pushed to GitHub (Railway reads from your repo).

### 2. Create a New Project on Railway

1. Go to [railway.com](https://railway.com) → **New Project** → **Deploy from GitHub repo**
2. Select `kyawyea92/TrendyKTelegramBot`
3. Railway auto-detects the `Procfile` — click **Deploy**

### 3. Set Environment Variables

In your Railway service → **Settings → Variables**, add the following:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from BotFather |
| `GOOGLE_SERVICE_ACCOUNT_EMAIL` | Service account email from Google Cloud |
| `GOOGLE_PRIVATE_KEY` | Full private key (with real line breaks, not `\n`) |
| `GOOGLE_SHEET_ID` | Google Sheet ID for the product catalogue |
| `GOOGLE_CUSTOMER_SHEET_ID` | Google Sheet ID for the customer list |

> **Note:** For `GOOGLE_PRIVATE_KEY`, paste the value with **actual newlines** inside the Railway variable editor — press Enter to create line breaks within the key value.

Railway will automatically redeploy after saving variables. Your bot will be live! 🎉

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `python-telegram-bot` | Telegram Bot API wrapper |
| `gspread` | Google Sheets API client |
| `google-auth` | Google authentication |
| `python-dotenv` | Load environment variables from `.env` |
| `fpdf2` | PDF generation for vouchers |
| `uharfbuzz` | Font shaping for Myanmar text in PDFs |

---

## 🔑 Google Sheets Setup

1. Create a **Google Cloud Project** and enable the **Google Sheets API**
2. Create a **Service Account** and download the JSON key
3. Copy the `client_email` and `private_key` from the JSON into your `.env`
4. **Share** your Google Sheets with the service account email (Editor access)

---

## 📝 Bot Commands

| Command | Description |
|---|---|
| `/start` | Show the main menu |
| `/menu` | Show the main menu |

---

## 📄 License

This project is private and intended for internal use by Trendy K Store.
