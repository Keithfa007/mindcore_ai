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
FISH_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "")

if not FISH_API_KEY:
    raise Exception("FISH_AUDIO_API_KEY secret is missing or empty")

print(f"[generate_voice] API key length: {len(FISH_API_KEY)} chars")

# Fish Audio requires Bearer prefix
headers = {
    "Authorization": f"Bearer {FISH_API_KEY}",
    "Content-Type": "application/json",
}

# Using Fish Audio default voice — no reference_id needed
# A custom voice can be added later once cloned to your Fish Audio account
payload = {
    "text": spoken_script,
    "format": "mp3",
    "mp3_bitrate": 128,
    "latency": "normal",
    "normalize": True,
}

print("[generate_voice] Calling Fish Audio API with default voice...")
response = requests.post(
    "https://api.fish.audio/v1/tts",
    headers=headers,
    json=payload,
    timeout=120,
)

if response.status_code != 200:
    print(f"[generate_voice] ❌ Fish Audio error {response.status_code}: {response.text}")
    raise Exception(f"Fish Audio API failed: {response.status_code}")

with open(AUDIO_FILE, "wb") as f:
    f.write(response.content)

size_kb = AUDIO_FILE.stat().st_size / 1024
print(f"[generate_voice] ✅ Voiceover saved: {AUDIO_FILE} ({size_kb:.1f} KB)")
