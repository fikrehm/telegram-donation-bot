import os
import telebot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

donations = {}
total_donated = 0
goal = 100000  # Set your donation goal

ADMIN_GROUP_ID = -1002262363425  # Admin group ID
CHANNEL_ID = -1002442298921  # Public channel ID
PRIVATE_CHANNEL_ID = -1002483781048  # Private channel ID for tracking donations

def get_pinned_message():
    """Fetch the pinned message from the private channel."""
    try:
        pinned_messages = bot.get_chat(PRIVATE_CHANNEL_ID).pinned_message
        if pinned_messages:
            return pinned_messages.text
        else:
            return None
    except Exception as e:
        print(f"Error fetching pinned message: {e}")
        return None

def update_pinned_message(new_total):
    """Update the pinned message with the new total donations."""
    try:
        pinned_message = get_pinned_message()
        if pinned_message:
            bot.edit_message_text(
                chat_id=PRIVATE_CHANNEL_ID,
                message_id=pinned_message.message_id,
                text=f"Total Donations: {new_total}/{goal}"
            )
        else:
            # If no pinned message, create one
            message = bot.send_message(
                PRIVATE_CHANNEL_ID, f"Total Donations: {new_total}/{goal}"
            )
            bot.pin_chat_message(PRIVATE_CHANNEL_ID, message.message_id)
    except Exception as e:
        print(f"Error updating pinned message: {e}")

def validate_amount(amount):
    """Check if the amount is a valid positive number."""
    try:
        amount = int(amount)
        if amount > 0:
            return amount
        else:
            return None
    except ValueError:
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "Hello! I'm your donation bot. You can use the following commands:\n"
        "/donate <amount> - Donate a specified amount\n"
        "/donate_anon <amount> - Donate anonymously\n"
        "After donating, send a screenshot for verification."
    )
    bot.reply_to(message, welcome_message)

@bot.message_handler(commands=['donate', 'donate_anon'])
def handle_donation(message):
    try:
        cmd = message.text.split(' ')[0]
        amount = validate_amount(message.text.split(' ')[1])
        
        if not amount:
            bot.reply_to(message, "Please enter a valid amount.")
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
        username = "Anonymous" if donation_info['anonymous'] else message.from_user.username
        
        # Send photo and verification buttons to the admin group
        markup = telebot.types.InlineKeyboardMarkup()
        verify_button = telebot.types.InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}")
        reject_button = telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}")
        markup.add(verify_button, reject_button)
        
        bot.send_photo(ADMIN_GROUP_ID, photo_id, caption=f"Donation from {username}: {amount}", reply_markup=markup)
        bot.reply_to(message, "Your screenshot has been received. Please wait for admin verification.")
    else:
        bot.reply_to(message, "Please donate first before sending a screenshot.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_') or call.data.startswith('reject_'))
def handle_verification(call):
    action, chat_id = call.data.split('_')
    chat_id = int(chat_id)

    if action == "verify":
        donation_info = donations.get(chat_id)
        if donation_info:
            amount = donation_info['amount']
            username = "Anonymous" if donation_info['anonymous'] else bot.get_chat(chat_id).username
            
            # Update total donations
            global total_donated
            total_donated += amount
            update_pinned_message(total_donated)
            
            # Notify user
            bot.send_message(chat_id, f"Thank you! Your donation of {amount} has been verified.")
            
            # Edit the admin message to remove buttons and mark as verified
            bot.edit_message_caption(
                caption=f"Donation from {username}: {amount} (✅ Verified)",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
    elif action == "reject":
        bot.send_message(chat_id, "Your donation verification was rejected.")
    
    # Remove buttons
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None
    )

if __name__ == '__main__':
    bot.polling()
