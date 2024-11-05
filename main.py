import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# IDs for the admin group and public channel
ADMIN_GROUP_ID = -1001234567890  # Replace with your admin group ID
CHANNEL_ID = -1009876543210      # Replace with your public channel ID

# Admin-only access check
def is_admin(user_id):
    member_status = bot.get_chat_member(ADMIN_GROUP_ID, user_id).status
    return member_status in ['administrator', 'creator']

# Product information storage for verification
products = {}

# Increment options (percentage)
increment_options = [5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000]

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Please use /sell to post your product for verification.")

@bot.message_handler(commands=['sell'])
def initiate_sale(message):
    msg = bot.reply_to(message, "Please enter the product details in the following format:\nCategory | Product Name | Phone Number | Price (optional) | Description (optional)")
    bot.register_next_step_handler(msg, process_product_details)

def process_product_details(message):
    try:
        details = message.text.split('|')
        if len(details) < 3:
            raise ValueError("Insufficient details")
        
        category, name, phone = details[:3]
        price = details[3].strip() if len(details) > 3 else "N/A"
        description = details[4].strip() if len(details) > 4 else "No description"

        # Save product details for admin verification
        product_id = message.from_user.id
        products[product_id] = {
            'category': category.strip(),
            'name': name.strip(),
            'phone': phone.strip(),
            'price': float(price) if price != "N/A" else 0,
            'description': description
        }

        msg = bot.reply_to(message, "Please send product images now.")
        bot.register_next_step_handler(msg, handle_images, product_id)
    
    except Exception as e:
        bot.reply_to(message, "There was an error. Please use the format: Category | Product Name | Phone Number | Price (optional) | Description (optional)")

def handle_images(message, product_id):
    if message.photo:
        photo_id = message.photo[-1].file_id
        products[product_id]['photo'] = photo_id
        
        # Send for admin verification
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Verify", callback_data=f"verify_{product_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{product_id}")
        )
        
        bot.send_photo(
            ADMIN_GROUP_ID, photo_id,
            caption=f"New product verification:\n\n"
                    f"Category: {products[product_id]['category']}\n"
                    f"Name: {products[product_id]['name']}\n"
                    f"Phone: {products[product_id]['phone']}\n"
                    f"Seller's Price: {products[product_id]['price']}\n"
                    f"Description: {products[product_id]['description']}",
            reply_markup=markup
        )
        bot.reply_to(message, "Your product is submitted for verification. You’ll be notified once it’s verified.")
    else:
        bot.reply_to(message, "Please send a valid image.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('verify_', 'reject_')))
def handle_verification(call):
    action, user_id = call.data.split('_')
    user_id = int(user_id)

    if action == 'verify':
        request_increment(user_id, call)
    elif action == 'reject':
        bot.answer_callback_query(call.id, "Product rejected.")
        bot.send_message(user_id, "Your product was rejected.")
        bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)

def request_increment(user_id, call):
    markup = InlineKeyboardMarkup()
    for percentage in increment_options:
        markup.add(InlineKeyboardButton(f"{percentage}%", callback_data=f"inc_{user_id}_{percentage}"))
    
    bot.edit_message_caption(
        caption=f"Set increment for seller’s price: {products[user_id]['price']}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("inc_"))
def handle_increment_selection(call):
    _, user_id, increment = call.data.split('_')
    user_id, increment = int(user_id), float(increment)

    # Calculate new price
    seller_price = products[user_id]['price']
    new_price = round(seller_price + (seller_price * increment / 100), 2)
    products[user_id]['new_price'] = new_price

    # Confirm increment choice
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Post", callback_data=f"post_{user_id}"),
        InlineKeyboardButton("🔄 Change Increment", callback_data=f"verify_{user_id}")
    )
    
    bot.edit_message_caption(
        caption=f"New price: {new_price} (Original: {seller_price} + {increment}%)\n\nConfirm post?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id, f"New price calculated: {new_price}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("post_"))
def post_product(call):
    user_id = int(call.data.split('_')[1])
    product = products[user_id]

    bot.send_photo(
        CHANNEL_ID, product['photo'],
        caption=f"Category: {product['category']}\n"
                f"Name: {product['name']}\n"
                f"Description: {product['description']}\n"
                f"Price: {product['new_price']}\n"
                f"Contact: {product['phone']}"
    )
    bot.edit_message_caption("Posted ✅", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Product posted!")

if __name__ == '__main__':
    bot.polling()
