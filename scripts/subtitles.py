import os
import re
import subprocess
from typing import List, Tuple

SCRIPT_FILE = "output/short_script.txt"
AUDIO_FILE = "output/audio/voice.mp3"
SUB_DIR = "output/subtitles"
SRT_FILE = os.path.join(SUB_DIR, "subtitles.srt")

def get_audio_duration(path: str) -> float:
    """Returns duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    result.check_returncode()
    return float(result.stdout.strip())

def detect_silence_points(path: str, silence_threshold: str = "-30dB", min_silence_duration: float = 0.3) -> List[float]:
    """
    Detect silence points in audio using FFmpeg's silencedetect filter.
    Returns list of timestamps where silence ends (good break points).
    """
    cmd = [
        "ffmpeg", "-i", path,
        "-af", f"silencedetect=noise={silence_threshold}:d={min_silence_duration}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.STDOUT)
    
    # Parse silence_end timestamps from output
    # Format: "silence_end: 2.34567 | silence_duration: 0.5"
    silence_points = []
    pattern = r"silence_end: ([\d.]+)"
    for match in re.finditer(pattern, result.stdout):
        silence_points.append(float(match.group(1)))
    
    return sorted(silence_points)

def seconds_to_srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours = millis // (3600 * 1000)
    millis %= 3600 * 1000
    minutes = millis // (60 * 1000)
    millis %= 60 * 1000
    secs = millis // 1000
    millis %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def compute_segments_with_silence(lines: List[str], total_duration: float, silence_points: List[float]) -> List[Tuple[float, float, str]]:
    """
    Compute segments using silence detection for better accuracy.
    If we have enough silence points, use them; otherwise fall back to weighted timing.
    """
    if len(silence_points) >= len(lines) - 1:
        # We have enough silence points to split between lines
        segments = []
        silence_points = [0.0] + silence_points + [total_duration]
        
        for i, line in enumerate(lines):
            start = silence_points[i] if i < len(silence_points) else silence_points[-1]
            end = silence_points[i + 1] if i + 1 < len(silence_points) else total_duration
            segments.append((start, end, line))
        
        return segments
    else:
        # Fall back to weighted timing based on character count
        print("⚠️  Not enough silence points detected, using weighted timing")
        weights = [max(len(l), 1) for l in lines]
        total_weight = sum(weights)
        segments = []
        current_start = 0.0
        for line, w in zip(lines, weights):
            line_duration = total_duration * (w / total_weight)
            start = current_start
            end = start + line_duration
            segments.append((start, end, line))
            current_start = end
        return segments

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ short_script.txt missing. Run summarizer first.")
        return

    if not os.path.exists(AUDIO_FILE):
        print("❌ voice.mp3 missing. Run tts first.")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.read().splitlines() if l.strip()]

    if not lines:
        print("❌ No lines to subtitle")
        return

    total_dur = get_audio_duration(AUDIO_FILE)
    print(f"⏱  Audio duration: {total_dur:.2f}s")
    
    # Detect silence points in audio for better timing
    print("🔍 Analyzing audio for silence points...")
    silence_points = detect_silence_points(AUDIO_FILE)
    print(f"   Found {len(silence_points)} silence break points")
    
    # Compute segments using actual audio analysis
    segments = compute_segments_with_silence(lines, total_dur, silence_points)

    os.makedirs(SUB_DIR, exist_ok=True)
    with open(SRT_FILE, "w", encoding="utf-8") as f:
        for idx, (start, end, text) in enumerate(segments, start=1):
            f.write(f"{idx}\n")
            f.write(f"{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}\n")
            f.write(text + "\n\n")

    print(f"✅ Subtitles written to {SRT_FILE}")

if __name__ == "__main__":
    main()

