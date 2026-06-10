#!/usr/bin/env python3
"""
MindCore AI — Ebook Promotion Pipeline v2
==========================================
Posts "The Silent Struggle" ebook promo content to Facebook and TikTok.
- TikTok: static image video + ElevenLabs voiceover
- Facebook: static image upload

v2: ElevenLabs TTS (replaces Fish Audio). 4x/week schedule.
"""

import os, sys, json, random, requests, subprocess, tempfile, datetime
from anthropic import Anthropic

COVER_IMAGE_URL     = "https://mindcoreai.eu/wp-content/uploads/2026/06/Poster-The-Silent-Struggle-Rise-from-Rock-Bottom-1.png"
PAYHIP_LINK         = "https://payhip.com/b/3HyoE"
EBOOK_TITLE         = "The Silent Struggle"
EBOOK_SUBTITLE      = "How to Rebuild Your Mental Health from Rock Bottom"

UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"
UPLOAD_POST_USER    = "MindCoreAI"
ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL     = "claude-sonnet-4-6"

# ElevenLabs — male voice (Keith narrating his book)
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "jfIS2w2yJi0grJZPyEsk"
ELEVENLABS_API_URL  = "https://api.elevenlabs.io/v1/text-to-speech"

HASHTAGS = "#mindcoreai #mentalhealth #recovery #addiction #sobriety #ebook #menswellness #selfhelp #healing #fyp"

PROMO_ANGLES = [
    "chapter_teaser", "personal_story", "pain_point", "transformation",
    "quote_style", "urgency", "social_proof_style", "raw_honesty",
]


def generate_caption(client):
    angle = random.choice(PROMO_ANGLES)
    print(f"   Angle: {angle}")
    prompt = f"""You are writing a SHORT social media promotional post for an ebook called
"{EBOOK_TITLE} — {EBOOK_SUBTITLE}" by Keith, Founder of MindCore AI.

EBOOK DETAILS:
- 7 chapters about addiction recovery, written by someone with 20 years of
  addiction who has been 2 years clean
- Topics: rock bottom, willpower, shame, first 7 days, mental reset toolkit,
  relapse, rebuilding
- Deeply personal recovery guide — NOT clinical self-help

ANGLE: {angle}

RULES:
- Maximum 2-3 SHORT sentences. Be punchy and direct.
- NO emojis
- Raw, honest tone — not salesy
- Use first person for personal_story/raw_honesty, second person for others
- Do NOT mention the price
- Do NOT include hashtags or links

Return ONLY the caption text, nothing else."""
    resp = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
    return resp.content[0].text.strip()


def generate_voiceover_script(client):
    angle = random.choice(PROMO_ANGLES)
    print(f"   Voiceover angle: {angle}")
    prompt = f"""Write a SHORT voiceover script for a TikTok video promoting an ebook called
"{EBOOK_TITLE} — {EBOOK_SUBTITLE}" by Keith, Founder of MindCore AI.

The ebook is a deeply personal recovery guide written by someone who spent
20 years in addiction and has been 2 years clean.

ANGLE: {angle}

RULES:
- Maximum 3-4 sentences that take 10-15 seconds to read aloud
- Speak as Keith (first person) — raw, honest, direct
- End with "The Silent Struggle. Available now." or "Link in bio."
- NO emojis, NO hashtags, NO links
- Natural spoken words — like talking to a friend
- Do NOT start with "Hey" or "What's up" — start powerful

Return ONLY the voiceover text, nothing else."""
    resp = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
    return resp.content[0].text.strip()


def download_cover(url, path):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    print(f"   Cover downloaded ({len(resp.content) / 1024:.0f} KB)")


def generate_voiceover(script_text, output_path):
    """Generate voiceover using ElevenLabs TTS."""
    if not ELEVENLABS_API_KEY:
        print("   ELEVENLABS_API_KEY not set — skipping voiceover")
        return False

    url = f"{ELEVENLABS_API_URL}/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": script_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.50, "similarity_boost": 0.75},
    }

    try:
        print(f"   ElevenLabs TTS: voice {ELEVENLABS_VOICE_ID[:8]}... | {len(script_text)} chars")
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
        if not resp.ok:
            print(f"   ElevenLabs error {resp.status_code}: {resp.text[:200]}")
            return False

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65_536):
                if chunk:
                    f.write(chunk)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"   Voiceover generated ({size_kb:.0f} KB)")
        return True

    except Exception as e:
        print(f"   ElevenLabs failed: {e}")
        return False


def create_static_video_with_voice(image_path, audio_path, output_path):
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")
    print(f"   Static video + voiceover created ({os.path.getsize(output_path) / (1024*1024):.1f} MB)")


def create_static_video_silent(image_path, output_path, duration=10):
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-t", str(duration), output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")
    print(f"   Silent static video created ({os.path.getsize(output_path) / (1024*1024):.1f} MB)")


def get_scheduled_time(hour_utc):
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_tiktok_video(video_path, caption, scheduled_date=None):
    if not UPLOAD_POST_API_KEY: return {"skipped": True, "reason": "no API key"}
    data = [("user", UPLOAD_POST_USER), ("platform[]", "tiktok"), ("title", caption[:2200])]
    if scheduled_date: data.append(("scheduled_date", scheduled_date))
    try:
        with open(video_path, "rb") as f:
            resp = requests.post(UPLOAD_POST_API_URL, headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
                                 files=[("video", ("ebook_promo.mp4", f, "video/mp4"))], data=data, timeout=180)
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        result["status_code"] = resp.status_code
        print(f"   TikTok upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        return result
    except Exception as e:
        print(f"   TikTok upload failed: {e}"); return {"error": str(e)}


def upload_facebook_image(image_path, caption, scheduled_date=None):
    if not UPLOAD_POST_API_KEY: return {"skipped": True, "reason": "no API key"}
    data = [("user", UPLOAD_POST_USER), ("platform[]", "facebook"),
            ("facebook_title", EBOOK_TITLE[:255]), ("facebook_description", caption)]
    if scheduled_date: data.append(("scheduled_date", scheduled_date))
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(UPLOAD_POST_API_URL, headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
                                 files=[("image", ("ebook_cover.png", f, "image/png"))], data=data, timeout=180)
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        result["status_code"] = resp.status_code
        print(f"   Facebook upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        return result
    except Exception as e:
        print(f"   Facebook upload failed: {e}"); return {"error": str(e)}


def main():
    print("== MindCore AI — Ebook Promotion Pipeline v2 (ElevenLabs) ==\n")
    if not ANTHROPIC_API_KEY: sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    if not UPLOAD_POST_API_KEY: sys.exit("ERROR: UPLOAD_POST_API_KEY not set")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    scheduled_date = get_scheduled_time(10)

    with tempfile.TemporaryDirectory() as tmp:
        cover = os.path.join(tmp, "cover.png")
        audio = os.path.join(tmp, "voiceover.mp3")
        video = os.path.join(tmp, "ebook_promo.mp4")

        print("1. Downloading cover image...")
        download_cover(COVER_IMAGE_URL, cover)

        print("2. Generating promotional caption...")
        caption = generate_caption(client)
        print(f"   Caption: {caption}\n")

        print("3. Generating voiceover (ElevenLabs)...")
        vo_script = generate_voiceover_script(client)
        print(f"   Script: {vo_script}\n")
        has_voice = generate_voiceover(vo_script, audio)

        print("4. Creating TikTok video...")
        if has_voice:
            create_static_video_with_voice(cover, audio, video)
        else:
            print("   No voiceover — falling back to silent video")
            create_static_video_silent(cover, video)

        tiktok_caption = f"{caption}\n\nGet your copy: {PAYHIP_LINK}\n\n{HASHTAGS}"
        fb_caption = f"{caption}\n\nGet your copy: {PAYHIP_LINK}\n\n{HASHTAGS}"

        print("5. Uploading to TikTok...")
        tk_result = upload_tiktok_video(video, tiktok_caption, scheduled_date=scheduled_date)

        print("6. Uploading to Facebook...")
        fb_result = upload_facebook_image(cover, fb_caption, scheduled_date=scheduled_date)

        for platform, result in [("TikTok", tk_result), ("Facebook", fb_result)]:
            if result.get("status_code") in (200, 202):
                print(f"   {platform}: Scheduled OK — fires at {scheduled_date}")
            elif result.get("skipped"):
                print(f"   {platform}: Skipped — {result.get('reason')}")
            else:
                print(f"   {platform}: Check result — {result.get('status_code', 'unknown')}")

    print("\n== Ebook promotion pipeline complete ==")

if __name__ == "__main__":
    main()
