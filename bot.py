import json
import os
import requests
import time

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

YOUR_USER_ID = 5848609177 # CHANGE TO YOUR ID

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
    message = f"📝 <b>Feedback</b>\n👤 {user_name}\n🆔 <code>{user_id}</code>\n💬 {feedback_text}"
    send_message(YOUR_USER_ID, message)

def handle_message(chat_id, text, user_name, user_id):
    user_text = text.lower().strip()
    
    if user_text == '/list':
        show_list = "\n".join([f"• {cmd['command']}" for cmd in COMMANDS])
        send_message(chat_id, f"📺 Shows:\n{show_list}")
        return True
    
    if user_text.startswith('/feedback'):
        feedback_msg = text.replace('/feedback', '').strip()
        if feedback_msg:
            forward_to_admin(chat_id, user_name, user_id, feedback_msg)
            send_message(chat_id, "✅ Feedback sent!")
        else:
            send_message(chat_id, "📝 Usage: /feedback your message")
        return True
    
    if user_text == '/notify':
        subs = load_subscribers()
        if user_id in subs:
            send_message(chat_id, "🔔 Already subscribed")
        else:
            subs.append(user_id)
            save_subscribers(subs)
            send_message(chat_id, "🔔 Subscribed!")
        return True
    
    if user_text == '/unnotify':
        subs = load_subscribers()
        if user_id in subs:
            subs.remove(user_id)
            save_subscribers(subs)
            send_message(chat_id, "🔕 Unsubscribed")
        else:
            send_message(chat_id, "❓ Not subscribed")
        return True
    
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
    
    # Simple not found - NO "Available shows" line
    send_message(chat_id, "❓ Not found. Use /list to see all shows.")
    return False

def main():
    print("Bot running...")
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
                        if text == '/start':
                            send_message(chat_id, "🎬 Send a show name or /list")
                        else:
                            handle_message(chat_id, text, user_name, user_id)
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()