import anthropic
import requests
import firebase_admin
from firebase_admin import credentials, storage, firestore, messaging
import json
import os
import re
from datetime import datetime

# ─────────────────────────────────────────
# VOICE CONFIG
# ─────────────────────────────────────────
FISH_AUDIO_VOICE_ID = "c1a8e435804f4676a9be5c7ac230c625"

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


# ─────────────────────────────────────────
# FIREBASE INIT
# ─────────────────────────────────────────
def init_firebase():
    service_account_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(service_account_dict)
    firebase_admin.initialize_app(cred, {
        "storageBucket": os.environ["FIREBASE_BUCKET"]
    })
    return firestore.client()


# ─────────────────────────────────────────
# PIPELINE STATE (stored in Firestore)
# ─────────────────────────────────────────
def get_pipeline_state(db):
    doc = db.collection("pipeline_state").document("relax_audio").get()
    if doc.exists:
        return doc.to_dict()
    return {"last_category_index": -1, "used_titles": []}


def save_pipeline_state(db, state):
    db.collection("pipeline_state").document("relax_audio").set(state)


# ─────────────────────────────────────────
# CATEGORY + TITLE SELECTION
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# SCRIPT GENERATION (Anthropic API)
# ─────────────────────────────────────────
def generate_script(title, category):
    print("  Calling Anthropic API...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are a professional meditation script writer for MindCore AI — a mental wellness app built specifically for men over 35 and men in recovery from alcohol or substances.

Write a complete guided relaxation audio script with these exact specifications:

TITLE: {title}
CATEGORY: {category['name']}
SEO KEYWORDS TO WEAVE IN NATURALLY: {category['seo_keywords']}

REQUIREMENTS:
- Length: 780-860 words
- Tone: Warm, calm, masculine authority. Grounded and real. Not clinical, not spiritual/religious, not soft or preachy.
- Target audience: Men 35+, many managing stress, anxiety, or recovery from substances
- Include pacing markers throughout: [pause 3s], [pause 5s], [pause 8s], [slow breath] — these guide the audio generation
- Structure:
    1. Opening (set the scene, first breath, invite the listener in) — ~120 words
    2. Body (the core technique — body scan, breathwork, visualisation, affirmations etc) — ~520 words
    3. Close (gently return, leave them with peace and strength) — ~120 words
- Naturally weave in 2-3 of the SEO keyword phrases without it feeling forced
- NEVER use: journey, universe, manifest, chakra, vibration, divine, higher self
- Speak directly to the listener as "you"
- Acknowledge real-world struggles honestly without dwelling on them
- Reference the specific technique named in the title
- End with quiet confidence — not spiritual transcendence, just real calm

Write ONLY the script. No title, no notes, no introduction. Begin immediately with the opening words of the meditation."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


# ─────────────────────────────────────────
# CLEAN SCRIPT FOR TTS
# ─────────────────────────────────────────
def clean_script_for_tts(script):
    clean = re.sub(r'\[.*?\]', '', script)
    clean = re.sub(r'\n\s*\n\s*\n', '\n\n', clean)
    return clean.strip()


# ─────────────────────────────────────────
# AUDIO GENERATION (Fish Audio API)
# ─────────────────────────────────────────
def generate_audio(script_text):
    clean_text = clean_script_for_tts(script_text)

    response = requests.post(
        "https://api.fish.audio/v1/tts",
        headers={
            "Authorization": f"Bearer {os.environ['FISH_AUDIO_API_KEY']}",
            "Content-Type": "application/json",
            "model": "s2-pro",
        },
        json={
            "text": clean_text,
            "reference_id": FISH_AUDIO_VOICE_ID,
            "format": "mp3",
            "sample_rate": 44100,
            "mp3_bitrate": 128,
            "prosody": {
                "speed": 0.88,
                "volume": 0,
                "normalize_loudness": True,
            },
            "latency": "normal",
            "repetition_penalty": 1.2,
        },
        timeout=180,
    )

    if response.status_code != 200:
        raise Exception(f"Fish Audio error {response.status_code}: {response.text}")

    return response.content


# ─────────────────────────────────────────
# UPLOAD TO FIREBASE STORAGE
# ─────────────────────────────────────────
def upload_to_firebase(audio_bytes, title, category_key):
    bucket = storage.bucket()

    clean = re.sub(r'[^a-z0-9 ]', '', title.lower())
    clean = clean.replace(' ', '_')[:50]
    timestamp = datetime.now().strftime('%Y%m%d')
    filename = f"relax_audio/{category_key}/{timestamp}_{clean}.mp3"

    blob = bucket.blob(filename)
    blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
    blob.make_public()

    return blob.public_url, filename


# ─────────────────────────────────────────
# ESTIMATE DURATION
# ─────────────────────────────────────────
def estimate_duration(script_text):
    words = len(script_text.split())
    return int((words / 110) * 60)


# ─────────────────────────────────────────
# CLEAR is_new ON ALL PREVIOUS TRACKS
# ─────────────────────────────────────────
def clear_previous_is_new(db):
    """Remove is_new badge from all existing tracks before adding the new one."""
    docs = db.collection("relax_tracks").where("is_new", "==", True).stream()
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"is_new": False})
        count += 1
    if count > 0:
        batch.commit()
        print(f"      ✅ Cleared is_new on {count} previous track(s)")


# ─────────────────────────────────────────
# SAVE TRACK TO FIRESTORE
# ─────────────────────────────────────────
def save_track_to_firestore(db, title, category_key, category, audio_url, filename, script_text):
    duration = estimate_duration(clean_script_for_tts(script_text))

    doc_ref = db.collection("relax_tracks").document()
    doc_ref.set({
        "title": title,
        "category": category_key,
        "category_name": category["name"],
        "audio_url": audio_url,
        "storage_path": filename,
        "duration_seconds": duration,
        "is_premium": True,
        "is_new": True,
        "active": True,
        "created_at": firestore.SERVER_TIMESTAMP,
    })

    return doc_ref.id


# ─────────────────────────────────────────
# SEND FCM PUSH NOTIFICATION
# ─────────────────────────────────────────
def send_push_notification(title, category_name):
    """Send push notification to all app users via FCM topic."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="New Relaxation Session",
                body=f"'{title}' is now available in Relaxing Audio.",
            ),
            data={
                "screen": "relax_audio",
                "category": category_name,
            },
            topic="relax_audio_updates",
        )
        response = messaging.send(message)
        print(f"      ✅ Notification sent: {response}")
    except Exception as e:
        print(f"      ⚠️  Notification failed (non-fatal): {e}")


# ─────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────
def run_pipeline():
    print("\n🎧  MindCore AI — Relax Audio Pipeline")
    print("=" * 45)

    print("\n[1/7] Connecting to Firebase...")
    db = init_firebase()
    print("      ✅ Connected")

    print("\n[2/7] Reading pipeline state...")
    state = get_pipeline_state(db)
    next_index, category_key, category, title, used_titles = pick_next_category_and_title(state)
    print(f"      ✅ Category : {category['name']}")
    print(f"      ✅ Title    : {title}")

    print("\n[3/7] Generating script (Anthropic API)...")
    script = generate_script(title, category)
    word_count = len(clean_script_for_tts(script).split())
    print(f"      ✅ Script ready ({word_count} words)")

    print("\n[4/7] Generating audio (Fish Audio)...")
    audio_bytes = generate_audio(script)
    size_mb = len(audio_bytes) / 1024 / 1024
    print(f"      ✅ Audio ready ({size_mb:.1f} MB)")

    print("\n[5/7] Uploading to Firebase Storage...")
    audio_url, filename = upload_to_firebase(audio_bytes, title, category_key)
    print(f"      ✅ Uploaded : {filename}")

    print("\n[6/7] Saving track to Firestore...")
    clear_previous_is_new(db)
    track_id = save_track_to_firestore(
        db, title, category_key, category, audio_url, filename, script
    )
    print(f"      ✅ Track ID : {track_id}")

    print("\n[7/7] Sending push notification...")
    send_push_notification(title, category["name"])

    # Save state — blog pipeline reads last_title, last_category, last_seo_keywords
    save_pipeline_state(db, {
        "last_category_index": next_index,
        "used_titles": used_titles + [title],
        "last_run": firestore.SERVER_TIMESTAMP,
        "last_title": title,
        "last_category": category_key,
        "last_category_name": category["name"],
        "last_seo_keywords": category["seo_keywords"],
        "last_audio_url": audio_url,
        "last_track_id": track_id,
    })

    print("\n" + "=" * 45)
    print("🎉  Pipeline complete!")
    print(f"    Title    : {title}")
    print(f"    Category : {category['name']}")
    print(f"    URL      : {audio_url}")
    print(f"    Track ID : {track_id}")
    print("=" * 45 + "\n")


if __name__ == "__main__":
    run_pipeline()
