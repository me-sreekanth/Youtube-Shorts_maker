#!/bin/bash

# Generate playlist file for YouTube Live streaming
# Usage: ./generate_live_playlist.sh

set -e

# Use stream videos directory (primary) or paused directory (fallback)
STREAM_DIR="output/stream"
PAUSED_DIR="videos/paused"
PLAYLIST_FILE="live_playlist.txt"

echo "📋 Generating Live Playlist"
echo "============================"

# Check for stream videos first (preferred)
if [ -d "$STREAM_DIR" ] && [ "$(find "$STREAM_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" \) | wc -l | tr -d ' ')" -gt 0 ]; then
    VIDEO_DIR="$STREAM_DIR"
    echo "📁 Using stream videos from: $VIDEO_DIR"
elif [ -d "$PAUSED_DIR" ] && [ "$(find "$PAUSED_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" \) | wc -l | tr -d ' ')" -gt 0 ]; then
    VIDEO_DIR="$PAUSED_DIR"
    echo "📁 Using paused videos from: $VIDEO_DIR"
else
    echo "❌ Error: No videos found in '$STREAM_DIR' or '$PAUSED_DIR'!"
    echo "   For stream videos: Run 'python3 scripts/stream/run_stream.py' first"
    echo "   For paused videos: Run 'batch_trim_videos.sh' first"
    exit 1
fi

# Count videos
video_count=$(find "$VIDEO_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" \) | wc -l | tr -d ' ')

if [ "$video_count" -eq 0 ]; then
    echo "❌ No video files found in '$VIDEO_DIR'"
    exit 1
fi

# Generate playlist file
echo "# YouTube Live Playlist" > "$PLAYLIST_FILE"
echo "# Generated on $(date)" >> "$PLAYLIST_FILE"
echo "# Source: $VIDEO_DIR" >> "$PLAYLIST_FILE"
echo "# Total videos: $video_count" >> "$PLAYLIST_FILE"
echo "" >> "$PLAYLIST_FILE"

# Add each video to playlist (sorted by filename for proper order)
find "$VIDEO_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mov" \) | sort | while IFS= read -r video; do
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

