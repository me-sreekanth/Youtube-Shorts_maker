#!/bin/bash

# Generate playlist file for YouTube Live streaming
# Usage: ./generate_live_playlist.sh

set -e

PAUSED_DIR="videos/paused"
PLAYLIST_FILE="live_playlist.txt"

echo "📋 Generating Live Playlist"
echo "============================"

# Check if paused directory exists
if [ ! -d "$PAUSED_DIR" ]; then
    echo "❌ Error: Directory '$PAUSED_DIR' not found!"
    echo "   Run batch_trim_videos.sh first to process videos."
    exit 1
fi

# Count videos
video_count=$(find "$PAUSED_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" \) | wc -l | tr -d ' ')

if [ "$video_count" -eq 0 ]; then
    echo "❌ No video files found in '$PAUSED_DIR'"
    exit 1
fi

# Get absolute path to paused directory
abs_paused_dir=$(cd "$PAUSED_DIR" && pwd)

# Generate playlist file
echo "# YouTube Live Playlist" > "$PLAYLIST_FILE"
echo "# Generated on $(date)" >> "$PLAYLIST_FILE"
echo "# Total videos: $video_count" >> "$PLAYLIST_FILE"
echo "" >> "$PLAYLIST_FILE"

# Add each video to playlist (sorted by filename)
find "$PAUSED_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" \) | sort | while IFS= read -r video; do
    [ -f "$video" ] || continue
    abs_path=$(cd "$(dirname "$video")" && pwd)/$(basename "$video")
    echo "file '$abs_path'" >> "$PLAYLIST_FILE"
done

echo "✅ Playlist generated: $PLAYLIST_FILE"
echo "📊 Total videos: $video_count"
echo ""
echo "💡 To stream, run:"
echo "   ./stream_to_youtube.sh"
echo ""

