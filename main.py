import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot token and group/channel IDs
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

donations = {}
goal = 100000  # Set your donation goal

# Admin group ID, public channel ID, and private channel ID for total donations
ADMIN_GROUP_ID = -1002262363425
CHANNEL_ID = -1002442298921
PRIVATE_CHANNEL_ID = -1002483781048  # Channel where the total donations are tracked

def get_latest_total():
    """Fetch the latest total donation amount from the last message in the private channel."""
    try:
        messages = bot.get_chat_history(PRIVATE_CHANNEL_ID, limit=1)
        if messages and messages[0].text.isdigit():
            return int(messages[0].text)
    except Exception as e:
        print(f"Error fetching total donations: {e}")
    return 0

def update_total_message(new_total):
    """Update the last message in the private channel with the new total."""
    try:
        messages = bot.get_chat_history(PRIVATE_CHANNEL_ID, limit=1)
        if messages:
            bot.edit_message_text(
                chat_id=PRIVATE_CHANNEL_ID,
                message_id=messages[0].message_id,
                text=str(new_total)
            )
        else:
            # If no message exists, send and pin a new one
            message = bot.send_message(PRIVATE_CHANNEL_ID, str(new_total))
            bot.pin_chat_message(PRIVATE_CHANNEL_ID, message.message_id)
    except Exception as e:
        print(f"Error updating total donations: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "Hello! I'm your donation bot. Here are the methods you can use to donate:\n"
        "1. Bank transfer: [Bank details]\n"
        "2. Telebirr: [Telebirr details]\n"
        "3. CBE: [CBE details]\n\n"
        "After donating, please send a screenshot for verification.\n"
        "Commands:\n"
        "/donate <amount> - Donate with your username\n"
        "/donate_anon <amount> - Donate anonymously"
    )
    bot.reply_to(message, welcome_message)

# Handle donation amounts
@bot.message_handler(commands=['donate', 'donate_anon'])
def handle_donation(message):
    try:
        cmd = message.text.split(' ')[0]
        amount = int(message.text.split(' ')[1])
        
        if amount <= 0:
            raise ValueError("Invalid amount")

        anonymous = (cmd == '/donate_anon')
        username = "Anonymous" if anonymous else message.from_user.username
        donations[message.chat.id] = {'amount': amount, 'anonymous': anonymous}

        bot.reply_to(message, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format or amount. Please use /donate <amount> or /donate_anon <amount>.")

@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    username = message.from_user.username if not donations[chat_id].get("anonymous") else "Anonymous"
    
    if chat_id in donations:
        photo_id = message.photo[-1].file_id
        amount = donations[chat_id]['amount']
        
        # Forward the photo to the admin group with verification buttons
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Verify", callback_data=f"verify_{chat_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}")
        )

        bot.send_photo(
            ADMIN_GROUP_ID, 
            photo_id, 
            caption=f"Donation screenshot from @{username}\nAmount: {amount}",
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
        verify_donation(user_chat_id, call)
        bot.answer_callback_query(call.id, "Donation verified!")
    elif action == 'reject':
        reject_donation(user_chat_id, call)
        bot.answer_callback_query(call.id, "Donation rejected.")

def verify_donation(chat_id, call):
    global total_donated
    amount = donations.get(chat_id, {}).get("amount", 0)
    latest_total = get_latest_total()  # Fetch the current total
    
    # Update the total donations and post to public channel
    new_total = latest_total + amount
    update_total_message(new_total)

    # Thank the user for their donation
    bot.send_message(chat_id, f"Your donation of {amount} has been verified. Thank you for your generosity!")
    
    # Edit the message in the admin group to show it's verified
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption=f"Donation from @{bot.get_chat(chat_id).username or 'Anonymous'}: {amount} (✅ Verified)"
    )

    # Post an update to the public channel
    bot.send_message(CHANNEL_ID, f"🎉 Donation received: {amount}!\n"
                                 f"Total donations so far: {new_total}/{goal}.")

def reject_donation(chat_id, call):
    bot.send_message(chat_id, "Sorry, your donation could not be verified by the admins.")
    
    # Edit the message in the admin group to show it's rejected
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption=f"Donation from @{bot.get_chat(chat_id).username or 'Anonymous'}: (❌ Rejected)"
    )

if __name__ == '__main__':
    bot.polling()
