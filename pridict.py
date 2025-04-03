import os
import telebot
import random
import time
import pytz
from datetime import datetime, timedelta
from flask import Flask

# Configuration from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'testsub01')
COOLDOWN_SECONDS = 120
PREDICTION_DELAY = 130

# Timezone setup for India
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("Missing required environment variable: BOT_TOKEN")

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize Flask app
app = Flask(__name__)

# Store cooldown timers
cooldowns = {}

def get_indian_time():
    """Get current time in Indian timezone"""
    return datetime.now(INDIAN_TIMEZONE)

def format_time(dt):
    """Format datetime object to Indian time string"""
    return dt.strftime("%I:%M:%S %p")

def is_member(user_id):
    """Check if user is a member of the channel."""
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

def generate_prediction():
    """Generate prediction values with Indian time."""
    try:
        prediction_multiplier = round(random.uniform(1.30, 2.40), 2)
        safe_multiplier = round(random.uniform(1.30, min(prediction_multiplier, 2.0)), 2)
        future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
        return format_time(future_time), prediction_multiplier, safe_multiplier
    except Exception as e:
        print(f"Error generating prediction: {e}")
        raise

def get_prediction_button():
    """Create inline keyboard with prediction button."""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎯 Get Prediction", callback_data="get_prediction"))
    return markup

@app.route('/')
def health_check():
    """Simple health check endpoint."""
    return "🤖 Telegram Prediction Bot is Running", 200

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    """Handle start command."""
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
        print(f"Error in welcome: {e}")
        bot.reply_to(message, "⚠️ Service temporary unavailable")

@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction(call):
    """Handle prediction requests."""
    try:
        user_id = call.message.chat.id
        current_time = format_time(get_indian_time())
        
        if not is_member(user_id):
            bot.answer_callback_query(call.id, "Join channel first!", show_alert=True)
            return

        # Cooldown check
        if user_id in cooldowns and (remaining := cooldowns[user_id] - time.time()) > 0:
            bot.answer_callback_query(call.id, f"Wait {int(remaining)}s", show_alert=True)
            return

        # Generate prediction
        future_time, pred, safe = generate_prediction()
        bot.send_message(
            user_id,
            f"📊 *Prediction*\n\n"
            f"⏳ Time: {future_time}\n"
            f"📈 Cofficient: {round(pred + 0.10, 2)}x\n"
            f"🛡 Safe: {safe}x",
            parse_mode="Markdown"
        )
        cooldowns[user_id] = time.time() + COOLDOWN_SECONDS
        bot.answer_callback_query(call.id, "✅ Done!")
        
    except Exception as e:
        print(f"Prediction error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Try again later")

def run_bot():
    """Run the Telegram bot."""
    print("🚀 Bot running in IST timezone...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot crashed: {e}")

if __name__ == '__main__':
    # Start bot in a separate thread
    from threading import Thread
    Thread(target=run_bot).start()
    
    # Run Flask app on port 10000
    app.run(host='0.0.0.0', port=10000)
