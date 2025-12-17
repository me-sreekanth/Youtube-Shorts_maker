"""
Mix audio for stream videos: BGM starts from pause (0:00), voiceover starts after 3-second pause.
"""
import os
import subprocess
from pathlib import Path

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

def mix_stream_audio(voice_file: str, bgm_file: str, output_file: str, pause_duration: float = 3.0, bgm_volume: float = 0.25, voice_volume: float = 1.0, bgm_fade_out_duration: float = 1.5):
    """
    Mix audio for stream videos:
    - BGM starts at 0:00 (beginning of pause)
    - Voiceover starts after pause_duration (3 seconds)
    - BGM continues through entire video
    - BGM fades out in the last bgm_fade_out_duration seconds
    
    Args:
        voice_file: Path to voice audio file
        bgm_file: Path to background music file
        output_file: Path to save mixed audio
        pause_duration: Duration of pause in seconds (default 3.0)
        bgm_volume: BGM volume multiplier (default 0.25)
        voice_volume: Voice volume multiplier (default 1.0)
        bgm_fade_out_duration: Duration in seconds to fade out BGM at the end (default 1.5)
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if not os.path.exists(voice_file):
        raise FileNotFoundError(f"Voice file not found: {voice_file}")
    if not os.path.exists(bgm_file):
        raise FileNotFoundError(f"BGM file not found: {bgm_file}")
    
    # Get durations
    voice_duration = get_audio_duration(voice_file)
    bgm_duration = get_audio_duration(bgm_file)
    
    if voice_duration is None:
        raise ValueError(f"Could not determine voice audio duration")
    if bgm_duration is None:
        raise ValueError(f"Could not determine BGM duration")
    
    # Total output duration = pause + voice duration
    total_duration = pause_duration + voice_duration
    
    # Create audio mix:
    # 1. BGM starts at 0:00 and loops/extends to total_duration
    # 2. Voice starts at pause_duration (3 seconds) and continues
    # 3. BGM fades out in the last bgm_fade_out_duration seconds
    # 4. Mix both with appropriate volumes
    
    # Build filter complex:
    # [0:a] = BGM input
    # [1:a] = Voice input
    # - BGM: volume adjustment, loop/extend to total_duration, fade-out at end
    # - Voice: volume adjustment, delay by pause_duration
    # - Mix both together
    
    # Apply fade-out to BGM if enabled and duration is sufficient
    if bgm_fade_out_duration > 0 and total_duration > bgm_fade_out_duration:
        fade_start = total_duration - bgm_fade_out_duration
        # BGM: volume, resample, loop, then fade-out
        bgm_filter = f"[0:a]volume={bgm_volume},aresample=44100,aloop=loop=-1:size=2e+09,afade=t=out:st={fade_start}:d={bgm_fade_out_duration}[bgm]"
    else:
        # No fade-out
        bgm_filter = f"[0:a]volume={bgm_volume},aresample=44100,aloop=loop=-1:size=2e+09[bgm]"
    
    filter_complex = (
        f"{bgm_filter};"
        f"[1:a]volume={voice_volume},aresample=44100,adelay={int(pause_duration * 1000)}|{int(pause_duration * 1000)}[voice];"
        f"[bgm][voice]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", bgm_file,  # Input 0: BGM
        "-i", voice_file,  # Input 1: Voice
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-t", str(total_duration),  # Set total duration
        output_file
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"   ✅ Mixed audio created: {output_file}")
        print(f"      Total duration: {total_duration:.2f}s (pause: {pause_duration}s + voice: {voice_duration:.2f}s)")
        if bgm_fade_out_duration > 0:
            print(f"      BGM fade-out: {bgm_fade_out_duration}s at the end")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to mix audio: {e.stderr}")
        raise

if __name__ == "__main__":
    # Test
    root = Path(__file__).resolve().parent.parent.parent
    voice_file = root / "output" / "audio" / "voice.mp3"
    bgm_file = root / "bgm" / "bgm.mp3"
    output_file = root / "output" / "stream" / "test_mixed_audio.mp3"
    
    if voice_file.exists() and bgm_file.exists():
        mix_stream_audio(str(voice_file), str(bgm_file), str(output_file))
        print(f"Test mixed audio created at {output_file}")
    else:
        print("Test files not found")

