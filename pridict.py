import os
import telebot
import random
import time
import pytz
import socket
from datetime import datetime, timedelta
from threading import Thread, Lock
from flask import Flask

# ================= CONFIGURATION =================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'testsub01')
COOLDOWN_SECONDS = 120
PREDICTION_DELAY = 130
PORT = int(os.environ.get('PORT', 10000))
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')

# ================ UTILITY FUNCTIONS ================
def is_port_in_use(port):
    """Check if port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_indian_time():
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    return dt.strftime("%I:%M:%S %p")

def is_member(user_id):
    """Check channel membership"""
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Membership error: {e}")
        return False

# ============== BOT INITIALIZATION ==============
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
bot_lock = Lock()
cooldowns = {}

# ============== PREDICTION ENGINE ==============
def generate_prediction():
    pred = round(random.uniform(1.30, 2.40), 2)
    safe = round(random.uniform(1.30, min(pred, 2.0)), 2)
    future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
    return format_time(future_time), pred, safe

# ============== TELEGRAM HANDLERS ==============
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        user_id = message.chat.id
        if is_member(user_id):
            bot.send_message(
                user_id,
                f"✅ *Welcome!*\nCurrent IST: {format_time(get_indian_time())}",
                reply_markup=telebot.types.InlineKeyboardMarkup().add(
                    telebot.types.InlineKeyboardButton(
                        "🎯 Get Prediction", 
                        callback_data="get_prediction"
                    )
                ),
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                user_id,
                f"❌ Join @{CHANNEL_USERNAME} first!",
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"Welcome error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction(call):
    try:
        user_id = call.message.chat.id
        if user_id in cooldowns and (remaining := cooldowns[user_id] - time.time()) > 0:
            bot.answer_callback_query(call.id, f"Wait {int(remaining)}s", show_alert=True)
            return

        future_time, pred, safe = generate_prediction()
        bot.send_message(
            user_id,
            f"📊 *Prediction*\n⏳ {future_time}\n📈 {round(pred+0.1,2)}x\n🛡 {safe}x",
            parse_mode="Markdown"
        )
        cooldowns[user_id] = time.time() + COOLDOWN_SECONDS
        bot.answer_callback_query(call.id, "✅ Done!")
    except Exception as e:
        print(f"Prediction error: {e}")

# ============== FLASK SERVER ==============
@app.route('/')
def health_check():
    return "🤖 Bot Operational", 200

@app.route('/ping')
def ping():
    return {
        "status": "ok",
        "time": format_time(get_indian_time()),
        "users_in_cooldown": len(cooldowns)
    }

def run_flask():
    """Run Flask web server"""
    if not is_port_in_use(PORT):
        app.run(host='0.0.0.0', port=PORT, threaded=True)

# ============== BOT POLLING ==============
def run_bot():
    """Run bot with auto-restart"""
    print("🤖 Bot polling started")
    while True:
        try:
            with bot_lock:
                # REMOVED restart_on_change TO AVOID WATCHDOG DEPENDENCY
                bot.infinity_polling(
                    long_polling_timeout=30,
                    timeout=20
                )
        except Exception as e:
            print(f"🛑 Bot crash: {e}")
            time.sleep(10)

# ============== MAIN EXECUTION ==============
if __name__ == '__main__':
    # Start bot in background thread
    Thread(target=run_bot, daemon=True).start()
    
    # Start Flask in main thread (required for Render)
    print(f"🌐 Starting web server on port {PORT}")
    run_flask()
