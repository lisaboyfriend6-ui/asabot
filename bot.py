from services.search import smart_search
import json
import sqlite3
import time
import difflib
import logging
import os

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
# IMPORTANT: Use environment variables for security!
# Set this in your terminal: export BOT_TOKEN="your_token_here"
# Or use python-dotenv for .env file
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Replace or use env var
ADMIN_ID = 5848609177
DB_FILE = "bot.db"
JSON_FILE = "quick_reply.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================
# LOAD DATA
# =====================
def load_series():
    """Load series data from JSON file"""
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{JSON_FILE} not found!")
        return []
    except json.JSONDecodeError:
        logger.error(f"{JSON_FILE} has invalid JSON!")
        return []

SERIES = load_series()

# =====================
# ANTI-DUPLICATION SYSTEM
# =====================
PROCESSED_UPDATES = {}
UPDATE_TTL = 30  # seconds


def is_duplicate(update_id: int):
    """Prevent duplicate updates from Telegram"""
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
    """Prevent user from sending same message repeatedly"""
    last = context.application.bot_data.get(user_id)
    if last == text:
        return True
    context.application.bot_data[user_id] = text
    return False


# =====================
# DATABASE
# =====================
def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized")


def add_sub(user_id):
    """Add user to subscribers list"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO subscribers VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def remove_sub(user_id):
    """Remove user from subscribers list"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_subs():
    """Get all subscribers"""
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
    """Calculate similarity score between query and series name"""
    ratio = difflib.SequenceMatcher(None, query, name).ratio()
    words = query.split()
    word_hits = sum(1 for w in words if w in name)
    return ratio * 3 + word_hits * 2


def search(query):
    """Search for series matching the query"""
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
    """Build inline keyboard from button data"""
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
# COMMAND HANDLERS
# =====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"🎬 ကြိုဆိုပါတယ် ၊ {user.first_name}!\n\n"
        " Animation by Asa ထဲက ကိုယ်အလိုရှိသော စီးရီးများကို ရှာဖွေလိုက်ပါ။\n\n"
        "Commands:\n"
        "/list - တင်ထားသောစီးရီးများကိုကြည့်ရန်\n"
        "/notify - သတင်းအချက်အလက်များရယူရန်\n"
        "/unnotify - သတင်းအချက်အလက်များကို ရပ်တန့်ရန်\n"
        "/help - Show this help message\n\n"
        "စီးရီးနာမည်မှ တခြားမရိုက်ပါနဲံဗျ။"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "📖 *Available Commands*\n\n"
        "/start - Start the bot\n"
        "/list - တင်ထားသောစီးရီးများကိုကြည့်ရန်\n"
        "/notify - သတင်းအချက်အလက်များရယူရန်\n"
        "/unnotify - သတင်းအချက်အလက်များကို ရပ်တန့်ရန်\n"
        "/help - Show this help message\n\n"
        "*How to use:*\n"
        "စီးရီးနာမည်ကို အတိအကျ ရိုက်ပေးပါဗျ။",
        parse_mode="Markdown"
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command - show all series"""
    if not SERIES:
        await update.message.reply_text("❌ No series data available")
        return
    
    names = "\n".join([f"• {s['command']}" for s in SERIES])
    
    # Split into multiple messages if too long (Telegram limit ~4000 chars)
    if len(names) > 4000:
        chunks = [names[i:i+4000] for i in range(0, len(names), 4000)]
        for chunk in chunks:
            await update.message.reply_text(f"📋 *Available Series:*\n\n{chunk}", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"📋 *Available Series:*\n\n{names}", parse_mode="Markdown")


async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /notify command - subscribe user"""
    user_id = update.effective_user.id
    add_sub(user_id)
    await update.message.reply_text("🔔 You have been subscribed to notifications!")


async def unnotify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unnotify command - unsubscribe user"""
    user_id = update.effective_user.id
    remove_sub(user_id)
    await update.message.reply_text("🔕 You have been unsubscribed from notifications!")


# =====================
# MESSAGE HANDLER (SEARCH)
# =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages (search queries)"""
    
    update_id = update.update_id
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Prevent duplicate updates
    if is_duplicate(update_id):
        logger.debug(f"Duplicate update {update_id}, ignoring")
        return

    # Debounce spam
    if debounce(context, user_id, text):
        logger.debug(f"Debounced message from {user_id}: {text}")
        return

    logger.info(f"Search query from {user_id}: {text}")

    # Perform search
    results = search(text)

    if not results or results[0][0] == 0:
        await update.message.reply_text("❓ Sorry, I couldn't find what you're looking for.\n\nTry using /list to see available options.")
        return

    best_score, best = results[0]

    # Strong match -> send directly
    if best_score > 3.5:
        markup = build_buttons(best.get("buttons"))
        response = best.get("msg", "No information available")
        await update.message.reply_text(response, reply_markup=markup)
        return

    # Weak match -> show suggestions
    top_results = results[:3]
    keyboard = []
    for score_val, item in top_results:
        if score_val > 0:  # Only show if there's some match
            keyboard.append([
                InlineKeyboardButton(
                    f"👉 {item['command']}",
                    callback_data=f"pick|{item['command']}"
                )
            ])
    
    if keyboard:
        await update.message.reply_text(
            "🤔 Did you mean one of these?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❓ No matches found. Try /list to see all available options.")


# =====================
# CALLBACK HANDLER
# =====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()

    data = query.data
    
    logger.info(f"Callback from {update.effective_user.id}: {data}")

    if data.startswith("pick|"):
        name = data.split("|")[1]

        for s in SERIES:
            if s["command"] == name:
                markup = build_buttons(s.get("buttons"))
                await query.message.reply_text(s["msg"], reply_markup=markup)
                return
        
        await query.message.reply_text("❌ Sorry, that item is no longer available.")


# =====================
# ADMIN COMMANDS (Optional)
# =====================
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: Broadcast message to all subscribers"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    # Get the message to broadcast
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    broadcast_msg = " ".join(context.args)
    subscribers = get_subs()
    
    if not subscribers:
        await update.message.reply_text("No subscribers to broadcast to.")
        return
    
    sent = 0
    failed = 0
    
    for sub_id in subscribers:
        try:
            await context.bot.send_message(chat_id=sub_id, text=f"📢 *Announcement:*\n\n{broadcast_msg}", parse_mode="Markdown")
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send to {sub_id}: {e}")
            failed += 1
        
        # Small delay to avoid hitting rate limits
        await asyncio.sleep(0.05)
    
    await update.message.reply_text(f"✅ Broadcast complete!\nSent: {sent}\nFailed: {failed}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: Show bot statistics"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    subscribers = len(get_subs())
    series_count = len(SERIES)
    
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Subscribers: {subscribers}\n"
        f"🎬 Series available: {series_count}\n"
        f"📁 Database: {DB_FILE}\n"
        f"📄 Data file: {JSON_FILE}",
        parse_mode="Markdown"
    )


# =====================
# ERROR HANDLER
# =====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and notify admin"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Notify admin about critical errors
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ Bot error occurred!\n\n{str(context.error)[:500]}"
        )
    except:
        pass


# =====================
# START BOT
# =====================
def main():
    """Main function to start the bot"""
    
    # Initialize database
    init_db()
    
    # Verify data loaded
    if not SERIES:
        logger.warning("No series data loaded! Check your JSON file.")
    
    # Create application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("notify", notify_command))
    app.add_handler(CommandHandler("unnotify", unnotify_command))
    
    # Admin commands (optional - remove if not needed)
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Add callback and message handlers
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot is starting...")
    print("🤖 Bot is running... Press Ctrl+C to stop")
    
    # Run the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Import asyncio for broadcast function
    import asyncio
    main()
