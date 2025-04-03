import os
import telebot
import random
import time
import threading
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import pytz
from datetime import datetime

# Configuration from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'testsub01')
PORT = int(os.environ.get('PORT', 10000))
COOLDOWN_SECONDS = 120
PREDICTION_DELAY = 130

# Timezone setup for India
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("Missing required environment variable: BOT_TOKEN")

# Initialize bot and Flask app
bot = telebot.TeleBot(BOT_TOKEN)
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
    """Check if user is a member of the channel with proper error handling."""
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException as e:
        if e.result_json.get('description') == 'Bad Request: user not found':
            return False
        print(f"Error checking membership: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking membership: {e}")
        return False

def generate_prediction():
    """Generate prediction values with improved randomization and Indian time."""
    prediction_multiplier = round(random.uniform(1.30, 2.40), 2)
    safe_multiplier = round(random.uniform(1.30, min(prediction_multiplier, 2.0)), 2)
    
    # Calculate future time in Indian timezone
    future_time = get_indian_time() + timedelta(seconds=PREDICTION_DELAY)
    future_time_str = format_time(future_time)
    
    return future_time_str, prediction_multiplier, safe_multiplier

def get_prediction_button():
    """Create inline keyboard with prediction button."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎯 Get Prediction", callback_data="get_prediction"))
    return markup

@app.route('/')
def health_check():
    """Simple health check endpoint for Render."""
    return "Telegram prediction bot is running", 200

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    """Handle start command with improved message formatting."""
    user_id = message.chat.id
    join_url = f"https://t.me/{CHANNEL_USERNAME}"
    current_time = format_time(get_indian_time())
    
    if is_member(user_id):
        bot.send_message(
            user_id,
            f"✅ *Welcome to Prediction Bot!*\n\n"
            f"🕒 Current Time (IST): `{current_time}`\n\n"
            "You are subscribed to our channel.\n"
            "Click the button below to get your prediction.",
            reply_markup=get_prediction_button(),
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            user_id,
            "❌ *Subscription Required*\n\n"
            f"🕒 Current Time (IST): `{current_time}`\n\n"
            f"Please [join our channel]({join_url}) to use this bot.\n"
            "After joining, send /start again.",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction_request(call):
    """Handle prediction requests with cooldown management."""
    user_id = call.message.chat.id
    current_time = format_time(get_indian_time())
    
    try:
        # Verify membership
        if not is_member(user_id):
            bot.answer_callback_query(call.id, "You need to join our channel first!")
            return

        # Check cooldown
        current_timestamp = time.time()
        if user_id in cooldowns and current_timestamp < cooldowns[user_id]:
            remaining = int(cooldowns[user_id] - current_timestamp)
            bot.answer_callback_query(
                call.id,
                f"Please wait {remaining} seconds before next prediction",
                show_alert=True
            )
            return

        # Generate and send prediction
        future_time, pred_mult, safe_mult = generate_prediction()
        
        bot.send_message(
            user_id,
            f"📊 *Prediction Results*\n\n"
            f"🕒 Current Time (IST): `{current_time}`\n"
            f"⏳ Prediction Time (IST): `{future_time}`\n"
            f"📈 Multiplier: `{round(pred_mult + 0.10, 2)}x`\n"
            f"🛡 Safe Bet: `{safe_mult}x`\n\n"
            f"⏳ Next prediction available in {COOLDOWN_SECONDS} seconds",
            parse_mode="Markdown"
        )

        # Set cooldown
        cooldowns[user_id] = current_timestamp + COOLDOWN_SECONDS
        bot.answer_callback_query(call.id, "Prediction generated!")

    except Exception as e:
        print(f"Error handling prediction request: {e}")
        bot.answer_callback_query(call.id, "❌ Error generating prediction. Please try again.")

def run_flask():
    """Run Flask web server for Render compatibility."""
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    # Start Flask in a separate thread for Render compatibility
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Bot is running with Indian timezone...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot stopped due to error: {e}")
