"""
Simple script to generate audio only:
1. Summarize transcript into short script
2. Generate TTS audio
"""
import subprocess
import sys
from pathlib import Path

def main():
    python_exec = sys.executable
    root = Path(__file__).resolve().parent.parent
    
    scripts = [
        "summarizer.py",
        "tts.py",
    ]
    
    for script in scripts:
        script_path = root / "scripts" / script
        print(f"\n🚀 Running {script} ...")
        result = subprocess.run([python_exec, str(script_path)], check=False)
        
        if result.returncode != 0:
            print(f"❌ {script} failed with exit code {result.returncode}")
            return
    
    print("\n✅ Audio generation complete!")
    print("   📄 Script: output/short_script.txt")
    print("   🎤 Audio: output/audio/voice.mp3")

if __name__ == "__main__":
    main()

