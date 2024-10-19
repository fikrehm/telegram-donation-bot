import os
import telebot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Replace 'TELEGRAM_BOT_TOKEN' with the token you received from BotFather
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Donation tracking
donations = {}
total_donated = 0
goal = 100000  # Set your donation goal

# Admin group ID and public channel ID
ADMIN_GROUP_ID = -1002262363425  # Ensure this is a negative number for group chats
CHANNEL_ID = -1002442298921  # Ensure this is a negative number for channel IDs

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

@bot.message_handler(commands=['donate'])
def handle_donation(message):
    try:
        amount = int(message.text.split(' ')[1])
        donations[message.chat.id] = amount
        bot.reply_to(message, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid format. Please use /donate <amount>.")

@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    chat_id = message.chat.id
    if chat_id in donations:
        photo_id = message.photo[-1].file_id
        bot.send_message(
            ADMIN_GROUP_ID,
            f"New donation verification from {message.from_user.username}.\n"
            f"Amount: {donations[chat_id]}",
        )
        bot.reply_to(message, "Your screenshot has been received. Please wait for admin verification.")
    else:
        bot.reply_to(message, "Please donate first before sending a screenshot.")

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)

if __name__ == '__main__':
    bot.polling()
