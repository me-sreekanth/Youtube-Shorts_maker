import os
import json
import base64
import datetime
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # e.g., username/Youtube-Shorts_maker

# Conversation states
WAITING_FOR_JSON, WAITING_FOR_SCHEDULE = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for the JSON script."""
    await update.message.reply_text(
        "👋 Welcome to the YouTube Shorts Maker Bot!\n\n"
        "Please send me the raw JSON script you'd like to process, or type /cancel to abort.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_FOR_JSON

async def receive_json(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate JSON and save it to context."""
    text = update.message.text
    try:
        # Validate that it's actually JSON
        json_data = json.loads(text)
        
        # Super simple check to ensure it at least strongly resembles our expected structure
        if "title" not in json_data and "scenes" not in json_data:
            await update.message.reply_text("⚠️ This doesn't look like a valid Shorts script (missing 'title' or 'scenes'). \n\nPlease send the correct JSON format.")
            return WAITING_FOR_JSON
            
        context.user_data['json_content'] = text
        
        reply_keyboard = [['Now', 'Schedule']]
        await update.message.reply_text(
            "✅ Valid JSON received.\n\n"
            "Would you like to generate and upload this video *now*, or let the daily cron job *schedule* it?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return WAITING_FOR_SCHEDULE
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Invalid JSON format. Please ensure you're pasting valid JSON.")
        return WAITING_FOR_JSON

async def schedule_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle choice and push to GitHub."""
    choice = update.message.text.lower()
    if choice not in ['now', 'schedule']:
        await update.message.reply_text("Please select either 'Now' or 'Schedule'.")
        return WAITING_FOR_SCHEDULE
        
    await update.message.reply_text("⏳ Pushing to GitHub...", reply_markup=ReplyKeyboardRemove())
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chat_id = update.effective_chat.id
    filename = f"input/daily/{timestamp}__chat_{chat_id}.json"
    
    content = context.user_data['json_content']
    encoded_content = base64.b64encode(content.encode()).decode()
    
    # 1. Commit file to GitHub via API
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"bot: Add script via Telegram: {filename}",
        "content": encoded_content,
        "branch": "main"  # Assumes your default branch is called main
    }
    
    try:
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            await update.message.reply_text(f"✅ Successfully added `{filename}` to GitHub!")
            
            if choice == 'now':
                await update.message.reply_text("🚀 Triggering remote GitHub Action to generate video immediately...")
                
                # 2. Trigger workflow_dispatch event
                dispatch_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/daily_upload.yml/dispatches"
                dispatch_data = {"ref": "main"}
                dispatch_resp = requests.post(dispatch_url, headers=headers, json=dispatch_data)
                
                if dispatch_resp.status_code == 204:
                    await update.message.reply_text("🎉 Generation triggered! Your video will start building remotely and be uploaded to YouTube shortly.")
                else:
                    await update.message.reply_text(f"⚠️ Failed to trigger action. Check your action permissions.\nAPI Response: {dispatch_resp.text}")
            else:
                await update.message.reply_text("🕒 Scheduled! The bot will process this during the next daily scheduled GitHub Actions run.")
        else:
            await update.message.reply_text(f"❌ Failed to commit to GitHub.\nHTTP Code: {response.status_code}\nResponse: {response.text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Network or internal error: {str(e)}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Operation cancelled. Type /start to try again.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    if not all([TELEGRAM_TOKEN, GITHUB_TOKEN, GITHUB_REPO]):
        print("❌ CRITICAL ERROR: Missing environment variables.")
        print("Please ensure the following are exported:")
        print("- TELEGRAM_TOKEN (from BotFather)")
        print("- GITHUB_TOKEN (Personal Access Token with 'repo' scope)")
        print("- GITHUB_REPO (Format: username/Youtube-Shorts_maker)")
        return

    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Set up conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_JSON: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_json)],
            WAITING_FOR_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    print("🤖 YouTube Shorts Telegram Bot is successfully listening...")
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
