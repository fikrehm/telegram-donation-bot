import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot token and group/channel IDs
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Donation tracking
donations = {}
goal = 100000  # Set your donation goal

# Admin group ID, public channel ID, and private total tracking channel ID
ADMIN_GROUP_ID = -1002262363425
CHANNEL_ID = -1002442298921
PRIVATE_CHANNEL_ID = -1002483781048  # Channel to read total donations

# Function to fetch the latest total donations from the private channel
def fetch_total_donated():
    updates = bot.get_updates(limit=100)
    for update in reversed(updates):
        if update.message and update.message.chat.id == PRIVATE_CHANNEL_ID:
            text = update.message.text
            if text.isdigit():
                return int(text)
    return 0

# Command for /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "Hello! I'm your donation bot. Thank you for your interest in donating!\n"
        "Here are the methods you can use to donate:\n"
        "1. Bank transfer: [Bank details]\n"
        "2. Telebirr: [Telebirr details]\n"
        "3. CBE: [CBE details]\n\n"
        "After donating, please send a screenshot for verification."
    )
    bot.reply_to(message, welcome_message)

# Handle donation amounts, including anonymous donations
@bot.message_handler(commands=['donate'])
def handle_donation(message):
    try:
        parts = message.text.split(' ')
        amount = int(parts[1])
        anonymous = len(parts) > 2 and parts[2].lower() == "anonymous"
        donations[message.chat.id] = {"amount": amount, "anonymous": anonymous}
        
        response = f"Thank you for your donation of {amount}! {'You have chosen to donate anonymously.' if anonymous else 'Please send a screenshot for verification.'}"
        bot.reply_to(message, response)
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount> [anonymous].")

# Handle screenshot/photo uploads for verification
@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    user_donation = donations.get(chat_id)

    if user_donation:
        photo_id = message.photo[-1].file_id
        username = message.from_user.username or "Anonymous" if user_donation["anonymous"] else f"@{message.from_user.username}"
        amount = user_donation["amount"]

        # Forward photo to admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
                   InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}"))

        bot.send_photo(ADMIN_GROUP_ID, photo_id, caption=f"Donation of {amount} from {username}",
                       reply_markup=markup)
        bot.reply_to(message, "Your screenshot has been received. Please wait for admin verification.")
    else:
        bot.reply_to(message, "Please donate first before sending a screenshot.")

# Handle admin verification actions (verify/reject)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('verify_', 'reject_')))
def handle_verification(call):
    action, user_chat_id = call.data.split('_')
    user_chat_id = int(user_chat_id)
    markup = InlineKeyboardMarkup()

    if action == 'verify':
        verify_donation(user_chat_id)
        bot.answer_callback_query(call.id, "Donation verified!")
        markup.add(InlineKeyboardButton("✅ Verified", callback_data="none"))
    elif action == 'reject':
        reject_donation(user_chat_id)
        bot.answer_callback_query(call.id, "Donation rejected.")
        markup.add(InlineKeyboardButton("❌ Rejected", callback_data="none"))

    # Edit the message in the admin group with the verification status
    bot.edit_message_reply_markup(ADMIN_GROUP_ID, call.message.message_id, reply_markup=markup)

# Function to verify the donation
def verify_donation(chat_id):
    amount = donations.get(chat_id, {}).get("amount", 0)
    username = donations[chat_id]["anonymous"] and "Anonymous" or f"@{bot.get_chat(chat_id).username}"
    current_total = fetch_total_donated() + amount

    # Update the total in the private channel
    bot.send_message(PRIVATE_CHANNEL_ID, f"{current_total}")

    # Thank the user for their donation
    bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")

    # Post an update to the public channel
    bot.send_message(CHANNEL_ID, f"🎉 {username} donated {amount}!\nTotal donations so far: {current_total}/{goal}.")

# Function to reject the donation
def reject_donation(chat_id):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")

# Start the bot polling
if __name__ == '__main__':
    bot.infinity_polling()
