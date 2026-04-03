# YouTube Shorts Maker

A comprehensive tool for creating YouTube Shorts videos from JSON scripts and streaming them live to YouTube.

## Features

- 🎬 **Video Generation**: Create videos from JSON scripts with AI-generated images, voiceovers, and subtitles
- 🎥 **Stream Videos**: Generate videos optimized for live streaming with title pauses and outros
- 📺 **Live Streaming**: Stream generated videos to YouTube Live
- 🎨 **Customizable**: Configure fonts, colors, spacing, and effects
- 🔊 **Audio Mixing**: Mix background music with voiceovers
- 📝 **Subtitle Generation**: Automatic subtitle generation with styling

## Quick Reference

### Main Commands

**Create YouTube Shorts Video:**
```bash
python3 scripts/run_video_from_script.py  # Generate video
python3 scripts/upload_to_youtube.py     # Upload to YouTube
```

**Generate Stream Videos:**
```bash
python3 scripts/stream/run_stream.py     # Generate videos for streaming
```

**Stream to YouTube Live:**
```bash
bash scripts/generate_live_playlist.sh    # Generate playlist
YOUTUBE_STREAM_KEY=your_key bash scripts/stream_to_youtube.sh  # Start streaming
```

## Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg installed (`brew install ffmpeg` on macOS, `apt install ffmpeg` on Linux)
- Required Python packages (install with `pip install -r requirements.txt`)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Place your fonts in the project root:
   - `Game of Thrones.ttf` (or `Montserrat.ttf` as fallback)
4. Add background music:
   - Place `bgm.mp3` in `bgm/` directory
5. Set up YouTube API (for uploads):
   - Create `youtube-web.json` credentials file (see YouTube API setup)

## Usage

### Creating YouTube Shorts Videos

This workflow generates a single YouTube Shorts video from a JSON script.

1. **Prepare your script**: Create a JSON file `input/video_script.json` (see `input/video_script_template.json` for template)

2. **Generate video**:
   ```bash
   python3 scripts/run_video_from_script.py
   ```
   
   This script automatically runs three steps:
   - `process_video_script.py` - Generates TTS audio, AI images, and subtitles
   - `create_clips_from_script.py` - Creates video clips from images with effects
   - `combine_final.py` - Combines clips, audio, and subtitles into final video
   
   **Output**: `output/final/final_short.mp4`

3. **Upload to YouTube**:
   ```bash
   python3 scripts/upload_to_youtube.py
   ```
   
   This will:
   - Use OAuth2 to authenticate with YouTube (first time only)
   - Upload `output/final/final_short.mp4` to your YouTube channel
   - Use title and description from `input/video_script.json`
   
   **Note**: Requires `youtube-web.json` credentials file (see setup instructions)

### Generating Stream Videos

Stream videos are optimized for live streaming with:
- 3-second title pause at the beginning (black screen with title text)
- Background music starting from the pause
- Voiceover starting after the 3-second pause
- Customizable outro (only added to the last video in the playlist)

1. **Prepare stream scripts**: Create numbered JSON files in `input/stream/`:
   - `1.json`, `2.json`, `3.json`, etc. (must be in numerical order)
   - Each JSON file uses the same format as `input/video_script.json`
   - Videos are processed in numerical order for the live playlist

2. **Generate stream videos**:
   ```bash
   python3 scripts/stream/run_stream.py
   ```
   
   This script:
   - Finds all numbered JSON files in `input/stream/`
   - Processes them in numerical order (1.json, 2.json, 3.json...)
   - Generates each video with title pause, audio mixing, and subtitles
   - Adds outro only to the last video
   
   **Output**: Videos saved to `output/stream/` with naming format:
   - `01_title_of_video.mp4`
   - `02_title_of_video.mp4`
   - `03_title_of_video.mp4`
   - etc.

3. **Configure settings**: Edit `stream_config.json` to customize:
   - **title_pause**: Duration, margins, font sizes, colors, line spacing
   - **audio**: BGM volume, voice volume, pause duration, BGM file path
   - **outro**: Enable/disable, narration text, image path, duration, effect
   - **text_processing**: Apostrophe replacement settings

### Streaming to YouTube Live

Stream your generated videos to YouTube Live in a continuous loop.

1. **Generate playlist**:
   ```bash
   bash scripts/generate_live_playlist.sh
   ```
   
   This script:
   - Automatically uses videos from `output/stream/` (preferred) or `videos/paused/` (fallback)
   - Creates `live_playlist.txt` with absolute paths to all videos
   - Sorts videos by filename for proper order
   
   **Output**: `live_playlist.txt` (FFmpeg concat format)
   
   Or manually create `live_playlist.txt` with video paths:
   ```
   file '/absolute/path/to/video1.mp4'
   file '/absolute/path/to/video2.mp4'
   ```

2. **Get your YouTube stream key**:
   - Go to [YouTube Studio](https://studio.youtube.com)
   - Click **"Go Live"** > **"Stream"** tab
   - Under **"Stream Settings"**, copy your Stream Key

3. **Start streaming**:
   ```bash
   export YOUTUBE_STREAM_KEY=your_stream_key_here
   bash scripts/stream_to_youtube.sh
   ```
   
   Or in one line:
   ```bash
   YOUTUBE_STREAM_KEY=your_stream_key_here bash scripts/stream_to_youtube.sh
   ```

   The script will:
   - Check for playlist file and stream key
   - Loop the playlist infinitely (`-stream_loop -1`)
   - Stream at optimal settings for YouTube Live (H.264, AAC, 3000k bitrate)
   - Show progress and errors in real-time
   - Press `Ctrl+C` to stop streaming

## Configuration Files

### `stream_config.json`
Main configuration for stream videos:
- **title_pause**: Duration, margins, font sizes, colors, line spacing
- **audio**: BGM volume, voice volume, pause duration
- **outro**: Enable/disable, narration text, image path, duration, effect
- **output**: Directory, naming format
- **text_processing**: Apostrophe replacement settings

### `video_config.json`
Video configuration for regular shorts videos:
- **audio**: BGM volume, voice volume, BGM file path
- **font**: Font name and file
- **style**: Subtitle styling (font size, colors, outline, etc.)
- **positioning**: Subtitle position and margins
- **display**: Subtitle display settings (max words, line spacing)
- **subtitle_background**: Background settings for subtitle area
- **transitions**: Fade effects
- **watermark**: Watermark overlay settings

## Project Structure

```
.
├── input/
│   ├── video_script.json          # JSON script for regular videos
│   ├── video_script_template.json # Template for creating scripts
│   ├── channel-promo.png          # Outro image for stream videos
│   └── stream/                    # Stream video scripts (numbered)
│       ├── 1.json
│       ├── 2.json
│       └── ...
├── output/
│   ├── final/
│   │   └── final_short.mp4        # Final regular video
│   ├── stream/                    # Generated stream videos
│   │   ├── 01_title.mp4
│   │   ├── 02_title.mp4
│   │   └── ...
│   ├── audio/                     # Generated audio files
│   ├── images/                    # Generated images
│   ├── video_clips/               # Video clips (intermediate)
│   └── subtitles/                 # Subtitle files
├── scripts/
│   ├── run_video_from_script.py   # Main: Generate regular video
│   ├── upload_to_youtube.py       # Upload video to YouTube
│   ├── process_video_script.py     # Generate audio, images, subtitles
│   ├── create_clips_from_script.py # Create video clips
│   ├── combine_final.py           # Combine final video
│   ├── stream/
│   │   ├── run_stream.py          # Main: Generate stream videos
│   │   ├── process_stream_videos.py # Process single stream video
│   │   ├── create_title_pause.py  # Create title pause screen
│   │   ├── mix_stream_audio.py    # Mix BGM and voiceover
│   │   └── combine_stream_video.py # Combine stream video
│   ├── generate_live_playlist.sh  # Generate playlist for streaming
│   └── stream_to_youtube.sh       # Stream to YouTube Live
├── stream_config.json             # Stream video configuration
├── video_config.json              # Video configuration (audio, subtitles, watermark)
├── youtube-web.json               # YouTube API credentials (not in repo)
└── live_playlist.txt              # Playlist for streaming (generated)
```

## JSON Script Format

### Regular Video Script (`input/video_script.json`)
```json
{
  "title": "Your Video Title",
  "scenes": [
    {
      "scene_number": 1,
      "narration": "Narration text for this scene",
      "image_prompt": "Description of image to generate",
      "duration": 4,
      "effect": "zoom_in"
    }
  ]
}
```

### Stream Video Script (`input/stream/1.json`)
Same format as regular video script. Videos are processed in numerical order (1.json, 2.json, etc.).

## Animation Effects

Available effects (see `ANIMATION_EFFECTS.md` for details):
- `zoom_in`, `zoom_out`
- `ken_burns_in`, `ken_burns_out`
- `pan_left`, `pan_right`, `pan_up`, `pan_down`
- `fade_in`, `fade_out`

## Troubleshooting

### Video Generation Fails
- **FFmpeg not found**: Install FFmpeg (`brew install ffmpeg` on macOS)
- **JSON format error**: Verify JSON syntax is valid (use a JSON validator)
- **Font not found**: Ensure `Game of Thrones.ttf` or `Montserrat.ttf` exists in project root
- **Image generation fails**: Check internet connection and Pollinations API availability
- **Audio generation fails**: Check Deepgram API key or gTTS fallback

### Upload to YouTube Fails
- **OAuth error**: Follow setup in `YOUTUBE_SETUP.md` (if still exists) or Google Cloud Console
- **Credentials missing**: Ensure `youtube-web.json` exists in project root
- **Token expired**: Delete `.youtube_token.json` and re-authenticate
- **Video too large**: YouTube has size limits; check video file size

### Stream Video Generation Fails
- **No JSON files found**: Ensure numbered JSON files exist in `input/stream/`
- **BGM file missing**: Check that `bgm/bgm.mp3` exists
- **Outro image missing**: Check `input/channel-promo.png` or update path in `stream_config.json`
- **Title pause issues**: Check font file exists and `stream_config.json` settings

### Streaming to YouTube Live Fails
- **Stream key error**: Verify `YOUTUBE_STREAM_KEY` is set correctly
- **Playlist not found**: Run `bash scripts/generate_live_playlist.sh` first
- **Empty playlist**: Ensure videos exist in `output/stream/` or `videos/paused/`
- **Connection failed**: Check internet connection and YouTube stream status
- **Video format issues**: Ensure videos are MP4 with H.264 video and AAC audio
- **Stream stops**: Check ffmpeg output for errors; verify videos are valid

## Advanced Usage

### Custom Fonts
Place font files in project root:
- `Game of Thrones.ttf` (primary)
- `Montserrat.ttf` (fallback)

### Background Music
Place `bgm.mp3` in `bgm/` directory. Configure volume:
- **Regular videos**: Set `audio.bgm_volume` in `video_config.json` (default: 0.25)
- **Stream videos**: Set `audio.bgm_volume` in `stream_config.json` (default: 0.25)

### Outro Image
Place outro image in `input/channel-promo.png` (or configure path in `stream_config.json`).

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]

