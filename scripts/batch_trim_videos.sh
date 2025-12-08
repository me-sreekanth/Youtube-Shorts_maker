#!/bin/bash

# Batch process YouTube Shorts: Remove outro and add pause
# Usage: OUTRO_SECONDS=2 PAUSE_SECONDS=1 ./batch_trim_videos.sh

set -e

# Configuration (can be overridden by environment variables)
OUTRO_SECONDS=${OUTRO_SECONDS:-2.3}
INTRO_PAUSE_SECONDS=${INTRO_PAUSE_SECONDS:-3}  # Black screen at beginning

# Text styling constants (adjust these values as needed)
FONT_SIZE=${FONT_SIZE:-30}              # Font size in pixels
LINE_HEIGHT_SPACING=${LINE_HEIGHT_SPACING:-30}  # Additional pixels between lines (added to font size)
MARGIN_PIXELS=${MARGIN_PIXELS:-300}     # Fixed margin in pixels on each side
CENTER_WORD_FONT_SIZE=${CENTER_WORD_FONT_SIZE:-40}  # Font size for center word(s) in pixels
CENTER_WORD_COLOR=${CENTER_WORD_COLOR:-yellow}  # Color for center word(s)

# Directories
INPUT_DIR="videos/originals"
TRIMMED_DIR="videos/trimmed"
PAUSED_DIR="videos/paused"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🎬 Batch Video Processing"
echo "========================"
echo "📁 Input: $INPUT_DIR"
echo "✂️  Trimmed output: $TRIMMED_DIR"
echo "⏸️  Paused output: $PAUSED_DIR"
echo "🔪 Removing last ${OUTRO_SECONDS}s from each video"
echo "⏸️  Adding ${INTRO_PAUSE_SECONDS}s black screen at the beginning"
echo ""

# Create output directories
mkdir -p "$TRIMMED_DIR"
mkdir -p "$PAUSED_DIR"

# Check if input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ Error: Input directory '$INPUT_DIR' not found!"
    exit 1
fi

# Count videos
video_count=$(find "$INPUT_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" \) | wc -l | tr -d ' ')

if [ "$video_count" -eq 0 ]; then
    echo "❌ No video files found in '$INPUT_DIR'"
    exit 1
fi

echo "📊 Found $video_count video(s) to process"
echo ""

processed=0
failed=0

# Process each video
for video in "$INPUT_DIR"/*.mp4 "$INPUT_DIR"/*.mov "$INPUT_DIR"/*.MP4 "$INPUT_DIR"/*.MOV; do
    # Check if file exists (glob might not match)
    [ -f "$video" ] || continue
    
    filename=$(basename "$video")
    name="${filename%.*}"
    extension="${filename##*.}"
    
    echo "📹 Processing: $filename"
    
    # Get video duration using ffprobe
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
    
    if [ -z "$duration" ] || [ "$duration" = "N/A" ]; then
        echo "   ⚠️  Could not read duration, skipping..."
        failed=$((failed + 1))
        continue
    fi
    
    # Calculate new duration (remove outro) using awk for floating point
    new_duration=$(awk "BEGIN {printf \"%.2f\", $duration - $OUTRO_SECONDS}")
    
    # Check if new duration is valid
    if awk "BEGIN {exit !($new_duration <= 0)}"; then
        echo "   ⚠️  Video too short (${duration}s), skipping..."
        failed=$((failed + 1))
        continue
    fi
    
    trimmed_output="$TRIMMED_DIR/$filename"
    paused_output="$PAUSED_DIR/$filename"
    
    # Step 1: Trim video (remove outro)
    echo "   ✂️  Trimming to ${new_duration}s..."
    if ffmpeg -y -i "$video" -t "$new_duration" -c copy "$trimmed_output" 2>/dev/null; then
        echo "   ✅ Trimmed: $trimmed_output"
    else
        echo "   ❌ Failed to trim, trying with re-encoding..."
        if ffmpeg -y -i "$video" -t "$new_duration" -c:v libx264 -c:a aac "$trimmed_output" 2>/dev/null; then
            echo "   ✅ Trimmed (re-encoded): $trimmed_output"
        else
            echo "   ❌ Failed to trim $filename"
            failed=$((failed + 1))
            continue
        fi
    fi
    
    # Step 2: Add black screen at the beginning with title
    echo "   ⏸️  Adding ${INTRO_PAUSE_SECONDS}s black screen with title at the beginning..."
    
    # Extract title from filename (remove extension and clean up)
    title="${name}"
    # Remove common patterns like "#matrix #shorts" if present
    title=$(echo "$title" | sed 's/#[^ ]*//g' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
    
    echo "   📝 Title: $title"
    
    # Get video dimensions from trimmed video
    video_info=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of default=noprint_wrappers=1 "$trimmed_output" 2>/dev/null)
    width=$(echo "$video_info" | grep width | cut -d= -f2)
    height=$(echo "$video_info" | grep height | cut -d= -f2)
    
    echo "   🔍 Video dimensions: ${width}x${height}"
    
    # Determine font file (use Game of Thrones if available, fallback to system font)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BASE_DIR="$(dirname "$SCRIPT_DIR")"
    FONT_FILE="$BASE_DIR/Game of Thrones.ttf"
    
    if [ ! -f "$FONT_FILE" ]; then
        # Try Montserrat as fallback
        FONT_FILE="$BASE_DIR/Montserrat.ttf"
    fi
    
    # Use system font if custom fonts not found
    if [ ! -f "$FONT_FILE" ]; then
        # macOS default font
        FONT_FILE="/System/Library/Fonts/Helvetica.ttc"
    fi
    
    # Use configurable constants
    font_size=$FONT_SIZE
    margin_pixels=$MARGIN_PIXELS
    text_width=$((width - 2 * margin_pixels))
    
    # Ensure text width is at least 100px
    if [ "$text_width" -lt 100 ]; then
        text_width=100
        margin_pixels=$(( (width - text_width) / 2 ))
    fi
    
    echo "   🔤 Using font: $(basename "$FONT_FILE"), size: ${font_size}px"
    echo "   📏 Text area: ${text_width}px wide (${margin_pixels}px margin on each side)"
    
    # Create black frame with title text
    temp_black_frame=$(mktemp /tmp/black_intro_XXXXXX.mp4)
    temp_concat_list=$(mktemp /tmp/concat_list_XXXXXX.txt)
    
    # Split title into multiple lines that fit within margins
    # For Game of Thrones font, characters are wider - use conservative estimate
    # Use 0.4 * font_size for more accurate width calculation
    chars_per_line=$(awk "BEGIN {printf \"%.0f\", $text_width / ($font_size * 0.4)}")
    
    # Set a maximum limit based on font size to force wrapping
    # For font size 16, limit to ~20-25 characters max per line
    if [ "$font_size" -le 20 ]; then
        max_chars=22
        if [ "$chars_per_line" -gt "$max_chars" ]; then
            chars_per_line=$max_chars
        fi
    fi
    
    # Ensure reasonable minimum (at least 10 characters per line)
    if [ "$chars_per_line" -lt 10 ]; then
        chars_per_line=10
    fi
    
    echo "   📐 Estimated ${chars_per_line} characters per line (text width: ${text_width}px, font: ${font_size}px)"
    
    # Split title into words and create lines
    temp_lines_file=$(mktemp /tmp/title_lines_XXXXXX.txt)
    
    # Convert title to array of words
    IFS=' ' read -ra words <<< "$title"
    
    current_line=""
    for word in "${words[@]}"; do
        if [ -z "$current_line" ]; then
            # First word
            current_line="$word"
        else
            # Check if adding this word would exceed line length
            test_line="$current_line $word"
            test_length=${#test_line}
            
            # Be more strict: if adding the word would exceed, start new line
            # Account for space character
            if [ "$test_length" -le "$chars_per_line" ]; then
                # Fits on current line
                current_line="$test_line"
            else
                # Current line is full, save it and start new line
                if [ -n "$current_line" ]; then
                    echo "$current_line" >> "$temp_lines_file"
                fi
                current_line="$word"
            fi
        fi
    done
    
    # Add the last line if it exists
    if [ -n "$current_line" ]; then
        echo "$current_line" >> "$temp_lines_file"
    fi
    
    # Count lines and verify
    line_count=$(wc -l < "$temp_lines_file" 2>/dev/null | tr -d ' ' || echo "0")
    
    # If no lines were created, use the original title as a single line
    if [ "$line_count" -eq 0 ] || [ ! -s "$temp_lines_file" ]; then
        echo "$title" > "$temp_lines_file"
        line_count=1
    fi
    
    # Debug: Show the lines that were created
    echo "   📄 Lines created:"
    line_num=1
    while IFS= read -r line_text || [ -n "$line_text" ]; do
        if [ -n "$line_text" ]; then
            echo "      Line $line_num: $line_text"
            line_num=$((line_num + 1))
        fi
    done < "$temp_lines_file"
    
    # Calculate vertical spacing (center the text block)
    # Use configurable line height spacing
    # For center line with larger font, we need to account for the extra height
    base_line_height=$((font_size + LINE_HEIGHT_SPACING))
    
    # Calculate total height accounting for center line(s) with larger font
    if [ "$line_count" -gt 1 ]; then
        # Multiple lines: check if we have center line(s) with larger font
        if [ $((line_count % 2)) -eq 1 ]; then
            # Odd: one center line
            center_line_height=$((CENTER_WORD_FONT_SIZE + LINE_HEIGHT_SPACING))
            total_text_height=$(( (line_count - 1) * base_line_height + center_line_height ))
        else
            # Even: two center lines
            center_line_height=$((CENTER_WORD_FONT_SIZE + LINE_HEIGHT_SPACING))
            total_text_height=$(( (line_count - 2) * base_line_height + 2 * center_line_height ))
        fi
    else
        # Single line
        total_text_height=$base_line_height
    fi
    
    start_y=$(( (height - total_text_height) / 2 ))
    line_height=$base_line_height  # Default line height for regular lines
    
    echo "   📝 Title split into $line_count line(s)"
    
    # Get absolute paths
    abs_font_file=$(cd "$(dirname "$FONT_FILE")" && pwd)/$(basename "$FONT_FILE")
    
    # Get audio sample rate from trimmed video for matching
    audio_info=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1 "$trimmed_output" 2>/dev/null)
    sample_rate=$(echo "$audio_info" | grep sample_rate | cut -d= -f2)
    
    # Default to 44100 if not found
    if [ -z "$sample_rate" ]; then
        sample_rate=44100
    fi
    
    # Build drawtext filter chain for multiple lines
    # Highlight center line(s) in yellow with larger font
    # Read lines and create drawtext filters for each
    drawtext_filters=""
    line_num=0
    current_y=$start_y
    
    # Determine which line(s) to highlight (center line)
    if [ "$line_count" -eq 1 ]; then
        # Single line: highlight center word(s)
        center_line_idx=0
        highlight_center_word=true
    else
        # Multiple lines: highlight center line(s)
        highlight_center_word=false
        if [ $((line_count % 2)) -eq 1 ]; then
            # Odd number of lines: highlight middle line
            center_line_idx=$((line_count / 2))
        else
            # Even number of lines: highlight middle two lines
            center_line_idx=$((line_count / 2 - 1))
            center_line_idx2=$((line_count / 2))
        fi
    fi
    
    # Read lines from file and build filter chain
    while IFS= read -r line_text || [ -n "$line_text" ]; do
        # Trim whitespace
        line_text=$(echo "$line_text" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [ -n "$line_text" ]; then
            escaped_line=$(printf '%s' "$line_text" | sed "s/\\\\/\\\\\\\\/g" | sed "s/'/\\\\'/g" | sed "s/:/\\\\:/g" | sed "s/\[/\\\\[/g" | sed "s/\]/\\\\]/g")
            
            # Check if this is a center line to highlight
            is_center_line=false
            if [ "$highlight_center_word" = "true" ]; then
                # Single line: highlight center word
                IFS=' ' read -ra words <<< "$line_text"
                word_count=${#words[@]}
                if [ "$word_count" -gt 1 ]; then
                    # Find center word(s)
                    if [ $((word_count % 2)) -eq 1 ]; then
                        center_idx=$((word_count / 2))
                        center_words="${words[$center_idx]}"
                    else
                        center_idx=$((word_count / 2 - 1))
                        center_words="${words[$center_idx]} ${words[$((center_idx + 1))]}"
                    fi
                    escaped_center=$(printf '%s' "$center_words" | sed "s/\\\\/\\\\\\\\/g" | sed "s/'/\\\\'/g" | sed "s/:/\\\\:/g" | sed "s/\[/\\\\[/g" | sed "s/\]/\\\\]/g")
                    
                    # Render full line in white, center word in yellow
                    line_filter_white="drawtext=text='$escaped_line':fontfile='$abs_font_file':fontcolor=white:fontsize=$font_size:x=(w-text_w)/2:y=$current_y"
                    line_filter_yellow="drawtext=text='$escaped_center':fontfile='$abs_font_file':fontcolor=$CENTER_WORD_COLOR:fontsize=$CENTER_WORD_FONT_SIZE:x=(w-text_w)/2:y=$current_y"
                    
                    if [ -z "$drawtext_filters" ]; then
                        drawtext_filters="$line_filter_white,$line_filter_yellow"
                    else
                        drawtext_filters="$drawtext_filters,$line_filter_white,$line_filter_yellow"
                    fi
                    echo "   🎨 Line $((line_num + 1)) at y=$current_y: '$line_text' (center word '$center_words' in $CENTER_WORD_COLOR)"
                    current_line_height=$line_height
                else
                    # Single word - render normally
                    line_filter="drawtext=text='$escaped_line':fontfile='$abs_font_file':fontcolor=white:fontsize=$font_size:x=(w-text_w)/2:y=$current_y"
                    if [ -z "$drawtext_filters" ]; then
                        drawtext_filters="$line_filter"
                    else
                        drawtext_filters="$drawtext_filters,$line_filter"
                    fi
                    echo "   🎨 Line $((line_num + 1)) at y=$current_y: '$line_text'"
                    current_line_height=$line_height
                fi
            else
                    # Multiple lines: check if this is center line
                    if [ "$line_num" -eq "$center_line_idx" ] || ([ -n "${center_line_idx2:-}" ] && [ "$line_num" -eq "$center_line_idx2" ]); then
                        # This is a center line - render in yellow with larger font
                        line_filter="drawtext=text='$escaped_line':fontfile='$abs_font_file':fontcolor=$CENTER_WORD_COLOR:fontsize=$CENTER_WORD_FONT_SIZE:x=(w-text_w)/2:y=$current_y"
                        echo "   🎨 Line $((line_num + 1)) at y=$current_y: '$line_text' (CENTER LINE in $CENTER_WORD_COLOR, size $CENTER_WORD_FONT_SIZE)"
                        # Use larger line height for center line to maintain spacing
                        current_line_height=$((CENTER_WORD_FONT_SIZE + LINE_HEIGHT_SPACING))
                    else
                        # Regular line - render in white with normal font
                        line_filter="drawtext=text='$escaped_line':fontfile='$abs_font_file':fontcolor=white:fontsize=$font_size:x=(w-text_w)/2:y=$current_y"
                        echo "   🎨 Line $((line_num + 1)) at y=$current_y: '$line_text'"
                        current_line_height=$line_height
                    fi
                    
                    if [ -z "$drawtext_filters" ]; then
                        drawtext_filters="$line_filter"
                    else
                        drawtext_filters="$drawtext_filters,$line_filter"
                    fi
                fi
                
                current_y=$((current_y + current_line_height))
                line_num=$((line_num + 1))
        fi
    done < "$temp_lines_file"
    
    echo "   📝 Built $line_num drawtext filter(s) for $line_count line(s)"
    
    # Create black frame with title text (multiple lines) and silent audio track
    echo "   🎬 Creating ${INTRO_PAUSE_SECONDS}s black screen with title..."
    
    # Check if font file exists
    if [ ! -f "$abs_font_file" ]; then
        echo "   ⚠️  Font file not found: $abs_font_file, using system font"
        use_system_font=true
    else
        use_system_font=false
    fi
    
    if [ "$use_system_font" = "false" ]; then
        # Try with custom font first
        if ffmpeg -y \
            -f lavfi -i "color=c=black:size=${width}x${height}:duration=$INTRO_PAUSE_SECONDS" \
            -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=$sample_rate" \
            -vf "$drawtext_filters" \
            -c:v libx264 -pix_fmt yuv420p -r 30 \
            -c:a aac -b:a 128k \
            -t "$INTRO_PAUSE_SECONDS" \
            -movflags +faststart \
            "$temp_black_frame" >/tmp/ffmpeg_black.log 2>&1; then
            # Verify the file was created and is valid
            if [ -f "$temp_black_frame" ] && [ -s "$temp_black_frame" ]; then
                # Check if it's a valid video file
                if ffprobe -v error "$temp_black_frame" >/dev/null 2>&1; then
                    echo "   ✅ Black screen with title created"
                else
                    echo "   ❌ Black frame file is invalid/corrupted"
                    echo "   🔍 ffmpeg output:"
                    tail -10 /tmp/ffmpeg_black.log | sed 's/^/      /'
                    use_system_font=true
                fi
            else
                echo "   ❌ Black frame file was not created"
                echo "   🔍 ffmpeg output:"
                tail -10 /tmp/ffmpeg_black.log | sed 's/^/      /'
                use_system_font=true
            fi
        else
            echo "   ⚠️  Failed with custom font, trying system font..."
            echo "   🔍 ffmpeg output:"
            tail -10 /tmp/ffmpeg_black.log | sed 's/^/      /'
            use_system_font=true
        fi
    fi
    
    if [ "$use_system_font" = "true" ]; then
        # Fallback: try without fontfile (use system default)
        echo "   ⚠️  Retrying with system font..."
        drawtext_filters_system=""
        current_y=$start_y
        
        # Re-read lines and build system font filters
        # Apply same center line/word highlighting logic
        system_line_num=0
        system_current_y=$start_y
        
        # Determine center line(s) same as before
        if [ "$line_count" -eq 1 ]; then
            highlight_center_word_system=true
        else
            highlight_center_word_system=false
            if [ $((line_count % 2)) -eq 1 ]; then
                center_line_idx_system=$((line_count / 2))
            else
                center_line_idx_system=$((line_count / 2 - 1))
                center_line_idx2_system=$((line_count / 2))
            fi
        fi
        
        while IFS= read -r line_text || [ -n "$line_text" ]; do
            line_text=$(echo "$line_text" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [ -n "$line_text" ]; then
                escaped_line=$(printf '%s' "$line_text" | sed "s/\\\\/\\\\\\\\/g" | sed "s/'/\\\\'/g" | sed "s/:/\\\\:/g" | sed "s/\[/\\\\[/g" | sed "s/\]/\\\\]/g")
                
                if [ "$highlight_center_word_system" = "true" ]; then
                    # Single line: highlight center word
                    IFS=' ' read -ra words <<< "$line_text"
                    word_count=${#words[@]}
                    if [ "$word_count" -gt 1 ]; then
                        if [ $((word_count % 2)) -eq 1 ]; then
                            center_idx=$((word_count / 2))
                            center_words="${words[$center_idx]}"
                        else
                            center_idx=$((word_count / 2 - 1))
                            center_words="${words[$center_idx]} ${words[$((center_idx + 1))]}"
                        fi
                        escaped_center=$(printf '%s' "$center_words" | sed "s/\\\\/\\\\\\\\/g" | sed "s/'/\\\\'/g" | sed "s/:/\\\\:/g" | sed "s/\[/\\\\[/g" | sed "s/\]/\\\\]/g")
                        
                        line_filter_white="drawtext=text='$escaped_line':fontcolor=white:fontsize=$font_size:x=(w-text_w)/2:y=$system_current_y"
                        line_filter_yellow="drawtext=text='$escaped_center':fontcolor=$CENTER_WORD_COLOR:fontsize=$CENTER_WORD_FONT_SIZE:x=(w-text_w)/2:y=$system_current_y"
                        
                        if [ -z "$drawtext_filters_system" ]; then
                            drawtext_filters_system="$line_filter_white,$line_filter_yellow"
                        else
                        drawtext_filters_system="$drawtext_filters_system,$line_filter_white,$line_filter_yellow"
                    fi
                    system_current_line_height=$line_height
                else
                    line_filter="drawtext=text='$escaped_line':fontcolor=white:fontsize=$font_size:x=(w-text_w)/2:y=$system_current_y"
                    if [ -z "$drawtext_filters_system" ]; then
                        drawtext_filters_system="$line_filter"
                    else
                        drawtext_filters_system="$drawtext_filters_system,$line_filter"
                    fi
                    system_current_line_height=$line_height
                fi
            else
                    # Multiple lines: check if center line
                    if [ "$system_line_num" -eq "$center_line_idx_system" ] || ([ -n "${center_line_idx2_system:-}" ] && [ "$system_line_num" -eq "$center_line_idx2_system" ]); then
                        line_filter="drawtext=text='$escaped_line':fontcolor=$CENTER_WORD_COLOR:fontsize=$CENTER_WORD_FONT_SIZE:x=(w-text_w)/2:y=$system_current_y"
                        system_current_line_height=$((CENTER_WORD_FONT_SIZE + LINE_HEIGHT_SPACING))
                    else
                        line_filter="drawtext=text='$escaped_line':fontcolor=white:fontsize=$font_size:x=(w-text_w)/2:y=$system_current_y"
                        system_current_line_height=$line_height
                    fi
                    
                    if [ -z "$drawtext_filters_system" ]; then
                        drawtext_filters_system="$line_filter"
                    else
                        drawtext_filters_system="$drawtext_filters_system,$line_filter"
                    fi
                fi
                system_current_y=$((system_current_y + system_current_line_height))
                system_line_num=$((system_line_num + 1))
            fi
        done < "$temp_lines_file"
        
        if [ -z "$drawtext_filters_system" ]; then
            echo "   ❌ No drawtext filters generated for system font"
            failed=$((failed + 1))
            rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
            continue
        fi
        
        if ffmpeg -y \
            -f lavfi -i "color=c=black:size=${width}x${height}:duration=$INTRO_PAUSE_SECONDS" \
            -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=$sample_rate" \
            -vf "$drawtext_filters_system" \
            -c:v libx264 -pix_fmt yuv420p -r 30 \
            -c:a aac -b:a 128k \
            -t "$INTRO_PAUSE_SECONDS" \
            -movflags +faststart \
            "$temp_black_frame" >/tmp/ffmpeg_black.log 2>&1; then
            # Verify the file was created and is valid
            if [ -f "$temp_black_frame" ] && [ -s "$temp_black_frame" ] && ffprobe -v error "$temp_black_frame" >/dev/null 2>&1; then
                echo "   ✅ Black screen with title created (system font)"
            else
                echo "   ❌ Black frame file is invalid/corrupted (system font)"
                echo "   🔍 ffmpeg output:"
                tail -15 /tmp/ffmpeg_black.log | sed 's/^/      /'
                failed=$((failed + 1))
                rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
                continue
            fi
        else
            echo "   ❌ Failed to create black screen with title"
            echo "   🔍 ffmpeg output:"
            tail -15 /tmp/ffmpeg_black.log | sed 's/^/      /'
            failed=$((failed + 1))
            rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
            continue
        fi
    fi
    
    # Create concat list: black screen first, then trimmed video
    echo "file '$(cd "$(dirname "$temp_black_frame")" && pwd)/$(basename "$temp_black_frame")'" > "$temp_concat_list"
    echo "file '$(cd "$(dirname "$trimmed_output")" && pwd)/$(basename "$trimmed_output")'" >> "$temp_concat_list"
    
    # Concatenate black screen with trimmed video
    # Both files now have audio tracks, so concatenation should preserve audio
    echo "   🔗 Concatenating black screen + trimmed video..."
    
    # Verify files exist before concatenation
    if [ ! -f "$temp_black_frame" ]; then
        echo "   ❌ Black frame file not found: $temp_black_frame"
        failed=$((failed + 1))
        rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
        continue
    fi
    
    if [ ! -f "$trimmed_output" ]; then
        echo "   ❌ Trimmed video file not found: $trimmed_output"
        failed=$((failed + 1))
        rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
        continue
    fi
    
    # Use absolute paths in concat list to avoid path issues
    abs_black_frame=$(cd "$(dirname "$temp_black_frame")" && pwd)/$(basename "$temp_black_frame")
    abs_trimmed=$(cd "$(dirname "$trimmed_output")" && pwd)/$(basename "$trimmed_output")
    
    # Update concat list with absolute paths
    echo "file '$abs_black_frame'" > "$temp_concat_list"
    echo "file '$abs_trimmed'" >> "$temp_concat_list"
    
    # Run ffmpeg concatenation
    # Capture output but check exit code, not grep result
    if ffmpeg -y -f concat -safe 0 -i "$temp_concat_list" \
        -c:v libx264 -c:a aac \
        "$paused_output" >/tmp/ffmpeg_concat.log 2>&1; then
        # Verify output file was created and has content
        if [ -f "$paused_output" ] && [ -s "$paused_output" ]; then
            output_size=$(ls -lh "$paused_output" | awk '{print $5}')
            echo "   ✅ Final video with intro pause: $paused_output ($output_size)"
            processed=$((processed + 1))
            rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
        else
            echo "   ❌ Output file was not created or is empty"
            failed=$((failed + 1))
            rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
        fi
    else
        echo "   ❌ Failed to concatenate video with black screen"
        echo "   🔍 Last few lines of ffmpeg output:"
        tail -5 /tmp/ffmpeg_concat.log | sed 's/^/      /'
        failed=$((failed + 1))
        rm -f "$temp_black_frame" "$temp_concat_list" "$temp_lines_file"
    fi
    
    echo ""
done

echo "========================"
echo -e "${GREEN}✅ Processed: $processed${NC}"
if [ "$failed" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Failed: $failed${NC}"
fi
echo ""
