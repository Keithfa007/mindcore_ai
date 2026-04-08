"""
generate_voice.py
MindCore AI Video Pipeline — Step 2
Reads script from outputs/script_output.json
Sends to Fish Audio TTS API and saves voiceover as outputs/voiceover.mp3

VOICE:
  Preferred voice: fish.audio/app/text-to-speech/?modelId=eed26f2294d64177911af612473cca98
  Voice ID: eed26f2294d64177911af612473cca98

  To activate this voice you need Fish Audio Plus ($5.50/month):
  1. Upgrade at fish.audio/plan
  2. Go to the voice page above
  3. Click Clone → it creates a copy in your account
  4. Go to My Voices → copy the new model ID
  5. Add as FISH_VOICE_ID secret in GitHub Settings → Secrets → Actions

  Until then the pipeline runs with Fish Audio's default voice.
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

# Preferred MindCore AI voice (warm, calm male)
# Overridden by FISH_VOICE_ID GitHub secret if set
# Requires Fish Audio Plus plan + voice cloned to your account
DEFAULT_VOICE_ID = "eed26f2294d64177911af612473cca98"
VOICE_ID = os.environ.get("FISH_VOICE_ID", "").strip() or DEFAULT_VOICE_ID

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
    "reference_id": VOICE_ID,
}

print(f"[generate_voice] Voice ID: {VOICE_ID}")
print("[generate_voice] Calling Fish Audio API...")

response = requests.post(
    "https://api.fish.audio/v1/tts",
    headers=headers,
    json=payload,
    timeout=120,
)

# If voice not found (free plan or not cloned) — fall back to default voice
if response.status_code == 400 and "Reference not found" in response.text:
    print("[generate_voice] ⚠️  Voice not found — falling back to default voice")
    print("[generate_voice] ⚠️  To fix: upgrade to Fish Audio Plus + clone the voice to your account")
    payload.pop("reference_id", None)
    response = requests.post(
        "https://api.fish.audio/v1/tts",
        headers=headers,
        json=payload,
        timeout=120,
    )

if response.status_code != 200:
    print(f"[generate_voice] ❌ Error {response.status_code}: {response.text}")
    raise Exception(f"Fish Audio API failed: {response.status_code}")

with open(AUDIO_FILE, "wb") as f:
    f.write(response.content)

size_kb = AUDIO_FILE.stat().st_size / 1024
print(f"[generate_voice] ✅ Voiceover saved: {AUDIO_FILE.name} ({size_kb:.1f} KB)")
