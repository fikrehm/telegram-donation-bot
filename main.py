import os
import re
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

# Admin group ID and public/private channel IDs
ADMIN_GROUP_ID = -1002262363425  # Make sure this is the correct group ID
CHANNEL_ID = -1002442298921  # Ensure this is your public channel ID
PRIVATE_CHANNEL_ID = -1002483781048  # Private channel for total updates

# Fetch the latest total donation amount from the private channel
def fetch_total_donated():
    updates = bot.get_chat_history(PRIVATE_CHANNEL_ID, limit=1)
    last_message = updates[0].text if updates else "Total Donations: 0"
    match = re.search(r'Total Donations: (\d+)', last_message)
    return int(match.group(1)) if match else 0

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "Hello! I'm your donation bot. Thank you for your interest in donating! "
        "Here are the methods you can use to donate:\n"
        "1. Bank transfer: [Bank details]\n"
        "2. Telebirr: [Telebirr details]\n"
        "3. CBE: [CBE details]\n\n"
        "After donating, please send a screenshot for verification."
    )
    bot.reply_to(message, welcome_message)

# Handle donation amounts
@bot.message_handler(commands=['donate'])
def handle_donation(message):
    try:
        amount = int(message.text.split(' ')[1])
        donations[message.chat.id] = amount
        bot.reply_to(message, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount>.")

# Handle screenshot/photo uploads
@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    username = message.from_user.username

    if chat_id in donations:
        photo_id = message.photo[-1].file_id
        
        # Forward the photo to the admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
                   InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}"))

        bot.send_message(ADMIN_GROUP_ID, f"New donation verification from @{username}.\nAmount: {donations[chat_id]}")
        bot.send_photo(ADMIN_GROUP_ID, photo_id, caption=f"Donation screenshot from @{username}",
                       reply_markup=markup)
        
        bot.reply_to(message, "Your screenshot has been received. Please wait for admin verification.")
    else:
        bot.reply_to(message, "Please donate first before sending a screenshot.")

# Handle admin verification actions (verify/reject)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('verify_', 'reject_')))
def handle_verification(call):
    action, user_chat_id = call.data.split('_')
    user_chat_id = int(user_chat_id)

    if action == 'verify':
        verify_donation(user_chat_id)
        bot.answer_callback_query(call.id, "Donation verified!")
    elif action == 'reject':
        reject_donation(user_chat_id)
        bot.answer_callback_query(call.id, "Donation rejected.")

# Function to verify the donation
def verify_donation(chat_id):
    amount = donations.get(chat_id, 0)
    current_total = fetch_total_donated() + amount

    # Thank the user for their donation
    bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")
    
    # Post an update to the public channel
    bot.send_message(CHANNEL_ID, f"🎉 @{bot.get_chat(chat_id).username} donated {amount}!\n"
                                 f"Total donations so far: {current_total}/{goal}.")

    # Update the private channel with new total
    bot.send_message(PRIVATE_CHANNEL_ID, f"Total Donations: {current_total}")

    # Mark the donation as verified (you could modify this to store verified donations)
    donations.pop(chat_id, None)

# Function to reject the donation
def reject_donation(chat_id):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")

# Start the bot polling
if __name__ == '__main__':
    bot.infinity_polling()
