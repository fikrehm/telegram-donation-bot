import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot token and group/channel IDs
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Donation goal
goal = 100000

# Admin group ID and public channel ID
ADMIN_GROUP_ID = -1002262363425  # Your admin group ID
CHANNEL_ID = -1002442298921      # Your public channel ID

# Keep track of donations
donations = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "Hello! I'm your donation bot. Thank you for your interest in donating! "
        "Here are the methods you can use to donate:\n"
        "1. Bank transfer: [Bank details]\n"
        "2. Telebirr: [Telebirr details]\n"
        "3. CBE: [CBE details]\n\n"
        "After donating, please send a screenshot for verification.\n\n"
        "You can also use:\n"
        "/donate <amount> - to donate with your username\n"
        "/donate_anon <amount> - to donate anonymously"
    )
    bot.reply_to(message, welcome_message)

@bot.message_handler(commands=['donate'])
def handle_donation(message):
    try:
        # Retrieve amount and anonymous preference
        parts = message.text.split(' ')
        amount = int(parts[1])
        anonymous = len(parts) > 2 and parts[2].lower() == 'anonymous'

        # Validate donation amount
        if amount <= 0:
            bot.reply_to(message, "Please enter a positive amount to donate.")
            return

        donations[message.chat.id] = {"amount": amount, "anonymous": anonymous}
        bot.reply_to(message, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount> [anonymous].")

@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    username = message.from_user.username
    donation_info = donations.get(chat_id)

    if donation_info:
        # Forward photo to admin group for verification
        photo_id = message.photo[-1].file_id
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
                   InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}"))

        bot.send_photo(
            ADMIN_GROUP_ID, photo_id,
            caption=f"Donation screenshot from @{username}.\nAmount: {donation_info['amount']}",
            reply_markup=markup
        )
        bot.reply_to(message, "Your screenshot has been received. Please wait for admin verification.")
    else:
        bot.reply_to(message, "Please donate first before sending a screenshot.")

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

def verify_donation(chat_id):
    donation_info = donations.get(chat_id)
    if not donation_info:
        return

    # Retrieve the latest total from the admin group
    total_donated = get_latest_total_donations()

    # Update total donations
    total_donated += donation_info['amount']
    update_total_donations(total_donated)

    # Notify user and update channel
    donor_name = "Anonymous" if donation_info['anonymous'] else f"@{bot.get_chat(chat_id).username}"
    bot.send_message(chat_id, f"Your donation of {donation_info['amount']} has been verified. Thank you for your generosity!")
    bot.send_message(CHANNEL_ID, f"🎉 {donor_name} donated {donation_info['amount']}!\nTotal donations so far: {total_donated}/{goal}.")

    # Mark the message as verified in the admin group
    bot.edit_message_caption(
        chat_id=ADMIN_GROUP_ID, message_id=call.message.message_id,
        caption=f"Donation screenshot from {donor_name}\nAmount: {donation_info['amount']} (Verified ✅)"
    )

def reject_donation(chat_id):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")

def get_latest_total_donations():
    messages = bot.get_chat_history(ADMIN_GROUP_ID, limit=100)
    for msg in reversed(messages):
        if "Total Donations" in msg.text:
            try:
                return int(msg.text.split(":")[1].strip())
            except ValueError:
                return 0
    return 0

def update_total_donations(total_donated):
    bot.send_message(ADMIN_GROUP_ID, f"Total Donations: {total_donated}")

if __name__ == '__main__':
    bot.polling()
