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
OUTPUT_DIR = "output"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
SUB_DIR = os.path.join(OUTPUT_DIR, "subtitles")
CLIPS_DIR = os.path.join(OUTPUT_DIR, "video_clips")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

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

def create_subtitles(scenes):
    """Create SRT subtitles from scenes with their durations."""
    print("\n📝 Creating subtitles...")
    os.makedirs(SUB_DIR, exist_ok=True)
    srt_file = os.path.join(SUB_DIR, "subtitles.srt")
    
    current_time = 0.0
    
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
    
    print(f"   ✅ Subtitles saved: {srt_file}")
    return srt_file

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
        
        # 3. Create subtitles
        srt_file = create_subtitles(scenes)
        
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

