"""
Main entry point for stream video generation.
Finds numbered JSON files (1.json, 2.json, etc.) in input/stream/,
processes them in order, and generates videos with proper naming.
"""
import os
import sys
import re
import importlib.util
from pathlib import Path

def find_numbered_json_files(input_dir: str):
    """
    Find numbered JSON files in input directory.
    Returns sorted list of (number, file_path) tuples.
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        return []
    
    json_files = []
    pattern = re.compile(r'^(\d+)\.json$')
    
    for file in input_path.iterdir():
        if file.is_file() and file.suffix.lower() == '.json':
            match = pattern.match(file.name)
            if match:
                number = int(match.group(1))
                json_files.append((number, str(file)))
    
    # Sort by number
    json_files.sort(key=lambda x: x[0])
    return json_files

def sanitize_filename(title: str) -> str:
    """Sanitize title for use in filename."""
    # Remove special characters, keep alphanumeric, spaces, hyphens, underscores
    sanitized = re.sub(r'[^\w\s-]', '', title)
    # Replace multiple spaces/hyphens with single underscore
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized

def main():
    """Main function to process all stream videos."""
    root = Path(__file__).resolve().parent.parent.parent
    input_dir = root / "input" / "stream"
    output_dir = root / "output" / "stream"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("🎬 Stream Video Generation")
    print("=" * 60)
    print(f"📁 Input directory: {input_dir}")
    print(f"📁 Output directory: {output_dir}")
    print()
    
    # Find numbered JSON files
    json_files = find_numbered_json_files(str(input_dir))
    
    if not json_files:
        print("❌ No numbered JSON files found in input/stream/")
        print("   Expected format: 1.json, 2.json, 3.json, etc.")
        return 1
    
    print(f"📋 Found {len(json_files)} JSON file(s):")
    for number, file_path in json_files:
        print(f"   {number}. {Path(file_path).name}")
    print()
    
    # Import processor using importlib
    processor_path = Path(__file__).resolve().parent / "process_stream_videos.py"
    spec = importlib.util.spec_from_file_location("process_stream_videos", processor_path)
    processor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(processor_module)
    process_single_stream_video = processor_module.process_single_stream_video
    
    # Process each file
    successful = []
    failed = []
    
    for idx, (number, json_file) in enumerate(json_files):
        is_last = (idx == len(json_files) - 1)
        
        print(f"\n{'='*60}")
        print(f"Processing video {number}/{len(json_files)}")
        if is_last:
            print("   (Last video - outro will be added)")
        print(f"{'='*60}")
        
        try:
            result = process_single_stream_video(
                json_file,
                str(output_dir),
                is_last=is_last
            )
            
            if result:
                successful.append((number, result))
                print(f"\n✅ Video {number} completed: {Path(result).name}")
            else:
                failed.append((number, json_file))
                print(f"\n❌ Video {number} failed")
        except Exception as e:
            failed.append((number, json_file))
            print(f"\n❌ Video {number} failed with error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Processing Summary")
    print("=" * 60)
    print(f"✅ Successful: {len(successful)}")
    for number, path in successful:
        print(f"   {number}. {Path(path).name}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for number, path in failed:
            print(f"   {number}. {Path(path).name}")
    
    print(f"\n📁 Output directory: {output_dir}")
    
    if successful:
        print("\n💡 Next steps:")
        print("   - Videos are ready in output/stream/")
        print("   - Use these videos for streaming or further processing")
    
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())

