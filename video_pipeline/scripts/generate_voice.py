"""
generate_voice.py
MindCore AI Video Pipeline — Step 2
Reads script from outputs/script_output.json
Sends to Fish Audio TTS API and saves voiceover as outputs/voiceover.mp3
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
print(f"[generate_voice] Script length: {len(spoken_script)} chars")
print(f"[generate_voice] Hook: {script_data.get('hook')}")

# ── Fish Audio API ─────────────────────────────────────────────────────────
FISH_API_KEY = os.environ["FISH_AUDIO_API_KEY"]

# Warm, calm male voice selected for MindCore AI
# FISH_VOICE_ID secret overrides this if set in GitHub Secrets
VOICE_ID = os.environ.get("FISH_VOICE_ID", "0b74ead073f2474a904f69033535b98e")

print(f"[generate_voice] Using voice ID: {VOICE_ID}")

headers = {
    "Authorization": f"Bearer {FISH_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "text": spoken_script,
    "reference_id": VOICE_ID,
    "format": "mp3",
    "mp3_bitrate": 128,
    "latency": "normal",
    "normalize": True,
}

print("[generate_voice] Calling Fish Audio API...")
response = requests.post(
    "https://api.fish.audio/v1/tts",
    headers=headers,
    json=payload,
    timeout=120,
)

if response.status_code != 200:
    print(f"[generate_voice] ❌ Fish Audio error {response.status_code}: {response.text}")
    print(f"[generate_voice] Check that FISH_AUDIO_API_KEY secret is correct in GitHub Settings → Secrets")
    raise Exception(f"Fish Audio API failed: {response.status_code}")

with open(AUDIO_FILE, "wb") as f:
    f.write(response.content)

size_kb = AUDIO_FILE.stat().st_size / 1024
print(f"[generate_voice] ✅ Voiceover saved: {AUDIO_FILE} ({size_kb:.1f} KB)")
