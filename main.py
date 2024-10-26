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
total_donated = 0
goal = 100000  # Set your donation goal

# Group and channel IDs
ADMIN_GROUP_ID = -1002262363425  # Admin group ID
CHANNEL_ID = -1002442298921  # Public channel ID
PRIVATE_CHANNEL_ID = -1002483781048  # Private channel for tracking total donations

def update_total_from_private_channel():
    """Fetch the last message in the private channel for the total donations."""
    global total_donated
    try:
        messages = bot.get_chat_history(PRIVATE_CHANNEL_ID, limit=1)
        if messages and messages[0].text.isdigit():
            total_donated = int(messages[0].text)
            print(f"Updated total donations from private channel: {total_donated}")
    except Exception as e:
        print(f"Error updating total donations: {e}")

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
@bot.message_handler(commands=['donate', 'donate_anon'])
def handle_donation(message):
    try:
        amount = int(message.text.split(' ')[1])
        anonymous = message.text.startswith('/donate_anon')
        username = message.from_user.username if not anonymous else "Anonymous"
        donations[message.chat.id] = {'amount': amount, 'anonymous': anonymous}

        bot.reply_to(
            message,
            f"Thank you for your donation of {amount}! {'You chose to donate anonymously.' if anonymous else ''} "
            "Please send a screenshot for verification."
        )
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount> or /donate_anon <amount>.")

# Handle screenshot/photo uploads
@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    if chat_id in donations:
        photo_id = message.photo[-1].file_id
        donation_info = donations[chat_id]
        amount = donation_info['amount']
        anonymous = donation_info['anonymous']
        username = "Anonymous" if anonymous else f"@{message.from_user.username}"

        # Forward the photo to the admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}")
        )

        sent_msg = bot.send_photo(
            ADMIN_GROUP_ID,
            photo_id,
            caption=f"Donation screenshot from {username}\nAmount: {amount}",
            reply_markup=markup
        )
        donations[chat_id]['admin_message_id'] = sent_msg.message_id
        bot.reply_to(message, "Your screenshot has been received. Please wait for admin verification.")
    else:
        bot.reply_to(message, "Please donate first before sending a screenshot.")

# Handle admin verification actions (verify/reject)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('verify_', 'reject_')))
def handle_verification(call):
    action, user_chat_id = call.data.split('_')
    user_chat_id = int(user_chat_id)

    if action == 'verify':
        verify_donation(user_chat_id, call.message.message_id)
        bot.answer_callback_query(call.id, "Donation verified!")
    elif action == 'reject':
        reject_donation(user_chat_id)
        bot.answer_callback_query(call.id, "Donation rejected.")

# Function to verify the donation
def verify_donation(chat_id, admin_message_id):
    global total_donated
    donation_info = donations.get(chat_id)
    if donation_info:
        amount = donation_info['amount']
        anonymous = donation_info['anonymous']
        username = "Anonymous" if anonymous else f"@{bot.get_chat(chat_id).username}"
        
        # Update total donations and pin the updated total in the private channel
        total_donated += amount
        bot.send_message(
            PRIVATE_CHANNEL_ID,
            f"{total_donated}",  # Update the private channel with the new total amount
            disable_notification=True
        )

        # Thank the user for their donation
        bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")

        # Post an update to the public channel
        bot.send_message(
            CHANNEL_ID,
            f"🎉 {username} donated {amount}!\n"
            f"Total donations so far: {total_donated}/{goal}."
        )

        # Edit the message in the admin group to mark as verified
        bot.edit_message_caption(
            chat_id=ADMIN_GROUP_ID,
            message_id=admin_message_id,
            caption=f"Donation screenshot from {username} (✅ Verified)\nAmount: {amount}"
        )

# Function to reject the donation
def reject_donation(chat_id):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")

# Start the bot polling
if __name__ == '__main__':
    update_total_from_private_channel()  # Initial load of total donations
    bot.polling()
