import os
import time
import requests
from urllib.parse import quote

SCRIPT_FILE = "output/short_script.txt"
IMAGE_DIR = "output/images"
IMAGE_ENDPOINT = "https://image.pollinations.ai/prompt"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
MAX_IMAGES = 18  # Hard limit to keep video under 2 minutes

def generate_image(prompt: str, filename: str, retries=MAX_RETRIES):
    """
    Generate image with retry logic and error handling.
    Returns path on success, None on failure.
    """
    os.makedirs(IMAGE_DIR, exist_ok=True)
    url = f"{IMAGE_ENDPOINT}/{quote(prompt)}"
    params = {
        "width": 1080,
        "height": 1920,
        "model": "flux"  # you can experiment with other models per docs
    }
    
    out_path = os.path.join(IMAGE_DIR, filename)
    
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=120)
            resp.raise_for_status()
            
            with open(out_path, "wb") as f:
                f.write(resp.content)
            return out_path
            
        except requests.exceptions.HTTPError as e:
            if attempt < retries:
                wait_time = RETRY_DELAY * attempt
                print(f"     ⚠️  Attempt {attempt} failed ({e.response.status_code}), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"     ❌ Failed after {retries} attempts: {e}")
                return None
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                wait_time = RETRY_DELAY * attempt
                print(f"     ⚠️  Attempt {attempt} failed (network error), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"     ❌ Failed after {retries} attempts: {e}")
                return None
    
    return None

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ output/short_script.txt not found. Run summarizer first.")
        return

    # Check if audio exists (should be created before images)
    audio_file = "output/audio/voice.mp3"
    if not os.path.exists(audio_file):
        print("⚠️  Audio file not found. Run tts.py first to generate audio.")
        print("   Continuing anyway, but timing may not be accurate...")

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.read().splitlines() if l.strip()]

    if not lines:
        print("❌ No lines in short_script.txt")
        return

    # Limit to MAX_IMAGES to keep video under 2 minutes
    if len(lines) > MAX_IMAGES:
        print(f"⚠️  Script has {len(lines)} lines, limiting to {MAX_IMAGES} images max")
        lines = lines[:MAX_IMAGES]

    print(f"🎨 Generating {len(lines)} images via Pollinations...")
    successful = 0
    failed = 0
    
    for i, line in enumerate(lines, start=1):
        # Enhanced prompt for dynamic, transition-friendly images
        prompt = (
            f"{line}, "
            "cinematic, dynamic composition, high quality, "
            "vertical video frame 9:16, "
            "motion blur, depth of field, "
            "suitable for smooth transitions and zoom effects, "
            "vibrant colors, professional photography"
        )
        print(f"  -> Image {i}/{len(lines)}: {line[:60]}...")
        path = generate_image(prompt, f"img_{i}.jpg")
        
        if path:
            print(f"     ✅ Saved {path}")
            successful += 1
        else:
            print(f"     ❌ Failed to generate image {i}")
            failed += 1
        
        # Small delay between requests to avoid rate limiting
        if i < len(lines):
            time.sleep(1)
    
    print(f"\n✅ Image generation complete: {successful} successful, {failed} failed")
    if failed > 0:
        print("⚠️  Some images failed. The script will continue, but missing images may cause issues.")

if __name__ == "__main__":
    main()

