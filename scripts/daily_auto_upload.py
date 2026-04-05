import os
import sys
import glob
import shutil
import subprocess
import re
import requests
from pathlib import Path

# Configuration
MAX_UPLOADS_PER_DAY = 5

BASE_DIR = Path(__file__).resolve().parent.parent
DAILY_INPUT_DIR = BASE_DIR / "input" / "daily"
VIDEO_SCRIPT_FILE = BASE_DIR / "input" / "video_script.json"

def main():
    print("🌅 Daily Auto Upload Script")
    print("=" * 50)
    
    # 1. Check directory
    if not DAILY_INPUT_DIR.exists():
        print(f"📁 Directory {DAILY_INPUT_DIR} does not exist. Creating it.")
        DAILY_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        print("🛑 No JSONs to process. Exiting.")
        sys.exit(0)
    
    # 2. Get pending JSONs sorted alphabetically
    json_files = sorted(glob.glob(str(DAILY_INPUT_DIR / "*.json")))
    
    if not json_files:
        print("🛑 No pending JSON scripts found in input/daily/. Exiting.")
        sys.exit(0)
    
    print(f"📊 Found {len(json_files)} pending JSON scripts.")
    
    # 3. Apply limit
    files_to_process = json_files[:MAX_UPLOADS_PER_DAY]
    print(f"🚀 Processing up to {MAX_UPLOADS_PER_DAY} files today.")
    
    python_exec = sys.executable
    
    for i, file_path_str in enumerate(files_to_process, 1):
        file_path = Path(file_path_str)
        print(f"\n🎬 Processing [{i}/{len(files_to_process)}]: {file_path.name}")
        
        # 4. Copy to input/video_script.json (overwrite)
        try:
            shutil.copy2(file_path, VIDEO_SCRIPT_FILE)
            print(f"   ✅ Copied to {VIDEO_SCRIPT_FILE.relative_to(BASE_DIR)}")
        except Exception as e:
            print(f"   ❌ Failed to copy script: {e}")
            sys.exit(1)
        
        # 5. Run run_video_from_script.py
        print("   🔨 Running video generation...")
        gen_script = BASE_DIR / "scripts" / "run_video_from_script.py"
        result_gen = subprocess.run([python_exec, str(gen_script)], check=False)
        
        if result_gen.returncode != 0:
            print("   ❌ Video generation failed. Aborting further processing.")
            sys.exit(1)
            
        print("   ✅ Video generation successful!")
        
        # 6. Run upload_to_youtube.py
        print("   📤 Running YouTube upload...")
        upload_script = BASE_DIR / "scripts" / "upload_to_youtube.py"
        
        result_up = subprocess.run([python_exec, str(upload_script)], capture_output=True, text=True)
        print(result_up.stdout) # Print output so we still see the log!
        
        if result_up.returncode != 0:
            print("   ❌ YouTube upload failed. Aborting further processing.")
            print(result_up.stderr)
            sys.exit(1)
            
        print("   ✅ YouTube upload successful!")
        
        # Parse the video URL from the standard output
        youtube_url = None
        url_match = re.search(r"URL:\s+(https://www.youtube.com/watch\?v=[\w-]+)", result_up.stdout)
        if url_match:
            youtube_url = url_match.group(1)
            print(f"   🔗 Extracted YouTube URL: {youtube_url}")
            
            # Send Telegram Notification!
            telegram_token = os.environ.get("TELEGRAM_TOKEN")
            chat_id_match = re.search(r"__chat_(\d+)\.json$", file_path.name)
            
            if telegram_token and chat_id_match:
                chat_id = chat_id_match.group(1)
                print(f"   📱 Sending Telegram notification to chat ID: {chat_id}...")
                try:
                    payload = {
                        "chat_id": chat_id,
                        "text": f"🎉 Your video was generated and successfully uploaded to YouTube!\n\n📺 Link: {youtube_url}"
                    }
                    req = requests.post(f"https://api.telegram.org/bot{telegram_token}/sendMessage", json=payload)
                    if req.status_code == 200:
                        print("   ✅ Notification sent!")
                    else:
                        print(f"   ⚠️ Failed to send notification: {req.text}")
                except Exception as e:
                    print(f"   ⚠️ Error pinging Telegram: {e}")
        
        # 7. Delete the processed JSON from daily/
        try:
            file_path.unlink()
            print(f"   🗑️ Deleted {file_path.name} from {DAILY_INPUT_DIR.relative_to(BASE_DIR)}")
        except Exception as e:
            print(f"   ⚠️ Could not delete {file_path.name}: {e}")
            
    print("\n🎉 All scheduled uploads for today are complete!")

if __name__ == "__main__":
    main()
