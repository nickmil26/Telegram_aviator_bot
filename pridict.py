import os
import telebot
import random
import time
import pytz
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

# ==============================================
# 🔧 CONFIGURATION (from Environment Variables)
# ==============================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # Your Telegram Bot Token (Required)
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'testsub01')  # Your Telegram Channel
COOLDOWN_SECONDS = 120  # 2-minute cooldown between predictions
PREDICTION_DELAY = 130  # 2min 10sec delay for predictions
PORT = int(os.environ.get('PORT', 10000))  # Render requires a port (default: 10000)
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')  # Timezone for predictions

# ==============================================
# ❌ ERROR HANDLING: Check if BOT_TOKEN exists
# ==============================================
if not BOT_TOKEN:
    raise ValueError("❌ Missing BOT_TOKEN! Set it in Render Environment Variables.")

# ==============================================
# 🤖 INITIALIZE BOT & FLASK (Web Server)
# ==============================================
bot = telebot.TeleBot(BOT_TOKEN)  # Initialize Telegram Bot
app = Flask(__name__)  # Initialize Flask (for Render's health check)
cooldowns = {}  # Stores user cooldowns {user_id: cooldown_end_time}

# ==============================================
# ⏰ TIME FUNCTIONS (Indian Standard Time)
# ==============================================
def get_indian_time():
    """Returns current time in IST (Asia/Kolkata)."""
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    """Formats datetime into readable HH:MM:SS AM/PM."""
    return dt.strftime("%I:%M:%S %p")

# ==============================================
# 🔍 CHECK IF USER IS IN CHANNEL
# ==============================================
def is_member(user_id):
    """Checks if user is a member of the channel."""
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"⚠️ Membership check error: {e}")
        return False  # Assume not a member if error occurs

# ==============================================
# 🎯 GENERATE PREDICTION (Random Multipliers)
# ==============================================
def generate_prediction():
    """Generates random prediction values."""
    try:
        pred = round(random.uniform(1.30, 2.40), 2)  # 1.30x to 2.40x
        safe = round(random.uniform(1.30, min(pred, 2.0)), 2)  # 1.30x to 2.00x
        future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
        return format_time(future_time), pred, safe
    except Exception as e:
        print(f"⚠️ Prediction error: {e}")
        return format_time(get_indian_time()), 1.50, 1.40  # Fallback values

# ==============================================
# 🔘 INLINE BUTTON FOR PREDICTION
# ==============================================
def get_prediction_button():
    """Creates 'Get Prediction' button."""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎯 Get Prediction", callback_data="get_prediction"))
    return markup

# ==============================================
# 🏁 START COMMAND (Welcome Message)
# ==============================================
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    """Sends welcome message with prediction button."""
    try:
        user_id = message.chat.id
        current_time = format_time(get_indian_time())
        
        if is_member(user_id):
            bot.send_message(
                user_id,
                f"✅ *Welcome!*\nCurrent IST: {current_time}\nClick below for prediction:",
                reply_markup=get_prediction_button(),
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                user_id,
                f"❌ Please join @{CHANNEL_USERNAME} first!\nCurrent IST: {current_time}",
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"⚠️ Welcome error: {e}")
        bot.reply_to(message, "⚠️ Service temporary unavailable")

# ==============================================
# 🎯 PREDICTION HANDLER (Button Click)
# ==============================================
@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction(call):
    """Sends prediction when button is clicked."""
    try:
        user_id = call.message.chat.id
        
        # Check if user is in channel
        if not is_member(user_id):
            bot.answer_callback_query(call.id, "Join channel first!", show_alert=True)
            return

        # Check cooldown
        if user_id in cooldowns and (remaining := cooldowns[user_id] - time.time()) > 0:
            bot.answer_callback_query(call.id, f"Wait {int(remaining)}s", show_alert=True)
            return

        # Generate and send prediction
        future_time, pred, safe = generate_prediction()
        bot.send_message(
            user_id,
            f"📊 *Prediction*\n\n"
            f"⏳ Time: {future_time}\n"
            f"📈 Coefficient: {round(pred + 0.10, 2)}x\n"
            f"🛡 Safe: {safe}x",
            parse_mode="Markdown"
        )
        
        # Set cooldown
        cooldowns[user_id] = time.time() + COOLDOWN_SECONDS
        bot.answer_callback_query(call.id, "✅ Done!")
        
    except Exception as e:
        print(f"⚠️ Prediction error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Try again later")

# ==============================================
# 🌐 FLASK HEALTH CHECK (For Render)
# ==============================================
@app.route('/')
def health_check():
    """Simple health check endpoint."""
    return "🤖 Bot is running!", 200

# ==============================================
# 🤖 RUN BOT (With Auto-Restart on Crash)
# ==============================================
def run_bot():
    """Runs the bot with auto-restart on failure."""
    print("🚀 Bot started polling...")
    while True:
        try:
            bot.infinity_polling(long_polling_timeout=30)  # 30s timeout
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}\n🔄 Restarting in 5 seconds...")
            time.sleep(5)

# ==============================================
# 🏁 MAIN EXECUTION (Start Flask & Bot)
# ==============================================
if __name__ == '__main__':
    print("🚀 Starting bot and web server...")
    
    # Start bot in a background thread
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask (for Render health checks)
    app.run(host='0.0.0.0', port=PORT)
