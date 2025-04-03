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

# Emojis for better visual appeal
INDIAN_FLAG = "🇮🇳"
CLOCK = "⏱"
CHART = "📊"
SHIELD = "🛡"
MONEY = "💰"
ROCKET = "🚀"
CHECK = "✅"
CROSS = "❌"
LOCK = "🔒"

# ================ UTILITY FUNCTIONS ================
def is_port_in_use(port):
    """Check if port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_indian_time():
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    return dt.strftime("%I:%M %p")

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
        current_time = format_time(get_indian_time())
        
        if is_member(user_id):
            welcome_msg = (
                f"{INDIAN_FLAG} *Sureshot Predictions*\n\n"
                f"{CHECK} *VIP Access Granted*\n"
                f"{CLOCK} Current IST: {current_time}\n\n"
                "_Get accurate predictions with high winning probability_"
            )
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    f"{ROCKET} GET PREDICTION {ROCKET}", 
                    callback_data="get_prediction"
                )
            )
            
            bot.send_message(
                user_id,
                welcome_msg,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    "Join Channel", 
                    url=f"https://t.me/{CHANNEL_USERNAME}"
                ),
                telebot.types.InlineKeyboardButton(
                    "Check Membership", 
                    callback_data="check_membership"
                )
            )
            
            bot.send_message(
                user_id,
                f"{CROSS} *Access Denied*\n\n"
                f"Join our VIP channel to get premium predictions:\n"
                f"👉 @{CHANNEL_USERNAME}\n\n"
                "_After joining, click 'Check Membership' below_",
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"Welcome error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership(call):
    try:
        user_id = call.message.chat.id
        if is_member(user_id):
            bot.answer_callback_query(call.id, "✅ Membership verified! Click below to get predictions")
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ You haven't joined the channel yet!", show_alert=True)
    except Exception as e:
        print(f"Membership check error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction(call):
    try:
        user_id = call.message.chat.id
        current_time = get_indian_time()
        
        if not is_member(user_id):
            bot.answer_callback_query(call.id, "❌ Join channel first!", show_alert=True)
            return
            
        if user_id in cooldowns and (remaining := cooldowns[user_id] - time.time()) > 0:
            mins, secs = divmod(int(remaining), 60)
            bot.answer_callback_query(
                call.id, 
                f"{LOCK} Cooldown: {mins}m {secs}s remaining", 
                show_alert=True
            )
            return

        future_time, pred, safe = generate_prediction()
        
        # Format prediction message professionally
        prediction_msg = (
            f"{INDIAN_FLAG} *Premium Prediction*\n\n"
            f"{CLOCK} *Bet Time:* {future_time} IST\n"
            f"{CHART} *Coefficient:* {round(pred+0.1,2)}x\n"
            f"{SHIELD} *Safe Cashout:* {safe}x\n"
            f"{MONEY} *Potential Profit:* {round((pred+0.1)*10,2)}%\n\n"
            "_Place bet 2 minutes before the specified time_"
        )
        
        # Create markup for new message
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton(
                f"{ROCKET} GET NEW PREDICTION {ROCKET}", 
                callback_data="get_prediction"
            )
        )
        
        # Send the prediction with button
        bot.send_message(
            user_id,
            prediction_msg,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        # Set cooldown
        cooldowns[user_id] = time.time() + COOLDOWN_SECONDS
        bot.answer_callback_query(call.id, "✅ Prediction generated!")
            
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
