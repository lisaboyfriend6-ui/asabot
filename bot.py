import json
import sqlite3
import logging
import difflib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================
# CONFIG
# =====================
BOT_TOKEN = "8705324629:AAG-tGNDzHbUoCJTKorJKv0B4d7h-tz4D6U"
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
# DB
# =====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT
    )""")

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


def save_feedback(user_id, msg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (user_id, message) VALUES (?, ?)", (user_id, msg))
    conn.commit()
    conn.close()


# =====================
# SMART SEARCH ENGINE
# =====================
def smart_match(text: str):
    text = text.lower().strip()

    commands = [s["command"] for s in SERIES]

    # 1. exact match
    for s in SERIES:
        if s["command"].lower() == text:
            return s

    # 2. substring match (very powerful)
    for s in SERIES:
        if text in s["command"].lower():
            return s

    # 3. reverse substring
    for s in SERIES:
        if s["command"].lower() in text:
            return s

    # 4. keyword scoring
    best_score = 0
    best_item = None

    for s in SERIES:
        name = s["command"].lower()

        score = 0

        # word overlap scoring
        for word in text.split():
            if word in name:
                score += 2

        # similarity scoring
        ratio = difflib.SequenceMatcher(None, text, name).ratio()
        score += ratio * 3

        if score > best_score:
            best_score = score
            best_item = s

    if best_score > 2:
        return best_item

    # 5. fallback fuzzy match
    match = difflib.get_close_matches(text, commands, n=1, cutoff=0.55)

    if match:
        for s in SERIES:
            if s["command"] == match[0]:
                return s

    return None


# =====================
# BUTTONS
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
# COMMANDS
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Bot ready!\n\n"
        "/list - series list\n"
        "/notify - subscribe\n"
        "/unnotify - unsubscribe\n"
        "/feedback message"
    )


async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = "\n".join([f"• {s['command']}" for s in SERIES])
    await update.message.reply_text(names)


async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_sub(update.effective_user.id)
    await update.message.reply_text("🔔 subscribed")


async def unnotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remove_sub(update.effective_user.id)
    await update.message.reply_text("🔕 unsubscribed")


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("Usage: /feedback message")
        return

    save_feedback(user_id, text)

    await context.bot.send_message(
        ADMIN_ID,
        f"📝 Feedback\nID: {user_id}\n\n{text}"
    )

    await update.message.reply_text("sent ✔")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = " ".join(context.args)
    if not msg:
        return await update.message.reply_text("Usage: /broadcast msg")

    users = get_subs()

    count = 0
    for u in users:
        try:
            await context.bot.send_message(u, msg)
            count += 1
        except:
            pass

    await update.message.reply_text(f"sent to {count}")


# =====================
# MESSAGE HANDLER
# =====================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    result = smart_match(text)

    if not result:
        await update.message.reply_text("❓ Not found. Try /list")
        return

    markup = build_buttons(result.get("buttons"))

    await update.message.reply_text(result["msg"], reply_markup=markup)


# =====================
# START BOT
# =====================
def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_series))
    app.add_handler(CommandHandler("notify", notify))
    app.add_handler(CommandHandler("unnotify", unnotify))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
