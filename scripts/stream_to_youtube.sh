#!/bin/bash

# Stream videos to YouTube Live using ffmpeg
# Usage: YOUTUBE_STREAM_KEY=your_key ./stream_to_youtube.sh

set -e

PLAYLIST_FILE="live_playlist.txt"
RTMP_URL="rtmp://a.rtmp.youtube.com/live2"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "📺 YouTube Live Streaming"
echo "========================"

# Check for stream key
if [ -z "$YOUTUBE_STREAM_KEY" ]; then
    echo -e "${RED}❌ Error: YOUTUBE_STREAM_KEY environment variable not set!${NC}"
    echo ""
    echo "Usage:"
    echo "  export YOUTUBE_STREAM_KEY=your_stream_key_here"
    echo "  ./stream_to_youtube.sh"
    echo ""
    echo "Get your stream key from:"
    echo "  YouTube Studio > Go Live > Stream Settings"
    exit 1
fi

# Check if playlist exists
if [ ! -f "$PLAYLIST_FILE" ]; then
    echo -e "${YELLOW}⚠️  Playlist file not found. Generating...${NC}"
    ./scripts/generate_live_playlist.sh
fi

# Check if playlist has content
if [ ! -s "$PLAYLIST_FILE" ] || ! grep -q "^file " "$PLAYLIST_FILE"; then
    echo -e "${RED}❌ Error: Playlist file is empty or invalid!${NC}"
    echo "   Run: ./scripts/generate_live_playlist.sh"
    exit 1
fi

# Count videos in playlist
video_count=$(grep -c "^file " "$PLAYLIST_FILE" || echo "0")
echo "📋 Playlist: $PLAYLIST_FILE"
echo "📊 Videos: $video_count"
echo "🔑 Stream Key: ${YOUTUBE_STREAM_KEY:0:10}..."
echo ""
echo -e "${YELLOW}⚠️  Starting stream in 5 seconds...${NC}"
echo "   Press Ctrl+C to stop"
echo ""
sleep 5

# Stream URL
STREAM_URL="$RTMP_URL/$YOUTUBE_STREAM_KEY"

echo -e "${GREEN}🚀 Starting stream...${NC}"
echo ""

# Stream loop using concat demuxer
# This will loop the playlist forever
# Use stream_loop=-1 to loop infinitely
echo "🔄 Streaming playlist in loop..."
echo ""

ffmpeg -re -stream_loop -1 \
    -f concat -safe 0 -i "$PLAYLIST_FILE" \
    -c:v libx264 -preset veryfast -maxrate 3000k -bufsize 6000k \
    -pix_fmt yuv420p -g 50 -keyint_min 50 \
    -c:a aac -b:a 160k -ar 44100 \
    -f flv "$STREAM_URL" 2>&1 | while IFS= read -r line; do
    # Show progress but filter out verbose output
    if echo "$line" | grep -qE "(frame=|time=|bitrate=)" || echo "$line" | grep -qi "error"; then
        echo "$line"
    fi
done

