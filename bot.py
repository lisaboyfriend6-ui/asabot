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
    """Send question to Cloudflare's Llama 3 model - forces Burmese response."""
    if not CLOUDFLARE_API_KEY or not CLOUDFLARE_ACCOUNT_ID:
        return "⚠️ AI ကို စနစ်ထည့်သွင်းထားခြင်း မရှိပါ။"
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3-8b-instruct"
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Force Burmese response with instruction
    prompt_with_instruction = f"""ကျေးဇူးပြု၍ မြန်မာလိုဖြေပါ။ အင်္ဂလိပ်လုံးဝမသုံးပါနဲ့။

မေးခွန်း: {question}

မြန်မာလိုအဖြေ:"""
    
    data = {
        "prompt": prompt_with_instruction,
        "max_tokens": 500,
        "temperature": 0.5
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        
        print(f"Llama 3 Response: {result}")
        
        if 'errors' in result and result['errors']:
            error_msg = result['errors'][0].get('message', 'Unknown error')
            return f"⚠️ API အမှား: {error_msg}"
        
        if 'result' in result:
            if isinstance(result['result'], dict) and 'response' in result['result']:
                answer = result['result']['response']
            elif isinstance(result['result'], str):
                answer = result['result']
            else:
                answer = str(result['result'])
        elif 'response' in result:
            answer = result['response']
        else:
            return "အဖြေရှာမတွေ့ပါ။"
        
        return answer
    
    except requests.exceptions.Timeout:
        return "⏰ AI အချိန်ကုန်သွားပါပြီ။ နောက်မှထပ်စမ်းပါ။"
    except Exception as e:
        print(f"AI Error: {e}")
        return f"🤖 AI အမှား: {str(e)}"

def handle_message(chat_id, text):
    """Process user messages - check for show commands or AI questions."""
    user_text = text.lower().strip()
    
    # Check 1: AI question first (starts with ? or ai:)
    if user_text.startswith('?') or user_text.startswith('ai:'):
        question = user_text.replace('?', '').replace('ai:', '').strip()
        
        if question:
            send_message(chat_id, "🤖 စဉ်းစားနေပါသည်...")
            answer = ask_cloudflare_ai(question)
            
            if len(answer) > 4000:
                answer = answer[:4000] + "..."
            
            # AI response ONLY - no buttons, no links
            send_message(chat_id, f"🤖 <b>AI ၏ အဖြေ:</b>\n\n{answer}")
            return True
    
    # Check 2: Exact match for show names (from your JSON)
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
    if CLOUDFLARE_API_KEY and CLOUDFLARE_ACCOUNT_ID:
        print("✅ AI စနစ် အသင့်ရှိပါသည်!")
    else:
        print("⚠️ AI စနစ် မပါရှိပါ")
    
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
                            # PURE BURMESE WELCOME - NO ENGLISH
                            send_message(
                                chat_id,
                                "🎬 <b>Animation by Asa ဘော့မှ ကြိုဆိုပါတယ်!</b>\n\n"
                                "စီးရီးအမည်ကို ရိုက်ထည့်လိုက်ရုံနဲ့ လင့်ခ်ရယူလို့ရပါတယ်။\n"
                                "ဥပမာ: <code>rick and morty</code>\n\n"
                                "🤖 <b>AI အကူအညီ:</b> မေးခွန်းရဲ့ရှေ့မှာ <code>?</code> ထည့်ပြီးမေးမြန်းနိုင်ပါတယ်။\n"
                                "ဥပမာ: <code>? Rick and Morty ဆိုတာဘာလဲ</code>\n\n"
                                "💡 AI ကို မြန်မာလို မေးမြန်းနိုင်ပါတယ်။"
                            )
                        else:
                            handled = handle_message(chat_id, text)
                            if not handled:
                                send_message(
                                    chat_id,
                                    "❓ ဒီအမည်ရှိ ရုပ်ရှင်ကို ရှာမတွေ့ပါ။\n\n"
                                    "AI ကို <code>? မေးခွန်း</code> ပုံစံဖြင့် မေးမြန်းနိုင်ပါတယ်။\n"
                                    "ဥပမာ: <code>? Rick and Morty ဆိုတာဘာလဲ</code>"
                                )
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()