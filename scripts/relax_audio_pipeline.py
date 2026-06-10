import anthropic
import requests
import firebase_admin
from firebase_admin import credentials, storage, firestore, messaging
import json
import os
import re
from datetime import datetime

# ─────────────────────────────────────────
# VOICE CONFIG -- ElevenLabs (replaces Fish Audio)
# ─────────────────────────────────────────
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "3cb1kceDIYlJwnoZWqaw"
ELEVENLABS_API_URL  = "https://api.elevenlabs.io/v1/text-to-speech"

# ─────────────────────────────────────────
# CATEGORY ROTATION ORDER
# ─────────────────────────────────────────
CATEGORY_ORDER = ["sleep", "stress", "recovery", "anxiety", "morning"]

CATEGORIES = {
    "sleep": {
        "name": "Sleep",
        "seo_keywords": "sleep meditation for recovery, sobriety sleep meditation, sleep without alcohol, insomnia men over 35",
        "titles": [
            "Sobriety Sleep Meditation: Calm Your Mind Without Substances",
            "Let It All Go: A Body Scan for Deep Sleep",
            "The Heavy Blanket: Progressive Muscle Relaxation for Sleep",
            "Quiet the Mind: Sleep Meditation for Racing Thoughts",
            "3am Reset: Guided Meditation for Middle-of-Night Anxiety",
        ],
    },
    "stress": {
        "name": "Stress & Decompression",
        "seo_keywords": "stress relief meditation for men, decompress after work, stress management men over 35, mental wellness men",
        "titles": [
            "5 Minutes to Calm: Stress Relief Meditation for Men Over 35",
            "Pressure Drop: Release Tension After a Hard Day",
            "Slow Down: Breathing Meditation When Everything Feels Overwhelming",
            "The Commute Wind-Down: Decompress After Work",
        ],
    },
    "recovery": {
        "name": "Recovery & Sobriety",
        "seo_keywords": "meditation for men in recovery, sobriety meditation, AI mental health coach for men, recovery mental wellness",
        "titles": [
            "One Day at a Time: Grounding Meditation for Early Recovery",
            "Craving Surfing: Ride Out Urges Without Acting",
            "Your Strength: Affirmation Meditation for Men in Recovery",
            "Stillness Without Substances: Finding Calm the Natural Way",
        ],
    },
    "anxiety": {
        "name": "Anxiety",
        "seo_keywords": "anxiety relief for men, guided meditation anxiety, mental health men over 35, anxiety without medication",
        "titles": [
            "Ground Yourself: 5-4-3-2-1 Anxiety Relief Meditation for Men",
            "Breathe Through It: Box Breathing Guided Session for Anxiety",
            "Safe Place: Visualisation Meditation for Anxiety Relief",
            "The Worried Mind: Accept Anxiety Without Fighting It",
        ],
    },
    "morning": {
        "name": "Morning",
        "seo_keywords": "morning meditation for men, morning mindfulness routine, mental clarity meditation, AI mental health coach for men",
        "titles": [
            "Wake With Purpose: Morning Intention Meditation for Men",
            "Morning Clarity: Breathwork for Mental Focus and Calm",
            "Today I Choose: Morning Affirmations for Men in Recovery",
        ],
    },
}


def init_firebase():
    service_account_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(service_account_dict)
    firebase_admin.initialize_app(cred, {"storageBucket": os.environ["FIREBASE_BUCKET"]})
    return firestore.client()


def get_pipeline_state(db):
    doc = db.collection("pipeline_state").document("relax_audio").get()
    if doc.exists:
        return doc.to_dict()
    return {"last_category_index": -1, "used_titles": []}


def save_pipeline_state(db, state):
    db.collection("pipeline_state").document("relax_audio").set(state)


def pick_next_category_and_title(state):
    next_index = (state["last_category_index"] + 1) % len(CATEGORY_ORDER)
    category_key = CATEGORY_ORDER[next_index]
    category = CATEGORIES[category_key]
    used = state.get("used_titles", [])
    available = [t for t in category["titles"] if t not in used]
    if not available:
        used = [t for t in used if t not in category["titles"]]
        available = category["titles"]
    title = available[0]
    return next_index, category_key, category, title, used


def generate_script(title, category):
    print("  Calling Anthropic API...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = f"""You are a professional meditation script writer for MindCore AI.

Write a complete guided relaxation audio script:

TITLE: {title}
CATEGORY: {category['name']}
SEO KEYWORDS: {category['seo_keywords']}

REQUIREMENTS:
- Length: 780-860 words
- Tone: Warm, calm, grounded. Not clinical, not spiritual/religious.
- Target: Men 35+, many managing stress, anxiety, or recovery
- Include pacing markers: [pause 3s], [pause 5s], [pause 8s], [slow breath]
- Structure: Opening (~120 words) -> Body (~520 words) -> Close (~120 words)
- Weave in 2-3 SEO keywords naturally
- NEVER use: journey, universe, manifest, chakra, vibration, divine, higher self
- Speak directly as "you"
- End with quiet confidence

Write ONLY the script. No title, no notes. Begin immediately."""
    message = client.messages.create(model="claude-opus-4-5", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
    return message.content[0].text


def clean_script_for_tts(script):
    clean = re.sub(r'\[.*?\]', '', script)
    clean = re.sub(r'\n\s*\n\s*\n', '\n\n', clean)
    return clean.strip()


def generate_audio(script_text):
    """Generate relaxation audio using ElevenLabs TTS."""
    clean_text = clean_script_for_tts(script_text)

    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    url = f"{ELEVENLABS_API_URL}/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": clean_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.70,
            "similarity_boost": 0.60,
        },
    }

    print(f"  ElevenLabs TTS: voice {ELEVENLABS_VOICE_ID[:8]}... | {len(clean_text)} chars")
    response = requests.post(url, headers=headers, json=payload, stream=True, timeout=180)

    if not response.ok:
        raise RuntimeError(f"ElevenLabs error {response.status_code}: {response.text[:300]}")

    audio_bytes = b""
    for chunk in response.iter_content(chunk_size=65_536):
        if chunk:
            audio_bytes += chunk

    print(f"  Audio ready ({len(audio_bytes) / 1024 / 1024:.1f} MB)")
    return audio_bytes


def upload_to_firebase(audio_bytes, title, category_key):
    bucket = storage.bucket()
    clean = re.sub(r'[^a-z0-9 ]', '', title.lower()).replace(' ', '_')[:50]
    timestamp = datetime.now().strftime('%Y%m%d')
    filename = f"relax_audio/{category_key}/{timestamp}_{clean}.mp3"
    blob = bucket.blob(filename)
    blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
    blob.make_public()
    return blob.public_url, filename


def estimate_duration(script_text):
    words = len(script_text.split())
    return int((words / 110) * 60)


def clear_previous_is_new(db):
    docs = db.collection("relax_tracks").where("is_new", "==", True).stream()
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"is_new": False})
        count += 1
    if count > 0:
        batch.commit()
        print(f"      Cleared is_new on {count} previous track(s)")


def save_track_to_firestore(db, title, category_key, category, audio_url, filename, script_text):
    duration = estimate_duration(clean_script_for_tts(script_text))
    doc_ref = db.collection("relax_tracks").document()
    doc_ref.set({
        "title": title, "category": category_key, "category_name": category["name"],
        "audio_url": audio_url, "storage_path": filename, "duration_seconds": duration,
        "is_premium": True, "is_new": True, "active": True, "created_at": firestore.SERVER_TIMESTAMP,
    })
    return doc_ref.id


def send_push_notification(title, category_name):
    try:
        message = messaging.Message(
            notification=messaging.Notification(title="New Relaxation Session", body=f"'{title}' is now available."),
            data={"screen": "relax_audio", "category": category_name},
            topic="relax_audio_updates",
        )
        response = messaging.send(message)
        print(f"      Notification sent: {response}")
    except Exception as e:
        print(f"      Notification failed (non-fatal): {e}")


def run_pipeline():
    print("\n  MindCore AI -- Relax Audio Pipeline (ElevenLabs)")
    print("=" * 50)

    print("\n[1/7] Connecting to Firebase...")
    db = init_firebase()

    print("\n[2/7] Reading pipeline state...")
    state = get_pipeline_state(db)
    next_index, category_key, category, title, used_titles = pick_next_category_and_title(state)
    print(f"      Category: {category['name']} | Title: {title}")

    print("\n[3/7] Generating script (Anthropic API)...")
    script = generate_script(title, category)
    word_count = len(clean_script_for_tts(script).split())
    print(f"      Script ready ({word_count} words)")

    print("\n[4/7] Generating audio (ElevenLabs)...")
    audio_bytes = generate_audio(script)

    print("\n[5/7] Uploading to Firebase Storage...")
    audio_url, filename = upload_to_firebase(audio_bytes, title, category_key)
    print(f"      Uploaded: {filename}")

    print("\n[6/7] Saving track to Firestore...")
    clear_previous_is_new(db)
    track_id = save_track_to_firestore(db, title, category_key, category, audio_url, filename, script)
    print(f"      Track ID: {track_id}")

    print("\n[7/7] Sending push notification...")
    send_push_notification(title, category["name"])

    save_pipeline_state(db, {
        "last_category_index": next_index, "used_titles": used_titles + [title],
        "last_run": firestore.SERVER_TIMESTAMP, "last_title": title,
        "last_category": category_key, "last_category_name": category["name"],
        "last_seo_keywords": category["seo_keywords"],
        "last_audio_url": audio_url, "last_track_id": track_id,
    })

    print(f"\n  DONE | {category['name']} | {title}")
    print(f"  URL: {audio_url}")


if __name__ == "__main__":
    run_pipeline()
