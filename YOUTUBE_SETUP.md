# YouTube Upload Setup Instructions

## Complete Setup Guide

### Step 1: Configure OAuth Consent Screen

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Select your project: `rouge-ai-404909`

2. **Set up OAuth Consent Screen**
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" (unless you have a Google Workspace)
   - Fill in required fields:
     - App name: Your app name
     - User support email: Your email
     - Developer contact: Your email
   - Click "SAVE AND CONTINUE"

3. **Add Scopes**
   - Click "ADD OR REMOVE SCOPES"
   - Search for and add: `https://www.googleapis.com/auth/youtube.upload`
   - Click "UPDATE" then "SAVE AND CONTINUE"

4. **Add Test Users** (IMPORTANT if app is in testing mode)
   - Click "ADD USERS"
   - Add your Google account email (the one you'll use to upload)
   - Click "ADD"
   - Click "SAVE AND CONTINUE"

5. **Review and Submit**
   - Review the summary
   - Click "BACK TO DASHBOARD"

### Step 2: Configure OAuth 2.0 Client ID

1. **Navigate to Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Find your OAuth 2.0 Client ID (the one with client_id ending in `...apps.googleusercontent.com`)
   - Click on it to edit

2. **Add Authorized redirect URIs**
   - In the "Authorized redirect URIs" section, click "ADD URI"
   - Add both of these URIs (one at a time):
     - `http://localhost:8080`
     - `http://localhost:8080/`
   - Click "SAVE"

3. **Wait 1-2 minutes**
   - Changes may take a few minutes to propagate

### Step 3: Enable YouTube Data API v3

1. **Go to APIs & Services > Library**
2. **Search for "YouTube Data API v3"**
3. **Click on it and press "ENABLE"**

### Step 4: Run the Upload Script

```bash
python3 scripts/upload_to_youtube.py
```

## Troubleshooting

### "redirect_uri_mismatch" Error
- Make sure you added BOTH `http://localhost:8080` AND `http://localhost:8080/` to Authorized redirect URIs
- Wait 1-2 minutes after saving
- Try clearing your browser cache

### "Can't select Google account" or "Access blocked"
- Make sure your email is added as a Test User in OAuth consent screen
- If app is in "Testing" mode, only test users can access it
- Go to OAuth consent screen > Test users > Add your email

### "Access denied" Error
- Make sure you click "Allow" when prompted
- Check that YouTube Data API v3 is enabled
- Verify the OAuth consent screen is configured

## First Time Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the upload script:**
   ```bash
   python3 scripts/upload_to_youtube.py
   ```

3. **Authorize the app:**
   - Your browser will open automatically
   - Sign in with your Google account
   - Click "Allow" to grant permissions
   - The token will be saved for future use

## Notes

- The token is saved in `.youtube_token.json` (gitignored for security)
- You only need to authorize once - the token will be reused automatically
- If the token expires, it will be refreshed automatically

