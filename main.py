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
ADMIN_GROUP_ID = -1002262363425  # Make sure this is the correct group ID
CHANNEL_ID = -1002442298921  # Ensure this is your public channel ID

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "Hello! I'm your donation bot. Thank you for your interest in donating! "
        "Here are the methods you can use to donate:\n"
        "1. Bank transfer: [Bank details]\n"
        "2. Telebirr: [Telebirr details]\n"
        "3. CBE: [CBE details]\n\n"
        "After donating, please send a screenshot for verification.\n\n"
        "If you want to donate anonymously, use /donate <amount> anonymous."
    )
    bot.reply_to(message, welcome_message)

# Handle donation amounts
@bot.message_handler(commands=['donate'])
def handle_donation(message):
    try:
        parts = message.text.split(' ')
        if len(parts) == 2 and parts[1].lower() == "anonymous":
            amount = int(parts[0])
            donations[message.chat.id] = (amount, True)  # True for anonymous
            bot.reply_to(message, "Thank you for your anonymous donation of {amount}!")
        else:
            amount = int(parts[1])
            donations[message.chat.id] = (amount, False)  # False for not anonymous
            bot.reply_to(message, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount> or /donate <amount> anonymous.")

# Handle screenshot/photo uploads
@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    username = message.from_user.username

    if chat_id in donations:
        amount, is_anonymous = donations[chat_id]
        photo_id = message.photo[-1].file_id
        
        # Forward the photo to the admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
                   InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}"))

        donation_user = "Anonymous" if is_anonymous else f"@{username}"
        bot.send_message(ADMIN_GROUP_ID, f"New donation verification from {donation_user}.\nAmount: {amount}")
        sent_photo_message = bot.send_photo(ADMIN_GROUP_ID, photo_id, caption=f"Donation screenshot from {donation_user}",
                                             reply_markup=markup)
        
        # Store message ID for editing later
        donations[chat_id] = (amount, is_anonymous, sent_photo_message.message_id)
        
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
    global total_donated
    amount, is_anonymous, message_id = donations.get(chat_id, (0, False, None))
    total_donated += amount
    
    # Thank the user for their donation
    bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")
    
    # Post an update to the public channel
    donor_message = "An anonymous donor" if is_anonymous else f"@{bot.get_chat(chat_id).username}"
    bot.send_message(CHANNEL_ID, f"🎉 {donor_message} donated {amount}!\n"
                                 f"Total donations so far: {total_donated}/{goal}.")

    # Edit the verification message to indicate it has been verified
    bot.edit_message_caption(
        chat_id=ADMIN_GROUP_ID,
        message_id=message_id,
        caption=f"Donation screenshot from {donor_message} - Verified! Amount: {amount}"
    )

# Function to reject the donation
def reject_donation(chat_id):
    amount, is_anonymous, message_id = donations.get(chat_id, (0, False, None))
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")
    
    # Edit the verification message to indicate it has been rejected
    donor_message = "Anonymous" if is_anonymous else f"@{bot.get_chat(chat_id).username}"
    bot.edit_message_caption(
        chat_id=ADMIN_GROUP_ID,
        message_id=message_id,
        caption=f"Donation screenshot from {donor_message} - Rejected! Amount: {amount}"
    )

# Command for admins to update total donations
@bot.message_handler(commands=['updateAmount'], chat_id=ADMIN_GROUP_ID)
def update_amount(message):
    try:
        new_amount = int(message.text.split(' ')[1])
        global total_donated
        total_donated = new_amount  # Update the total donated amount
        bot.reply_to(message, f"Total donations updated to {total_donated}.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /updateAmount <new_total>.")

# Start the bot polling
if __name__ == '__main__':
    bot.polling()
