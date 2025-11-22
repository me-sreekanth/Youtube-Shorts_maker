# Video Script Format

This project now uses a structured JSON format for video generation instead of the summarizer workflow.

## Format Structure

Create a file `input/video_script.json` with the following structure:

```json
{
  "title": "Your Video Title",
  "scenes": [
    {
      "scene_number": 1,
      "scene_type": "hook",  // Optional: "hook" or "final"
      "narration": "Text that will be spoken",
      "subtitle": "Text that appears on screen",
      "image_prompt": "Detailed prompt for image generation",
      "duration": 4  // Duration in seconds
    }
  ],
  "total_duration": 45  // Total video duration (optional)
}
```

## Field Descriptions

- **title**: The title of your video
- **scenes**: Array of scene objects
  - **scene_number**: Sequential number (1, 2, 3...)
  - **scene_type**: Optional - "hook" for first scene, "final" for last scene
  - **narration**: Text that will be converted to speech (TTS)
  - **subtitle**: Text that appears as subtitles on the video
  - **image_prompt**: Detailed prompt for AI image generation
  - **duration**: How long this scene should last (in seconds)

## Image Prompt Tips

- Be specific and descriptive
- Include style keywords: "cinematic", "high quality", "vertical video frame"
- Specify dimensions: "1080x1920" or "vertical 9:16"
- Add mood/atmosphere: "dramatic lighting", "cyberpunk", "dystopian"
- Mention composition: "dynamic composition", "depth of field"

## Usage

1. **Create your script**: Edit `input/video_script.json` (use `video_script_template.json` as a starting point)

2. **Generate all assets**:
   ```bash
   python3 scripts/process_video_script.py
   ```
   This will:
   - Generate TTS audio for each narration
   - Generate images for each image prompt
   - Create subtitle file (SRT)

3. **Create video clips**:
   ```bash
   python3 scripts/create_clips_from_script.py
   ```

4. **Combine final video**:
   ```bash
   python3 scripts/combine_final.py
   ```

Or run everything at once:
```bash
python3 scripts/run_video_from_script.py
```

## Example

See `input/video_script.json` for a complete example based on "The Matrix Explained in 60 Seconds".

