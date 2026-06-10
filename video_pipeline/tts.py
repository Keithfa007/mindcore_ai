"""
MindCore AI -- ElevenLabs TTS v1.0
===================================
Shared TTS module for all video pipelines + ebook promo.
Replaces Fish Audio for voiceovers. Fish Audio stays for in-app voice only.

Voices:
  Male:   jfIS2w2yJi0grJZPyEsk
  Female: uIZsnBL0YK1S5j69bAih
"""

import os
from pathlib import Path
import requests

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

MALE_VOICE_ID   = "jfIS2w2yJi0grJZPyEsk"
FEMALE_VOICE_ID = "uIZsnBL0YK1S5j69bAih"


def generate_elevenlabs_tts(text, output_path, voice_id, model_id="eleven_multilingual_v2"):
    """Generate TTS audio using ElevenLabs API.

    Args:
        text: Script text to synthesize
        output_path: Where to save the MP3
        voice_id: ElevenLabs voice ID
        model_id: ElevenLabs model (default: eleven_multilingual_v2)

    Returns:
        output_path on success
    """
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    url = f"{ELEVENLABS_API_URL}/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.75,
        },
    }

    print(f"  ElevenLabs TTS: voice {voice_id[:8]}... | {len(text)} chars | model: {model_id}")
    resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)

    if not resp.ok:
        raise RuntimeError(f"ElevenLabs TTS failed {resp.status_code}: {resp.text[:300]}")

    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)

    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  TTS: {size_kb:.0f} KB")
    return output_path
