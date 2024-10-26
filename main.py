import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot token and group/channel IDs
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Admin group and channel IDs
ADMIN_GROUP_ID = -1002262363425  # Admin group for verification
CHANNEL_ID = -1002442298921  # Public channel for donation announcements
PRIVATE_CHANNEL_ID = -1002483781048  # Private channel for tracking total donations

# Donation goal
goal = 100000  # Set your donation goal

# Helper function to get the last total donation amount from the private channel
def get_total_donated():
    try:
        # Fetch the last message in the private channel
        messages = bot.get_chat_history(PRIVATE_CHANNEL_ID, limit=1)
        last_message = messages[0].text if messages else "0"
        # Ensure only numbers are parsed as total donations
        return int(last_message) if last_message.isdigit() else 0
    except Exception as e:
        print(f"Error fetching total donations: {e}")
        return 0

# Update the total donations message in the private channel
def update_total_donated(new_total):
    try:
        # Send the updated total to the private channel
        message = bot.send_message(PRIVATE_CHANNEL_ID, str(new_total))
        bot.pin_chat_message(PRIVATE_CHANNEL_ID, message.message_id)
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
        "To donate, use /donate <amount> or /donate_anon <amount> for anonymous donations."
    )
    bot.reply_to(message, welcome_message)

# Handle donation amounts
@bot.message_handler(commands=['donate', 'donate_anon'])
def handle_donation(message):
    try:
        cmd = message.text.split(' ')[0]
        amount = int(message.text.split(' ')[1])
        anonymous = (cmd == '/donate_anon')

        # Store donation with anonymity preference
        donations[message.chat.id] = {'amount': amount, 'anonymous': anonymous}
        
        donor_name = "Anonymous" if anonymous else f"@{message.from_user.username}"
        bot.reply_to(message, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
        
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount> or /donate_anon <amount>.")

# Handle screenshot/photo uploads
@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    donation_info = donations.get(chat_id)

    if donation_info:
        photo_id = message.photo[-1].file_id
        amount = donation_info['amount']
        donor_name = "Anonymous" if donation_info['anonymous'] else f"@{message.from_user.username}"
        
        # Forward the photo to the admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}")
        )

        # Send photo and amount to admin group
        bot.send_photo(
            ADMIN_GROUP_ID, 
            photo_id, 
            caption=f"Donation screenshot from {donor_name}, Amount: {amount}", 
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
    donation_info = donations.get(user_chat_id)

    if donation_info:
        amount = donation_info['amount']
        donor_name = "Anonymous" if donation_info['anonymous'] else bot.get_chat(user_chat_id).username
        if action == 'verify':
            verify_donation(user_chat_id, amount, donor_name, call)
        elif action == 'reject':
            reject_donation(user_chat_id, call)

# Verify donation and update the total in the private channel
def verify_donation(chat_id, amount, donor_name, call):
    # Get the current total from the private channel
    current_total = get_total_donated()
    new_total = current_total + amount
    update_total_donated(new_total)  # Update the private channel message

    # Thank the user and notify the public channel
    bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")
    bot.send_message(CHANNEL_ID, f"🎉 {donor_name} donated {amount}!\nTotal donations so far: {new_total}/{goal}.")

    # Edit the admin message to mark it as verified and remove the buttons
    bot.edit_message_caption(
        caption=f"Donation from {donor_name}, Amount: {amount} (✅ Verified)", 
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id
    )

# Reject the donation and notify the user
def reject_donation(chat_id, call):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")
    # Edit the admin message to mark it as rejected and remove the buttons
    bot.edit_message_caption(
        caption="Donation rejected ❌", 
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id
    )

if __name__ == '__main__':
    bot.polling()
