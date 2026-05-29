import json
import sqlite3
import time
import difflib
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =====================
# CONFIG
# =====================
BOT_TOKEN = "PUT_NEW_TOKEN_HERE"
ADMIN_ID = 5848609177
DB_FILE = "bot.db"
JSON_FILE = "quick_reply.json"

logging.basicConfig(level=logging.INFO)

# =====================
# LOAD DATA
# =====================
with open(JSON_FILE, "r", encoding="utf-8") as f:
    SERIES = json.load(f)

# =====================
# ANTI-DUPLICATION SYSTEM
# =====================
PROCESSED_UPDATES = {}
UPDATE_TTL = 30  # seconds


def is_duplicate(update_id: int):
    now = time.time()

    # cleanup old updates
    expired = [k for k, v in PROCESSED_UPDATES.items() if now - v > UPDATE_TTL]
    for k in expired:
        del PROCESSED_UPDATES[k]

    if update_id in PROCESSED_UPDATES:
        return True

    PROCESSED_UPDATES[update_id] = now
    return False


def debounce(context, user_id, text):
    last = context.application.bot_data.get(user_id)
    if last == text:
        return True
    context.application.bot_data[user_id] = text
    return False


# =====================
# DATABASE
# =====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


def add_sub(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO subscribers VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def remove_sub(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_subs():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM subscribers")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


# =====================
# SMART SEARCH ENGINE
# =====================
def score(query, name):
    ratio = difflib.SequenceMatcher(None, query, name).ratio()
    words = query.split()
    word_hits = sum(1 for w in words if w in name)
    return ratio * 3 + word_hits * 2


def search(query):
    query = query.lower().strip()
    results = []

    for s in SERIES:
        name = s["command"].lower()
        sc = score(query, name)

        if query in name or name in query:
            sc += 3

        results.append((sc, s))

    results.sort(reverse=True, key=lambda x: x[0])
    return results


# =====================
# BUTTON BUILDER
# =====================
def build_buttons(buttons):
    if not buttons:
        return None

    keyboard = []
    for row in buttons:
        keyboard.append([
            InlineKeyboardButton(b["text"], url=b["url"])
            for b in row
        ])
    return InlineKeyboardMarkup(keyboard)


# =====================
# ROUTER (NO DUPLICATION)
# =====================
async def route(update: Update, context: ContextTypes.DEFAULT_TYPE):

    update_id = update.update_id
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # 1. prevent Telegram duplicate updates
    if is_duplicate(update_id):
        return

    # 2. debounce spam
    if debounce(context, user_id, text):
        return

    # 3. COMMANDS
    if text == "/start":
        await update.message.reply_text("🎬 Bot ready")
        return

    if text == "/list":
        names = "\n".join([f"• {s['command']}" for s in SERIES])
        await update.message.reply_text(names)
        return

    if text == "/notify":
        add_sub(user_id)
        await update.message.reply_text("🔔 subscribed")
        return

    if text == "/unnotify":
        remove_sub(user_id)
        await update.message.reply_text("🔕 unsubscribed")
        return

    # 4. SEARCH
    results = search(text)

    if not results:
        await update.message.reply_text("❓ မတွေ့ပါ")
        return

    best_score, best = results[0]

    # strong match → send directly
    if best_score > 3.5:
        markup = build_buttons(best.get("buttons"))
        await update.message.reply_text(best["msg"], reply_markup=markup)
        return

    # weak match → suggestions
    top = results[:3]

    keyboard = []
    for _, item in top:
        keyboard.append([
            InlineKeyboardButton(
                f"👉 {item['command']}",
                callback_data=f"pick|{item['command']}"
            )
        ])

    await update.message.reply_text(
        "🤔 Did you mean?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =====================
# CALLBACK HANDLER
# =====================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("pick|"):
        name = data.split("|")[1]

        for s in SERIES:
            if s["command"] == name:
                markup = build_buttons(s.get("buttons"))
                await query.message.reply_text(s["msg"], reply_markup=markup)
                return


# =====================
# START BOT
# =====================
def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
