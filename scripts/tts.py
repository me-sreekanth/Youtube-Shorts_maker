import os
import requests

SCRIPT_FILE = "output/short_script.txt"
AUDIO_DIR = "output/audio"
VOICE_FILE = os.path.join(AUDIO_DIR, "voice.mp3")
POLLINATIONS_TTS_ENDPOINT = "https://text.pollinations.ai"

def call_pollinations_tts(text: str, out_path: str):
    """
    Uses Deepgram API for text-to-speech.
    For long text, splits into sentences and concatenates audio files.
    """
    import subprocess
    
    # Deepgram API configuration
    DEEPGRAM_API_KEY = "d85755dcff46bcce90b27465e544ab45d94aa141"
    DEEPGRAM_API_URL = "https://api.deepgram.com/v1/speak"
    DEEPGRAM_MODEL = "aura-2-odysseus-en"
    
    # Split text into sentences (by periods, exclamation, question marks)
    import re
    sentences = re.split(r'([.!?]+\s*)', text)
    # Rejoin sentences with their punctuation
    parts = []
    for i in range(0, len(sentences)-1, 2):
        if i+1 < len(sentences):
            parts.append(sentences[i] + sentences[i+1])
        else:
            parts.append(sentences[i])
    parts = [p.strip() for p in parts if p.strip()]
    
    # If text is short enough, use as single request
    if len(text) < 500:
        parts = [text]
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    temp_dir = os.path.join(os.path.dirname(out_path), "temp_audio")
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_files = []
    
    print(f"   🔊 Generating TTS with Deepgram for {len(parts)} part(s)...")
    
    for i, part in enumerate(parts, 1):
        print(f"   🔄 Part {i}/{len(parts)}: {part[:50]}...")
        
        try:
            # Make POST request to Deepgram API
            url = f"{DEEPGRAM_API_URL}?model={DEEPGRAM_MODEL}"
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "text/plain"
            }
            
            resp = requests.post(url, headers=headers, data=part, timeout=120)
            resp.raise_for_status()
            
            # Check if response is audio
            if len(resp.content) < 1000:
                raise ValueError(f"Response too small ({len(resp.content)} bytes)")
            
            temp_file = os.path.join(temp_dir, f"part_{i}.mp3")
            with open(temp_file, "wb") as f:
                f.write(resp.content)
            
            # Verify file was created
            if os.path.getsize(temp_file) < 1000:
                raise ValueError(f"Generated audio file too small ({os.path.getsize(temp_file)} bytes)")
            
            audio_files.append(temp_file)
            print(f"   ✅ Part {i} saved: {os.path.getsize(temp_file)} bytes")
            
        except Exception as e:
            print(f"   ❌ Failed to generate part {i}: {e}")
            # Fallback to gTTS if Deepgram fails
            print(f"   🔄 Falling back to gTTS...")
            try:
                from gtts import gTTS
                tts = gTTS(text=part, lang='en', slow=False)
                temp_file = os.path.join(temp_dir, f"part_{i}.mp3")
                tts.save(temp_file)
                if os.path.getsize(temp_file) < 1000:
                    raise ValueError(f"gTTS file too small")
                audio_files.append(temp_file)
                print(f"   ✅ Part {i} saved using gTTS: {os.path.getsize(temp_file)} bytes")
            except Exception as gtts_error:
                print(f"   ❌ gTTS fallback also failed: {gtts_error}")
                raise
    
    # Concatenate all audio files
    if len(audio_files) > 1:
        print(f"   🔗 Concatenating {len(audio_files)} audio parts...")
        # Create concat list for ffmpeg
        concat_list = os.path.join(temp_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for af in audio_files:
                abs_path = os.path.abspath(af)
                f.write(f"file '{abs_path}'\n")
        
        # Use ffmpeg to concatenate
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c", "copy", out_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"   ✅ Audio concatenated")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # If ffmpeg not available, just use first file
            print(f"   ⚠️  FFmpeg not available, using first part only")
            import shutil
            shutil.copy(audio_files[0], out_path)
    else:
        # Single file, just copy
        import shutil
        shutil.copy(audio_files[0], out_path)
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Verify final file
    file_size = os.path.getsize(out_path)
    if file_size < 1000:
        raise ValueError(f"Final audio file too small ({file_size} bytes)")
    
    print(f"   ✅ Final audio saved: {file_size} bytes")

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ output/short_script.txt not found. Run summarizer first.")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.read().splitlines() if l.strip()]

    if not lines:
        print("❌ short_script.txt is empty")
        return

    # Join lines with spaces for TTS (not newlines)
    script_text = " ".join(lines)
    
    print(f"🎤 Generating TTS via Deepgram...")
    print(f"   Text length: {len(script_text)} characters")
    print(f"   Number of lines: {len(lines)}")
    
    try:
        call_pollinations_tts(script_text, VOICE_FILE)
        print(f"✅ Voice saved to {VOICE_FILE}")
    except Exception as e:
        print(f"❌ Failed to generate TTS: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check if Pollinations TTS API is working")
        print("   - Try visiting: https://text.pollinations.ai?text=Hello&model=openai-audio&voice=nova")
        raise

if __name__ == "__main__":
    main()

