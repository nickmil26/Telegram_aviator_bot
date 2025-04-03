import telebot
import random
import time
import threading
from datetime import datetime, timedelta
import pytz

# Replace with your bot token
BOT_TOKEN = "7870128724:AAF0zniFAw9RSuqFSofv5GEPk-5GEtRlRhw"
CHANNEL_USERNAME = "testsub01"

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Store cooldown timers
cooldowns = {}

# Function to check if a user is a member of the channel
def is_member(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        return False  # Assume not a member if an error occurs

# Function to generate a prediction with IST time
def generate_prediction():
    prediction_multiplier = round(random.uniform(1.30, 2.40), 2)
    safe_multiplier = round(random.uniform(1.30, prediction_multiplier), 2)
    
    # Get current time in IST
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist)
    
    # Calculate future prediction time (current time + 130 seconds)
    future_time = current_time + timedelta(seconds=130)
    
    # Format time as HH:MM:SS AM/PM
    formatted_time = future_time.strftime("%I:%M:%S %p")
    
    return formatted_time, prediction_multiplier, safe_multiplier

# Start Command
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id

    if is_member(user_id):
        bot.send_message(
            user_id,
            "✅ Welcome! You are a member of our channel.\nClick the button below to get a prediction.",
            reply_markup=get_prediction_button()
        )
    else:
        bot.send_message(
            user_id,
            f"❌ You must join our channel first!\nJoin here: [Join Channel](https://t.me/{CHANNEL_USERNAME})",
            parse_mode="Markdown"
        )

# Function to create "Get Prediction" button
def get_prediction_button():
    markup = telebot.types.InlineKeyboardMarkup()
    button = telebot.types.InlineKeyboardButton("🎯 Get Prediction", callback_data="get_prediction")
    markup.add(button)
    return markup

# Handle button clicks
@bot.callback_query_handler(func=lambda call: call.data == "get_prediction")
def handle_prediction_request(call):
    user_id = call.message.chat.id

    if not is_member(user_id):
        bot.send_message(
            user_id,
            f"❌ You must join our channel first!\nJoin here: [Join Channel](https://t.me/{CHANNEL_USERNAME})",
            parse_mode="Markdown"
        )
        return

    # Check cooldown
    if user_id in cooldowns and time.time() < cooldowns[user_id]:
        remaining_time = int(cooldowns[user_id] - time.time())
        bot.send_message(user_id, f"⏳ Please wait {remaining_time} seconds before requesting another prediction.")
        return

    # Generate prediction
    future_time, prediction_multiplier, safe_multiplier = generate_prediction()

    # Send prediction message
    bot.send_message(
        user_id,
        f"📊 *Prediction*\n"
        f"🕒 *Time (IST):* {future_time}\n"
        f"📈 *Coefficient:* {round(prediction_multiplier + 0.10, 2)}\n"
        f"🛡 *Safe:* {safe_multiplier}",
        parse_mode="Markdown"
    )

    # Set cooldown for 2 minutes (120 seconds)
    cooldowns[user_id] = time.time() + 120

# Start the bot
bot.polling(none_stop=True)
