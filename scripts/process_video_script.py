"""
Process structured video script JSON and generate all assets.
This replaces the summarizer workflow with a direct script format.
"""
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_FILE = "input/video_script.json"
CONFIG_FILE = "subtitle_config.json"
OUTPUT_DIR = "output"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
SUB_DIR = os.path.join(OUTPUT_DIR, "subtitles")
CLIPS_DIR = os.path.join(OUTPUT_DIR, "video_clips")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

def load_subtitle_config():
    """Load subtitle configuration from JSON file."""
    if not os.path.exists(CONFIG_FILE):
        print(f"⚠️  Config file not found: {CONFIG_FILE}, using defaults")
        return get_default_config()
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_default_config():
    """Return default configuration if config file doesn't exist."""
    return {
        "font": {
            "name": "Game of Thrones",
            "file": "Game of Thrones.ttf"
        },
        "highlighted_word": {
            "font_size": 48,
            "text_color": "#FFFFFF",
            "background_color": "#000000",
            "background_transparency": 176,
            "outline_color": "#000000",
            "border_thickness": 12,
            "font_spacing": 6,
            "bold": True
        },
        "normal_word": {
            "font_size": 36,
            "text_color": "#FFFFFF",
            "outline_color": "#000000",
            "border_thickness": 4,
            "font_spacing": 6,
            "bold": True
        },
        "positioning": {
            "alignment": 2,
            "margin_left": 40,
            "margin_right": 40,
            "margin_vertical": 60
        },
        "display": {
            "max_words": 3,
            "word_separator": " "
        }
    }

def hex_to_ass_color(hex_color, alpha=0):
    """Convert hex color (#RRGGBB) to ASS format for style definitions (&HAABBGGRR).
    ASS uses BGR format with alpha channel for style definitions.
    Note: For ASS, alpha is inverted: 0x00 = opaque, 0xFF = transparent.
    Parameter alpha: Standard alpha where 0 = fully opaque, 255 = fully transparent
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # ASS style format: &HAABBGGRR (Alpha, Blue, Green, Red)
        # Alpha is inverted: 0x00 = opaque, 0xFF = transparent
        # Standard alpha: 0 = opaque, 255 = transparent
        # ASS alpha: 0x00 = opaque, 0xFF = transparent
        # So we use alpha directly: 0 -> 0x00 (opaque), 255 -> 0xFF (transparent)
        ass_alpha = alpha  # Direct mapping works: 0=opaque, 255=transparent
        return f"&H{ass_alpha:02X}{b:02X}{g:02X}{r:02X}"
    return "&H00FFFFFF"  # Default to white (opaque: alpha=0x00)

def hex_to_ass_inline_color(hex_color):
    """Convert hex color (#RRGGBB) to ASS inline tag format (&HBBGGRR&).
    ASS inline tags use BGR format without alpha, and must end with &.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # ASS inline format: &HBBGGRR& (Blue, Green, Red, ending with &)
        return f"&H{b:02X}{g:02X}{r:02X}&"
    return "&HFFFFFF&"  # Default to white

def get_bold_value(bold, font_weight=None):
    """Convert boolean to ASS bold value. If font_weight is provided, use it for inline tags."""
    if font_weight is not None:
        return font_weight
    return 1 if bold else 0

def load_video_script():
    """Load the video script JSON file and automatically ensure promo scene is at the end."""
    if not os.path.exists(SCRIPT_FILE):
        raise FileNotFoundError(f"Video script not found: {SCRIPT_FILE}")
    
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    
    # Automatically ensure promo scene is at the end with correct settings
    scenes = script_data.get("scenes", [])
    promo_image_path = "input/channel-promo.png"
    promo_narration = "Anyway, Subscribe for more"
    
    # Remove any existing promo scenes (check by narration text)
    scenes = [s for s in scenes if s.get("narration", "").lower() != promo_narration.lower()]
    
    # Always add promo scene at the end with correct settings
    promo_scene = {
        "scene_number": len(scenes) + 1,
        "scene_type": "promo",
        "narration": promo_narration,
        "subtitle": "Subscribe for more",
        "image_prompt": promo_image_path,  # Use path to indicate it's a local file
        "duration": 4,
        "effect": "zoom_in"
    }
    scenes.append(promo_scene)
    script_data["scenes"] = scenes
    # Update total duration
    script_data["total_duration"] = sum(s.get("duration", 4) for s in scenes)
    
    return script_data

def generate_audio_for_scenes(scenes):
    """Generate TTS audio for each scene and concatenate."""
    # Import tts module
    import importlib.util
    tts_path = os.path.join(os.path.dirname(__file__), "tts.py")
    spec = importlib.util.spec_from_file_location("tts", tts_path)
    tts_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tts_module)
    call_pollinations_tts = tts_module.call_pollinations_tts
    
    print("\n🎤 Generating audio for all scenes...")
    os.makedirs(AUDIO_DIR, exist_ok=True)
    temp_dir = os.path.join(AUDIO_DIR, "temp_scenes")
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_files = []
    
    for i, scene in enumerate(scenes, 1):
        narration = scene["narration"]
        print(f"   🔊 Scene {i}: {narration[:50]}...")
        
        temp_audio = os.path.join(temp_dir, f"scene_{i}.mp3")
        try:
            call_pollinations_tts(narration, temp_audio)
            audio_files.append(temp_audio)
        except Exception as e:
            print(f"   ❌ Failed to generate audio for scene {i}: {e}")
            raise
    
    # Concatenate all audio files
    if len(audio_files) > 1:
        print(f"   🔗 Concatenating {len(audio_files)} audio files...")
        concat_list = os.path.join(temp_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for af in audio_files:
                abs_path = os.path.abspath(af)
                f.write(f"file '{abs_path}'\n")
        
        final_audio = os.path.join(AUDIO_DIR, "voice.mp3")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c", "copy", final_audio
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"   ✅ Final audio saved: {final_audio}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"   ⚠️  FFmpeg not available, using first scene audio")
            import shutil
            shutil.copy(audio_files[0], final_audio)
    else:
        import shutil
        final_audio = os.path.join(AUDIO_DIR, "voice.mp3")
        shutil.copy(audio_files[0], final_audio)
    
    # Don't cleanup temp_dir yet - clips need the audio durations
    # Cleanup will happen after clips are created
    # shutil.rmtree(temp_dir, ignore_errors=True)
    
    return final_audio

def crop_image_remove_bottom(image_path):
    """Crop image to remove bottom watermark area.
    If image is 576x1024, crops to 576x978 (removes 46 pixels from bottom).
    For other sizes, calculates proportionally: removes ~4.49% from bottom.
    """
    try:
        # Get image dimensions using ffprobe
        cmd_probe = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            image_path
        ]
        result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
        width, height = map(int, result.stdout.strip().split('x'))
        
        # Calculate pixels to remove from bottom
        # Target: 576x1024 -> 576x978 (remove 46 pixels = 4.49% of 1024)
        # For other sizes, use the same percentage
        pixels_to_remove = int(height * 0.0449)  # 4.49% of height
        new_height = height - pixels_to_remove
        
        print(f"      📐 Original: {width}x{height}, Cropping to: {width}x{new_height} (removing {pixels_to_remove}px from bottom)")
        
        # Crop from top, removing bottom portion
        # Crop filter: crop=width:height:x:y (x and y are top-left coordinates)
        # We keep the top portion, so x=0, y=0
        temp_path = image_path + ".temp.jpg"
        cmd_crop = [
            "ffmpeg", "-y",
            "-i", image_path,
            "-vf", f"crop={width}:{new_height}:0:0",
            "-q:v", "2",  # High quality
            temp_path
        ]
        result = subprocess.run(cmd_crop, capture_output=True, text=True, check=True)
        
        # Verify the cropped image was created and has correct dimensions
        if os.path.exists(temp_path):
            # Check dimensions of cropped image
            cmd_probe_temp = cmd_probe.copy()
            cmd_probe_temp[-1] = temp_path
            result_check = subprocess.run(cmd_probe_temp, capture_output=True, text=True, check=True)
            width_check, height_check = map(int, result_check.stdout.strip().split('x'))
            
            # Allow 1 pixel tolerance due to rounding differences
            if abs(height_check - new_height) <= 1:
                # Replace original with cropped version
                import shutil
                shutil.move(temp_path, image_path)
                print(f"      ✅ Successfully cropped to {width_check}x{height_check}")
                return True
            else:
                print(f"      ⚠️  Crop verification failed: expected {new_height}±1, got {height_check}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
        else:
            print(f"      ⚠️  Cropped image file was not created")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"      ❌ FFmpeg error cropping image {image_path}: {e.stderr if e.stderr else e}")
        return False
    except Exception as e:
        print(f"      ❌ Error cropping image {image_path}: {e}")
        return False

def generate_images_for_scenes(scenes):
    """Generate images for each scene."""
    # Import generate_images module
    import importlib.util
    import shutil
    img_path = os.path.join(os.path.dirname(__file__), "generate_images.py")
    spec = importlib.util.spec_from_file_location("generate_images", img_path)
    img_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(img_module)
    generate_image = img_module.generate_image
    
    print("\n🎨 Generating images for all scenes...")
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    image_files = []
    promo_image_path = "input/channel-promo.png"
    
    for i, scene in enumerate(scenes, 1):
        prompt = scene["image_prompt"]
        print(f"   🖼️  Scene {i}: {prompt[:60]}...")
        
        image_file = os.path.join(IMAGE_DIR, f"img_{i}.jpg")
        
        # Check if this is the promo scene (uses local image file)
        # Check if prompt is the promo image path or if it's a file path that exists
        is_promo_scene = (prompt == promo_image_path or 
                         prompt.endswith("channel-promo.png") or
                         (os.path.exists(prompt) and prompt.endswith((".png", ".jpg", ".jpeg"))))
        
        if is_promo_scene:
            # Use the actual file path (could be relative or absolute)
            source_image = promo_image_path if os.path.exists(promo_image_path) else prompt
            
            # Copy and process the promo image instead of generating
            try:
                if os.path.exists(source_image):
                    # Convert PNG to JPG and resize to 1080x1920 if needed
                    # Use FFmpeg to convert and ensure correct dimensions
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", source_image,
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                        "-q:v", "2",  # High quality
                        image_file
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    image_files.append(image_file)
                    print(f"      ✅ Copied and processed promo image: {image_file}")
                else:
                    print(f"      ⚠️  Promo image not found at {source_image}, skipping scene {i}")
            except Exception as e:
                print(f"      ⚠️  Error processing promo image for scene {i}: {e}")
                print(f"      Continuing with other images...")
        else:
            # Generate image using API
            try:
                path = generate_image(prompt, f"img_{i}.jpg")
                if path:
                    # Immediately crop to remove bottom watermark
                    print(f"      ✂️  Cropping image to remove watermark...")
                    crop_image_remove_bottom(path)
                    image_files.append(path)
                    print(f"      ✅ Saved and cropped {path}")
                else:
                    print(f"      ⚠️  Failed to generate image for scene {i}, will skip")
                    # Don't raise - continue with other images
            except Exception as e:
                print(f"      ⚠️  Error generating image for scene {i}: {e}")
                print(f"      Continuing with other images...")
            
            # Longer delay between requests to avoid rate limiting and server overload
            if i < len(scenes):
                delay = 5  # 5 second delay between image generations
                print(f"      ⏳ Waiting {delay}s before next image...")
                time.sleep(delay)
                # Don't raise - continue processing
    
    return image_files

def create_subtitles(scenes, word_timings=None):
    """Create SRT and ASS subtitles from scenes with their durations.
    If word_timings is provided, creates word-level highlighting subtitles.
    """
    print("\n📝 Creating subtitles...")
    os.makedirs(SUB_DIR, exist_ok=True)
    srt_file = os.path.join(SUB_DIR, "subtitles.srt")
    ass_file = os.path.join(SUB_DIR, "subtitles.ass")
    
    current_time = 0.0
    
    # Create SRT file (basic subtitles)
    with open(srt_file, "w", encoding="utf-8") as f:
        for idx, scene in enumerate(scenes, 1):
            duration = scene.get("duration", 4)
            start_time = current_time
            end_time = current_time + duration
            
            # Convert to SRT time format
            def seconds_to_srt_time(seconds):
                millis = int(round(seconds * 1000))
                hours = millis // (3600 * 1000)
                millis %= 3600 * 1000
                minutes = millis // (60 * 1000)
                millis %= 60 * 1000
                secs = millis // 1000
                millis %= 1000
                return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
            
            # IMPORTANT: Use narration for subtitles to match the audio
            # subtitle field is optional - we use narration to ensure audio and subtitles match
            subtitle_text = scene.get('narration', scene.get('subtitle', ''))
            f.write(f"{idx}\n")
            f.write(f"{seconds_to_srt_time(start_time)} --> {seconds_to_srt_time(end_time)}\n")
            f.write(f"{subtitle_text}\n\n")
            
            current_time = end_time
    
    # Create ASS file with beautiful styling and word-level highlighting
    # Try to get scene audio files for accurate duration calculation
    scene_audio_files = []
    temp_audio_dir = os.path.join(AUDIO_DIR, "temp_scenes")
    if os.path.exists(temp_audio_dir):
        for i in range(1, len(scenes) + 1):
            scene_audio = os.path.join(temp_audio_dir, f"scene_{i}.mp3")
            if os.path.exists(scene_audio):
                scene_audio_files.append(scene_audio)
            else:
                scene_audio_files.append(None)
    create_styled_ass_subtitles(scenes, word_timings, ass_file, scene_audio_files if scene_audio_files else None)
    
    print(f"   ✅ Subtitles saved: {srt_file}")
    print(f"   ✅ Styled subtitles saved: {ass_file}")
    return srt_file, ass_file

def get_audio_duration(audio_file):
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            audio_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None

def create_styled_ass_subtitles(scenes, word_timings, ass_file, scene_audio_files=None):
    """Create ASS subtitle file with beautiful styling and word-level highlighting."""
    
    # Load configuration
    config = load_subtitle_config()
    font_name = config["font"]["name"]
    style_config = config.get("style", {})
    pos = config["positioning"]
    display = config["display"]
    
    # Load style settings
    font_size = style_config.get("font_size", 72)
    primary_color = style_config.get("primary_color", "#FFFFFF")
    secondary_color = style_config.get("secondary_color", "#00FF00")
    outline_color = style_config.get("outline_color", "#000000")
    outline_thickness = style_config.get("outline_thickness", 5)
    shadow = style_config.get("shadow", 0)
    bold = style_config.get("bold", True)
    letter_spacing = style_config.get("letter_spacing", -2)  # Negative = tighter letters
    
    # Add padding inside the black background by increasing outline thickness
    # The outline value in BorderStyle=3 controls the padding inside the box
    background_padding = 20  # Padding in pixels inside the black background box
    border_style = style_config.get("border_style", 1)
    
    # Load subtitle background settings (separate from style)
    subtitle_bg = config.get("subtitle_background", {})
    bg_enabled = subtitle_bg.get("enabled", True)
    bg_color = subtitle_bg.get("color", "#000000") if bg_enabled else "#000000"
    bg_transparency = subtitle_bg.get("transparency", 255) if bg_enabled else 0
    
    # Load line spacing and transition settings
    line_spacing = display.get("line_spacing", 10)  # Line spacing in pixels
    transitions = config.get("transitions", {})
    fade_enabled = transitions.get("fade_enabled", True)
    fade_in_ms = transitions.get("fade_in_duration", 200)
    fade_out_ms = transitions.get("fade_out_duration", 200)
    
    # Convert colors to ASS format (for style definitions)
    # Note: ASS alpha is inverted: 0x00 = opaque, 0xFF = transparent
    # For primary/secondary/outline, we want fully opaque (alpha=0x00 in ASS = 0x00)
    primary_color_style = hex_to_ass_color(primary_color, alpha=0)  # Fully opaque (0x00 in ASS)
    secondary_color_style = hex_to_ass_color(secondary_color, alpha=0)  # Fully opaque (0x00 in ASS)
    outline_color_style = hex_to_ass_color(outline_color, alpha=0)  # Fully opaque (0x00 in ASS)
    # Background transparency: In ASS, BackColour alpha is inverted
    # bg_transparency: 0 = transparent, 255 = fully opaque
    # ASS alpha: 0x00 = opaque, 0xFF = transparent
    # So if bg_transparency=255 (opaque), we want 0x00 in ASS
    # If bg_transparency=0 (transparent), we want 0xFF in ASS
    # Convert: ass_alpha = 255 - bg_transparency
    bg_alpha = (255 - bg_transparency) if bg_enabled else 255  # 255 = transparent if disabled
    bg_color_style = hex_to_ass_color(bg_color, alpha=bg_alpha)
    
    # Bold value: -1 for bold, 0 for not bold
    bold_value = -1 if bold else 0
    
    # ASS file header with styles - using proper format matching standard
    # Note: Spacing field is for character spacing, not line spacing
    # Line spacing will be handled via inline tags
    ass_content = f"""[Script Info]
; Generated for vertical/shorts style captions
Title: YouTube Shorts Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 1

[V4+ Styles]
; PrimaryColour  = base text (white)
; SecondaryColour = karaoke highlight (green)
; OutlineColour  = black border
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MATRIX_CAPTION,{font_name},{font_size},{primary_color_style},{secondary_color_style},{outline_color_style},{bg_color_style},{bold_value},0,0,0,100,100,{letter_spacing},0,3,{background_padding},{shadow},{pos["alignment"]},{pos["margin_left"]},{pos["margin_right"]},{pos["margin_vertical"]},0

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    
    def seconds_to_ass_time(seconds):
        """Convert seconds to ASS time format (H:MM:SS.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    # Calculate actual scene boundaries
    # Priority: 1) Actual audio file durations, 2) Word timings, 3) JSON durations
    scene_boundaries = []
    current_time = 0.0
    
    if scene_audio_files:
        # Use actual audio file durations (most accurate)
        for i, audio_file in enumerate(scene_audio_files):
            if os.path.exists(audio_file):
                duration = get_audio_duration(audio_file)
                if duration:
                    scene_boundaries.append((current_time, current_time + duration))
                    current_time += duration
                    continue
            # Fallback to JSON duration if audio file not found
            duration = scenes[i].get("duration", 4) if i < len(scenes) else 4
            scene_boundaries.append((current_time, current_time + duration))
            current_time += duration
        
        # For the last scene, extend boundary to include all remaining words if we have word timings
        if word_timings and len(word_timings) > 0 and len(scene_boundaries) > 0:
            last_word_end = word_timings[-1][2]  # End time of the very last word
            last_scene_start, last_scene_end = scene_boundaries[-1]
            # Extend last scene to include the last word
            if last_word_end > last_scene_end:
                scene_boundaries[-1] = (last_scene_start, last_word_end)
    elif word_timings and len(word_timings) > 0:
        # Use word timings to determine scene boundaries
        # Match words to scenes by counting words per scene narration
        word_idx = 0
        
        for scene_idx, scene in enumerate(scenes):
            scene_start = current_time
            scene_narration_words = scene["narration"].split()
            words_collected = 0
            last_word_end = scene_start
            
            # Collect words for this scene based on word count matching narration
            # Include ALL words that belong to this scene's narration
            while word_idx < len(word_timings) and words_collected < len(scene_narration_words):
                word, word_start, word_end = word_timings[word_idx]
                # Only collect if this word hasn't been assigned to a previous scene
                if word_start >= scene_start:
                    words_collected += 1
                    last_word_end = word_end
                    word_idx += 1
                else:
                    # This word was already processed, skip it
                    word_idx += 1
            
            # If we collected fewer words than expected, continue collecting until we find the next scene's start
            # This handles cases where transcription has more words or timing differences
            if words_collected < len(scene_narration_words) and word_idx < len(word_timings):
                # Try to collect a few more words to ensure we get the complete sentence
                # Stop when we've collected enough or when we reach the next scene's expected start
                expected_next_start = scene_start + scene.get("duration", 4)
                while word_idx < len(word_timings):
                    word, word_start, word_end = word_timings[word_idx]
                    # If word starts before expected next scene, include it
                    if word_start < expected_next_start:
                        words_collected += 1
                        last_word_end = word_end
                        word_idx += 1
                    else:
                        break
            
            # Scene ends when its last word ends, or use JSON duration as fallback
            # Add a small buffer to ensure we capture the complete last word
            if words_collected > 0:
                scene_end = last_word_end + 0.1  # Small buffer to ensure last word is fully captured
            else:
                scene_end = scene_start + scene.get("duration", 4)
            scene_boundaries.append((scene_start, scene_end))
            current_time = scene_end
    else:
        # Fallback: use JSON durations
        for scene in scenes:
            duration = scene.get("duration", 4)
            scene_boundaries.append((current_time, current_time + duration))
            current_time += duration
    
    # Load config for display settings
    display = config["display"]
    max_words = display["max_words"]
    word_separator = display["word_separator"]
    num_lines = display.get("lines", 1)  # Number of lines (1 or 2)
    # line_spacing already loaded above
    
    # Helper function to add fade transition to text
    def add_fade_transition(text):
        """Add fade transition to subtitle text if enabled."""
        if fade_enabled:
            return f"{{\\fad({fade_in_ms},{fade_out_ms})}}{text}"
        return text
    
    # Helper function to convert seconds to centiseconds for \k tags
    def seconds_to_centiseconds(seconds):
        """Convert seconds to centiseconds for karaoke \k tags."""
        return int(round(seconds * 100))
    
    word_index = 0
    
    for idx, scene in enumerate(scenes, 1):
        # Use calculated scene boundaries from actual word timings
        # CRITICAL: Store original boundaries and use them strictly for non-last scenes
        original_scene_start, original_scene_end = scene_boundaries[idx - 1]
        scene_start = original_scene_start
        scene_end = original_scene_end
        # IMPORTANT: Use narration for subtitles to match the audio (word timings are based on narration)
        # subtitle field is optional - if provided and different, it will cause word mismatch
        # So we always use narration to ensure audio and subtitles match
        subtitle_text = scene.get('narration', scene.get('subtitle', ''))
        
        # Get next scene's start time to ensure strict boundaries (prevent overlap)
        next_scene_start = scene_boundaries[idx][0] if idx < len(scene_boundaries) else float('inf')
        
        # If we have word timings, create word-level highlighting
        if word_timings and word_index < len(word_timings):
            words_in_scene = []
            seen_word_indices = set()  # Track which word indices we've already added to prevent duplicates
            
            # Collect words that belong STRICTLY to this scene only
            # For the last scene, be more lenient to include all words
            is_last_scene = (idx == len(scenes))
            
            # Debug: Print scene boundaries for troubleshooting
            # print(f"Scene {idx}: {scene_start:.2f}s - {scene_end:.2f}s")
            
            # Collect words that belong STRICTLY to this scene only
            # Use a small buffer (0.05s) to account for timing precision, but be very strict
            boundary_buffer = 0.05  # Small buffer for timing precision
            
            while word_index < len(word_timings):
                # Skip if we've already processed this word index
                if word_index in seen_word_indices:
                    word_index += 1
                    continue
                
                word, word_start, word_end = word_timings[word_index]
                
                if is_last_scene:
                    # For the last scene, include all words that start within the scene
                    # This ensures we capture all remaining words
                    if word_start >= scene_start - boundary_buffer:
                        words_in_scene.append((word, word_start, word_end))
                        seen_word_indices.add(word_index)
                        word_index += 1
                    else:
                        # Word is before scene start, skip it
                        word_index += 1
                else:
                    # For non-last scenes, include words that START within the scene
                    # This ensures we capture all words, even if they extend slightly beyond scene_end
                    # Word must:
                    # 1. Start at or after scene_start (with small buffer for precision)
                    # 2. Start before next scene starts (this is the key - include if word starts in this scene)
                    # 3. Allow words to extend slightly beyond scene_end to capture complete sentences
                    next_scene_start = scene_boundaries[idx][0] if idx < len(scene_boundaries) else float('inf')
                    
                    # Include word if it starts within this scene (even if it extends beyond scene_end)
                    # This ensures we capture all words, especially at the end of sentences
                    word_starts_in_scene = word_start >= (scene_start - boundary_buffer) and word_start < next_scene_start
                    
                    if word_starts_in_scene:
                        # Word starts in this scene - include it even if it extends beyond scene_end
                        words_in_scene.append((word, word_start, word_end))
                        seen_word_indices.add(word_index)
                        word_index += 1
                    elif word_start >= next_scene_start:
                        # This word starts in the next scene, stop collecting for this scene
                        break
                    else:
                        # Word is before scene start, skip it
                        word_index += 1
            
            # Create word-by-word subtitles showing only one word at a time with random size and color
            if words_in_scene:
                # Extend scene_end to include the last word's end time for ALL scenes
                # This ensures we capture complete sentences, especially the final words
                last_word_end_time = words_in_scene[-1][2]  # Get end time of last word
                scene_end = max(scene_end, last_word_end_time + 0.1)  # Extend scene to include last word with buffer
                
                # Define colors: yellow, white, red
                colors = ["#FFFF00", "#FFFFFF", "#FF0000"]  # Yellow, White, Red
                
                # Define two font sizes (base size and larger size)
                base_font_size = font_size
                larger_font_size = int(font_size * 1.3)  # 30% larger
                
                # Calculate fixed Y position to lock vertical alignment
                # For 1920px height video with margin_vertical from bottom, calculate center X and Y
                # Alignment 2 = center-bottom, so Y position = height - margin_vertical
                video_height = 1920
                fixed_y = video_height - pos["margin_vertical"]
                fixed_x = 540  # Center X for 1080px width
                
                # Create dialogue entries for each word - show only one word at a time
                for i, (current_word, word_start, word_end) in enumerate(words_in_scene):
                    # Randomly select color and size for this word
                    selected_color = random.choice(colors)
                    selected_size = random.choice([base_font_size, larger_font_size])
                    
                    # Convert selected color to inline format
                    selected_color_inline = hex_to_ass_inline_color(selected_color)
                    
                    # Build text with inline styling - only the current word
                    w_upper = current_word.upper()
                    
                    # Apply random color and size to the word
                    # \1c for text color, \fs for font size
                    # Use \pos to lock the position so all words appear at the same vertical position
                    # regardless of font size changes - this prevents words from appearing at different heights
                    full_text = f"{{\\pos({fixed_x},{fixed_y})\\1c{selected_color_inline}\\fs{selected_size}}}{w_upper}{{\\r}}"
                    
                    # Determine timing for this dialogue entry
                    # Show from start of current word to end of current word
                    dialogue_start = word_start  # Start when current word starts
                    dialogue_end = word_end      # End when current word ends
                    
                    # Ensure timing doesn't exceed scene boundaries, but allow slight extension for last word
                    dialogue_start = max(dialogue_start, scene_start)
                    # For the last word in a scene, allow it to extend slightly beyond scene_end to ensure it's fully visible
                    if i == len(words_in_scene) - 1:
                        dialogue_end = max(dialogue_end, scene_end)  # Allow last word to extend
                    else:
                        dialogue_end = min(dialogue_end, scene_end)
                    
                    # Add fade transition
                    full_text_with_fade = add_fade_transition(full_text)
                    ass_content += f"Dialogue: 0,{seconds_to_ass_time(dialogue_start)},{seconds_to_ass_time(dialogue_end)},MATRIX_CAPTION,,0,0,0,,{full_text_with_fade}\n"
            else:
                # Fallback to simple subtitle (no word timings)
                # Limit to max_words for single line, capitalize
                words = subtitle_text.split()
                display_words = words[:max_words] if len(words) > max_words else words
                
                # Single line
                display_text = word_separator.join([w.upper() for w in display_words])
                
                # Add fade transition to subtitle text
                display_text_with_fade = add_fade_transition(display_text)
                ass_content += f"Dialogue: 0,{seconds_to_ass_time(scene_start)},{seconds_to_ass_time(scene_end)},MATRIX_CAPTION,,0,0,0,,{display_text_with_fade}\n"
        else:
            # No word timings, use simple subtitle
            # Single line - limit to max_words
            words = subtitle_text.split()
            display_words = words[:max_words] if len(words) > max_words else words
            
            # Create simple text (no karaoke since we don't have word timings)
            styled_text = word_separator.join([w.upper() for w in display_words])
            
            styled_text_with_fade = add_fade_transition(styled_text)
            ass_content += f"Dialogue: 0,{seconds_to_ass_time(scene_start)},{seconds_to_ass_time(scene_end)},MATRIX_CAPTION,,0,0,0,,{styled_text_with_fade}\n"
    
    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(ass_content)

def main():
    """Main function to process video script."""
    print("🎬 Processing Video Script")
    print("=" * 50)
    
    # Load script
    script_data = load_video_script()
    print(f"📄 Title: {script_data['title']}")
    print(f"📊 Scenes: {len(script_data['scenes'])}")
    print(f"⏱️  Total Duration: {script_data.get('total_duration', 'N/A')} seconds")
    
    scenes = script_data["scenes"]
    
    # Generate all assets
    try:
        # 1. Generate audio
        audio_file = generate_audio_for_scenes(scenes)
        
        # 2. Generate images
        image_files = generate_images_for_scenes(scenes)
        
        # 3. Transcribe audio for word-level timing
        print("\n📝 Transcribing audio for word-level subtitle timing...")
        try:
            import importlib.util
            transcribe_path = os.path.join(os.path.dirname(__file__), "transcribe_audio.py")
            spec = importlib.util.spec_from_file_location("transcribe_audio", transcribe_path)
            transcribe_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(transcribe_module)
            
            transcription_result = transcribe_module.transcribe_audio(audio_file)
            word_timings = transcribe_module.extract_word_timings(transcription_result)
            print(f"   ✅ Extracted {len(word_timings)} words with timings")
        except Exception as e:
            print(f"   ⚠️  Transcription failed: {e}")
            print(f"   Using scene-based subtitles instead...")
            word_timings = None
        
        # 4. Create subtitles (with word-level timing if available)
        srt_file, ass_file = create_subtitles(scenes, word_timings)
        
        print("\n✅ All assets generated successfully!")
        print(f"   🎤 Audio: {audio_file}")
        print(f"   🖼️  Images: {len(image_files)} files (out of {len(scenes)} scenes)")
        if len(image_files) < len(scenes):
            print(f"   ⚠️  Warning: {len(scenes) - len(image_files)} images failed to generate")
        print(f"   📝 Subtitles: {srt_file}")
        print("\n💡 Next steps:")
        print("   - Run: python3 scripts/create_clips_from_script.py")
        print("   - Then: python3 scripts/combine_final.py")
        
    except Exception as e:
        print(f"\n❌ Error processing video script: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

