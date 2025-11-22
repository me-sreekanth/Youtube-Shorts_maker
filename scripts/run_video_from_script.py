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

if __name__ == "__main__":
    main()

