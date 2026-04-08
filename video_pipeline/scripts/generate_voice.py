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

# Debug: print masked key so we can verify it's loading correctly
if FISH_API_KEY:
    masked = FISH_API_KEY[:6] + "..." + FISH_API_KEY[-4:]
    print(f"[generate_voice] API key loaded: {masked} (length: {len(FISH_API_KEY)})")
else:
    print("[generate_voice] ❌ FISH_AUDIO_API_KEY is empty or not set!")
    raise Exception("FISH_AUDIO_API_KEY secret is missing or empty")

# Warm, calm male voice selected for MindCore AI
VOICE_ID = os.environ.get("FISH_VOICE_ID", "0b74ead073f2474a904f69033535b98e")
print(f"[generate_voice] Using voice ID: {VOICE_ID}")

# Fish Audio uses just the raw token — no "Bearer" prefix
headers = {
    "Authorization": FISH_API_KEY,
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

print("[generate_voice] Calling Fish Audio API (no Bearer prefix)...")
response = requests.post(
    "https://api.fish.audio/v1/tts",
    headers=headers,
    json=payload,
    timeout=120,
)

# If raw token fails, retry with Bearer prefix
if response.status_code == 401:
    print("[generate_voice] Raw token 401 — retrying with Bearer prefix...")
    headers["Authorization"] = f"Bearer {FISH_API_KEY}"
    response = requests.post(
        "https://api.fish.audio/v1/tts",
        headers=headers,
        json=payload,
        timeout=120,
    )

if response.status_code != 200:
    print(f"[generate_voice] ❌ Fish Audio error {response.status_code}: {response.text}")
    print(f"[generate_voice] Key length was: {len(FISH_API_KEY)}")
    print(f"[generate_voice] Go to fish.audio → profile → API Keys and regenerate your key,")
    print(f"[generate_voice] then update FISH_AUDIO_API_KEY in GitHub Settings → Secrets → Actions")
    raise Exception(f"Fish Audio API failed: {response.status_code}")

with open(AUDIO_FILE, "wb") as f:
    f.write(response.content)

size_kb = AUDIO_FILE.stat().st_size / 1024
print(f"[generate_voice] ✅ Voiceover saved: {AUDIO_FILE} ({size_kb:.1f} KB)")
