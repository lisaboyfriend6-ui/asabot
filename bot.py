import json
import os
import requests
import time

# Environment variables
TOKEN = os.environ.get('BOT_TOKEN')

# File to store subscribed users
SUBSCRIBERS_FILE = 'subscribers.json'

# Load your show commands
with open('quick_reply.json', 'r', encoding='utf-8') as f:
    COMMANDS = json.load(f)

# Load subscribers
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Save subscribers
def save_subscribers(subscribers):
    with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=4)

# CHANGE THIS TO YOUR TELEGRAM USER ID!
YOUR_USER_ID = 5848609177  # <--- Replace with your actual ID from @userinfobot

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

def forward_to_admin(chat_id, user_name, user_id, feedback_text):
    """Forward feedback to bot admin."""
    message = f"📝 <b>တုံ့ပြန်ချက်အသစ်</b>\n\n"
    message += f"👤 <b>အသုံးပြုသူ:</b> {user_name}\n"
    message += f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
    message += f"💬 <b>တုံ့ပြန်ချက်:</b>\n{feedback_text}"
    
    send_message(YOUR_USER_ID, message)

def handle_message(chat_id, text, user_name, user_id):
    """Process user messages - check for show commands."""
    user_text = text.lower().strip()
    
    # Command: /list
    if user_text == '/list':
        show_list = "\n".join([f"• {cmd['command']}" for cmd in COMMANDS])
        send_message(
            chat_id,
            f"📺 <b>ရရှိနိုင်တဲ့ စီးရီးများ:</b>\n\n{show_list}"
        )
        return True
    
    # Command: /feedback
    if user_text.startswith('/feedback'):
        feedback_msg = text.replace('/feedback', '').strip()
        if feedback_msg:
            forward_to_admin(chat_id, user_name, user_id, feedback_msg)
            send_message(
                chat_id,
                "✅ <b>ကျေးဇူးတင်ပါတယ်!</b>\n\nသင့်ရဲ့ တုံ့ပြန်ချက်ကို အက်မင်ထံ ပေးပို့ပြီးပါပြီ။"
            )
        else:
            send_message(
                chat_id,
                "📝 <b>/feedback အသုံးပြုနည်း</b>\n\n<code>/feedback သင့်ရဲ့ တုံ့ပြန်ချက်</code>"
            )
        return True
    
    # Command: /notify
    if user_text == '/notify':
        subscribers = load_subscribers()
        if user_id in subscribers:
            send_message(
                chat_id,
                "🔔 <b>သင်သည် သတင်းအကြောင်းကြားချက် ရရှိပြီးသားဖြစ်ပါသည်။</b>"
            )
        else:
            subscribers.append(user_id)
            save_subscribers(subscribers)
            send_message(
                chat_id,
                "🔔 <b>သတင်းအကြောင်းကြားချက် စာရင်းသွင်းပြီးပါပြီ!</b>"
            )
        return True
    
    # Command: /unnotify
    if user_text == '/unnotify':
        subscribers = load_subscribers()
        if user_id in subscribers:
            subscribers.remove(user_id)
            save_subscribers(subscribers)
            send_message(
                chat_id,
                "🔕 <b>သတင်းအကြောင်းကြားချက် စာရင်းမှ ဖယ်ရှားပြီးပါပြီ။</b>"
            )
        else:
            send_message(
                chat_id,
                "❓ <b>သင်သည် သတင်းအကြောင်းကြားချက် စာရင်းတွင် မပါရှိပါ။</b>"
            )
        return True
    
    # Check for exact match in show names
    for cmd in COMMANDS:
        if user_text == cmd['command'].lower():
            buttons = []
            for row in cmd.get('buttons', []):
                button_row = []
                for btn in row:
                    button_row.append({'text': btn['text'], 'url': btn['url']})
                buttons.append(button_row)
            
            reply_markup = {'inline_keyboard': buttons} if buttons else None
            send_message(chat_id, cmd['msg'], reply_markup)
            return True
    
    # No match found - simple message (NO "Available shows" line!)
    send_message(
        chat_id,
        "❓ <b>စီးရီးအမည်ကို ရှာမတွေ့ပါ။</b>\n\n<code>/list</code> ကိုရိုက်ထည့်ပြီး ရရှိနိုင်တဲ့ စီးရီးများကို ကြည့်ရှုနိုင်ပါတယ်။"
    )
    return False

def main():
    """Main bot loop - polls for messages."""
    print("🚀 ဘော့စတင်လည်ပတ်နေပါပြီ...")
    print("✅ Bot started - Clean version")
    
    last_update_id = 0
    processed_updates = set()
    
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
                update_id = update['update_id']
                
                if update_id in processed_updates:
                    continue
                processed_updates.add(update_id)
                
                if len(processed_updates) > 1000:
                    processed_updates = set(list(processed_updates)[-500:])
                
                last_update_id = update_id
                
                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    user_id = msg['from']['id']
                    user_name = msg['from'].get('first_name', 'Unknown')
                    
                    if 'text' in msg:
                        text = msg['text']
                        
                        if text == '/start':
                            send_message(
                                chat_id,
                                "🎬 <b>Animation by Asa ဘော့မှ ကြိုဆိုပါတယ်!</b>\n\n"
                                "📺 <b>Command များ:</b>\n"
                                "• <code>/list</code> - စီးရီးအားလုံးကို ကြည့်ရန်\n"
                                "• <code>/feedback &lt;မက်ဆေ့ချ်&gt;</code> - တုံ့ပြန်ချက်ပေးရန်\n"
                                "• <code>/notify</code> - သတင်းအကြောင်းကြားချက် ရယူရန်\n"
                                "• <code>/unnotify</code> - သတင်းအကြောင်းကြားချက် ရပ်ရန်\n\n"
                                "🎬 စီးရီးအမည်ကို ရိုက်ထည့်ပါ။ ဥပမာ: <code>rick and morty</code>"
                            )
                        else:
                            handle_message(chat_id, text, user_name, user_id)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()