"""
Process structured video script JSON and generate all assets.
This replaces the summarizer workflow with a direct script format.
"""
import json
import os
import subprocess
import sys
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

def hex_to_ass_color(hex_color, alpha=255):
    """Convert hex color (#RRGGBB) to ASS format for style definitions (&HAABBGGRR).
    ASS uses BGR format with alpha channel for style definitions.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # ASS style format: &HAABBGGRR (Alpha, Blue, Green, Red)
        return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"
    return "&H00FFFFFF"  # Default to white

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

def get_bold_value(bold):
    """Convert boolean to ASS bold value."""
    return 1 if bold else 0

def load_video_script():
    """Load the video script JSON file."""
    if not os.path.exists(SCRIPT_FILE):
        raise FileNotFoundError(f"Video script not found: {SCRIPT_FILE}")
    
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

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
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    return final_audio

def generate_images_for_scenes(scenes):
    """Generate images for each scene."""
    # Import generate_images module
    import importlib.util
    img_path = os.path.join(os.path.dirname(__file__), "generate_images.py")
    spec = importlib.util.spec_from_file_location("generate_images", img_path)
    img_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(img_module)
    generate_image = img_module.generate_image
    
    print("\n🎨 Generating images for all scenes...")
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    image_files = []
    
    for i, scene in enumerate(scenes, 1):
        prompt = scene["image_prompt"]
        print(f"   🖼️  Scene {i}: {prompt[:60]}...")
        
        image_file = os.path.join(IMAGE_DIR, f"img_{i}.jpg")
        try:
            path = generate_image(prompt, f"img_{i}.jpg")
            if path:
                image_files.append(path)
                print(f"      ✅ Saved {path}")
            else:
                print(f"      ⚠️  Failed to generate image for scene {i}, will skip")
                # Don't raise - continue with other images
        except Exception as e:
            print(f"      ⚠️  Error generating image for scene {i}: {e}")
            print(f"      Continuing with other images...")
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
            
            f.write(f"{idx}\n")
            f.write(f"{seconds_to_srt_time(start_time)} --> {seconds_to_srt_time(end_time)}\n")
            f.write(f"{scene['subtitle']}\n\n")
            
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
    highlight = config["highlighted_word"]
    normal = config["normal_word"]
    pos = config["positioning"]
    display = config["display"]
    
    # Convert colors to ASS format (for style definitions)
    highlight_text_color_style = hex_to_ass_color(highlight["text_color"])
    highlight_bg_color = hex_to_ass_color(highlight["background_color"], highlight["background_transparency"])
    highlight_outline_color_style = hex_to_ass_color(highlight["outline_color"])
    normal_text_color_style = hex_to_ass_color(normal["text_color"])
    normal_outline_color_style = hex_to_ass_color(normal["outline_color"])
    
    # Convert colors to ASS inline tag format (for inline tags)
    highlight_text_color = hex_to_ass_inline_color(highlight["text_color"])
    highlight_outline_color = hex_to_ass_inline_color(highlight["outline_color"])
    normal_text_color = hex_to_ass_inline_color(normal["text_color"])
    normal_outline_color = hex_to_ass_inline_color(normal["outline_color"])
    
    # ASS file header with styles - using proper format matching standard
    ass_content = f"""[Script Info]
Title: YouTube Shorts Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
Collisions: Normal

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Highlight,{font_name},{normal["font_size"]},{highlight_text_color_style},&H000000FF,{highlight_outline_color_style},{highlight_bg_color},{get_bold_value(highlight["bold"])},0,0,0,100,100,0,0,3,{highlight["border_thickness"]},0,{pos["alignment"]},{pos["margin_left"]},{pos["margin_right"]},{pos["margin_vertical"]},1
Style: Normal,{font_name},{normal["font_size"]},{normal_text_color_style},&H000000FF,{normal_outline_color_style},&H80000000,{get_bold_value(normal["bold"])},0,0,0,100,100,0,0,1,{normal["border_thickness"]},{normal["border_thickness"]},{pos["alignment"]},{pos["margin_left"]},{pos["margin_right"]},{pos["margin_vertical"]},1

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
            
            # Scene ends when its last word ends, or use JSON duration as fallback
            if words_collected > 0:
                scene_end = last_word_end
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
    
    # Load config for inline styling
    config = load_subtitle_config()
    highlight = config["highlighted_word"]
    normal = config["normal_word"]
    display = config["display"]
    max_words = display["max_words"]
    word_separator = display["word_separator"]
    
    # Convert colors for inline tags (must use inline format with 6 hex digits + &)
    highlight_text_color = hex_to_ass_inline_color(highlight["text_color"])
    highlight_outline_color = hex_to_ass_inline_color(highlight["outline_color"])
    normal_text_color = hex_to_ass_inline_color(normal["text_color"])
    normal_outline_color = hex_to_ass_inline_color(normal["outline_color"])
    
    word_index = 0
    
    for idx, scene in enumerate(scenes, 1):
        # Use calculated scene boundaries from actual word timings
        scene_start, scene_end = scene_boundaries[idx - 1]
        subtitle_text = scene['subtitle']
        
        # If we have word timings, create word-level highlighting
        if word_timings and word_index < len(word_timings):
            words_in_scene = []
            # scene_start and scene_end are already set from scene_boundaries above
            
            # Collect words that fall strictly within this scene (not from next scene)
            # Only include words that start AND end within the scene boundaries
            # Use strict inequality to prevent boundary overlap
            while word_index < len(word_timings):
                word, word_start, word_end = word_timings[word_index]
                # Only include words that:
                # 1. Start at or after scene_start
                # 2. Start strictly before scene_end (not equal to or after)
                # 3. End strictly before or at scene_end
                if word_start >= scene_start and word_start < scene_end and word_end <= scene_end:
                    words_in_scene.append((word, word_start, word_end))
                    word_index += 1
                elif word_start >= scene_end:
                    # This word belongs to the next scene (starts at or after scene_end), stop collecting
                    break
                else:
                    # Word is before scene start or extends beyond scene end, skip it
                    word_index += 1
            
            # Create word-level highlighted subtitle with karaoke effect
            # Show only 3 words at a time, sliding window - ONLY from current scene
            if words_in_scene:
                # Create non-overlapping segments, one for each word
                for i, (word, word_start, word_end) in enumerate(words_in_scene):
                    # Determine segment end time (next word start or scene end)
                    # NEVER exceed the scene end time
                    if i < len(words_in_scene) - 1:
                        segment_end = min(words_in_scene[i + 1][1], scene_end)  # Next word start, but not beyond scene
                    else:
                        # Last word in scene - end at scene end, no overlap
                        segment_end = scene_end
                    
                    # Show only 3 words: current word, previous word (if exists), next word (if exists)
                    # BUT only from words_in_scene (current scene only)
                    # For the last word in scene, don't show a "next" word even if it exists
                    # Calculate window: [max(0, i-1), min(len(words_in_scene), i+2)]
                    # BUT if we're at the last word, only show up to the last word (don't try to show next)
                    window_start = max(0, i - 1)
                    if i == len(words_in_scene) - 1:
                        # Last word in scene - only show words up to and including this word
                        window_end = len(words_in_scene)  # Don't try to show next word
                    else:
                        window_end = min(len(words_in_scene), i + max_words - 1)  # Never go beyond current scene's words
                    
                    # Build the subtitle text with only words from current scene
                    text_parts = []
                    for j in range(window_start, window_end):
                        w, ws, we = words_in_scene[j]
                        # Capitalize the word
                        w_upper = w.upper()
                        if j == i:
                            # Current word being spoken - highlighted with background
                            # Use config values for styling
                            bold_tag = "\\b900" if highlight["bold"] else "\\b0"
                            text_parts.append(f"{{\\1c{highlight_text_color}\\3c{highlight_outline_color}\\bord{highlight['border_thickness']}\\shad0\\blur0{bold_tag}\\fs{highlight['font_size']}\\fsp{highlight['font_spacing']}}}{w_upper}")
                        else:
                            # Other words - normal styling
                            bold_tag = "\\b900" if normal["bold"] else "\\b0"
                            text_parts.append(f"{{\\1c{normal_text_color}\\3c{normal_outline_color}\\4c{normal_outline_color}\\bord{normal['border_thickness']}\\shad0\\blur0{bold_tag}\\fs{normal['font_size']}\\fsp{normal['font_spacing']}}}{w_upper}")
                    
                    # Join with configured separator between all words
                    full_text = word_separator.join(text_parts)
                    
                    # Create dialogue entry for this segment (non-overlapping)
                    # Use alignment 2 (bottom center) - no need for \pos, alignment handles it
                    # Ensure segment_end never exceeds scene_end - use scene_end as hard limit
                    # For the last word, end exactly at scene_end to prevent any overlap
                    if i == len(words_in_scene) - 1:
                        # Last word in scene - end exactly at scene boundary, no extension
                        final_segment_end = scene_end
                    else:
                        final_segment_end = min(segment_end, scene_end)
                    
                    ass_content += f"Dialogue: 0,{seconds_to_ass_time(word_start)},{seconds_to_ass_time(final_segment_end)},Highlight,,0,0,0,,{full_text}\n"
            else:
                # Fallback to simple subtitle
                # Limit to max_words and position at bottom center, capitalize
                words = subtitle_text.split()
                if len(words) > max_words:
                    display_text = word_separator.join([w.upper() for w in words[:max_words]])
                else:
                    display_text = word_separator.join([w.upper() for w in words])
                ass_content += f"Dialogue: 0,{seconds_to_ass_time(scene_start)},{seconds_to_ass_time(scene_end)},Normal,,0,0,0,,{display_text}\n"
        else:
            # No word timings, use simple subtitle with style
            # Create a styled version with background box effect
            # Split into words and show max max_words
            words = subtitle_text.split()
            if len(words) > max_words:
                # Show first max_words words
                display_words = word_separator.join(words[:max_words])
            else:
                display_words = subtitle_text
            
            # First word gets background with white text, rest white, all capitalized
            words_list = display_words.split()
            if len(words_list) > 0:
                styled_parts = []
                # First word: highlighted with background
                bold_tag = "\\b900" if highlight["bold"] else "\\b0"
                styled_parts.append(f"{{\\1c{highlight_text_color}\\3c{highlight_outline_color}\\bord{highlight['border_thickness']}\\shad0\\blur0{bold_tag}\\fs{highlight['font_size']}\\fsp{highlight['font_spacing']}}}{words_list[0].upper()}")
                for word in words_list[1:]:
                    # Other words: normal styling
                    bold_tag = "\\b900" if normal["bold"] else "\\b0"
                    styled_parts.append(f"{word_separator}{{\\1c{normal_text_color}\\3c{normal_outline_color}\\4c{normal_outline_color}\\bord{normal['border_thickness']}\\shad0\\blur0{bold_tag}\\fs{normal['font_size']}\\fsp{normal['font_spacing']}}}{word.upper()}")
                styled_text = "".join(styled_parts)
            else:
                bold_tag = "\\b900" if highlight["bold"] else "\\b0"
                styled_text = f"{{\\1c{highlight_text_color}\\3c{highlight_outline_color}\\bord{highlight['border_thickness']}\\shad0\\blur0{bold_tag}\\fs{highlight['font_size']}\\fsp{highlight['font_spacing']}}}{display_words.upper()}"
            ass_content += f"Dialogue: 0,{seconds_to_ass_time(scene_start)},{seconds_to_ass_time(scene_end)},Highlight,,0,0,0,,{styled_text}\n"
    
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

