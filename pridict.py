import os
import telebot
import random
import time
import pytz
from datetime import datetime, timedelta
from flask import Flask, request
import threading

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'testsub01')
COOLDOWN_SECONDS = 120
PREDICTION_DELAY = 130
PORT = int(os.environ.get('PORT', 10000))
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')

if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN")

# Initialize
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
cooldowns = {}

# Prediction Functions (same as before)
def get_indian_time():
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    return dt.strftime("%I:%M:%S %p")

def generate_prediction():
    pred = round(random.uniform(1.30, 2.40), 2)
    safe = round(random.uniform(1.30, min(pred, 2.0)), 2)
    future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
    return format_time(future_time), pred, safe

# Telegram Handlers (same as before)
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # ... (keep existing implementation)

@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction(call):
    # ... (keep existing implementation)

# Flask Routes
@app.route('/')
def health_check():
    return "🤖 Bot Operational", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400

def run_bot():
    print("🚀 Bot started polling...")
    while True:
        try:
            bot.infinity_polling(long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ Bot error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask app
    print(f"🌐 Web server starting on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
