import os
import telebot
import random
import time
import pytz
from datetime import datetime, timedelta
from threading import Thread, Lock
import socket
from flask import Flask

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'testsub01')
COOLDOWN_SECONDS = 120
PREDICTION_DELAY = 130
PORT = int(os.environ.get('PORT', 10000))
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')

# Validate token
if not BOT_TOKEN:
    raise ValueError("Missing required environment variable: BOT_TOKEN")

# Initialize bot with file-based lock
bot = telebot.TeleBot(BOT_TOKEN)
bot_lock = Lock()

# Store cooldown timers
cooldowns = {}

def get_indian_time():
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    return dt.strftime("%I:%M:%S %p")

def is_member(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

def generate_prediction():
    try:
        pred = round(random.uniform(1.30, 2.40), 2)
        safe = round(random.uniform(1.30, min(pred, 2.0)), 2)
        future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
        return format_time(future_time), pred, safe
    except Exception as e:
        print(f"Prediction generation error: {e}")
        raise

def get_prediction_button():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎯 Get Prediction", callback_data="get_prediction"))
    return markup

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    try:
        user_id = message.chat.id
        if is_member(user_id):
            bot.send_message(
                user_id,
                f"✅ *Welcome!*\nCurrent IST: {format_time(get_indian_time())}\nClick below for prediction:",
                reply_markup=get_prediction_button(),
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                user_id,
                f"❌ Please join @{CHANNEL_USERNAME} first!\nCurrent IST: {format_time(get_indian_time())}",
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"Welcome error: {e}")
        bot.reply_to(message, "⚠️ Service temporary unavailable")

@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction(call):
    try:
        user_id = call.message.chat.id
        if not is_member(user_id):
            bot.answer_callback_query(call.id, "Join channel first!", show_alert=True)
            return

        if user_id in cooldowns and (remaining := cooldowns[user_id] - time.time()) > 0:
            bot.answer_callback_query(call.id, f"Wait {int(remaining)}s", show_alert=True)
            return

        future_time, pred, safe = generate_prediction()
        bot.send_message(
            user_id,
            f"📊 *Prediction*\n\n⏳ Time: {future_time}\n📈 Coefficient: {round(pred + 0.10, 2)}x\n🛡 Safe: {safe}x",
            parse_mode="Markdown"
        )
        cooldowns[user_id] = time.time() + COOLDOWN_SECONDS
        bot.answer_callback_query(call.id, "✅ Done!")
    except Exception as e:
        print(f"Prediction error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Try again later")

def run_bot():
    print("🤖 Starting bot polling...")
    while True:
        try:
            with bot_lock:
                bot.infinity_polling(long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Bot error: {e}")
            time.sleep(5)

def run_flask():
    app = Flask(__name__)
    @app.route('/')
    def health_check():
        return "Bot is running", 200
    app.run(host='0.0.0.0', port=PORT)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

if __name__ == '__main__':
    print("🚀 Starting application...")
    
    # Start Flask only if port is available and running on Render
    if os.environ.get('RENDER') and not is_port_in_use(PORT):
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
    
    # Run bot with restart mechanism
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
