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

def mix_audio():
    os.makedirs(os.path.dirname(MIXED_AUDIO), exist_ok=True)
    if not os.path.exists(VOICE_FILE):
        raise FileNotFoundError(VOICE_FILE)
    
    # Load video config for audio settings
    config_file = "video_config.json"
    bgm_volume = 0.25  # Default
    voice_volume = 1.0  # Default
    bgm_file = BGM_FILE  # Default
    bgm_fade_out_duration = 1.5  # Default
    
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            audio_config = config.get("audio", {})
            bgm_volume = audio_config.get("bgm_volume", 0.25)
            voice_volume = audio_config.get("voice_volume", 1.0)
            bgm_file = audio_config.get("bgm_file", BGM_FILE)
            bgm_fade_out_duration = audio_config.get("bgm_fade_out_duration", 1.5)
    
    if not os.path.exists(bgm_file):
        raise FileNotFoundError(f"BGM file not found: {bgm_file}")

    # Get voice duration to determine total duration
    voice_duration = get_audio_duration(VOICE_FILE)
    if voice_duration is None:
        raise ValueError("Could not determine voice audio duration")
    
    total_duration = voice_duration
    
    print("🎧 Mixing voice and background music...")
    print(f"   BGM volume: {bgm_volume}, Voice volume: {voice_volume}")
    if bgm_fade_out_duration > 0:
        print(f"   BGM fade-out: {bgm_fade_out_duration}s at the end")
    
    # Build filter complex
    # If fade-out is enabled and total duration is longer than fade duration
    if bgm_fade_out_duration > 0 and total_duration > bgm_fade_out_duration:
        fade_start = total_duration - bgm_fade_out_duration
        # Apply fade-out to BGM: afade=t=out:st=<start_time>:d=<duration>
        filter_complex = (
            f"[0:a]volume={voice_volume},aresample=44100[a0];"
            f"[1:a]volume={bgm_volume},aresample=44100,afade=t=out:st={fade_start}:d={bgm_fade_out_duration}[a1];"
            "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    else:
        # No fade-out
        filter_complex = (
            f"[0:a]volume={voice_volume},aresample=44100[a0];"
            f"[1:a]volume={bgm_volume},aresample=44100[a1];"
            "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    
    # Convert output to MP3 properly - use libmp3lame codec
    cmd = [
        "ffmpeg", "-y",
        "-i", VOICE_FILE,
        "-i", bgm_file,
        "-filter_complex", filter_complex,
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
    
    # Load video config
    config_file = "video_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        # Default config
        config = {
            "font": {"name": "Montserrat", "file": "Montserrat.ttf"},
            "style": {"font_size": 72},
            "positioning": {"alignment": 2, "margin_left": 50, "margin_right": 50, "margin_vertical": 180},
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
    font_size = config["style"]["font_size"]
    pos = config["positioning"]
    
    # Get style settings
    style_config = config.get("style", {})
    outline_thickness = style_config.get("outline_thickness", 5)
    shadow = style_config.get("shadow", 0)
    bold_value = 1 if style_config.get("bold", True) else 0
    
    font_path = os.path.abspath(font_file)
    if os.path.exists(font_path):
        # Use fontsdir to help FFmpeg find the font
        # Note: force_style is optional since ASS file already has styles defined
        subtitle_filter = f"subtitles={os.path.abspath(subtitle_file)}:fontsdir={os.path.dirname(font_path)}"
    else:
        # Fallback if font not found - still try font name (might be in system fonts)
        # Note: force_style is optional since ASS file already has styles defined
        subtitle_filter = f"subtitles={os.path.abspath(subtitle_file)}"
    
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
        
        # Since clips now use actual audio durations, video should match audio closely
        # Only extend if the difference is significant (> 1.0s)
        # For smaller differences, use -shortest to match the shorter duration
        if duration_diff > 1.0:  # If audio is significantly longer
            print(f"   ⚠️  Audio is {duration_diff:.2f}s longer than video")
            print(f"   📹 Extending video by looping (avoiding promo scene duplication)...")
            # Extend video by looping, but stop before the promo scene repeats
            # Get the duration of video without the last scene (promo)
            clips_dir = os.path.dirname(JOINED_VIDEO)
            extended_video = os.path.join(clips_dir, "extended_video.mp4")
            
            # Simple approach: loop the entire video, but trim to exact audio duration
            # This way if promo is at the end, it won't show for the full extra duration
            concat_file = os.path.join(clips_dir, "extend_concat.txt")
            with open(concat_file, "w") as f:
                abs_video = os.path.abspath(video_file)
                # Add enough loops to cover the duration difference
                loops = int(duration_diff / video_duration) + 2  # Add extra to ensure we have enough
                for _ in range(loops):
                    f.write(f"file '{abs_video}'\n")
            
            # Concatenate and trim to exact audio duration
            temp_extended = extended_video + ".temp.mp4"
            cmd_extend = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                temp_extended
            ]
            subprocess.run(cmd_extend, check=True, capture_output=True)
            
            # Trim to exact audio duration
            cmd_trim = [
                "ffmpeg", "-y",
                "-i", temp_extended,
                "-t", str(audio_duration),
                "-c", "copy",
                extended_video
            ]
            subprocess.run(cmd_trim, check=True, capture_output=True)
            os.remove(temp_extended)
            os.remove(concat_file)
            video_file = extended_video
            print(f"   ✅ Video extended to match audio")
        elif duration_diff > 0.1:
            # Small difference, just note it - FFmpeg will handle with -shortest
            print(f"   ℹ️  Small duration difference ({duration_diff:.2f}s), will use shorter duration")
    
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
            "-shortest",  # Use shortest stream to avoid extending and causing overlap
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
            "-shortest",  # Use shortest stream to avoid extending and causing overlap
            FINAL_VIDEO
        ]
    
    subprocess.run(cmd, check=True)
    print(f"✅ Final video with styled subtitles and watermark written to {FINAL_VIDEO}")

def main():
    mix_audio()
    mux_video()

if __name__ == "__main__":
    main()

