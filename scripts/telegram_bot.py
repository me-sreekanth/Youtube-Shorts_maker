import os
import json
import base64
import datetime
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # e.g., username/Youtube-Shorts_maker
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Conversation states
WAITING_FOR_JSON, WAITING_FOR_SCHEDULE = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for the JSON script or topic."""
    await update.message.reply_text(
        "👋 Welcome to the YouTube Shorts Maker Bot!\n\n"
        "Please send me the raw JSON script you'd like to process, or type a regular text topic, or type /cancel to abort.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_FOR_JSON

def generate_script_from_topic_openrouter(topic: str) -> str:
    """Generate a valid JSON video script from a text topic using OpenRouter."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in environment.")
        
    system_prompt = """You are an expert YouTube Shorts video script creator. 
You must output ONLY a valid JSON object. Do not include markdown formatting blocks (like ```json).
The JSON must strictly follow this exact structure WITHOUT ANY ADDITIONAL KEYS (do NOT output a 'subtitle' key):
{
  "title": "A catchy title about the topic",
  "scenes": [
    {
      "scene_number": 1,
      "scene_type": "content",
      "narration": "A captivating narration sentence.",
      "image_prompt": "A highly detailed image generation prompt specifying cinematic lighting, style, subject, and composition",
      "duration": 4,
      "effect": "zoom_in"
    }
  ]
}

CRITICAL RULES YOU MUST FOLLOW OR YOU WILL BE PENALIZED:
1. ONLY generate exactly 7-10 scenes containing actual content. NEVER generate a "promo", "subscribe", or "outro" scene. Your scenes should end with the final fact or story point.
2. The "effect" field MUST be chosen strictly from this exact list: ["zoom_in", "zoom_out", "ken_burns_in", "ken_burns_out", "pan_left", "pan_right", "pan_up", "pan_down", "zoom_center", "zoom_rapid", "parallax_up", "parallax_down", "drift_left", "drift_right", "float_up", "pulse", "breathe", "diagonal_tl_br", "diagonal_tr_bl", "static"]. ANY OTHER EFFECT IS INVALID.
3. DO NOT output a "subtitle" field inside the scenes.
"""
    user_prompt = f'Generate a short video script about the topic: "{topic}".'
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/terrificminds/Youtube-Shorts_maker",
        "X-Title": "YouTube Shorts Bot",
        "Content-Type": "application/json"
    }
    models_to_try = [
        "openrouter/free",
        "google/gemma-3-27b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "meta-llama/llama-3.3-70b-instruct:free"
    ]
    
    errors = []
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            # Strip markdown if the model hallucinates it despite instructions
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return content.strip()
        else:
            errors.append(f"{model}: {response.text}")
            continue
            
    all_errors = " | ".join(errors)
    raise Exception(f"All fallback models failed. Errors: {all_errors}")

def enforce_strict_json_structure(json_data):
    valid_effects = [
        "zoom_in", "zoom_out", "ken_burns_in", "ken_burns_out",
        "pan_left", "pan_right", "pan_up", "pan_down",
        "zoom_center", "zoom_rapid", "parallax_up", "parallax_down",
        "drift_left", "drift_right", "float_up", "pulse", "breathe",
        "diagonal_tl_br", "diagonal_tr_bl", "static"
    ]

    default_effect_cycle = [
        "zoom_in", "ken_burns_in", "pan_left", "parallax_up",
        "drift_right", "zoom_rapid", "pulse", "breathe",
        "diagonal_tl_br", "zoom_out"
    ]

    scenes = json_data.get("scenes", [])

    # Ensure 7–10 scenes
    if len(scenes) < 7:
        raise ValueError("❌ Too few scenes. Minimum 7 required.")
    if len(scenes) > 10:
        scenes = scenes[:10]

    sanitized = []

    for i, s in enumerate(scenes):
        scene = {}

        # REQUIRED FIELDS
        scene["scene_number"] = i + 1
        scene["scene_type"] = s.get("scene_type", "content")

        scene["narration"] = s.get("narration", "").strip() or "..."

        scene["image_prompt"] = s.get("image_prompt", "").strip() or "cinematic fantasy scene"

        scene["duration"] = 4

        # EFFECT FIX (CRITICAL)
        effect = s.get("effect")
        if effect not in valid_effects:
            effect = default_effect_cycle[i % len(default_effect_cycle)]

        scene["effect"] = effect

        sanitized.append(scene)

    json_data["scenes"] = sanitized

    # Optional: enforce total_duration
    json_data["total_duration"] = len(sanitized) * 4

    return json_data

async def receive_json(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate JSON or generate it from topic, and save it to context."""
    text = update.message.text
    try:
        # If it looks like JSON, parse it as JSON
        if text.strip().startswith('{') or text.strip().startswith('['):
            json_data = json.loads(text)
            
            # Super simple check to ensure it at least strongly resembles our expected structure
            if "title" not in json_data and "scenes" not in json_data:
                await update.message.reply_text("⚠️ This doesn't look like a valid Shorts script (missing 'title' or 'scenes'). \n\nPlease send the correct JSON format.")
                return WAITING_FOR_JSON
                
            context.user_data['json_content'] = text
            await update.message.reply_text("✅ Valid JSON received.\n")
        else:
            # Treat as text topic
            await update.message.reply_text(f"🤖 Generating a video script for topic: '{text}'...")
            
            import asyncio
            try:
                json_content = await asyncio.to_thread(generate_script_from_topic_openrouter, text)
                
                json_data = json.loads(json_content)
                if "title" not in json_data or "scenes" not in json_data:
                    raise ValueError("Generated JSON is missing 'title' or 'scenes'.")
                
                # Apply the strict schema structure enforcement
                json_data = enforce_strict_json_structure(json_data)
                json_content = json.dumps(json_data, indent=2)
                
                context.user_data['json_content'] = json_content
                num_scenes = len(json_data.get('scenes', []))
                
                keyboard = [[InlineKeyboardButton("📑 Show script", callback_data="show_script")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"✅ Generated script: '{json_data.get('title', 'Unknown Title')}' with {num_scenes} scenes.\n",
                    reply_markup=reply_markup
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to generate script. Please send valid JSON or try a different topic.\nError: {str(e)}")
                return WAITING_FOR_JSON
        
        reply_keyboard = [['Now', 'Schedule']]
        await update.message.reply_text(
            "Would you like to generate and upload this video *now*, or let the daily cron job *schedule* it?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return WAITING_FOR_SCHEDULE
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Invalid JSON format. Please ensure you're pasting valid JSON if you intend to send a script directly.")
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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button clicks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_script":
        json_content = context.user_data.get('json_content')
        if json_content:
            # Telegram limits messages to 4096 characters.
            if len(json_content) > 4000:
                truncated = json_content[:3900] + "\n... (truncated)"
                await query.message.reply_text(f"```json\n{truncated}\n```", parse_mode='Markdown')
            else:
                await query.message.reply_text(f"```json\n{json_content}\n```", parse_mode='Markdown')
        else:
            await query.message.reply_text("❌ No script found in current session.")

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Telegram bot is running on Render!")
        
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def main() -> None:
    """Run the bot."""
    if not all([TELEGRAM_TOKEN, GITHUB_TOKEN, GITHUB_REPO]):
        print("❌ CRITICAL ERROR: Missing environment variables.")
        print("Please ensure the following are exported:")
        print("- TELEGRAM_TOKEN (from BotFather)")
        print("- GITHUB_TOKEN (Personal Access Token with 'repo' scope)")
        print("- GITHUB_REPO (Format: username/Youtube-Shorts_maker)")
        print("- OPENROUTER_API_KEY (Optional, for text topic generation)")
        return
        
    if not OPENROUTER_API_KEY:
        print("⚠️ Warning: OPENROUTER_API_KEY is not set. Topic generation will fail. Direct JSON will still work.")

    # Start dummy web server for Render health checks
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("🌐 Started dummy web server for health checks.")

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
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 YouTube Shorts Telegram Bot is successfully listening...")
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
