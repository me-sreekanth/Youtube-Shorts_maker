"""
Combine title pause + main video + subtitles + watermark with proper audio timing.
"""
import os
import json
import subprocess
from pathlib import Path

def get_duration(file_path):
    """Get video/audio duration in seconds using ffprobe."""
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

def combine_stream_video(
    title_pause_video: str,
    main_video: str,
    mixed_audio: str,
    subtitle_file: str,
    output_file: str,
    watermark_file: str = None,
    pause_duration: float = 3.0
):
    """
    Combine title pause video + main video with subtitles, watermark, and mixed audio.
    
    Args:
        title_pause_video: Path to 3-second title pause video
        main_video: Path to main video (without pause)
        mixed_audio: Path to mixed audio (BGM from start, voice after pause)
        subtitle_file: Path to subtitle file (ASS or SRT)
        output_file: Path to save final video
        watermark_file: Optional path to watermark image
        pause_duration: Duration of pause in seconds (default 3.0)
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Check required files
    if not os.path.exists(title_pause_video):
        raise FileNotFoundError(f"Title pause video not found: {title_pause_video}")
    if not os.path.exists(main_video):
        raise FileNotFoundError(f"Main video not found: {main_video}")
    if not os.path.exists(mixed_audio):
        raise FileNotFoundError(f"Mixed audio not found: {mixed_audio}")
    if not os.path.exists(subtitle_file):
        raise FileNotFoundError(f"Subtitle file not found: {subtitle_file}")
    
    # Load subtitle config
    root = Path(__file__).resolve().parent.parent.parent
    config_file = root / "subtitle_config.json"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {
            "font": {"name": "Game of Thrones", "file": "Game of Thrones.ttf"},
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
    
    # Get font file path
    font_file = config["font"]["file"]
    font_path = root / font_file
    if not font_path.exists():
        font_path = None
    
    # Determine subtitle type
    subtitle_type = "ASS" if subtitle_file.endswith(".ass") else "SRT"
    
    # Build subtitle filter
    if font_path:
        subtitle_filter = f"subtitles={os.path.abspath(subtitle_file)}:fontsdir={os.path.dirname(font_path)}"
    else:
        subtitle_filter = f"subtitles={os.path.abspath(subtitle_file)}"
    
    # Adjust subtitle timing: subtitles should start after pause_duration
    # We need to shift subtitle timings by pause_duration
    # For ASS files, we can use the setpts filter, but it's easier to adjust in the subtitle file itself
    # For now, we'll apply subtitles only to the main video part (after pause)
    # Actually, we can concatenate videos first, then apply subtitles to the whole thing
    # But subtitles need to be time-shifted by pause_duration
    
    # Approach: Concatenate title pause + main video, then apply subtitles with time offset
    # However, ASS/SRT subtitles can't be easily time-shifted in ffmpeg filter
    # Better approach: Create a temporary subtitle file with shifted timings
    
    # For now, let's concatenate videos first, then apply subtitles
    # We'll need to handle subtitle timing offset separately or create adjusted subtitle file
    
    # Step 1: Concatenate title pause + main video
    concat_list = os.path.join(os.path.dirname(output_file), "temp_concat.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{os.path.abspath(title_pause_video)}'\n")
        f.write(f"file '{os.path.abspath(main_video)}'\n")
    
    temp_concatenated = os.path.join(os.path.dirname(output_file), "temp_concatenated.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        temp_concatenated
    ]
    
    try:
        subprocess.run(cmd_concat, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        os.remove(concat_list)
        raise RuntimeError(f"Failed to concatenate videos: {e.stderr}")
    
    # Step 2: Apply subtitles with time offset
    # We need to shift subtitle timings by pause_duration
    # Create a time-shifted subtitle file
    temp_subtitle = os.path.join(os.path.dirname(output_file), "temp_subtitle" + os.path.splitext(subtitle_file)[1])
    
    if subtitle_type == "ASS":
        # For ASS files, we need to shift all dialogue timings
        with open(subtitle_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Shift dialogue timings by pause_duration
        lines = content.split("\n")
        shifted_lines = []
        for line in lines:
            if line.startswith("Dialogue:"):
                # Format: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
                parts = line.split(",", 9)
                if len(parts) >= 3:
                    start_time = parts[1]
                    end_time = parts[2]
                    
                    # Convert ASS time to seconds, add pause_duration, convert back
                    def ass_time_to_seconds(ass_time):
                        h, m, s = ass_time.split(":")
                        s, cs = s.split(".")
                        return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
                    
                    def seconds_to_ass_time(seconds):
                        hours = int(seconds // 3600)
                        minutes = int((seconds % 3600) // 60)
                        secs = int(seconds % 60)
                        centisecs = int((seconds % 1) * 100)
                        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
                    
                    start_seconds = ass_time_to_seconds(start_time) + pause_duration
                    end_seconds = ass_time_to_seconds(end_time) + pause_duration
                    
                    parts[1] = seconds_to_ass_time(start_seconds)
                    parts[2] = seconds_to_ass_time(end_seconds)
                    line = ",".join(parts)
            
            shifted_lines.append(line)
        
        with open(temp_subtitle, "w", encoding="utf-8") as f:
            f.write("\n".join(shifted_lines))
    else:
        # For SRT files, shift timings
        with open(subtitle_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.split("\n")
        shifted_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if "-->" in line:
                # Format: HH:MM:SS,mmm --> HH:MM:SS,mmm
                parts = line.split(" --> ")
                if len(parts) == 2:
                    def srt_time_to_seconds(srt_time):
                        time_part, ms = srt_time.split(",")
                        h, m, s = time_part.split(":")
                        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                    
                    def seconds_to_srt_time(seconds):
                        millis = int(round(seconds * 1000))
                        hours = millis // (3600 * 1000)
                        millis %= 3600 * 1000
                        minutes = millis // (60 * 1000)
                        millis %= 60 * 1000
                        secs = millis // 1000
                        millis %= 1000
                        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
                    
                    start_time = srt_time_to_seconds(parts[0]) + pause_duration
                    end_time = srt_time_to_seconds(parts[1]) + pause_duration
                    
                    line = f"{seconds_to_srt_time(start_time)} --> {seconds_to_srt_time(end_time)}"
            
            shifted_lines.append(line)
            i += 1
        
        with open(temp_subtitle, "w", encoding="utf-8") as f:
            f.write("\n".join(shifted_lines))
    
    # Update subtitle filter to use shifted subtitle file
    if font_path:
        subtitle_filter = f"subtitles={os.path.abspath(temp_subtitle)}:fontsdir={os.path.dirname(font_path)}"
    else:
        subtitle_filter = f"subtitles={os.path.abspath(temp_subtitle)}"
    
    # Step 3: Apply subtitles, watermark, and mix audio
    watermark_config = config.get("watermark", {})
    watermark_enabled = watermark_config.get("enabled", True) if watermark_file else False
    
    if watermark_enabled and watermark_file and os.path.exists(watermark_file):
        # Get watermark settings
        position_config = watermark_config.get("position", {})
        size_config = watermark_config.get("size", {})
        opacity_config = watermark_config.get("opacity", {})
        
        location = position_config.get("location", "top-right")
        margin_x = position_config.get("margin_x", 20)
        margin_y = position_config.get("margin_y", 20)
        
        # Calculate overlay position
        if location == "top-right":
            overlay_pos = f"W-w-{margin_x}:{margin_y}"
        elif location == "top-left":
            overlay_pos = f"{margin_x}:{margin_y}"
        elif location == "bottom-right":
            overlay_pos = f"W-w-{margin_x}:H-h-{margin_y}"
        elif location == "bottom-left":
            overlay_pos = f"{margin_x}:H-h-{margin_y}"
        else:
            overlay_pos = f"W-w-{margin_x}:{margin_y}"
        
        size_mode = size_config.get("mode", "auto")
        size_width = size_config.get("width", 200)
        scale_filter = f"scale={size_width}:-1" if size_mode == "auto" and size_width else "scale=-1:-1"
        
        opacity = opacity_config.get("value", 0.5)
        
        # Filter chain: subtitles -> watermark overlay
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_concatenated,
            "-i", watermark_file,
            "-i", mixed_audio,
            "-filter_complex",
            f"[0:v]{subtitle_filter}[v0];[1:v]{scale_filter},format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*{opacity}'[wm];[v0][wm]overlay={overlay_pos}[v]",
            "-map", "[v]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            output_file
        ]
    else:
        # No watermark, just subtitles
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_concatenated,
            "-i", mixed_audio,
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            output_file
        ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"   ✅ Final video created: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to create final video: {e.stderr}")
        raise
    finally:
        # Cleanup temp files
        if os.path.exists(concat_list):
            os.remove(concat_list)
        if os.path.exists(temp_concatenated):
            os.remove(temp_concatenated)
        if os.path.exists(temp_subtitle):
            os.remove(temp_subtitle)

if __name__ == "__main__":
    # Test
    root = Path(__file__).resolve().parent.parent.parent
    title_pause = root / "output" / "stream" / "test_title_pause.mp4"
    main_video = root / "output" / "video_clips" / "joined_video.mp4"
    mixed_audio = root / "output" / "stream" / "test_mixed_audio.mp3"
    subtitle_file = root / "output" / "subtitles" / "subtitles.ass"
    output_file = root / "output" / "stream" / "test_final.mp4"
    
    if all(f.exists() for f in [title_pause, main_video, mixed_audio, subtitle_file]):
        combine_stream_video(
            str(title_pause),
            str(main_video),
            str(mixed_audio),
            str(subtitle_file),
            str(output_file)
        )
        print(f"Test video created at {output_file}")
    else:
        print("Test files not found")

