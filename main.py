import telebot
from flask import Flask, request
import os

app = Flask(__name__)

# Telegram bot token and secret from environment variables
TOKEN = os.getenv('TOKEN')  # Set this in Railway environment variables
SECRET = os.getenv('SECRET')  # Set this in Railway environment variables

bot = telebot.TeleBot(TOKEN)

# Donation tracking
donations = {}
total_donated = 0
goal = 100000  # Set your donation goal

# Admin group ID and public channel ID
ADMIN_GROUP_ID = 1002262363425
CHANNEL_ID = 1002442298921

@app.route(f'/{SECRET}', methods=['POST'])
def webhook():
    print("Webhook triggered")
    update = Update.de_json(request.get_json(force=True), bot)
    print("Update:", update)  # Log the incoming update
    if update.message:
        print("Webhook received message")
        handle_message(update)
    elif update.callback_query:
        print("Webhook received callback")
        handle_callback(update)
    return "OK"


# Set up webhook
@app.before_request
def setup_webhook():
    REPLIT_URL = 'telegram-donation-bot-production.up.railway.app'  # Replace with your Railway app URL
    webhook_url = f"https://{REPLIT_URL}/{SECRET}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

# Handle /start
@bot.message_handler(commands=['start'])
def send_donation_methods(message):
    bot.send_message(
        message.chat.id, 
        "Thank you for your interest in donating! Here are the methods you can use to donate:\n"
        "1. Bank transfer: [Bank details]\n"
        "2. Telebirr: [Telebirr details]\n"
        "3. CBE: [CBE details]\n\n"
        "After donating, please send a screenshot for verification."
    )

# Handle donations
@bot.message_handler(commands=['donate'])
def handle_donation(message):
    try:
        amount = int(message.text.split(' ')[1])
        donations[message.chat.id] = amount
        bot.send_message(message.chat.id, f"Thank you for your donation of {amount}! Please send a screenshot for verification.")
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "Invalid format. Please use /donate <amount>.")

# Handle photo verification
@bot.message_handler(content_types=['photo'])
def handle_photo_verification(message):
    bot.send_message(
        ADMIN_GROUP_ID,
        f"New donation verification from {message.from_user.username}.\nAmount: {donations.get(message.chat.id, 'Unknown')}"
    )
    bot.send_message(message.chat.id, "Your screenshot has been received. Please wait for admin verification.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
