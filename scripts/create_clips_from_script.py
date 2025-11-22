"""
Create video clips from images using the video script JSON format.
This uses the exact durations specified in the script.
"""
import json
import os
import subprocess
from typing import List, Tuple

SCRIPT_FILE = "input/video_script.json"
IMAGE_DIR = "output/images"
CLIPS_DIR = "output/video_clips"
JOINED_VIDEO = os.path.join(CLIPS_DIR, "joined_video.mp4")

def load_video_script():
    """Load the video script JSON file."""
    if not os.path.exists(SCRIPT_FILE):
        raise FileNotFoundError(f"Video script not found: {SCRIPT_FILE}")
    
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def create_clip(image_path: str, duration: float, out_path: str):
    """Create a video clip from an image with specified duration."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Simple scale (zoom effects can be added later if needed)
    vf = "scale=1080:1920,format=yuv420p"
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-c:v", "libx264",
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-pix_fmt", "yuv420p",
        "-r", "30",
        out_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"     ⚠️  FFmpeg error: {result.stderr[:200]}")
        raise subprocess.CalledProcessError(result.returncode, cmd)

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ input/video_script.json not found.")
        return
    
    script_data = load_video_script()
    scenes = script_data["scenes"]
    
    print(f"🎬 Creating {len(scenes)} clips from images...")
    clip_files = []
    
    for idx, scene in enumerate(scenes, start=1):
        duration = scene.get("duration", 4)
        img_path = os.path.join(IMAGE_DIR, f"img_{idx}.jpg")
        
        if not os.path.exists(img_path):
            print(f"⚠️  Missing {img_path}, skipping scene {idx}")
            continue
        
        clip_path = os.path.join(CLIPS_DIR, f"clip_{idx}.mp4")
        print(f"  -> Clip {idx}: {duration}s from {img_path}")
        
        try:
            create_clip(img_path, duration, clip_path)
            clip_files.append(clip_path)
        except Exception as e:
            print(f"  ❌ Failed to create clip {idx}: {e}")
            continue
    
    if not clip_files:
        print("❌ No clips created")
        return
    
    # Create concat list with absolute paths
    list_file = os.path.join(CLIPS_DIR, "list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for path in clip_files:
            abs_path = os.path.abspath(path)
            abs_path_escaped = abs_path.replace("'", "'\\''")
            f.write(f"file '{abs_path_escaped}'\n")
    
    # Concatenate with transitions
    print("🔗 Concatenating clips with transitions to joined_video.mp4 ...")
    
    transition_duration = 0.3
    faded_clips = []
    
    for i, clip_path in enumerate(clip_files):
        faded_path = os.path.join(CLIPS_DIR, f"faded_clip_{i+1}.mp4")
        scene = scenes[i]
        duration = scene.get("duration", 4)
        
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
                "-an",
                "-r", "30",
                faded_path
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-c:v", "copy",
                "-an",
                faded_path
            ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        faded_clips.append(faded_path)
    
    # Update concat list
    with open(list_file, "w", encoding="utf-8") as f:
        for path in faded_clips:
            abs_path = os.path.abspath(path)
            abs_path_escaped = abs_path.replace("'", "'\\''")
            f.write(f"file '{abs_path_escaped}'\n")
    
    # Concat
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
    print(f"✅ Joined video created at {JOINED_VIDEO}")

if __name__ == "__main__":
    main()

