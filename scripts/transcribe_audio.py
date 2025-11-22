"""
Transcribe audio using Deepgram API to get word-level timings for subtitle synchronization.
"""
import os
import requests
import json

DEEPGRAM_API_KEY = "d85755dcff46bcce90b27465e544ab45d94aa141"
DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"

def transcribe_audio(audio_file: str) -> dict:
    """
    Transcribe audio file using Deepgram API.
    Returns transcription with word-level timings.
    """
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"Audio file not found: {audio_file}")
    
    print(f"📝 Transcribing audio: {audio_file}")
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/mpeg"
    }
    
    # Read audio file
    with open(audio_file, "rb") as f:
        audio_data = f.read()
    
    # Make POST request
    params = {
        "smart_format": "true",
        "language": "en",
        "model": "nova-2",
        "punctuate": "true",
        "diarize": "false"
    }
    
    try:
        resp = requests.post(
            DEEPGRAM_API_URL,
            headers=headers,
            data=audio_data,
            params=params,
            timeout=120
        )
        resp.raise_for_status()
        
        result = resp.json()
        return result
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text[:200]}")
        raise

def extract_word_timings(transcription_result: dict) -> list:
    """
    Extract word-level timings from Deepgram transcription result.
    Returns list of (word, start_time, end_time) tuples.
    """
    words = []
    
    try:
        if "results" in transcription_result and "channels" in transcription_result["results"]:
            for channel in transcription_result["results"]["channels"]:
                if "alternatives" in channel:
                    for alternative in channel["alternatives"]:
                        if "words" in alternative:
                            for word_info in alternative["words"]:
                                word = word_info.get("word", "")
                                start = word_info.get("start", 0)
                                end = word_info.get("end", 0)
                                words.append((word, start, end))
    except Exception as e:
        print(f"⚠️  Error extracting word timings: {e}")
    
    return words

if __name__ == "__main__":
    # Test transcription
    audio_file = "output/audio/voice.mp3"
    if os.path.exists(audio_file):
        result = transcribe_audio(audio_file)
        words = extract_word_timings(result)
        print(f"✅ Extracted {len(words)} words with timings")
        for word, start, end in words[:10]:
            print(f"   {word}: {start:.2f}s - {end:.2f}s")
    else:
        print(f"❌ Audio file not found: {audio_file}")

