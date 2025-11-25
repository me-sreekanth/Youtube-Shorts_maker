"""
Create video clips from images using the video script JSON format.
This uses actual audio durations when available, falling back to JSON durations.
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

def get_animation_filter(effect_type: str, duration: float, width: int = 1080, height: int = 1920):
    """Generate FFmpeg filter for different animation effects optimized for shorts."""
    base_scale = f"scale={width}:{height}"
    fps = 30
    total_frames = int(duration * fps)
    
    # Calculate zoom parameters - reduced for better clarity
    zoom_end = 1.15  # Reduced from 1.4 to 1.15 (15% zoom instead of 40%)
    
    effects = {
        # Zoom effects - reduced zoom for better clarity
        "zoom_in": f"scale={int(width*zoom_end)}:{int(height*zoom_end)},zoompan=z='min(zoom+0.0012,{zoom_end})':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}",
        "zoom_out": f"scale={int(width*zoom_end)}:{int(height*zoom_end)},zoompan=z='if(lte(zoom,1.0),1.0,max(zoom-0.0012,1.0))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:zoom={zoom_end}",
        "ken_burns_in": f"scale={int(width*1.15)}:{int(height*1.15)},zoompan=z='min(zoom+0.0010,1.15)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}",
        "ken_burns_out": f"scale={int(width*1.15)}:{int(height*1.15)},zoompan=z='if(lte(zoom,1.0),1.0,max(zoom-0.0010,1.0))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:zoom=1.15",
        
        # Pan effects - reduced scale for better clarity
        "pan_left": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:'if(gte(t,0), (iw-{width})*t/{duration}, 0)':0",
        "pan_right": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:'if(gte(t,0), (iw-{width})*(1-t/{duration}), 0)':0",
        "pan_up": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:0:'if(gte(t,0), (ih-{height})*t/{duration}, 0)'",
        "pan_down": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:0:'if(gte(t,0), (ih-{height})*(1-t/{duration}), 0)'",
        
        # Dynamic zoom effects - reduced for better clarity
        "zoom_center": f"scale={int(width*1.15)}:{int(height*1.15)},zoompan=z='min(zoom+0.0008,1.15)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}",
        "zoom_rapid": f"scale={int(width*1.2)}:{int(height*1.2)},zoompan=z='min(zoom+0.0015,1.2)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}",
        
        # Parallax-like effects - reduced scale
        "parallax_up": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:0:'if(gte(t,0), (ih-{height})*0.3*sin(PI*t/{duration}), 0)'",
        "parallax_down": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:0:'if(gte(t,0), (ih-{height})*(1-0.3*sin(PI*t/{duration})), 0)'",
        
        # Movement effects - reduced scale
        "drift_left": f"scale={int(width*1.1)}:{int(height*1.1)},crop={width}:{height}:'if(gte(t,0), 20*sin(2*PI*t/{duration}), 0)':0",
        "drift_right": f"scale={int(width*1.1)}:{int(height*1.1)},crop={width}:{height}:'if(gte(t,0), -20*sin(2*PI*t/{duration}), 0)':0",
        "float_up": f"scale={int(width*1.1)}:{int(height*1.1)},crop={width}:{height}:0:'if(gte(t,0), 15*sin(2*PI*t/{duration}), 0)'",
        
        # Pulse and breathing
        "pulse": f"{base_scale},scale='iw*(1+0.04*sin(2*PI*t/{duration}))':'ih*(1+0.04*sin(2*PI*t/{duration}))',crop={width}:{height}",
        "breathe": f"{base_scale},scale='iw*(1+0.02*sin(4*PI*t/{duration}))':'ih*(1+0.02*sin(4*PI*t/{duration}))',crop={width}:{height}",
        
        # Diagonal movements - reduced scale
        "diagonal_tl_br": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:'if(gte(t,0), (iw-{width})*t/{duration}, 0)':'if(gte(t,0), (ih-{height})*t/{duration}, 0)'",
        "diagonal_tr_bl": f"scale={int(width*1.15)}:{int(height*1.15)},crop={width}:{height}:'if(gte(t,0), (iw-{width})*(1-t/{duration}), 0)':'if(gte(t,0), (ih-{height})*t/{duration}, 0)'",
        
        # Static
        "static": base_scale
    }
    
    return effects.get(effect_type, base_scale)

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

def create_clip(image_path: str, duration: float, out_path: str, effect: str = "ken_burns_in"):
    """Create a video clip from an image with specified duration and animation effect."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Get animation filter
    vf = get_animation_filter(effect, duration)
    vf += ",format=yuv420p"
    
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
    clip_scene_map = []  # Map clip index to scene index
    
    # Engaging effects optimized for shorts format
    available_effects = [
        "zoom_in", "zoom_out", "ken_burns_in", "ken_burns_out",
        "pan_left", "pan_right", "pan_up", "pan_down",
        "zoom_center", "zoom_rapid",
        "parallax_up", "parallax_down",
        "drift_left", "drift_right", "float_up",
        "pulse", "breathe",
        "diagonal_tl_br", "diagonal_tr_bl"
    ]
    
    for idx, scene in enumerate(scenes, start=1):
        # Try to get actual audio duration first, fallback to JSON duration
        duration = scene.get("duration", 4)
        scene_audio = os.path.join("output/audio/temp_scenes", f"scene_{idx}.mp3")
        if os.path.exists(scene_audio):
            audio_duration = get_audio_duration(scene_audio)
            if audio_duration:
                duration = audio_duration
                print(f"  📊 Using actual audio duration: {duration:.2f}s (was {scene.get('duration', 4)}s)")
        
        img_path = os.path.join(IMAGE_DIR, f"img_{idx}.jpg")
        
        # Get effect from scene, or auto-assign engaging effect
        effect = scene.get("effect")
        if not effect or effect not in available_effects:
            # Auto-assign effect based on scene number for maximum variety
            # Mix zoom, pan, and dynamic effects for engaging shorts
            effect = available_effects[(idx - 1) % len(available_effects)]
        
        if not os.path.exists(img_path):
            print(f"⚠️  Missing {img_path}, skipping scene {idx}")
            continue
        
        clip_path = os.path.join(CLIPS_DIR, f"clip_{idx}.mp4")
        print(f"  -> Clip {idx}: {duration:.2f}s from {img_path} [Effect: {effect}]")
        
        try:
            create_clip(img_path, duration, clip_path, effect)
            clip_files.append(clip_path)
            clip_scene_map.append(idx - 1)  # Store scene index (0-based)
        except Exception as e:
            print(f"  ❌ Failed to create clip {idx} with effect '{effect}': {e}")
            # Try with a simpler, more reliable effect as fallback
            print(f"  🔄 Retrying with fallback effect 'ken_burns_in'...")
            try:
                create_clip(img_path, duration, clip_path, "ken_burns_in")
                clip_files.append(clip_path)
                clip_scene_map.append(idx - 1)  # Store scene index
                print(f"  ✅ Clip {idx} created successfully with fallback effect")
            except Exception as e2:
                print(f"  ❌ Fallback also failed: {e2}")
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
        # Use the scene map to get the correct scene
        scene_idx = clip_scene_map[i]
        scene = scenes[scene_idx]
        duration = scene.get("duration", 4)
        
        # Try to get actual audio duration if available
        scene_audio = os.path.join("output/audio/temp_scenes", f"scene_{scene_idx + 1}.mp3")
        if os.path.exists(scene_audio):
            audio_duration = get_audio_duration(scene_audio)
            if audio_duration:
                duration = audio_duration
        
        # Only apply fade_in if not the first clip
        fade_in = f"fade=t=in:st=0:d={transition_duration}" if i > 0 else ""
        # Only apply fade_out if not the last clip (preserve full duration of last scene)
        # For the last clip, don't apply fade_out to preserve full duration
        is_last_clip = (i == len(clip_files) - 1)
        fade_out_start = max(0, duration - transition_duration)
        fade_out = f"fade=t=out:st={fade_out_start}:d={transition_duration}" if not is_last_clip else ""
        
        filters = []
        if fade_in:
            filters.append(fade_in)
        if fade_out:
            filters.append(fade_out)
        
        if filters:
            vf = ",".join(filters)
            # For last clip, ensure full duration without fade cutting it
            if is_last_clip:
                # Last clip: no fade_out, preserve full duration
                cmd = [
                    "ffmpeg", "-y",
                    "-i", clip_path,
                    "-vf", vf if fade_in else "null",  # Only apply fade_in if present
                    "-c:v", "libx264",
                    "-t", f"{duration:.3f}",  # Full duration
                    "-an",
                    "-r", "30",
                    faded_path
                ]
            else:
                # Not last clip: can have fade_out
                cmd = [
                    "ffmpeg", "-y",
                    "-i", clip_path,
                    "-vf", vf,
                    "-c:v", "libx264",
                    "-t", f"{duration:.3f}",  # Full duration
                    "-an",
                    "-r", "30",
                    faded_path
                ]
        else:
            # No filters (first clip with no fades, or last clip with no fades)
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-t", f"{duration:.3f}",  # Explicitly set duration
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

