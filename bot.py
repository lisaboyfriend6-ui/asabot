import json
import os
import requests
import time

# Environment variables
TOKEN = os.environ.get('BOT_TOKEN')
CLOUDFLARE_API_KEY = os.environ.get('CLOUDFLARE_API_KEY')
CLOUDFLARE_ACCOUNT_ID = os.environ.get('CLOUDFLARE_ACCOUNT_ID')

# Load your show commands
with open('quick_reply.json', 'r', encoding='utf-8') as f:
    COMMANDS = json.load(f)

def send_message(chat_id, text, reply_markup=None):
    """Send a message to Telegram user/group."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

def ask_cloudflare_ai(question):
    """Send question to Cloudflare's Burmese-supported AI model."""
    if not CLOUDFLARE_API_KEY or not CLOUDFLARE_ACCOUNT_ID:
        return "⚠️ AI is not configured. Please add Cloudflare API keys."
    
    # Using Gemma SEA-Lion - supports Burmese!
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/aisingapore/gemma-sea-lion-v4-27b-it"
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "prompt": question,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        
        if 'errors' in result and result['errors']:
            return f"AI Error: {result['errors'][0].get('message', 'Unknown error')}"
        
        return result.get('result', {}).get('response', "Sorry, I couldn't answer that.")
    
    except requests.exceptions.Timeout:
        return "⏰ AI service timed out. Please try again."
    except Exception as e:
        print(f"AI Error: {e}")
        return "🤖 AI service temporarily unavailable. Please try again later."

def handle_message(chat_id, text):
    """Process user messages - check for show commands or AI questions."""
    user_text = text.lower().strip()
    
    # Check 1: Exact match for show names (from your JSON)
    for cmd in COMMANDS:
        if user_text == cmd['command'].lower():
            # Build buttons from JSON
            buttons = []
            for row in cmd.get('buttons', []):
                button_row = []
                for btn in row:
                    button_row.append({'text': btn['text'], 'url': btn['url']})
                buttons.append(button_row)
            
            reply_markup = {'inline_keyboard': buttons} if buttons else None
            send_message(chat_id, cmd['msg'], reply_markup)
            return True
    
    # Check 2: AI question (starts with ? or ai:)
    if user_text.startswith('?') or user_text.startswith('ai:'):
        question = user_text.replace('?', '').replace('ai:', '').strip()
        
        if question:
            send_message(chat_id, "🤖 စဥ်းစားနေပါသည်။...")
            answer = ask_cloudflare_ai(question)
            
            if len(answer) > 4000:
                answer = answer[:4000] + "..."
            
            send_message(chat_id, f"🤖 <b>Ai ၏ တုံ့ပြန်ချက်:</b>\n\n{answer}")
            return True
    
    return False

def main():
    """Main bot loop - polls for messages."""
    print("🚀 Bot is running...")
    print("✅ Show commands loaded:", [cmd['command'] for cmd in COMMANDS])
    print("✅ AI is enabled!" if CLOUDFLARE_API_KEY else "⚠️ AI not configured")
    
    last_update_id = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            response = requests.get(
                url, 
                params={'timeout': 30, 'offset': last_update_id + 1},
                timeout=35
            )
            
            data = response.json()
            
            for update in data.get('result', []):
                last_update_id = update['update_id']
                
                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    
                    if 'text' in msg:
                        text = msg['text']
                        
                        if text == '/start':
                            send_message(
                                chat_id,
                                "🎬 <b>Animation by Asa ရဲ့ Bot လေးကနေကြိုဆိုလိုက်ပါမယ်!</b>\n\n"
                                "ကြိုက်နှစ်သက်ရာ စီးရီးများကို စာရိုက်လိုက်ရုံနဲ့ ကြည့်ရှုနိုင်ပါပြီ ၊ ဥပမာ ၊ <code>rick and morty</code> ၊ လင့်ကို ရယူပါ။\n\n"
                                "🤖 <b>AI လက်ထောက်:</b> ဒီပုံစံအတိုင်း ? ကို ရှေ့မှားထားပီးမေးပေးပါ။ <code>? မေးခွန်း</code>\n"
                                "ဥပမာ: <code>? Rick and Morty ဆိုတာဘာလဲ?</code>\n\n"
                                "💡 AI ကို မြန်မာလို ပြောလည်းရပါတယ်!"
                            )
                        else:
                            handled = handle_message(chat_id, text)
                            if not handled:
                                send_message(
                                    chat_id,
                                    "❓ ဒီအမည်ရှိ ရုပ်ရှင်ကို ရှာမတွေ့ပါဗျာ။\n\n"
                                    "Type <code>? your question</code> to ask the AI assistant!\n"
                                    "Example: <code>? what is Rick and Morty about?</code>"
                                )
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()