import os
import json
import subprocess

VOICE_FILE = "output/audio/voice.mp3"
BGM_FILE = "bgm/bgm.mp3"
MIXED_AUDIO = "output/audio/mix.mp3"
JOINED_VIDEO = "output/video_clips/joined_video.mp4"
SRT_FILE = "output/subtitles/subtitles.srt"
ASS_FILE = "output/subtitles/subtitles.ass"
WATERMARK_FILE = "input/watermark.png"
FINAL_DIR = "output/final"
FINAL_VIDEO = os.path.join(FINAL_DIR, "final_short.mp4")

def mix_audio():
    os.makedirs(os.path.dirname(MIXED_AUDIO), exist_ok=True)
    if not os.path.exists(VOICE_FILE):
        raise FileNotFoundError(VOICE_FILE)
    if not os.path.exists(BGM_FILE):
        raise FileNotFoundError(BGM_FILE)

    print("🎧 Mixing voice and background music...")
    # Convert output to MP3 properly - use libmp3lame codec
    cmd = [
        "ffmpeg", "-y",
        "-i", VOICE_FILE,
        "-i", BGM_FILE,
        "-filter_complex",
        "[0:a]volume=1.0,aresample=44100[a0];"
        "[1:a]volume=0.25,aresample=44100[a1];"
        "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "[aout]",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        MIXED_AUDIO
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✅ Mixed audio written to {MIXED_AUDIO}")

def mux_video():
    os.makedirs(FINAL_DIR, exist_ok=True)
    if not os.path.exists(JOINED_VIDEO):
        raise FileNotFoundError(JOINED_VIDEO)
    if not os.path.exists(MIXED_AUDIO):
        raise FileNotFoundError(MIXED_AUDIO)
    if not os.path.exists(SRT_FILE):
        raise FileNotFoundError(SRT_FILE)

    print("📽  Combining video + mixed audio + styled subtitles...")
    
    # Use ASS file if available (for styled subtitles), otherwise fall back to SRT
    subtitle_file = ASS_FILE if os.path.exists(ASS_FILE) else SRT_FILE
    subtitle_type = "ASS" if os.path.exists(ASS_FILE) else "SRT"
    print(f"   Using {subtitle_type} subtitles: {subtitle_file}")
    
    # Load subtitle config
    config_file = "subtitle_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        # Default config
        config = {
            "font": {"name": "Game of Thrones", "file": "Game of Thrones.ttf"},
            "normal_word": {"font_size": 36},
            "positioning": {"alignment": 2, "margin_left": 40, "margin_right": 40, "margin_vertical": 60},
            "watermark": {
                "enabled": True,
                "file": "input/watermark.png",
                "position": {"location": "top-right", "margin_x": 20, "margin_y": 20},
                "size": {"width": 200, "mode": "auto"},
                "opacity": {"value": 0.5}
            }
        }
    
    # Get absolute path to font file and configure subtitle filter
    font_file = config["font"]["file"]
    font_name = config["font"]["name"]
    font_size = config["normal_word"]["font_size"]
    pos = config["positioning"]
    
    font_path = os.path.abspath(font_file)
    if os.path.exists(font_path):
        # Use fontsdir to help FFmpeg find the font
        subtitle_filter = f"subtitles={os.path.abspath(subtitle_file)}:fontsdir={os.path.dirname(font_path)}:force_style='FontName={font_name},FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H0000FF00,BackColour=&H80000000,BorderStyle=1,Outline=3,Shadow=3,Alignment={pos['alignment']},MarginL={pos['margin_left']},MarginR={pos['margin_right']},MarginV={pos['margin_vertical']},Bold=1'"
    else:
        # Fallback if font not found - still try font name (might be in system fonts)
        subtitle_filter = f"subtitles={os.path.abspath(subtitle_file)}:force_style='FontName={font_name},FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H0000FF00,BackColour=&H80000000,BorderStyle=1,Outline=3,Shadow=3,Alignment={pos['alignment']},MarginL={pos['margin_left']},MarginR={pos['margin_right']},MarginV={pos['margin_vertical']},Bold=1'"
    
    # Get video and audio durations to ensure we preserve all content
    def get_duration(file_path):
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except:
            return None
    
    # Use local variable to avoid scoping issues
    video_file = JOINED_VIDEO
    
    video_duration = get_duration(video_file)
    audio_duration = get_duration(MIXED_AUDIO)
    
    if video_duration and audio_duration:
        print(f"   Video duration: {video_duration:.2f}s, Audio duration: {audio_duration:.2f}s")
        duration_diff = audio_duration - video_duration
        if duration_diff > 0.1:  # If audio is significantly longer
            print(f"   ⚠️  Audio is {duration_diff:.2f}s longer than video")
            print(f"   📹 Extending video to match audio duration...")
            # Extend video by looping the last frame to match audio
            # Create extended video in the same directory as the original
            clips_dir = os.path.dirname(JOINED_VIDEO)
            extended_video = os.path.join(clips_dir, "extended_video.mp4")
            cmd_extend = [
                "ffmpeg", "-y",
                "-i", video_file,
                "-vf", f"tpad=stop_mode=clone:stop_duration={duration_diff:.3f}",
                "-c:v", "libx264",
                "-r", "30",
                extended_video
            ]
            subprocess.run(cmd_extend, check=True, capture_output=True)
            video_file = extended_video  # Use extended video
            print(f"   ✅ Video extended to match audio")
    
    # Build FFmpeg command with watermark if available
    watermark_config = config.get("watermark", {})
    watermark_enabled = watermark_config.get("enabled", True)
    watermark_file = watermark_config.get("file", WATERMARK_FILE)
    watermark_path = os.path.abspath(watermark_file)
    
    if watermark_enabled and os.path.exists(watermark_path):
        # Get watermark settings from config
        position_config = watermark_config.get("position", {})
        size_config = watermark_config.get("size", {})
        opacity_config = watermark_config.get("opacity", {})
        
        location = position_config.get("location", "top-right")
        margin_x = position_config.get("margin_x", 20)
        margin_y = position_config.get("margin_y", 20)
        
        # Calculate overlay position based on location
        if location == "top-right":
            overlay_pos = f"W-w-{margin_x}:{margin_y}"
        elif location == "top-left":
            overlay_pos = f"{margin_x}:{margin_y}"
        elif location == "bottom-right":
            overlay_pos = f"W-w-{margin_x}:H-h-{margin_y}"
        elif location == "bottom-left":
            overlay_pos = f"{margin_x}:H-h-{margin_y}"
        else:
            overlay_pos = f"W-w-{margin_x}:{margin_y}"  # Default to top-right
        
        # Get watermark size
        size_mode = size_config.get("mode", "auto")
        size_width = size_config.get("width", 200)
        
        if size_mode == "auto" and size_width:
            # Scale to specified width, maintain aspect ratio
            scale_filter = f"scale={size_width}:-1"
        else:
            # Auto scale (maintain aspect ratio, no specific size)
            scale_filter = "scale=-1:-1"
        
        # Get opacity (0.0 to 1.0)
        opacity = opacity_config.get("value", 0.5)
        
        print(f"   🎨 Adding watermark at {location}: {watermark_file}")
        print(f"      Size: {size_width}px width (auto), Opacity: {opacity:.1%}")
        
        # Video with watermark: need to add watermark as input and use filter_complex
        # Filter chain: apply subtitles to video, scale watermark, apply opacity, then overlay
        # Use format=rgba and geq to modify alpha channel for transparency
        # Format: [1:v]scale=W:-1,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*OPACITY'[wm];[v0][wm]overlay=POS[v]
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-i", watermark_path,
            "-i", MIXED_AUDIO,
            "-filter_complex",
            f"[0:v]{subtitle_filter}[v0];[1:v]{scale_filter},format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*{opacity}'[wm];[v0][wm]overlay={overlay_pos}[v]",
            "-map", "[v]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            FINAL_VIDEO
        ]
    else:
        # Video without watermark: simple subtitle filter
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-i", MIXED_AUDIO,
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",  # Match the shorter stream (should be same now)
            FINAL_VIDEO
        ]
    
    subprocess.run(cmd, check=True)
    print(f"✅ Final video with styled subtitles and watermark written to {FINAL_VIDEO}")

def main():
    mix_audio()
    mux_video()

if __name__ == "__main__":
    main()

