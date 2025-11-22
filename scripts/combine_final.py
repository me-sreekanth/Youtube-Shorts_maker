import os
import subprocess

VOICE_FILE = "output/audio/voice.mp3"
BGM_FILE = "bgm/bgm.mp3"
MIXED_AUDIO = "output/audio/mix.mp3"
JOINED_VIDEO = "output/video_clips/joined_video.mp4"
SRT_FILE = "output/subtitles/subtitles.srt"
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

    print("📽  Combining video + mixed audio + subtitles...")
    cmd = [
        "ffmpeg", "-y",
        "-i", JOINED_VIDEO,
        "-i", MIXED_AUDIO,
        "-vf", f"subtitles={SRT_FILE}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        FINAL_VIDEO
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Final video written to {FINAL_VIDEO}")

def main():
    mix_audio()
    mux_video()

if __name__ == "__main__":
    main()

