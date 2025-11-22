import os
import re
import subprocess
from typing import List, Tuple

IMAGE_DIR = "output/images"
CLIPS_DIR = "output/video_clips"
SRT_FILE = "output/subtitles/subtitles.srt"
JOINED_VIDEO = os.path.join(CLIPS_DIR, "joined_video.mp4")

TIME_RE = re.compile(r"(\d+):(\d+):(\d+),(\d+)\s+-->\s+(\d+):(\d+):(\d+),(\d+)")

def parse_srt(path: str) -> List[Tuple[float, float, str]]:
    segments = []
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as f:
        blocks = f.read().strip().split("\n\n")

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        time_line = lines[1]
        m = TIME_RE.search(time_line)
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        start = h1*3600 + m1*60 + s1 + ms1/1000.0
        end   = h2*3600 + m2*60 + s2 + ms2/1000.0
        text = " ".join(lines[2:]) if len(lines) > 2 else ""
        segments.append((start, end, text))
    return segments

def create_clip(image_path: str, duration: float, out_path: str, clip_index: int, total_clips: int):
    """
    Create a video clip from an image with subtle zoom effect.
    Each clip will have a gentle zoom-in to add motion and keep viewer engaged.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Subtle zoom: start at 100%, end at 110% (Ken Burns effect)
    # Using zoompan filter for smooth zoom animation
    zoom_factor = 1.1
    frames = int(duration * 30)  # 30 fps
    
    # Create zoom filter - smooth zoom from center
    vf = (
        f"scale=1080*{zoom_factor}:1920*{zoom_factor},"
        f"zoompan=z='min(zoom+0.0005,{zoom_factor})':"
        f"d={frames}:"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"s=1080x1920,"
        f"format=yuv420p"
    )
    
    # Fallback to simple scale if zoompan fails
    vf_simple = (
        f"scale=1080:1920,"
        f"format=yuv420p"
    )
    
    # Try zoom effect first, fallback to simple if it fails
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-c:v", "libx264",
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-pix_fmt", "yuv420p",
        "-r", "30",  # 30 fps for smooth playback
        out_path
    ]
    
    # Run with error handling - fallback to simple if zoom fails
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback to simple scale
        print(f"     ⚠️  Zoom effect failed, using simple scale")
        cmd_simple = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-c:v", "libx264",
            "-t", f"{duration:.3f}",
            "-vf", vf_simple,
            "-pix_fmt", "yuv420p",
            "-r", "30",
            out_path
        ]
        subprocess.run(cmd_simple, check=True, capture_output=True)

def main():
    if not os.path.exists(SRT_FILE):
        print("❌ subtitles.srt missing. Run subtitles.py first.")
        return

    segments = parse_srt(SRT_FILE)
    if not segments:
        print("❌ No segments parsed from SRT")
        return

    print(f"🎬 Creating {len(segments)} clips from images...")
    clip_files = []
    clip_durations = []
    last_image = None

    for idx, (start, end, text) in enumerate(segments, start=1):
        duration = max(end - start, 0.5)
        img_path = os.path.join(IMAGE_DIR, f"img_{idx}.jpg")
        if not os.path.exists(img_path):
            # fallback: reuse last image if any
            if last_image and os.path.exists(last_image):
                img_path = last_image
            else:
                print(f"⚠️ Missing {img_path}, skipping segment {idx}")
                continue
        last_image = img_path

        clip_path = os.path.join(CLIPS_DIR, f"clip_{idx}.mp4")
        print(f"  -> Clip {idx}: {duration:.2f}s from {img_path}")
        create_clip(img_path, duration, clip_path, idx, len(segments))
        clip_files.append(clip_path)
        clip_durations.append(duration)

    if not clip_files:
        print("❌ No clips created")
        return

    # create concat list with absolute paths
    list_file = os.path.join(CLIPS_DIR, "list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for path in clip_files:
            abs_path = os.path.abspath(path)
            # Escape single quotes in path for FFmpeg
            abs_path_escaped = abs_path.replace("'", "'\\''")
            f.write(f"file '{abs_path_escaped}'\n")

    # concat with crossfade transitions between clips
    print("🔗 Concatenating clips with transitions to joined_video.mp4 ...")
    
    # First, create individual clips with fade in/out
    transition_duration = 0.3  # 0.3 second fade for smoother transitions
    faded_clips = []
    
    for i, (clip_path, duration) in enumerate(zip(clip_files, clip_durations)):
        faded_path = os.path.join(CLIPS_DIR, f"faded_clip_{i+1}.mp4")
        
        # Add fade in at start (except first) and fade out at end (except last)
        fade_in = f"fade=t=in:st=0:d={transition_duration}" if i > 0 else ""
        fade_out_start = max(0, duration - transition_duration)
        fade_out = f"fade=t=out:st={fade_out_start}:d={transition_duration}" if i < len(clip_files) - 1 else ""
        
        filters = []
        if fade_in:
            filters.append(fade_in)
        if fade_out:
            filters.append(fade_out)
        
        if filters:
            vf = ",".join(filters)
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-vf", vf,
                "-c:v", "libx264",
                "-an",  # Remove audio (we'll add it later)
                "-r", "30",
                faded_path
            ]
        else:
            # No fade needed, just copy (but remove audio)
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-c:v", "copy",
                "-an",
                faded_path
            ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        faded_clips.append(faded_path)
    
    # Update concat list with faded clips
    with open(list_file, "w", encoding="utf-8") as f:
        for path in faded_clips:
            abs_path = os.path.abspath(path)
            abs_path_escaped = abs_path.replace("'", "'\\''")
            f.write(f"file '{abs_path_escaped}'\n")
    
    # Concat with crossfade using filter_complex
    # For simplicity, we'll use concat demuxer (fades already applied)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        JOINED_VIDEO
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Joined video with transitions created at {JOINED_VIDEO}")

if __name__ == "__main__":
    main()

