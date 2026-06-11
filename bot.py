"""
Trendy K Telegram Bot
---------------------
Menu flow:
  /start  →  Main Menu
             ├─ 🧾 Open Voucher  →  Voucher Flow (PDF Creation)
             ├─ 📦 View Products  →  Categories
             │                       └─ [Category]  →  Products
             │                                          └─ [Product]  →  Detail
             └─ ℹ️ Help
"""

import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import sheets_service as sheet
from voucher_flow import build_voucher_handler

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────── Keyboard helpers ────────────────────────────────

def _kb(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)


def main_menu_kb() -> InlineKeyboardMarkup:
    return _kb([
        [InlineKeyboardButton("🧾 Open Voucher", callback_data="menu_voucher")],
        [InlineKeyboardButton("📦 View Products", callback_data="menu_categories")],
        [InlineKeyboardButton("ℹ️ Help / Info",   callback_data="menu_help")],
    ])


def back_to_main_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")]


def back_to_categories_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("🔙 Back to Categories", callback_data="menu_categories:0")]


# ─────────────────────────── /start ──────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome to *Trendy K Store*\\!\nWhat would you like to do?",
        parse_mode="MarkdownV2",
        reply_markup=main_menu_kb(),
    )


# ─────────────────────────── Callback router ─────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()          # acknowledge immediately — removes loading spinner

    data: str = query.data
    logger.info("Callback [%s] from chat %s", data, query.message.chat.id)

    # ── Main Menu ─────────────────────────────────────────────────────────────
    if data == "menu_main":
        await query.edit_message_text(
            "👋 Welcome to *Trendy K Store*\\!\nWhat would you like to do?",
            parse_mode="MarkdownV2",
            reply_markup=main_menu_kb(),
        )

    # ── Help ──────────────────────────────────────────────────────────────────
    elif data == "menu_help":
        await query.edit_message_text(
            "ℹ️ *Help*\n\n"
            "Use the buttons below to browse our product catalogue\\.\n"
            "• Choose a brand/category\n"
            "• Select a product to view details\n"
            "• Press *Back* at any level to return",
            parse_mode="MarkdownV2",
            reply_markup=_kb([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]]),
        )

    # ── Categories ────────────────────────────────────────────────────────────
    elif data.startswith("menu_categories"):
        parts = data.split(":")
        page = int(parts[1]) if len(parts) > 1 else 0
        
        categories = sheet.get_categories()
        logger.info("Categories fetched: %d", len(categories))

        rows: list[list[InlineKeyboardButton]] = []
        if categories:
            per_page = 10
            total_pages = (len(categories) + per_page - 1) // per_page
            
            # bounds check
            if page < 0: page = 0
            if page >= total_pages: page = max(0, total_pages - 1)
            
            start_idx = page * per_page
            end_idx = start_idx + per_page
            current_cats = categories[start_idx:end_idx]
            
            # One category per row for 5 items max
            for idx, cat in enumerate(current_cats):
                rows.append([InlineKeyboardButton(f"{start_idx + idx + 1}. {cat}", callback_data=f"cat_{cat}")])
                
            # Pagination buttons
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data=f"menu_categories:{page-1}"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"menu_categories:{page+1}"))
            if nav_row:
                rows.append(nav_row)
        else:
            rows.append([InlineKeyboardButton("📦 View All Products", callback_data="all_products")])

        rows.append(back_to_main_row())
        await query.edit_message_text(
            f"📂 *Select a Brand / Category \(Page {page+1}\):*",
            parse_mode="MarkdownV2",
            reply_markup=_kb(rows),
        )

    # ── Products by Category ──────────────────────────────────────────────────
    elif data.startswith("cat_"):
        category = data[4:]
        products = sheet.get_products_by_category(category)
        logger.info("Products in [%s]: %d", category, len(products))

        rows: list[list[InlineKeyboardButton]] = []
        for p in products:
            size_str = f" ({p['weight']})" if p.get('weight') else ""
            full_name = f"{p['name']}{size_str}"
            label = full_name[:35] + "…" if len(full_name) > 35 else full_name
            rows.append([InlineKeyboardButton(label, callback_data=f"prod_{p['id']}")])

        if not rows:
            rows.append([InlineKeyboardButton("⚠️ No products found", callback_data="menu_categories:0")])

        rows.append(back_to_categories_row())
        rows.append(back_to_main_row())

        # Escape MarkdownV2 special chars in category name
        safe_cat = _escape_md(category)
        await query.edit_message_text(
            f"📁 *{safe_cat}* — {len(products)} item\\(s\\)",
            parse_mode="MarkdownV2",
            reply_markup=_kb(rows),
        )

    # ── All Products (fallback when no categories exist) ──────────────────────
    elif data == "all_products":
        products = sheet.get_all_products()
        rows: list[list[InlineKeyboardButton]] = []
        for p in products:
            size_str = f" ({p['weight']})" if p.get('weight') else ""
            full_name = f"{p['name']}{size_str}"
            label = full_name[:35] + "…" if len(full_name) > 35 else full_name
            rows.append([InlineKeyboardButton(label, callback_data=f"prod_{p['id']}")])
        rows.append(back_to_categories_row())
        rows.append(back_to_main_row())

        await query.edit_message_text(
            "📦 *All Products:*",
            parse_mode="MarkdownV2",
            reply_markup=_kb(rows),
        )

    # ── Product Detail ────────────────────────────────────────────────────────
    elif data.startswith("prod_"):
        product_id = data[5:]
        product = sheet.get_product_by_id(product_id)
        logger.info("Product detail [%s]: %s", product_id, product["name"] if product else "NOT FOUND")

        if not product:
            await query.edit_message_text(
                "❌ Product not found\\.",
                parse_mode="MarkdownV2",
                reply_markup=_kb([back_to_categories_row(), back_to_main_row()]),
            )
            return

        detail = (
            f"*{_escape_md(product['name'])}*\n\n"
            f"🏷 Brand:      {_escape_md(product['category'] or 'N/A')}\n"
            f"🔖 Code:       {_escape_md(product.get('product_code') or 'N/A')}\n"
            f"📐 Size:       {_escape_md(product['weight'] or 'N/A')}\n"
            f"📦 Available:  {_escape_md(product['available'] or '0')}\n"
            f"🏪 Branch:     {_escape_md(product['branch'] or 'N/A')}\n"
            f"📅 Expiry:     {_escape_md(product['expiry'] or 'N/A')}"
        )

        back_rows: list[list[InlineKeyboardButton]] = []
        if product["category"]:
            back_rows.append([
                InlineKeyboardButton(
                    f"🔙 Back to {product['category']}",
                    callback_data=f"cat_{product['category']}",
                )
            ])
        back_rows.append(back_to_categories_row())
        back_rows.append(back_to_main_row())

        await query.edit_message_text(
            detail,
            parse_mode="MarkdownV2",
            reply_markup=_kb(back_rows),
        )

    else:
        logger.warning("Unknown callback data: %s", data)


# ─────────────────────────── MarkdownV2 helper ───────────────────────────────

_MD_SPECIAL = r"\_*[]()~`>#+-=|{}.!"

def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    for ch in _MD_SPECIAL:
        text = text.replace(ch, f"\\{ch}")
    return text


# ─────────────────────────── Entry point ─────────────────────────────────────

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN is missing from .env")

    logger.info("🤖 Connecting to Google Sheets …")
    # Warm up the sheet connection at startup so the first user doesn't wait
    try:
        sheet._get_sheet()
    except Exception as exc:
        logger.error("Google Sheets connection failed: %s", exc)

    logger.info("🚀 Starting Telegram bot …")

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    # Register conversation handler first so it intercepts callback_queries
    app.add_handler(build_voucher_handler())
    
    app.add_handler(CommandHandler(["start", "menu"], cmd_start))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("✅ Bot is running! Send /start to begin.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
