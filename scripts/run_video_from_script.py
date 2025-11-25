"""
Main script to generate video from structured JSON script.
This replaces the old summarizer-based workflow.
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "process_video_script.py",  # Generate audio, images, subtitles
    "create_clips_from_script.py",  # Create video clips
    "combine_final.py",  # Combine everything
]

def main():
    python_exec = sys.executable
    root = Path(__file__).resolve().parent.parent
    failed_scripts = []

    for script in SCRIPTS:
        script_path = root / "scripts" / script
        print(f"\n🚀 Running {script} ...")
        result = subprocess.run([python_exec, str(script_path)], check=False)
        
        if result.returncode != 0:
            print(f"⚠️  {script} exited with code {result.returncode}")
            failed_scripts.append(script)
            continue

    if failed_scripts:
        print(f"\n⚠️  Some scripts failed: {', '.join(failed_scripts)}")
        print("Check the output above for details.")
    else:
        print("\n🎉 All done! Check output/final/final_short.mp4")
    
    # Cleanup temp audio files after all processing is complete
    import shutil
    temp_audio_dir = root / "output" / "audio" / "temp_scenes"
    if temp_audio_dir.exists():
        try:
            shutil.rmtree(temp_audio_dir, ignore_errors=True)
            print("🧹 Cleaned up temporary audio files")
        except Exception as e:
            print(f"⚠️  Could not clean up temp files: {e}")

if __name__ == "__main__":
    main()

