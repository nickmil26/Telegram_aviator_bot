import os
import telebot
import random
import time
import pytz
import socket
import redis
from datetime import datetime, timedelta
from threading import Thread, Lock
from flask import Flask, jsonify

# ======================
# 🛠 CONFIGURATION
# ======================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'testsub01')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
COOLDOWN_SECONDS = 120
PREDICTION_DELAY = 130
PORT = int(os.environ.get('PORT', 10000))
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')

# ======================
# 🔐 INITIALIZATION
# ======================
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
bot_lock = Lock()

# Redis connection with fallback
try:
    r = redis.from_url(REDIS_URL, socket_timeout=3)
    r.ping()
    print("✅ Redis connected")
except Exception as e:
    print(f"⚠️ Redis failed: {e}. Using in-memory storage")
    r = None

# ======================
# ⏰ TIME UTILITIES
# ======================
def get_indian_time():
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    return dt.strftime("%I:%M:%S %p")

# ======================
# 🗄️ DATA STORAGE
# ======================
def get_cooldown(user_id):
    if r:
        remaining = r.ttl(f'cooldown:{user_id}')
        return remaining if remaining > 0 else 0
    return max(cooldowns.get(user_id, 0) - time.time(), 0)

def set_cooldown(user_id):
    expiry = int(time.time()) + COOLDOWN_SECONDS
    if r:
        r.setex(f'cooldown:{user_id}', COOLDOWN_SECONDS, '1')
    else:
        cooldowns[user_id] = expiry

# ======================
# 🎯 PREDICTION ENGINE
# ======================
def generate_prediction():
    pred = round(random.uniform(1.30, 2.40), 2)
    safe = round(random.uniform(1.30, min(pred, 2.0)), 2)
    future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
    return format_time(future_time), pred, safe

# ======================
# 🤖 BOT HANDLERS
# ======================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        user_id = message.chat.id
        if is_member(user_id):
            bot.send_message(
                user_id,
                f"✅ *Welcome!*\nCurrent IST: {format_time(get_indian_time())}",
                reply_markup=get_prediction_button(),
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
        if (remaining := get_cooldown(user_id)) > 0:
            bot.answer_callback_query(call.id, f"Wait {remaining}s", show_alert=True)
            return

        future_time, pred, safe = generate_prediction()
        bot.send_message(
            user_id,
            f"📊 *Prediction*\n⏳ {future_time}\n📈 {round(pred+0.1,2)}x\n🛡 {safe}x",
            parse_mode="Markdown"
        )
        set_cooldown(user_id)
        bot.answer_callback_query(call.id, "✅ Done!")
    except Exception as e:
        print(f"Prediction error: {e}")

# ======================
# 🌐 WEB SERVER
# ======================
@app.route('/')
def health_check():
    return jsonify({
        "status": "operational",
        "time": format_time(get_indian_time())
    })

@app.route('/metrics')
def metrics():
    return jsonify({
        "users_active": len(cooldowns) if not r else r.dbsize(),
        "memory_usage": os.sys.getsizeof(cooldowns)
    })

# ======================
# 🚀 LAUNCH SYSTEM
# ======================
def run_bot():
    print("🤖 Bot instance started")
    while True:
        try:
            with bot_lock:
                bot.infinity_polling(
                    long_polling_timeout=30,
                    timeout=20,
                    restart_on_change=True
                )
        except Exception as e:
            print(f"🛑 Bot crash: {e}")
            time.sleep(10)

def run_flask():
    if not is_port_in_use(PORT):
        app.run(host='0.0.0.0', port=PORT, threaded=True)

if __name__ == '__main__':
    print("🚀 Starting services...")
    Thread(target=run_bot, daemon=True).start()
    Thread(target=run_flask, daemon=True).start()
    
    while True:
        time.sleep(3600)  # Keep main thread alive
