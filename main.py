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
CHANNEL_ID = -1002359300420  # Supergroup ID for approved listings
BOT_PHONE_NUMBER = "+251991602186"  # Placeholder phone number for posts

# Global dictionary to hold user data
user_data = {}

# Step 1: Start Command to Welcome Users
@bot.message_handler(commands=['start'])
def welcome_message(message):
    bot.reply_to(
        message, 
        "Welcome to the Delala Bot! 🎉\n\n"
        "To sell an item, simply type /sell, and I’ll guide you step-by-step! \n\"
        "እንኳን ወደ ደላላ ቦት በደህና መጡ! 🎉\n\n"
        "ዕቃ ለመሸጥ /sell ይጻፉ"
    )

# Step 2: Sell Command to Collect Item Details
@bot.message_handler(commands=['sell'])
def initiate_sell(message):
    bot.reply_to(message, "Let's start listing your item for sale! 🛒\nFirst, please enter the **name of the product**(የምትሸጠው ዕቃ ስም):")
    bot.register_next_step_handler(message, get_product_name)

# Step 3: Get Product Details Step-by-Step
def get_product_name(message):
    try:
        product = {"user_id": message.from_user.id}
        product['name'] = message.text
        bot.reply_to(message, "Great! Now, what category does it fall under (e.g., Electronics, Clothing)?(የሚሸጡት ዕቃ ዓይነት)")
        bot.register_next_step_handler(message, get_category, product)
    except ValueError:
        bot.reply_to(message, "Please enter a valid product name to proceed with your listing.(እባክዎ ትክክለኛ ስም ያስገቡ)")
        bot.register_next_step_handler(message, get_product_name , product)

def get_category(message, product):
    product['category'] = message.text
    bot.reply_to(message, "Please provide a description (optional). You can skip this by typing 'skip'.(ስለ ዕቃዎ የበለጠ ያብራሩ)")
    bot.register_next_step_handler(message, get_description, product)

def get_description(message, product):
    product['description'] = message.text if message.text.lower() != 'skip' else None
    bot.reply_to(message, "How much are you selling it for?(የእቃዎ ዋጋ) (Enter just the number, e.g., 100)")
    bot.register_next_step_handler(message, get_price, product)

def get_price(message, product):
    try:
        product['price'] = int(message.text)
        bot.reply_to(message, "Lastly, please provide your contact phone number.(ስልክ ቁጥር)")
        bot.register_next_step_handler(message, get_phone, product)
    except ValueError:
        bot.reply_to(message, "Please enter a valid number for the price.")
        bot.register_next_step_handler(message, get_price, product)

def get_phone(message, product):
    product['phone'] = message.text
    bot.reply_to(message, "Now, please send a photo of the product.(የእቃው ፎቶ)")
    bot.register_next_step_handler(message, get_photo, product)

def get_photo(message, product):
    if message.content_type != 'photo':
        bot.reply_to(message, "Please send a valid photo. /sell to start again! ")
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
    
    user_data[message.from_user.id] = {"product": product, "confirmation_msg_id": confirmation_message.message_id}

# Step 4: Handle Confirmation or Editing Request
@bot.callback_query_handler(func=lambda call: call.data in ["confirm_sell", "edit_sell"])
def handle_confirmation(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "No product details found. Please restart the process with /sell.")
        return

    product = user_data[user_id]["product"]
    confirmation_msg_id = user_data[user_id]["confirmation_msg_id"]

    if call.data == "confirm_sell":
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
            caption=(f"**New Product for Verification:**\n\n"
                     f"**Name:** {product['name']}\n"
                     f"**Category:** {product['category']}\n"
                     f"**Description:** {product['description'] or 'No description'}\n"
                     f"**Seller's Price:** {product['price']}\n"
                     f"**Contact:** {product['phone']}"),
            reply_markup=markup
        )

    elif call.data == "edit_sell":
        bot.edit_message_reply_markup(call.message.chat.id, confirmation_msg_id, reply_markup=None)
        bot.send_message(call.message.chat.id, "Let's edit your product details. Starting from the beginning.")
        initiate_sell(call.message)

# Step 5: Admin Verification Process
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_verification(call):
    user_id = int(call.data.split("_")[1])
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "Error: Product not found.")
        return
    product = user_data.get(user_id)["product"]

    if call.data.startswith("approve_"):
        # Notify seller of approval
        bot.send_message(product['user_id'], f"✅ Your product '{product['name']}' has been approved and will be posted soon.")
        
        # Display increment options
        increments = [1, 2.5 , 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 
                  250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 2500,5000, 7500,10000]
        markup = InlineKeyboardMarkup()
        buttons = [InlineKeyboardButton(f"{inc}%", callback_data=f"increment_{inc}_{user_id}") for inc in increments]
        for i in range(0, len(buttons), 2):
            markup.row(*buttons[i:i+2])
        markup.add(InlineKeyboardButton("🔄 Go Back", callback_data=f"back_to_approval_{user_id}"))

        bot.edit_message_caption(
            caption=f"Select the price increment for {product['name']}:\nSeller's Price: {product['price']}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    elif call.data.startswith("reject_"):
        # Notify seller of rejection
        bot.send_message(product['user_id'], f"❌ Unfortunately, your product '{product['name']}' has been rejected.")
        
        # Edit message caption to indicate rejection
        bot.edit_message_caption(
            caption=f"Product **Rejected** ❌\n\n**Product Details:**\n"
                    f"**Name:** {product['name']}\n"
                    f"**Category:** {product['category']}\n"
                    f"**Price:** {product['price']}\n"
                    f"**Contact:** {product['phone']}\n",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("increment_"))
def apply_increment(call):
    _, percent, user_id = call.data.split("_")
    user_id = int(user_id)
    product = user_data[user_id]["product"]

    incremented_price = product['price'] * (1 + float(percent) / 100)
    product['final_price'] = round(incremented_price, 2)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Post", callback_data=f"post_{user_id}"),
        InlineKeyboardButton("🔄 Go Back", callback_data=f"back_to_increments_{user_id}")
    )
    bot.edit_message_caption(
        caption=f"Increment of {percent}% applied.\nNew Price: {product['final_price']}\n\nReady to post?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("post_"))
def post_to_channel(call):
    user_id = int(call.data.split("_")[1])
    product = user_data[user_id]["product"]

    bot.send_photo(
        CHANNEL_ID, product['photo'],
        caption=f"**{product['name']}**\n\n"
                f"Category: {product['category']}\n"
                f"Description: {product['description'] or 'No description'}\n"
                f"Price: {product['final_price']}\n"
                f"Contact Seller: {BOT_PHONE_NUMBER}"
    )

    bot.edit_message_caption(
        caption=f"Product **Posted** ✅\n\n**Product Details:**\n"
                f"**Name:** {product['name']}\n"
                f"**Category:** {product['category']}\n"
                f"**Price:** {product['price']}\n"
                f"**Contact:** {product['phone']}\n"
                f"**Final Price:** {product['final_price']}\n",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_to_increments_"))
def back_to_increment_selection(call):
    user_id = int(call.data.split("_")[-1])
    product = user_data[user_id]["product"]

    increments = [1, 2.5 , 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 
                  250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 2500,5000, 7500,10000]
    markup = InlineKeyboardMarkup()
    buttons = [InlineKeyboardButton(f"{inc}%", callback_data=f"increment_{inc}_{user_id}") for inc in increments]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.add(InlineKeyboardButton("🔄 Go Back", callback_data=f"back_to_approval_{user_id}"))

    bot.edit_message_caption(
        caption=f"Select the price increment for {product['name']}:\nSeller's Price: {product['price']}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_to_approval_"))
def back_to_approval_options(call):
    user_id = int(call.data.split("_")[-1])
    product = user_data[user_id]["product"]

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
    )
    bot.edit_message_caption(
        caption=f"Product Pending Approval 🔄\n\n**Product Details:**\n"
                f"**Name:** {product['name']}\n"
                f"**Category:** {product['category']}\n"
                f"**Price:** {product['price']}\n"
                f"**Contact:** {product['phone']}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

# Start polling for messages
bot.polling()
