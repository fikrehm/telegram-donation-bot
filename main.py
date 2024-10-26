import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

donations = {}
goal = 100000  # Set your donation goal

ADMIN_GROUP_ID = -1002262363425  # Private group for admins
CHANNEL_ID = -1002442298921  # Public channel to announce donations

# Function to fetch the current total from the pinned message
def get_pinned_total():
    try:
        chat = bot.get_chat(ADMIN_GROUP_ID)
        pinned_message = chat.pinned_message
        if pinned_message and pinned_message.text.startswith("Total Donations:"):
            return int(pinned_message.text.split(':')[1].strip())
        else:
            # If no valid pinned message, create one with 0
            msg = bot.send_message(ADMIN_GROUP_ID, "Total Donations: 0")
            bot.pin_chat_message(ADMIN_GROUP_ID, msg.message_id)
            return 0
    except Exception as e:
        print(f"Error fetching pinned message: {e}")
        return 0

# Function to update the pinned message with the new total
def update_pinned_total(new_total):
    try:
        chat = bot.get_chat(ADMIN_GROUP_ID)
        pinned_message = chat.pinned_message
        if pinned_message:
            bot.edit_message_text(
                chat_id=ADMIN_GROUP_ID,
                message_id=pinned_message.message_id,
                text=f"Total Donations: {new_total}/{goal}"
            )
        else:
            # Create and pin a new message if no pinned message exists
            msg = bot.send_message(ADMIN_GROUP_ID, f"Total Donations: {new_total}/{goal}")
            bot.pin_chat_message(ADMIN_GROUP_ID, msg.message_id)
    except Exception as e:
        print(f"Error updating pinned message: {e}")

# Function to validate donation amount
def validate_amount(amount_text):
    try:
        amount = int(amount_text)
        return amount if amount > 0 else None
    except ValueError:
        return None

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

@bot.message_handler(commands=['donate', 'donate_anon'])
def handle_donation(message):
    try:
        cmd = message.text.split(' ')[0]
        amount = validate_amount(message.text.split(' ')[1])
        
        if not amount:
            bot.reply_to(message, "Please enter a valid positive amount.")
            return

        anonymous = (cmd == '/donate_anon')
        username = message.from_user.username if not anonymous else "Anonymous"
        donations[message.chat.id] = {'amount': amount, 'anonymous': anonymous}

        bot.reply_to(message, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount> or /donate_anon <amount>.")

@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    if chat_id in donations:
        photo_id = message.photo[-1].file_id
        donation_info = donations[chat_id]
        amount = donation_info['amount']
        username = message.from_user.username if not donation_info['anonymous'] else "Anonymous"
        
        # Forward the photo to the admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
                   InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}"))

        bot.send_photo(
            ADMIN_GROUP_ID, photo_id, 
            caption=f"New donation verification from {username}.\nAmount: {amount}",
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
        verify_donation(user_chat_id, call.message)
        bot.answer_callback_query(call.id, "Donation verified!")
    elif action == 'reject':
        reject_donation(user_chat_id)
        bot.answer_callback_query(call.id, "Donation rejected.")

def verify_donation(chat_id, admin_message):
    amount = donations.get(chat_id, {}).get('amount', 0)
    if amount:
        # Update total donation amount from the pinned message
        total_donated = get_pinned_total() + amount
        update_pinned_total(total_donated)

        # Notify the user
        bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")
        
        # Post update to the public channel
        username = bot.get_chat(chat_id).username or "Anonymous"
        bot.send_message(CHANNEL_ID, f"🎉 @{username} donated {amount}!\nTotal donations so far: {total_donated}/{goal}.")
        
        # Edit the admin message to mark as verified and remove buttons
        bot.edit_message_caption(
            caption=f"Donation from @{username} - Amount: {amount} (✅ Verified)",
            chat_id=admin_message.chat.id,
            message_id=admin_message.message_id
        )

def reject_donation(chat_id):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")

if __name__ == '__main__':
    bot.polling()
