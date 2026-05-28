import json
import os
import requests
import time
from collections import defaultdict

TOKEN = os.environ.get('BOT_TOKEN')
SUBSCRIBERS_FILE = 'subscribers.json'

with open('quick_reply.json', 'r', encoding='utf-8') as f:
    COMMANDS = json.load(f)

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_subscribers(subscribers):
    with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=4)

YOUR_USER_ID = 5848609177  # CHANGE TO YOUR ID

# Cooldown tracker to prevent duplicate responses
last_user_message_time = defaultdict(float)

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

def forward_to_admin(chat_id, user_name, user_id, feedback_text):
    message = f"📝 <b>တုံ့ပြန်ချက်အသစ်</b>\n\n👤 {user_name}\n🆔 <code>{user_id}</code>\n💬 {feedback_text}"
    send_message(YOUR_USER_ID, message)

def handle_message(chat_id, text, user_name, user_id):
    user_text = text.lower().strip()
    
    # /list command
    if user_text == '/list':
        show_list = "\n".join([f"• {cmd['command']}" for cmd in COMMANDS])
        send_message(chat_id, f"📺 <b>ရရှိနိုင်တဲ့ စီးရီးများ:</b>\n\n{show_list}")
        return True
    
    # /feedback command
    if user_text.startswith('/feedback'):
        feedback_msg = text.replace('/feedback', '').strip()
        if feedback_msg:
            forward_to_admin(chat_id, user_name, user_id, feedback_msg)
            send_message(chat_id, "✅ <b>ကျေးဇူးတင်ပါတယ်!</b>\n\nသင့်ရဲ့ တုံ့ပြန်ချက်ကို အက်မင်ထံ ပေးပို့ပြီးပါပြီ။")
        else:
            send_message(chat_id, "📝 <b>/feedback အသုံးပြုနည်း</b>\n\n<code>/feedback သင့်ရဲ့ တုံ့ပြန်ချက်</code>")
        return True
    
    # /notify command
    if user_text == '/notify':
        subscribers = load_subscribers()
        if user_id in subscribers:
            send_message(chat_id, "🔔 <b>သင်သည် သတင်းအကြောင်းကြားချက် ရရှိပြီးသားဖြစ်ပါသည်။</b>")
        else:
            subscribers.append(user_id)
            save_subscribers(subscribers)
            send_message(chat_id, "🔔 <b>သတင်းအကြောင်းကြားချက် စာရင်းသွင်းပြီးပါပြီ။</b>")
        return True
    
    # /unnotify command
    if user_text == '/unnotify':
        subscribers = load_subscribers()
        if user_id in subscribers:
            subscribers.remove(user_id)
            save_subscribers(subscribers)
            send_message(chat_id, "🔕 <b>သတင်းအကြောင်းကြားချက် စာရင်းမှ ဖယ်ရှားပြီးပါပြီ။</b>")
        else:
            send_message(chat_id, "❓ <b>သင်သည် သတင်းအကြောင်းကြားချက် စာရင်းတွင် မပါရှိပါ။</b>")
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
    
    # No match found
    send_message(chat_id, "❓ <b>စီးရီးအမည်ကို ရှာမတွေ့ပါ။</b>\n\n<code>/list</code> ကိုရိုက်ထည့်ပြီး ရရှိနိုင်တဲ့ စီးရီးများကို ကြည့်ရှုနိုင်ပါတယ်။")
    return False

def main():
    print("🚀 Bot is running...")
    last_id = 0
    processed = set()
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            resp = requests.get(url, params={'timeout': 30, 'offset': last_id + 1}, timeout=35)
            
            for update in resp.json().get('result', []):
                uid = update['update_id']
                if uid in processed:
                    continue
                processed.add(uid)
                if len(processed) > 1000:
                    processed = set(list(processed)[-500:])
                last_id = uid
                
                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    user_id = msg['from']['id']
                    user_name = msg['from'].get('first_name', 'Unknown')
                    
                    if 'text' in msg:
                        text = msg['text']
                        
                        # COOLDOWN CHECK - Prevent duplicate processing
                        current_time = time.time()
                        last_time = last_user_message_time.get(f"{chat_id}_{user_id}", 0)
                        if current_time - last_time < 1.5:
                            continue  # Skip if same user sent message less than 1.5 seconds ago
                        last_user_message_time[f"{chat_id}_{user_id}"] = current_time
                        
                        if text == '/start':
                            welcome_msg = (
                                "🎬 <b>Animation by Asa ဘော့မှ ကြိုဆိုပါတယ်!</b>\n\n"
                                "📺 <b>အသုံးပြုနိုင်တဲ့ Command များ:</b>\n\n"
                                "• <code>/list</code> - ရရှိနိုင်တဲ့ စီးရီးအားလုံးကို ကြည့်ရှုရန်\n"
                                "• <code>/feedback &lt;မက်ဆေ့ချ်&gt;</code> - တုံ့ပြန်ချက် ပေးပို့ရန်\n"
                                "• <code>/notify</code> - သတင်းအကြောင်းကြားချက် စာရင်းသွင်းရန်\n"
                                "• <code>/unnotify</code> - သတင်းအကြောင်းကြားချက် စာရင်းမှ ထွက်ရန်\n\n"
                                "🎬 <b>စီးရီးကြည့်ရှုရန်:</b>\n"
                                "စီးရီးအမည်ကို တိုက်ရိုက်ရိုက်ထည့်ပါ။\n"
                                "ဥပမာ: <code>rick and morty</code>\n\n"
                                "💡 အကူအညီလိုပါက <code>/feedback</code> ဖြင့် ဆက်သွယ်နိုင်ပါတယ်။"
                            )
                            send_message(chat_id, welcome_msg)
                        else:
                            handle_message(chat_id, text, user_name, user_id)
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()