import os
import json
import subprocess

VOICE_FILE = "output/audio/voice.mp3"
BGM_FILE = "bgm/bgm.mp3"
MIXED_AUDIO = "output/audio/mix.mp3"
JOINED_VIDEO = "output/video_clips/joined_video.mp4"
SRT_FILE = "output/subtitles/subtitles.srt"
ASS_FILE = "output/subtitles/subtitles.ass"
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
            "positioning": {"alignment": 2, "margin_left": 40, "margin_right": 40, "margin_vertical": 60}
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
    
    cmd = [
        "ffmpeg", "-y",
        "-i", JOINED_VIDEO,
        "-i", MIXED_AUDIO,
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        FINAL_VIDEO
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Final video with styled subtitles written to {FINAL_VIDEO}")

def main():
    mix_audio()
    mux_video()

if __name__ == "__main__":
    main()

