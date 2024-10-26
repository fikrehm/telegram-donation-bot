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

# Admin group ID and public channel ID
ADMIN_GROUP_ID = -1002262363425  # Replace with your admin group ID
CHANNEL_ID = -1002442298921  # Replace with your public channel ID

# Restrict access to certain commands
def is_admin(chat_id):
    # Check if user is an admin in the admin group
    member_status = bot.get_chat_member(ADMIN_GROUP_ID, chat_id).status
    return member_status in ['administrator', 'creator']

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "Hello! I'm your donation bot. Thank you for your interest in donating! "
        "Here are the methods you can use to donate:\n"
        "1. Bank transfer: [Bank details]\n"
        "2. Telebirr: [Telebirr details]\n"
        "3. CBE: [CBE details]\n\n"
        "After donating, please send a screenshot for verification.\n\n"
        "Use /help to view available commands."
    )
    bot.reply_to(message, welcome_message)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_message = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/donate <amount> - Register a donation\n"
        "/updateAmount <new_amount> - (Admin only) Update the total donation amount\n"
        "/help - List of commands"
    )
    bot.reply_to(message, help_message)

# Handle donation amounts with option for anonymous donation
@bot.message_handler(commands=['donate'])
def handle_donation(message):
    try:
        args = message.text.split(' ')
        amount = int(args[1])
        anonymous = len(args) > 2 and args[2].lower() == 'anonymous'
        
        donations[message.chat.id] = {'amount': amount, 'anonymous': anonymous}
        confirmation_msg = (
            f"Thank you for your donation of {amount}! Please send a screenshot for verification."
            if not anonymous else
            "Thank you for your anonymous donation! Please send a screenshot for verification."
        )
        bot.reply_to(message, confirmation_msg)
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount> [anonymous].")

# Update total donated amount (Admin only)
@bot.message_handler(commands=['updateAmount'])
def update_amount(message):
    if is_admin(message.from_user.id):
        try:
            global total_donated
            new_amount = int(message.text.split(' ')[1])
            total_donated = new_amount
            bot.reply_to(message, f"Total donation amount updated to {total_donated}.")
        except (IndexError, ValueError):
            bot.reply_to(message, "Please provide a valid amount. Usage: /updateAmount <new_amount>")
    else:
        bot.reply_to(message, "You do not have permission to use this command.")

# Handle screenshot/photo uploads for verification
@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    user_info = donations.get(chat_id)

    if user_info:
        photo_id = message.photo[-1].file_id
        amount = user_info['amount']
        anonymous = user_info['anonymous']
        
        # Forward the photo to the admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}")
        )

        donor_text = "Anonymous donor" if anonymous else f"@{message.from_user.username}"
        bot.send_message(
            ADMIN_GROUP_ID, f"New donation verification from {donor_text}.\nAmount: {amount}"
        )
        bot.send_photo(
            ADMIN_GROUP_ID, photo_id,
            caption=f"Donation screenshot from {donor_text}",
            reply_markup=markup
        )
        
        bot.reply_to(message, "Your screenshot has been received. Please wait for admin verification.")
    else:
        bot.reply_to(message, "Please donate first before sending a screenshot.")

# Handle admin verification actions (verify/reject)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('verify_', 'reject_')))
def handle_verification(call):
    action, user_chat_id = call.data.split('_')
    user_chat_id = int(user_chat_id)

    if action == 'verify':
        verify_donation(user_chat_id, call)
    elif action == 'reject':
        reject_donation(user_chat_id, call)

# Function to verify the donation
def verify_donation(chat_id, call):
    global total_donated
    amount = donations.get(chat_id, {}).get('amount', 0)
    total_donated += amount
    
    # Thank the user for their donation
    bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")
    
    # Post an update to the public channel
    donor_text = "Anonymous donor" if donations[chat_id]['anonymous'] else f"@{bot.get_chat(chat_id).username}"
    bot.send_message(
        CHANNEL_ID, f"🎉 {donor_text} donated {amount}!\nTotal donations so far: {total_donated}/{goal}."
    )
    
    # Edit message in the admin group to indicate it's verified
    bot.edit_message_caption(
        caption="Verified ✅",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id, "Donation verified!")

# Function to reject the donation
def reject_donation(chat_id, call):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")
    bot.edit_message_caption(
        caption="Rejected ❌",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id, "Donation rejected.")

# Catch-all handler for non-command messages
@bot.message_handler(func=lambda message: True)
def handle_non_command(message):
    reply = (
        "I'm here to assist with donations!\n"
        "Please use one of the following commands:\n\n"
        "/start - Start the bot and learn more\n"
        "/donate <amount> - Register a donation\n"
        "/help - List all available commands"
    )
    bot.reply_to(message, reply)

# Start the bot polling
if __name__ == '__main__':
    bot.polling()
