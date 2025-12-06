"""
Upload the generated video to YouTube.
Handles OAuth2 authentication and video upload.
"""
import json
import os
import sys
from pathlib import Path
import time

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ Missing required packages. Please install:")
    print("   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# OAuth2 scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Paths
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / "youtube-web.json"
TOKEN_FILE = BASE_DIR / ".youtube_token.json"
VIDEO_SCRIPT_FILE = BASE_DIR / "input" / "video_script.json"
FINAL_VIDEO_FILE = BASE_DIR / "output" / "final" / "final_short.mp4"

# OAuth2 callback server
REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"


def get_credentials():
    """Get valid user credentials from storage or OAuth flow."""
    creds = None
    
    # Load existing token
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"⚠️  Could not load existing token: {e}")
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️  Could not refresh token: {e}")
                creds = None
        
        if not creds:
            print("🔐 Starting OAuth2 flow...")
            
            if not CREDENTIALS_FILE.exists():
                print(f"❌ Credentials file not found: {CREDENTIALS_FILE}")
                sys.exit(1)
            
            # Load client secrets
            with open(CREDENTIALS_FILE, 'r') as f:
                client_config = json.load(f)
            
            # Convert web credentials to installed app format if needed
            # InstalledAppFlow works better with installed app credentials
            if "web" in client_config and "installed" not in client_config:
                # Convert web to installed format for better compatibility
                client_config["installed"] = {
                    "client_id": client_config["web"]["client_id"],
                    "client_secret": client_config["web"]["client_secret"],
                    "auth_uri": client_config["web"]["auth_uri"],
                    "token_uri": client_config["web"]["token_uri"],
                    "auth_provider_x509_cert_url": client_config["web"]["auth_provider_x509_cert_url"],
                    "redirect_uris": ["http://localhost"]
                }
            
            # Create OAuth flow - don't specify redirect_uri, let run_local_server handle it
            flow = InstalledAppFlow.from_client_config(
                client_config,
                SCOPES
            )
            
            print("\n🌐 Opening browser for authorization...")
            print("   Please authorize the app in your browser.\n")
            
            # Run the OAuth flow using the built-in local server
            # This handles the callback automatically with the correct redirect URI
            try:
                # Try with redirect_uri_trailing_slash=False first (if supported)
                try:
                    creds = flow.run_local_server(port=REDIRECT_PORT, open_browser=True, redirect_uri_trailing_slash=False)
                except TypeError:
                    # Fallback if parameter not supported
                    creds = flow.run_local_server(port=REDIRECT_PORT, open_browser=True)
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Authorization failed: {error_msg}")
                
                if "redirect_uri_mismatch" in error_msg.lower():
                    print("\n⚠️  Redirect URI mismatch error detected.")
                    print("   Please ensure you've added BOTH of these to Google Cloud Console:")
                    print(f"   1. http://localhost:{REDIRECT_PORT}")
                    print(f"   2. http://localhost:{REDIRECT_PORT}/")
                    print("\n   Go to: APIs & Services > Credentials > Your OAuth 2.0 Client ID")
                    print("   Add both URIs in 'Authorized redirect URIs' section")
                    print("   Wait 1-2 minutes after saving, then try again.\n")
                elif "access_denied" in error_msg.lower():
                    print("\n⚠️  Access was denied. Please try again and make sure to click 'Allow'.")
                else:
                    print(f"\n   Full error: {error_msg}")
                
                sys.exit(1)
        
        # Save credentials for next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print("✅ Credentials saved for future use")
    
    return creds


def get_video_metadata():
    """Get video title and description from video script."""
    if not VIDEO_SCRIPT_FILE.exists():
        print(f"⚠️  Video script not found: {VIDEO_SCRIPT_FILE}")
        return {
            "title": "YouTube Short",
            "description": "Generated YouTube Short"
        }
    
    with open(VIDEO_SCRIPT_FILE, 'r') as f:
        script_data = json.load(f)
    
    title = script_data.get("title", "YouTube Short")
    
    # Use description from JSON if provided, otherwise create from scenes
    if "description" in script_data and script_data["description"]:
        description = script_data["description"]
    else:
        # Fallback: Create description from scenes
        description_parts = [title, "", "Scenes:"]
        for scene in script_data.get("scenes", []):
            if "narration" in scene:
                description_parts.append(f"• {scene['narration']}")
        description = "\n".join(description_parts)
    
    return {
        "title": title,
        "description": description
    }


def upload_video(creds, video_path, title, description):
    """Upload video to YouTube."""
    youtube = build('youtube', 'v3', credentials=creds)
    
    print(f"\n📤 Uploading video: {video_path}")
    print(f"   Title: {title}")
    
    # Check if video file exists
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        sys.exit(1)
    
    # Get file size for progress tracking
    file_size = video_path.stat().st_size
    print(f"   File size: {file_size / (1024 * 1024):.2f} MB")
    
    # Create media file upload object
    media = MediaFileUpload(
        str(video_path),
        chunksize=-1,
        resumable=True,
        mimetype='video/mp4'
    )
    
    # Create video metadata
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': ['shorts', 'youtube shorts'],
            'categoryId': '22'  # People & Blogs
        },
        'status': {
            'privacyStatus': 'public',
            'madeForKids': False
        }
    }
    
    # Insert video
    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    # Upload with progress
    print("\n📊 Upload progress:")
    response = None
    error = None
    retry = 0
    
    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    print(f"\n✅ Video uploaded successfully!")
                    print(f"   URL: {video_url}")
                    return video_id, video_url
                else:
                    print(f"❌ Upload failed: {response}")
                    sys.exit(1)
            elif status:
                progress = int(status.progress() * 100)
                print(f"   {progress}% complete", end='\r')
        except Exception as e:
            if isinstance(e, Exception):
                error = e
                if retry < 3:
                    retry += 1
                    print(f"\n⚠️  Upload error, retrying ({retry}/3)...")
                    time.sleep(2 ** retry)  # Exponential backoff
                else:
                    print(f"\n❌ Upload failed after retries: {error}")
                    sys.exit(1)
            else:
                raise
    
    return None, None


def main():
    """Main function."""
    print("🎬 YouTube Upload Script")
    print("=" * 50)
    
    # Check if video exists
    if not FINAL_VIDEO_FILE.exists():
        print(f"❌ Final video not found: {FINAL_VIDEO_FILE}")
        print("   Please run the video generation script first.")
        sys.exit(1)
    
    # Get credentials
    creds = get_credentials()
    
    # Get video metadata
    metadata = get_video_metadata()
    
    # Upload video
    video_id, video_url = upload_video(
        creds,
        FINAL_VIDEO_FILE,
        metadata["title"],
        metadata["description"]
    )
    
    if video_id:
        print(f"\n🎉 Success! Video is now live on YouTube.")
        print(f"   Video ID: {video_id}")
        print(f"   URL: {video_url}")
    else:
        print("\n❌ Upload failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

