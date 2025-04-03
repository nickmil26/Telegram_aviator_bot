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

# Emojis and Stickers
ROCKET = "🚀"
LOCK = "🔒"
CHECK = "✅"
CROSS = "❌"
HOURGLASS = "⏳"
DIAMOND = "◆"
CALENDAR = "📅"
MONEY_BAG = "💰"
GRAPH = "📈"
SHIELD = "🛡️"
ROCKET_STICKER_ID = "CAACAgUAAxkBAAEL3xRmEeX3xQABHYYYr4YH1LQhUe3VdW8AAp4LAAIWjvlVjXjWbJQN0k80BA"  # Replace with actual sticker ID

# Track first-time users
first_time_users = set()

# ================ UTILITY FUNCTIONS ================
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_indian_time():
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    return dt.strftime("%H:%M")

def is_member(user_id):
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
    pred = round(random.uniform(2.50, 4.50), 2)
    safe = round(random.uniform(1.50, min(pred, 3.0)), 2)
    future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
    return format_time(future_time), pred, safe

# ============== TELEGRAM HANDLERS ==============
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        user_id = message.chat.id
        
        welcome_msg = (
            f"{GRAPH} *ᗯEᒪᑕOᗰE TO ᗩI-ᑭOᗯEᖇEᗪ ᑭᖇEᗪIᑕTIOᑎ ᗷOT* {GRAPH}\n\n"
            
            "This bot generates high-probability predictions using "
            "advanced algorithms. For optimal results:\n"
            
            f"{DIAMOND} Use suggested assurance for risk management\n"
            f"{DIAMOND} Follow cooldown periods between predictions\n\n"
            f"{SHIELD} *VIP Channel:* @{CHANNEL_USERNAME}"
        )
        
        if is_member(user_id):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    f"{ROCKET} Generate Prediction {ROCKET}", 
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
                    "Join VIP Channel", 
                    url=f"https://t.me/{CHANNEL_USERNAME}"
                ),
                telebot.types.InlineKeyboardButton(
                    "Verify Membership", 
                    callback_data="check_membership"
                )
            )
            
            bot.send_message(
                user_id,
                f"{CROSS} *🅿🆁🅴🅼🅸🆄🅼 🅰🅲🅲🅴🆂🆂 🆁🅴🆀🆄🅸🆁🅴🅳*\n\n"
                "\n You must join our VIP channel to access predictions:\n"
                f"👉 @{CHANNEL_USERNAME}\n\n"
                "After joining, click 'Verify Membership'",
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
            bot.answer_callback_query(call.id, "✅ Membership verified!")
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Please join the channel first!", show_alert=True)
    except Exception as e:
        print(f"Membership check error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction(call):
    try:
        user_id = call.message.chat.id
        
        if not is_member(user_id):
            bot.answer_callback_query(call.id, "❌ Channel membership required!", show_alert=True)
            return
            
        if user_id in cooldowns and (remaining := cooldowns[user_id] - time.time()) > 0:
            mins, secs = divmod(int(remaining), 60)
            bot.answer_callback_query(
                call.id, 
                f"{LOCK} Please wait {mins}m {secs}s", 
                show_alert=True
            )
            return

        # Remove button from original message
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
        except Exception as e:
            print(f"Button removal error: {e}")

        # Send rocket sticker for first-time users
        if user_id not in first_time_users:
            try:
                bot.send_sticker(user_id, ROCKET_STICKER_ID)
                first_time_users.add(user_id)
            except Exception as e:
                print(f"Sticker sending error: {e}")

        # Generate and send prediction
        future_time, pred, safe = generate_prediction()
        
        prediction_msg = (
            f"{ROCKET} *LUCKY JET PREDICTION*\n"
            "┏━━━━━━━━━━━━━\n"
            f"┠ {DIAMOND} 🕒 𝐓𝐈𝐌𝐄 : {future_time}\n"
            f"┠\n"
            f"┠ {DIAMOND} 𝐂𝐎𝐄𝐅𝐅𝐈𝐂𝐈𝐄𝐍𝐓 : {pred}X {ROCKET}\n"
            f"┠\n"
            f"┠ {DIAMOND} 𝐀𝐒𝐒𝐔𝐑𝐄𝐍𝐂𝐄 : {safe}X\n"
            "┗━━━━━━━━━━━━━\n\n"
            f"{HOURGLASS} Next prediction available in {COOLDOWN_SECONDS//60} minutes"
        )
        
        # Create new button for next prediction
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton(
                f"{ROCKET} New Prediction {ROCKET}", 
                callback_data="get_prediction"
            )
        )
        
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
    if not is_port_in_use(PORT):
        app.run(host='0.0.0.0', port=PORT, threaded=True)

# ============== BOT POLLING ==============
def run_bot():
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

if __name__ == '__main__':
    Thread(target=run_bot, daemon=True).start()
    print(f"🌐 Starting web server on port {PORT}")
    run_flask()
