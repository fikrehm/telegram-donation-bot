import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Define your admin and channel group IDs
ADMIN_GROUP_ID = -1002262363425  # Admin group for verification
CHANNEL_ID = -1002442298921  # Public channel for approved listings
BOT_PHONE_NUMBER = "+251991602186"  # Placeholder phone number for posts

# Step 1: Start Command to Welcome Users
@bot.message_handler(commands=['start'])
def welcome_message(message):
    bot.reply_to(
        message, 
        "Welcome to the Buy & Sell Bot! 🎉\n\n"
        "To list an item, simply type /sell, and I’ll guide you step-by-step!"
    )

# Step 2: Sell Command to Collect Item Details
@bot.message_handler(commands=['sell'])
def initiate_sell(message):
    bot.reply_to(message, "Let's start listing your item for sale! 🛒\nFirst, please enter the **name of the product**:")
    bot.register_next_step_handler(message, get_product_name)

# Step 3: Get Product Details Step-by-Step
def get_product_name(message):
    product = {"user_id": message.from_user.id}
    product['name'] = message.text
    bot.reply_to(message, "Great! Now, what category does it fall under (e.g., Electronics, Clothing)?")
    bot.register_next_step_handler(message, get_category, product)

def get_category(message, product):
    product['category'] = message.text
    bot.reply_to(message, "Please provide a description (optional). You can skip this by typing 'skip'.")
    bot.register_next_step_handler(message, get_description, product)

def get_description(message, product):
    product['description'] = message.text if message.text.lower() != 'skip' else None
    bot.reply_to(message, "How much are you selling it for? (Enter just the number, e.g., 100)")
    bot.register_next_step_handler(message, get_price, product)

def get_price(message, product):
    try:
        product['price'] = int(message.text)
        bot.reply_to(message, "Lastly, please provide your contact phone number.")
        bot.register_next_step_handler(message, get_phone, product)
    except ValueError:
        bot.reply_to(message, "Please enter a valid number for the price.")
        bot.register_next_step_handler(message, get_price, product)

def get_phone(message, product):
    product['phone'] = message.text
    bot.reply_to(message, "Now, please send a photo of the product.")
    bot.register_next_step_handler(message, get_photo, product)

# Step 3: Get Product Details Step-by-Step (No change here, provided for context)
def get_photo(message, product):
    if message.content_type != 'photo':
        bot.reply_to(message, "Please send a valid photo.")
        bot.register_next_step_handler(message, get_photo, product)
        return
    product['photo'] = message.photo[-1].file_id

    # Show product summary to user for confirmation
    product_summary = (
        f"**Product Summary:**\n\n"
        f"**Name:** {product['name']}\n"
        f"**Category:** {product['category']}\n"
        f"**Description:** {product['description'] or 'No description provided'}\n"
        f"**Price:** {product['price']}\n"
        f"**Contact:** {product['phone']}\n"
        "Please confirm if all the information is correct."
    )
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Confirm", callback_data="confirm_sell"),
        InlineKeyboardButton("🔄 Edit", callback_data="edit_sell")
    )
    confirmation_message = bot.send_photo(
        message.chat.id, product['photo'], caption=product_summary, reply_markup=markup
    )
    
    # Store product data and confirmation message ID for further processing
    bot.user_data[message.from_user.id] = {"product": product, "confirmation_msg_id": confirmation_message.message_id}

# Step 4: Handle Confirmation or Editing Request (Modified)
@bot.callback_query_handler(func=lambda call: call.data in ["confirm_sell", "edit_sell"])
def handle_confirmation(call):
    user_id = call.from_user.id
    user_data = bot.user_data.get(user_id)
    
    if not user_data:
        bot.answer_callback_query(call.id, "No product details found. Please restart the process with /sell.")
        return

    product = user_data["product"]
    confirmation_msg_id = user_data["confirmation_msg_id"]

    if call.data == "confirm_sell":
        # Remove Confirm and Edit buttons from user's message
        bot.edit_message_reply_markup(call.message.chat.id, confirmation_msg_id, reply_markup=None)
        bot.send_message(call.message.chat.id, "Thank you! Your item is being reviewed by our admins. Please wait for confirmation.")

        # Send product details to the admin group for verification
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        )
        bot.send_photo(
            ADMIN_GROUP_ID, product['photo'],
            caption=(
                f"**New Product for Verification:**\n\n"
                f"**Name:** {product['name']}\n"
                f"**Category:** {product['category']}\n"
                f"**Description:** {product['description'] or 'No description'}\n"
                f"**Seller's Price:** {product['price']}\n"
                f"**Contact:** {product['phone']}"
            ),
            reply_markup=markup
        )

    elif call.data == "edit_sell":
        # Reset the process, starting with the product name
        bot.send_message(call.message.chat.id, "Let's edit your product details. Starting from the beginning.")
        initiate_sell(call.message)

# Step 5: Admin Verification Process

# Step 5: Admin Verification Process
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_verification(call):
    user_id = int(call.data.split("_")[1])
    product = bot.user_data.get(user_id)

    if call.data.startswith("approve_"):
        # Prompt for price adjustment
        markup = InlineKeyboardMarkup()
        increments = [5, 7.5, 10, 15, 20, 25, 30, 50, 100, 150, 200, 500, 1000]
        buttons = [InlineKeyboardButton(f"{inc}%", callback_data=f"increment_{inc}_{user_id}") for inc in increments]
        for i in range(0, len(buttons), 3):
            markup.row(*buttons[i:i+3])
        bot.send_message(
            call.message.chat.id, 
            f"Select the price increment for {product['name']}:\nSeller's Price: {product['price']}",
            reply_markup=markup
        )
    else:
        bot.edit_message_caption(
            caption="Product **Rejected** ❌",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.send_message(user_id, "Unfortunately, your product was not approved.")

# Step 6: Apply Increment and Final Posting (Modified Increment Options)
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_verification(call):
    user_id = int(call.data.split("_")[1])
    product = bot.user_data.get(user_id)

    if call.data.startswith("approve_"):
        # Updated increment options based on new range
        markup = InlineKeyboardMarkup()
        increments = [5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 250, 300, 350, 
                      400, 450, 500, 600, 700, 800, 900, 1000]
        buttons = [InlineKeyboardButton(f"{inc}%", callback_data=f"increment_{inc}_{user_id}") for inc in increments]
        for i in range(0, len(buttons), 3):
            markup.row(*buttons[i:i+3])
        bot.send_message(
            call.message.chat.id, 
            f"Select the price increment for {product['name']}:\nSeller's Price: {product['price']}",
            reply_markup=markup
        )
    else:
        bot.edit_message_caption(
            caption="Product **Rejected** ❌",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.send_message(user_id, "Unfortunately, your product was not approved.")



# Step 6: Apply Increment and Final Posting
@bot.callback_query_handler(func=lambda call: call.data.startswith("increment_"))
def apply_increment(call):
    _, percent, user_id = call.data.split("_")
    user_id = int(user_id)
    product = bot.user_data.get(user_id)
    
    incremented_price = product['price'] * (1 + int(percent) / 100)
    product['final_price'] = round(incremented_price, 2)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Post", callback_data=f"post_{user_id}"),
               InlineKeyboardButton("🔄 Go Back", callback_data=f"back_{user_id}"))
    bot.send_message(
        call.message.chat.id, 
        f"Increment of {percent}% applied.\nNew Price: {product['final_price']}\n\nReady to post?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("post_"))
def post_to_channel(call):
    user_id = int(call.data.split("_")[1])
    product = bot.user_data.pop(user_id, None)
    
    if product:
        post_text = (
            f"**{product['name']}**\n"
            f"Category: {product['category']}\n"
            f"Price: {product['final_price']} {BOT_PHONE_NUMBER}\n"
            f"Description: {product['description'] or 'No description provided'}"
        )
        bot.send_photo(CHANNEL_ID, product['photo'], caption=post_text)
        bot.send_message(user_id, "🎉 Your item has been successfully posted!")
    bot.edit_message_caption(
        caption="Product **Approved and Posted** ✅",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

# Start the bot polling
if __name__ == '__main__':
    bot.polling()
