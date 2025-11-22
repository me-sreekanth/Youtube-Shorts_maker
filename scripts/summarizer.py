import os
import requests
from urllib.parse import quote

INPUT_FILE = "input/transcript.txt"
OUTPUT_FILE = "output/short_script.txt"
POLLINATIONS_TEXT_ENDPOINT = "https://text.pollinations.ai"

def call_pollinations_text(prompt: str) -> str:
    """
    Uses Pollinations text API: GET https://text.pollinations.ai/{prompt}
    Note: for very large transcripts, you may hit URL length limits.
    In that case, consider chunking the transcript or using their OpenAI-compatible endpoint.
    """
    url = f"{POLLINATIONS_TEXT_ENDPOINT}/{quote(prompt)}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text.strip()

def main():
    if not os.path.exists(INPUT_FILE):
        print("❌ input/transcript.txt not found")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        transcript = f.read().strip()

    if not transcript:
        print("❌ transcript.txt is empty")
        return

    os.makedirs("output", exist_ok=True)

    prompt = (
        "You are a YouTube Shorts script writer.\n"
        "Create a 45-60 second script (maximum 15-18 lines) from the transcript below.\n"
        "- Use short, punchy lines.\n"
        "- One sentence per line.\n"
        "- Maximum 18 lines total (aim for 15-16 lines).\n"
        "- Each line should be 2-4 seconds when spoken.\n"
        "- No numbering or bullet points.\n"
        "- No explanation before or after the lines.\n"
        "Transcript:\n"
        f"{transcript}"
    )

    print("🧠 Calling Pollinations to summarize & rewrite script...")
    short_script = call_pollinations_text(prompt)

    # Post-process: limit to 18 lines max to keep video under 2 minutes
    lines = [l.strip() for l in short_script.splitlines() if l.strip()]
    if len(lines) > 18:
        print(f"⚠️  Script has {len(lines)} lines, truncating to 18 lines max")
        lines = lines[:18]
        short_script = "\n".join(lines)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(short_script)

    print(f"✅ Short script saved to {OUTPUT_FILE} ({len(lines)} lines)")
    print("------")
    print(short_script)
    print("------")

if __name__ == "__main__":
    main()

