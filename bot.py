import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Your bot token (you'll set this as an environment variable on PythonAnywhere)
TOKEN = os.environ.get('BOT_TOKEN')

# Load your commands from quick_reply.json
with open('quick_reply.json', 'r', encoding='utf-8') as f:
    COMMANDS = json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Animation Bot!\n\n"
        "Type any of these show names to get links:\n"
        "• rick and morty\n"
        "• Pantheon\n"
        "• Primal\n"
        "• Adventure time\n"
        "• And many more!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()
    
    for cmd in COMMANDS:
        if cmd['command'].lower() in user_text:
            # Build buttons (support multiple buttons)
            buttons = []
            for row in cmd.get('buttons', []):
                button_row = []
                for btn in row:
                    button_row.append(InlineKeyboardButton(btn['text'], url=btn['url']))
                buttons.append(button_row)
            
            reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
            
            await update.message.reply_text(
                cmd['msg'],
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return
    
    # No match found
    await update.message.reply_text(
        "ဒီအမည်ရှိ ရုပ်ရှင်ကို ရှာမတွေ့ပါဗျာ။\n\n"
        "Available shows: rick and morty, Pantheon, Primal, Adventure time, Bojack, and more!"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is polling for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()