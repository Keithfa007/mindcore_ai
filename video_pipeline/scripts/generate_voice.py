"""
generate_voice.py
MindCore AI Video Pipeline — Step 2
Reads script from outputs/script_output.json
Sends to Fish Audio TTS API and saves voiceover as outputs/voiceover.mp3

VOICE SETUP:
  To use a custom voice:
  1. Go to fish.audio and find the voice you want
  2. Click the voice → click 'Clone' to copy it to your account
  3. Go to your account → My Voices → copy the model ID
  4. Add it as FISH_VOICE_ID secret in GitHub Settings → Secrets → Actions
"""

import os
import json
import requests
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = BASE_DIR / "outputs"
SCRIPT_FILE = OUTPUT_DIR / "script_output.json"
AUDIO_FILE  = OUTPUT_DIR / "voiceover.mp3"

# ── Load script ────────────────────────────────────────────────────────────
with open(SCRIPT_FILE, "r") as f:
    script_data = json.load(f)

spoken_script = script_data["script"]
print(f"[generate_voice] Script: {len(spoken_script)} chars")
print(f"[generate_voice] Hook:   {script_data.get('hook')}")

# ── Fish Audio API ─────────────────────────────────────────────────────────
FISH_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "")
if not FISH_API_KEY:
    raise Exception("FISH_AUDIO_API_KEY secret is missing")

print(f"[generate_voice] API key length: {len(FISH_API_KEY)} chars")

# Custom voice ID — set FISH_VOICE_ID secret in GitHub to use a cloned voice
# To clone the voice: fish.audio → find voice → Clone → copy new model ID
VOICE_ID = os.environ.get("FISH_VOICE_ID", "").strip()

headers = {
    "Authorization": f"Bearer {FISH_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "text": spoken_script,
    "format": "mp3",
    "mp3_bitrate": 128,
    "latency": "normal",
    "normalize": True,
}

if VOICE_ID:
    payload["reference_id"] = VOICE_ID
    print(f"[generate_voice] Using custom voice ID: {VOICE_ID[:8]}...")
else:
    print("[generate_voice] No FISH_VOICE_ID set — using Fish Audio default voice")
    print("[generate_voice] → Clone your preferred voice at fish.audio then add FISH_VOICE_ID secret")

print("[generate_voice] Calling Fish Audio API...")
response = requests.post(
    "https://api.fish.audio/v1/tts",
    headers=headers,
    json=payload,
    timeout=120,
)

if response.status_code != 200:
    print(f"[generate_voice] ❌ Error {response.status_code}: {response.text}")
    if response.status_code == 400 and "Reference not found" in response.text:
        print("[generate_voice] ⚠️  Voice ID not found — the voice must be cloned to YOUR account first")
        print("[generate_voice] ⚠️  Go to fish.audio → find the voice → click Clone → copy the new ID")
        print("[generate_voice] ⚠️  Add the new ID as FISH_VOICE_ID in GitHub Secrets")
    raise Exception(f"Fish Audio API failed: {response.status_code}")

with open(AUDIO_FILE, "wb") as f:
    f.write(response.content)

size_kb = AUDIO_FILE.stat().st_size / 1024
print(f"[generate_voice] ✅ Voiceover saved: {AUDIO_FILE.name} ({size_kb:.1f} KB)")
