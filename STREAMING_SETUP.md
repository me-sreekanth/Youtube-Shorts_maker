# YouTube Live Streaming Setup Guide

## Overview
This guide will help you set up a continuous loop stream of your processed YouTube Shorts to YouTube Live.

## Prerequisites
- ✅ Videos processed in `videos/paused/` directory
- ✅ Playlist generated (`live_playlist.txt`)
- ✅ YouTube Live stream key
- ✅ `ffmpeg` installed

## Step 1: Get Your YouTube Stream Key

1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click **"Go Live"** in the top right
3. Click **"Stream"** tab
4. Under **"Stream Settings"**, find your **Stream Key**
5. Copy the stream key (it looks like: `xxxx-xxxx-xxxx-xxxx`)

## Step 2: Generate Playlist

If you haven't already, generate the playlist:

```bash
./scripts/generate_live_playlist.sh
```

This creates `live_playlist.txt` with all videos from `videos/paused/`.

## Step 3: Start Streaming

Set your stream key and start streaming:

```bash
export YOUTUBE_STREAM_KEY=your_stream_key_here
./scripts/stream_to_youtube.sh
```

Or in one line:

```bash
YOUTUBE_STREAM_KEY=your_stream_key_here ./scripts/stream_to_youtube.sh
```

## Step 4: Go Live on YouTube

1. In YouTube Studio, click **"Go Live"**
2. Set up your stream:
   - **Title**: Your stream title
   - **Description**: Your stream description
   - **Visibility**: Choose Public/Unlisted/Private
3. Click **"Go Live"** when ready
4. The stream will start automatically when ffmpeg connects

## Stream Settings

The script uses these optimized settings for YouTube Live:
- **Video Codec**: H.264 (libx264)
- **Preset**: veryfast (low latency)
- **Bitrate**: 3000k max
- **Audio Codec**: AAC
- **Audio Bitrate**: 160k
- **Format**: FLV (RTMP)

## Stopping the Stream

Press `Ctrl+C` to stop the stream.

## Troubleshooting

### Stream won't connect
- Verify your stream key is correct
- Check your internet connection
- Make sure YouTube Live is set to "Stream" mode (not "Quick")

### Videos not looping
- The script uses `-stream_loop -1` to loop infinitely
- If it stops, check ffmpeg output for errors

### Playlist issues
- Regenerate playlist: `./scripts/generate_live_playlist.sh`
- Verify videos exist in `videos/paused/`

## Notes

- The stream will loop your playlist continuously
- Each video will play in order, then repeat
- Make sure your YouTube Live event is set up before starting the stream
- The stream will start automatically when ffmpeg connects to YouTube's RTMP server
