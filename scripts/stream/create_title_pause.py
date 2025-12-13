"""
Create a 3-second title pause video with black background and title text.
Supports multi-line titles with customizable margins and center line styling.
"""
import os
import subprocess
import textwrap
from pathlib import Path

def create_title_pause(
    title: str,
    output_path: str,
    duration: float = 3.0,
    width: int = 1080,
    height: int = 1920,
    margin_left: int = 100,
    margin_right: int = 100,
    font_size_normal: int = 72,
    font_size_center: int = 300,
    center_line_color: str = "yellow",
    normal_line_color: str = "white",
    line_spacing: int = 20,
    visual_gap_adjustment: int = 5
):
    """
    Create a 3-second black background video with multi-line title text.
    
    Args:
        title: Title text to display (will be wrapped into multiple lines)
        output_path: Path to save the video
        duration: Duration in seconds (default 3.0)
        width: Video width (default 1080)
        height: Video height (default 1920)
        margin_left: Left margin in pixels (default 100)
        margin_right: Right margin in pixels (default 100)
        font_size_normal: Font size for non-center lines (default 72)
        font_size_center: Font size for center line (default 96)
        center_line_color: Color for center line (default "yellow")
        normal_line_color: Color for other lines (default "white")
        line_spacing: Spacing between lines in pixels (default 20)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Load stream config to get apostrophe replacement setting
    root = Path(__file__).resolve().parent.parent.parent
    stream_config_file = root / "stream_config.json"
    apostrophe_replacement = "'"  # Default
    replace_curly_quotes = True  # Default
    
    if stream_config_file.exists():
        try:
            import json
            with open(stream_config_file, "r", encoding="utf-8") as f:
                stream_config = json.load(f)
            text_processing_config = stream_config.get("text_processing", {})
            apostrophe_replacement = text_processing_config.get("apostrophe_replacement", "'")
            replace_curly_quotes = text_processing_config.get("replace_curly_quotes", True)
        except:
            pass  # Use defaults if config can't be loaded
    
    # Normalize quotes/apostrophes in title for proper font rendering
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
    
    title = normalize_quotes(title)
    
    # Get font file path
    root = Path(__file__).resolve().parent.parent.parent
    font_file = root / "Game of Thrones.ttf"
    
    if not font_file.exists():
        raise FileNotFoundError(f"Font file not found: {font_file}")
    
    # Use absolute path and ensure it's properly escaped for ffmpeg
    font_file_abs = str(font_file.resolve())
    
    # Calculate available width for text
    available_width = width - margin_left - margin_right
    
    # Better text wrapping: use a more accurate character width estimation
    # For Game of Thrones font, characters are roughly 0.5-0.7x the font size in width
    # Use a conservative estimate to avoid overflow
    avg_char_width = font_size_normal * 0.55
    max_chars_per_line = int(available_width / avg_char_width)
    
    # Remove hashtags and clean up title for display
    # Split by spaces but preserve the words
    words = title.split()
    # Filter out hashtags if configured (default: true)
    # This is handled by the calling code, but we can also do it here as a safety measure
    # For now, we'll keep hashtags unless explicitly filtered by the config
    
    # Wrap text into lines using a better algorithm
    lines = []
    current_line = []
    current_line_chars = 0
    
    for word in words:
        # Calculate width if we add this word
        word_with_space = word if not current_line else ' ' + word
        word_width = len(word_with_space) * avg_char_width
        new_line_chars = current_line_chars + len(word_with_space)
        
        # Check if adding this word would exceed the line
        if new_line_chars <= max_chars_per_line:
            # Word fits, add it to current line
            current_line.append(word)
            current_line_chars = new_line_chars
        else:
            # Word doesn't fit, start a new line
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_line_chars = len(word)
    
    # Add remaining words
    if current_line:
        lines.append(' '.join(current_line))
    
    # Debug output
    print(f"      Title wrapped into {len(lines)} line(s):")
    for i, line in enumerate(lines):
        print(f"         Line {i+1}: {line}")
    
    # If only one line, make it the center line
    if len(lines) == 1:
        lines = [lines[0]]
    
    # Determine center line index
    center_line_idx = len(lines) // 2
    
    # Escape text for ffmpeg drawtext filter
    def escape_text(text):
        """Escape special characters for ffmpeg drawtext filter.
        For drawtext, we'll use a workaround: replace apostrophe with a placeholder
        or use proper escaping. Actually, let's try using the textfile approach or
        proper escaping for single quotes.
        For single quotes in ffmpeg, to include an apostrophe, we escape it as \'
        But we need to ensure Python preserves the backslash correctly.
        """
        if not text:
            return text
        # Order matters - escape backslashes first
        text = text.replace("\\", "\\\\")
        # For ffmpeg drawtext with single quotes, escape apostrophe properly
        # Use raw string approach: replace ' with \' but ensure it's preserved
        # Actually, in Python strings, \\' becomes \' when passed to subprocess
        text = text.replace("'", "\\'")
        # Escape other special characters that need escaping in drawtext
        text = text.replace(":", "\\:")
        text = text.replace("[", "\\[")
        text = text.replace("]", "\\]")
        # Don't escape commas - they're used to separate filters
        # text = text.replace(",", "\\,")  # Don't escape commas
        text = text.replace("=", "\\=")
        text = text.replace("%", "\\%")
        return text
    
    # Ensure title text doesn't accidentally contain font name
    # (safety check - shouldn't happen but just in case)
    if "Game of Thrones" in title or "game of thrones" in title.lower():
        print(f"      ⚠️  Warning: Title contains 'Game of Thrones' - this might cause display issues")
    
    # Build drawtext filters for each line
    drawtext_filters = []
    
    # Calculate line heights
    line_heights = []
    for i, line in enumerate(lines):
        is_center = (i == center_line_idx)
        line_height = font_size_center if is_center else font_size_normal
        line_heights.append(line_height)
    
    # Calculate Y positions using the same simple approach as batch_trim_videos.sh
    # This approach uses line_height = font_size + line_spacing and simply increments Y
    # It naturally creates equal spacing between lines
    
    y_positions = []
    
    # Calculate line heights: font_size + line_spacing (same as bash script)
    # The bash script uses: base_line_height = font_size + LINE_HEIGHT_SPACING
    base_line_height = font_size_normal + line_spacing
    center_line_height = font_size_center + line_spacing
    
    # Calculate total text height (sum of all line heights)
    total_text_height = 0
    for i, line in enumerate(lines):
        is_center = (i == center_line_idx)
        line_height = center_line_height if is_center else base_line_height
        total_text_height += line_height
    
    # Calculate start Y position to center the entire text block vertically
    # Same as bash script: start_y = (height - total_text_height) / 2
    start_y = (height - total_text_height) // 2
    
    # In FFmpeg drawtext, y is the baseline position
    # The bash script treats start_y as the Y position for the first line
    # and increments by line_height for each subsequent line
    # This works because line_height = font_size + line_spacing naturally creates
    # the correct spacing (accounting for text extending above/below baseline)
    current_y = start_y
    
    # Calculate Y positions by incrementing by line height for each line
    # This exactly matches the bash script's approach
    for i, line in enumerate(lines):
        is_center = (i == center_line_idx)
        line_height = center_line_height if is_center else base_line_height
        
        # Store the baseline position for this line (same as bash script's current_y)
        y_positions.append(current_y)
        
        # Move to next line: increment by line height (same as bash script)
        # The bash script does: current_y = current_y + current_line_height
        current_y = current_y + line_height
    
    # Create temporary text files for each line to avoid escaping issues
    import tempfile
    temp_text_files = []
    temp_dir = os.path.dirname(output_path)
    
    for i, line in enumerate(lines):
        is_center = (i == center_line_idx)
        font_size = font_size_center if is_center else font_size_normal
        text_color = center_line_color if is_center else normal_line_color
        y_pos = y_positions[i]
        
        # Create a temporary text file for this line
        temp_text_file = os.path.join(temp_dir, f"title_line_{i}.txt")
        with open(temp_text_file, "w", encoding="utf-8") as f:
            f.write(line)
        temp_text_files.append(temp_text_file)
        
        # Escape font file path for ffmpeg (handle spaces and special chars)
        font_file_escaped = font_file_abs.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
        
        # Use textfile option to read text from file - avoids all escaping issues
        drawtext_filter = (
            f"drawtext=textfile='{temp_text_file}':"
            f"fontfile='{font_file_escaped}':"
            f"fontsize={font_size}:"
            f"fontcolor={text_color}:"
            f"x=(w+{margin_left}-{margin_right}-text_w)/2:"
            f"y={y_pos}:"
            f"borderw=2:"
            f"bordercolor=black"
        )
        drawtext_filters.append(drawtext_filter)
    
    # Combine all drawtext filters with commas
    # For ffmpeg, multiple filters can be comma-separated
    vf_filter = ",".join(drawtext_filters)
    
    # Create black background video with multi-line title text
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={width}x{height}:d={duration}",
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-t", str(duration),
        "-an",  # No audio
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"   ✅ Title pause created: {output_path}")
        print(f"      Lines: {len(lines)}, Center line: {center_line_idx + 1} ({font_size_center}px, {center_line_color})")
        
        # Cleanup temporary text files
        for temp_file in temp_text_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to create title pause: {e.stderr}")
        # Cleanup temporary text files even on error
        for temp_file in temp_text_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        raise

if __name__ == "__main__":
    # Test
    test_output = "output/stream/test_title_pause.mp4"
    create_title_pause("Test Title", test_output)
    print(f"Test title pause created at {test_output}")

