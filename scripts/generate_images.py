import os
import time
import requests
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SCRIPT_FILE = "output/short_script.txt"
IMAGE_DIR = "output/images"
IMAGE_ENDPOINT = "https://image.pollinations.ai/prompt"
MAX_RETRIES = 5
RETRY_DELAY = 3  # base delay in seconds
MAX_IMAGES = 18  # Hard limit to keep video under 2 minutes

# Create a session with retry strategy
def create_session():
    """Create a requests session with retry strategy."""
    session = requests.Session()
    
    # Retry strategy: retry on connection errors, timeouts, and 5xx errors
    # 524 is Cloudflare timeout error - should retry
    retry_strategy = Retry(
        total=2,  # Lower here since we handle retries manually
        backoff_factor=2,  # 2, 4 seconds
        status_forcelist=[500, 502, 503, 504, 524],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

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
    
    # Use separate timeouts: connect timeout (10s) and read timeout (90s)
    # Image generation can take a while, but we don't want to wait forever
    # If server times out (524), we'll retry with longer waits
    timeout = (10, 90)  # (connect_timeout, read_timeout)
    
    session = None
    for attempt in range(1, retries + 1):
        try:
            # Create a new session for each attempt to avoid connection reuse issues
            session = create_session()
            
            print(f"     🔄 Attempt {attempt}/{retries} (max 90s)...")
            start_time = time.time()
            
            # Make the request with timeout
            resp = session.get(url, params=params, timeout=timeout, stream=True)
            resp.raise_for_status()
            
            elapsed = time.time() - start_time
            print(f"     ✅ Response received ({elapsed:.1f}s), downloading...")
            
            # Stream the content to handle large images better
            content_length = resp.headers.get('content-length')
            total_size = int(content_length) if content_length else None
            downloaded = 0
            chunk_start = time.time()
            
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Show progress every 50KB or every 2 seconds
                        chunk_elapsed = time.time() - chunk_start
                        if chunk_elapsed >= 2.0 or (total_size and downloaded % (50 * 1024) < 8192):
                            if total_size:
                                percent = (downloaded / total_size) * 100
                                print(f"     📥 Downloading... {percent:.1f}% ({downloaded//1024}KB)", end='\r')
                            else:
                                print(f"     📥 Downloading... {downloaded//1024}KB", end='\r')
                            chunk_start = time.time()
            
            if session:
                session.close()
            print()  # New line after progress
            total_time = time.time() - start_time
            print(f"     ✅ Image downloaded ({total_time:.1f}s total)")
            return out_path
            
        except requests.exceptions.Timeout as e:
            if session:
                session.close()
            if attempt < retries:
                wait_time = RETRY_DELAY * (2 ** (attempt - 1))  # Exponential backoff: 3, 6, 12, 24s
                print(f"     ⚠️  Attempt {attempt} timed out, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"     ❌ Failed after {retries} attempts: Request timed out")
                return None
        except requests.exceptions.ConnectionError as e:
            if session:
                session.close()
            if attempt < retries:
                wait_time = RETRY_DELAY * (2 ** (attempt - 1))  # Exponential backoff
                print(f"     ⚠️  Attempt {attempt} connection error, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"     ❌ Failed after {retries} attempts: Connection error - {str(e)[:100]}")
                return None
        except requests.exceptions.HTTPError as e:
            if session:
                session.close()
            status_code = e.response.status_code if e.response else 0
            
            # HTTP 524 is Cloudflare timeout - server is overloaded or request takes too long
            # Use longer wait times for server-side timeouts
            if status_code == 524:
                if attempt < retries:
                    # Longer wait for 524: 10, 20, 40, 80 seconds
                    wait_time = 10 * (2 ** (attempt - 1))
                    print(f"     ⚠️  Attempt {attempt} failed (HTTP 524 - Server timeout), retrying in {wait_time}s...")
                    print(f"     💡 Tip: Server is processing, this may take longer...")
                    time.sleep(wait_time)
                else:
                    print(f"     ❌ Failed after {retries} attempts: Server timeout (HTTP 524)")
                    print(f"     💡 The API server may be overloaded. Try again later.")
                    return None
            elif status_code >= 500:
                # Other 5xx errors - server errors
                if attempt < retries:
                    wait_time = RETRY_DELAY * (2 ** (attempt - 1))
                    print(f"     ⚠️  Attempt {attempt} failed (HTTP {status_code} - Server error), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"     ❌ Failed after {retries} attempts: HTTP {status_code}")
                    return None
            else:
                # 4xx errors - client errors, usually shouldn't retry
                print(f"     ❌ HTTP {status_code} - Client error, not retrying")
                return None
        except requests.exceptions.RequestException as e:
            if session:
                session.close()
            if attempt < retries:
                wait_time = RETRY_DELAY * (2 ** (attempt - 1))
                print(f"     ⚠️  Attempt {attempt} failed (network error), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"     ❌ Failed after {retries} attempts: {str(e)[:100]}")
                return None
        except Exception as e:
            if session:
                session.close()
            if attempt < retries:
                wait_time = RETRY_DELAY * (2 ** (attempt - 1))
                print(f"     ⚠️  Attempt {attempt} failed (unexpected error), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"     ❌ Failed after {retries} attempts: {str(e)[:100]}")
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

