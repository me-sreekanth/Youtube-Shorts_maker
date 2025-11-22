import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "summarizer.py",      # Step 1: Create script
    "tts.py",             # Step 2: Generate audio FIRST
    "subtitles.py",        # Step 3: Analyze audio timing
    "generate_images.py", # Step 4: Generate images based on audio timing
    "create_clips.py",    # Step 5: Create video clips
    "combine_final.py",   # Step 6: Combine everything
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
            # Continue to next script instead of stopping
            continue

    if failed_scripts:
        print(f"\n⚠️  Some scripts failed: {', '.join(failed_scripts)}")
        print("Check the output above for details.")
    else:
        print("\n🎉 All done! Check output/final/final_short.mp4")

if __name__ == "__main__":
    main()

