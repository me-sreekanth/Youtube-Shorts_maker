"""
Process a single stream video from JSON script.
Reuses existing video generation logic but adapts for stream requirements.
"""
import json
import os
import sys
import subprocess
from pathlib import Path

# Add parent scripts directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def process_single_stream_video(json_file: str, output_dir: str, is_last: bool = False):
    """
    Process a single video from JSON script for streaming.
    
    Args:
        json_file: Path to JSON script file (e.g., 1.json, 2.json)
        output_dir: Directory to save output files
        is_last: Whether this is the last video (determines if outro is added)
    
    Returns:
        Path to final video file, or None if failed
    """
    root = Path(__file__).resolve().parent.parent.parent
    
    # Load stream config first to get text processing settings
    stream_config_file = root / "stream_config.json"
    if stream_config_file.exists():
        with open(stream_config_file, "r", encoding="utf-8") as f:
            stream_config = json.load(f)
    else:
        stream_config = {}
    
    text_processing_config = stream_config.get("text_processing", {})
    outro_config = stream_config.get("outro", {})
    
    # Get apostrophe replacement character from config
    apostrophe_replacement = text_processing_config.get("apostrophe_replacement", "'")
    replace_curly_quotes = text_processing_config.get("replace_curly_quotes", True)
    
    # Load JSON script
    with open(json_file, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    
    # Replace curly apostrophes/quotes with configurable character
    def normalize_quotes(text):
        """Replace curly quotes/apostrophes with configurable replacement character."""
        if not text or not replace_curly_quotes:
            return text
        # Replace curly apostrophes and quotes with configured character
        text = text.replace(''', apostrophe_replacement)  # Curly apostrophe
        text = text.replace(''', apostrophe_replacement)  # Curly apostrophe (right single quote)
        text = text.replace('"', '"')  # Left double quote -> straight double quote
        text = text.replace('"', '"')  # Right double quote -> straight double quote
        text = text.replace(''', apostrophe_replacement)  # Left single quote
        text = text.replace(''', apostrophe_replacement)  # Right single quote
        return text
    
    title = normalize_quotes(script_data.get("title", "Untitled"))
    scenes = script_data.get("scenes", [])
    
    # Normalize narration text in all scenes
    for scene in scenes:
        if "narration" in scene:
            scene["narration"] = normalize_quotes(scene["narration"])
        if "subtitle" in scene:
            scene["subtitle"] = normalize_quotes(scene.get("subtitle", ""))
    
    print(f"\n{'='*60}")
    print(f"Processing: {title}")
    print(f"{'='*60}")
    
    # Create temporary working directories for this video
    video_id = Path(json_file).stem  # e.g., "1" from "1.json"
    temp_base = root / "output" / "stream" / f"temp_{video_id}"
    temp_audio = temp_base / "audio"
    temp_images = temp_base / "images"
    temp_subtitles = temp_base / "subtitles"
    temp_clips = temp_base / "video_clips"
    
    for d in [temp_audio, temp_images, temp_subtitles, temp_clips]:
        os.makedirs(d, exist_ok=True)
    
    try:
        # Step 1: Add outro scene if this is the last video
        if is_last and outro_config.get("enabled", True):
            promo_image_path = outro_config.get("image_path", "input/channel-promo.png")
            # Use absolute path if relative
            if not os.path.isabs(promo_image_path):
                promo_image_path = str(root / promo_image_path)
            else:
                promo_image_path = str(Path(promo_image_path))
            
            promo_narration = outro_config.get("narration", "Anyway, Subscribe for more")
            promo_subtitle = outro_config.get("subtitle", "Subscribe for more")
            
            # Remove any existing promo scenes
            scenes = [s for s in scenes if s.get("narration", "").lower() != promo_narration.lower()]
            
            # Add promo scene at the end
            promo_scene = {
                "scene_number": len(scenes) + 1,
                "scene_type": "promo",
                "narration": promo_narration,
                "subtitle": promo_subtitle,
                "image_prompt": promo_image_path,
                "duration": outro_config.get("duration", 4),
                "effect": outro_config.get("effect", "zoom_in")
            }
            scenes.append(promo_scene)
            script_data["scenes"] = scenes
            script_data["total_duration"] = sum(s.get("duration", 4) for s in scenes)
        
        # Step 2: Generate audio for scenes
        print("\n🎤 Generating audio...")
        import importlib.util
        tts_path = root / "scripts" / "tts.py"
        spec = importlib.util.spec_from_file_location("tts", tts_path)
        tts_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tts_module)
        call_pollinations_tts = tts_module.call_pollinations_tts
        
        temp_audio_dir = temp_audio / "temp_scenes"
        os.makedirs(temp_audio_dir, exist_ok=True)
        
        audio_files = []
        for i, scene in enumerate(scenes, 1):
            narration = scene["narration"]
            print(f"   🔊 Scene {i}: {narration[:50]}...")
            
            temp_audio_file = temp_audio_dir / f"scene_{i}.mp3"
            try:
                call_pollinations_tts(narration, str(temp_audio_file))
                audio_files.append(str(temp_audio_file))
            except Exception as e:
                print(f"   ❌ Failed to generate audio for scene {i}: {e}")
                raise
        
        # Concatenate audio files
        if len(audio_files) > 1:
            concat_list = temp_audio_dir / "concat.txt"
            with open(concat_list, "w") as f:
                for af in audio_files:
                    f.write(f"file '{os.path.abspath(af)}'\n")
            
            voice_audio = temp_audio / "voice.mp3"
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list), "-c", "copy", str(voice_audio)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            import shutil
            voice_audio = temp_audio / "voice.mp3"
            shutil.copy(audio_files[0], str(voice_audio))
        
        print(f"   ✅ Voice audio: {voice_audio}")
        
        # Step 3: Generate images for scenes
        print("\n🎨 Generating images...")
        img_path = root / "scripts" / "generate_images.py"
        spec = importlib.util.spec_from_file_location("generate_images", img_path)
        img_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(img_module)
        generate_image = img_module.generate_image
        
        image_files = []
        promo_image_path = str(root / "input" / "channel-promo.png")
        
        for i, scene in enumerate(scenes, 1):
            prompt = scene["image_prompt"]
            print(f"   🖼️  Scene {i}: {prompt[:60]}...")
            
            image_file = temp_images / f"img_{i}.jpg"
            
            # Check if this is promo scene
            is_promo_scene = (
                prompt == promo_image_path or
                prompt.endswith("channel-promo.png") or
                (os.path.exists(prompt) and prompt.endswith((".png", ".jpg", ".jpeg")))
            )
            
            if is_promo_scene:
                source_image = promo_image_path if os.path.exists(promo_image_path) else prompt
                if os.path.exists(source_image):
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", source_image,
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                        "-q:v", "2",
                        str(image_file)
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    image_files.append(str(image_file))
                    print(f"      ✅ Processed promo image")
                else:
                    print(f"      ⚠️  Promo image not found, skipping")
            else:
                try:
                    path = generate_image(prompt, f"img_{i}.jpg")
                    if path:
                        # Move to temp_images directory
                        import shutil
                        shutil.move(path, str(image_file))
                        image_files.append(str(image_file))
                        print(f"      ✅ Generated image")
                    else:
                        print(f"      ⚠️  Failed to generate image")
                except Exception as e:
                    print(f"      ⚠️  Error: {e}")
        
        # Step 4: Create subtitles
        print("\n📝 Creating subtitles...")
        
        # Import process_video_script module to use its functions
        process_script_path = root / "scripts" / "process_video_script.py"
        spec = importlib.util.spec_from_file_location("process_video_script", process_script_path)
        process_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(process_module)
        
        # Try to get word timings from transcription
        word_timings = None
        try:
            transcribe_path = root / "scripts" / "transcribe_audio.py"
            spec = importlib.util.spec_from_file_location("transcribe_audio", transcribe_path)
            transcribe_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(transcribe_module)
            
            transcription_result = transcribe_module.transcribe_audio(str(voice_audio))
            word_timings = transcribe_module.extract_word_timings(transcription_result)
            print(f"   ✅ Extracted {len(word_timings)} words with timings")
        except Exception as e:
            print(f"   ⚠️  Transcription failed: {e}, using scene-based subtitles")
        
        # Temporarily modify paths in process_video_script module
        original_audio_dir = getattr(process_module, "AUDIO_DIR", "output/audio")
        original_image_dir = getattr(process_module, "IMAGE_DIR", "output/images")
        original_sub_dir = getattr(process_module, "SUB_DIR", "output/subtitles")
        original_clips_dir = getattr(process_module, "CLIPS_DIR", "output/video_clips")
        
        # Set temp paths
        process_module.AUDIO_DIR = str(temp_audio)
        process_module.IMAGE_DIR = str(temp_images)
        process_module.SUB_DIR = str(temp_subtitles)
        process_module.CLIPS_DIR = str(temp_clips)
        
        # Get scene audio files for subtitle timing
        scene_audio_files = []
        for i in range(1, len(scenes) + 1):
            scene_audio = temp_audio_dir / f"scene_{i}.mp3"
            scene_audio_files.append(str(scene_audio) if scene_audio.exists() else None)
        
        # Create subtitles
        srt_file, ass_file = process_module.create_subtitles(scenes, word_timings)
        
        # Restore original paths
        process_module.AUDIO_DIR = original_audio_dir
        process_module.IMAGE_DIR = original_image_dir
        process_module.SUB_DIR = original_sub_dir
        process_module.CLIPS_DIR = original_clips_dir
        
        print(f"   ✅ Subtitles created: {ass_file}")
        
        # Step 5: Create video clips
        print("\n🎬 Creating video clips...")
        clips_path = root / "scripts" / "create_clips_from_script.py"
        spec = importlib.util.spec_from_file_location("create_clips", clips_path)
        clips_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(clips_module)
        create_clip = clips_module.create_clip
        get_audio_duration = clips_module.get_audio_duration
        
        clip_files = []
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
            duration = scene.get("duration", 4)
            scene_audio = temp_audio_dir / f"scene_{idx}.mp3"
            if scene_audio.exists():
                audio_duration = get_audio_duration(str(scene_audio))
                if audio_duration:
                    duration = audio_duration
            
            img_path = temp_images / f"img_{idx}.jpg"
            if not img_path.exists():
                print(f"   ⚠️  Missing {img_path}, skipping scene {idx}")
                continue
            
            effect = scene.get("effect")
            if not effect or effect not in available_effects:
                effect = available_effects[(idx - 1) % len(available_effects)]
            
            clip_path = temp_clips / f"clip_{idx}.mp4"
            print(f"   -> Clip {idx}: {duration:.2f}s [Effect: {effect}]")
            
            try:
                create_clip(str(img_path), duration, str(clip_path), effect)
                clip_files.append(str(clip_path))
            except Exception as e:
                print(f"   ❌ Failed to create clip {idx}: {e}")
                # Try fallback
                try:
                    create_clip(str(img_path), duration, str(clip_path), "ken_burns_in")
                    clip_files.append(str(clip_path))
                except:
                    continue
        
        if not clip_files:
            raise RuntimeError("No clips created")
        
        # Concatenate clips
        print("\n🔗 Concatenating clips...")
        list_file = temp_clips / "list.txt"
        with open(list_file, "w") as f:
            for path in clip_files:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        joined_video = temp_clips / "joined_video.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            str(joined_video)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"   ✅ Joined video: {joined_video}")
        
        # Step 6: Create title pause
        print("\n⏸️  Creating title pause...")
        title_pause_path = Path(__file__).resolve().parent / "create_title_pause.py"
        spec = importlib.util.spec_from_file_location("create_title_pause", title_pause_path)
        title_pause_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(title_pause_module)
        
        # Load stream config
        stream_config_file = root / "stream_config.json"
        if stream_config_file.exists():
            with open(stream_config_file, "r", encoding="utf-8") as f:
                stream_config = json.load(f)
        else:
            stream_config = {}
        
        # Get title pause config with defaults
        title_config = stream_config.get("title_pause", {})
        
        # Process title: remove hashtags if configured
        display_title = title
        if title_config.get("remove_hashtags", True):
            words = title.split()
            display_title = ' '.join([w for w in words if not w.startswith('#')])
        
        title_pause_video = temp_base / "title_pause.mp4"
        title_pause_module.create_title_pause(
            display_title,
            str(title_pause_video),
            duration=title_config.get("duration", 3.0),
            margin_left=title_config.get("margin_left", 100),
            margin_right=title_config.get("margin_right", 100),
            font_size_normal=title_config.get("font_size_normal", 72),
            font_size_center=title_config.get("font_size_center", 96),
            center_line_color=title_config.get("center_line_color", "yellow"),
            normal_line_color=title_config.get("normal_line_color", "white"),
            line_spacing=title_config.get("line_spacing", 20),
            visual_gap_adjustment=title_config.get("visual_gap_adjustment", 5)
        )
        
        # Step 7: Mix audio (BGM from start, voice after pause)
        print("\n🎧 Mixing audio...")
        mix_audio_path = Path(__file__).resolve().parent / "mix_stream_audio.py"
        spec = importlib.util.spec_from_file_location("mix_stream_audio", mix_audio_path)
        mix_audio_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mix_audio_module)
        
        # Get audio config
        audio_config = stream_config.get("audio", {})
        bgm_file_path = audio_config.get("bgm_file", "bgm/bgm.mp3")
        if not os.path.isabs(bgm_file_path):
            bgm_file = root / bgm_file_path
        else:
            bgm_file = Path(bgm_file_path)
        
        if not bgm_file.exists():
            raise FileNotFoundError(f"BGM file not found: {bgm_file}")
        
        mixed_audio = temp_audio / "mix.mp3"
        pause_duration = audio_config.get("pause_duration", 3.0)
        bgm_volume = audio_config.get("bgm_volume", 0.25)
        voice_volume = audio_config.get("voice_volume", 1.0)
        
        mix_audio_module.mix_stream_audio(
            str(voice_audio),
            str(bgm_file),
            str(mixed_audio),
            pause_duration=pause_duration,
            bgm_volume=bgm_volume,
            voice_volume=voice_volume
        )
        
        # Step 8: Combine everything
        print("\n🎞️  Combining final video...")
        combine_path = Path(__file__).resolve().parent / "combine_stream_video.py"
        spec = importlib.util.spec_from_file_location("combine_stream_video", combine_path)
        combine_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(combine_module)
        
        watermark_file = root / "input" / "watermark.png"
        watermark_path = str(watermark_file) if watermark_file.exists() else None
        
        # Sanitize filename
        import re
        final_video_name = re.sub(r'[^\w\s-]', '', title).strip()
        final_video_name = re.sub(r'[-\s]+', '_', final_video_name)
        final_video = Path(output_dir) / f"{video_id.zfill(2)}_{final_video_name}.mp4"
        
        combine_module.combine_stream_video(
            str(title_pause_video),
            str(joined_video),
            str(mixed_audio),
            str(ass_file),
            str(final_video),
            watermark_path
        )
        
        print(f"\n✅ Video complete: {final_video}")
        
        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_base, ignore_errors=True)
        
        return str(final_video)
        
    except Exception as e:
        print(f"\n❌ Error processing video: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test with a single file
    import sys
    if len(sys.argv) < 2:
        print("Usage: python process_stream_videos.py <json_file> [is_last]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    is_last = sys.argv[2].lower() == "true" if len(sys.argv) > 2 else False
    output_dir = Path(__file__).resolve().parent.parent.parent / "output" / "stream"
    
    result = process_single_stream_video(json_file, str(output_dir), is_last)
    if result:
        print(f"\n✅ Success: {result}")
    else:
        print(f"\n❌ Failed")
        sys.exit(1)

