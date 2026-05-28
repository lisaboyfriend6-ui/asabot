import json
import os
import requests
import time

# Environment variables
TOKEN = os.environ.get('BOT_TOKEN')

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

def handle_message(chat_id, text):
    """Process user messages - check for show commands."""
    user_text = text.lower().strip()
    
    # Check for exact match in show names
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
    
    return False

def main():
    """Main bot loop - polls for messages."""
    print("🚀 ဘော့စတင်လည်ပတ်နေပါပြီ...")
    print("✅ ရှိုးစာရင်းများ ပါဝင်သည်:", [cmd['command'] for cmd in COMMANDS])
    
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
                                "🎬 <b>Animation by Asa ဘော့မှ ကြိုဆိုပါတယ်!</b>\n\n"
                                "စီးရီးအမည်ကို ရိုက်ထည့်လိုက်ရုံနဲ့ လင့်ခ်ရယူလို့ရပါတယ်။\n"
                                "ဥပမာ: <code>rick and morty</code>\n\n"
                                "ရရှိနိုင်တဲ့ စီးရီးများ:\n"
                                "• rick and morty\n"
                                "• Pantheon\n"
                                "• Primal\n"
                                "• Adventure time\n"
                                "• Bojack Horseman\n"
                                "• နောက်ထပ်များစွာ..."
                            )
                        else:
                            handled = handle_message(chat_id, text)
                            if not handled:
                                send_message(
                                    chat_id,
                                    "❓ ဒီအမည်ရှိ ရုပ်ရှင်ကို ရှာမတွေ့ပါ။\n\n"
                                    "စီးရီးအမည်ကို အတိအကျ ရိုက်ထည့်ပေးပါ။\n"
                                    "ဥပမာ: <code>rick and morty</code>"
                                )
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()