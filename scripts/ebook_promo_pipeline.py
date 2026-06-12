#!/usr/bin/env python3
"""
MindCore AI — Ebook Promotion Pipeline v2.5
============================================
v2.5: Expanded voiceover variations (18 angles, 12 hooks, 6 closers).
v2.4: Rotating cover image pool (7 Canva designs).
v2.3: Single upload call -- video to TikTok + Facebook + YouTube.
v2.2: Added YouTube.
v2.1: Updated hashtags.
v2: ElevenLabs TTS. 4x/week.
"""

import os, sys, json, random, requests, subprocess, tempfile, datetime
from anthropic import Anthropic

COVER_IMAGE_POOL = [
    "https://mindcoreai.eu/wp-content/uploads/2026/06/Poster-The-Silent-Struggle-Rise-from-Rock-Bottom-1.png",
    "https://mindcoreai.eu/wp-content/uploads/2026/06/Lone-Silhouette-Against-Golden-Dawn-Poster.png",
    "https://mindcoreai.eu/wp-content/uploads/2026/06/Solitary-Figure-at-Dawn-on-Beach-Poster.png",
    "https://mindcoreai.eu/wp-content/uploads/2026/06/Dramatic-Poster-Journey-to-Resilience.png",
    "https://mindcoreai.eu/wp-content/uploads/2026/06/Cinematic-Poster-Rise-from-Rock-Bottom.png",
    "https://mindcoreai.eu/wp-content/uploads/2026/06/A-Cinematic-Journey-Through-Misty-Trees.png",
    "https://mindcoreai.eu/wp-content/uploads/2026/06/Somber-Path-to-Hope-in-a-Dark-Forest.png",
]
COVER_IMAGE_URL = random.choice(COVER_IMAGE_POOL)
PAYHIP_LINK         = "https://payhip.com/b/3HyoE"
EBOOK_TITLE         = "The Silent Struggle"
EBOOK_SUBTITLE      = "How to Rebuild Your Mental Health from Rock Bottom"

UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"
UPLOAD_POST_USER    = "MindCoreAI"
ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL     = "claude-sonnet-4-6"

ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "jfIS2w2yJi0grJZPyEsk"
ELEVENLABS_API_URL  = "https://api.elevenlabs.io/v1/text-to-speech"

TK_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #recovery #addiction #sobriety #sobertok #soberlife #ebook #selfhelp #healing #selflove #fyp #mentalhealthrecovery"
FB_HASHTAGS = "#mentalhealth #mentalhealthmatters #recovery #addiction #sobriety #healing #selfhelp #mindcoreai"

PROMO_ANGLES = [
    "chapter_teaser", "personal_story", "pain_point", "transformation",
    "quote_style", "urgency", "social_proof_style", "raw_honesty",
    "before_and_after", "3am_moment", "letter_to_past_self", "one_line_truth",
    "what_nobody_tells_you", "the_day_everything_changed", "relapse_honesty",
    "first_7_days", "shame_chapter", "rebuilding_identity", "midnight_confession",
    "if_you_are_reading_this",
]

VOICEOVER_HOOKS = [
    "I spent twenty years destroying myself before I wrote a single word of this book.",
    "Nobody talks about what happens after rock bottom. I did.",
    "This isn't a self-help book. It's a survival guide written in the dark.",
    "I wrote this at 3am because that's when the truth comes out.",
    "The hardest chapter to write was the one about shame. You'll understand why.",
    "Relapse doesn't mean failure. That's chapter six. It nearly killed me to write it.",
    "If someone handed me this book ten years ago, I might have saved a decade of pain.",
    "I didn't write this to inspire you. I wrote it because I needed it to exist.",
    "Twenty years of addiction. Two years clean. Seven chapters of everything in between.",
    "Rock bottom has a basement. I found it. Then I found the stairs.",
    "The first seven days clean were the longest year of my life.",
    "This book isn't about willpower. It's about what happens when willpower runs out.",
]

VOICEOVER_CLOSERS = [
    "The Silent Struggle. Available now.",
    "The Silent Struggle. Link in bio.",
    "The Silent Struggle. If you need it, you already know.",
    "The Silent Struggle. Written in the dark so you don't have to stay there.",
    "The Silent Struggle. Seven chapters. Zero bullshit.",
    "The Silent Struggle. For the ones still fighting.",
]

def generate_caption(client):
    angle = random.choice(PROMO_ANGLES); print(f"   Angle: {angle}")
    prompt = f"""You are writing a SHORT social media promotional post for an ebook called
"{EBOOK_TITLE} — {EBOOK_SUBTITLE}" by Keith, Founder of MindCore AI.

EBOOK DETAILS:
- 7 chapters about addiction recovery, written by someone with 20 years of addiction who has been 2 years clean
- Topics: rock bottom, willpower, shame, first 7 days, mental reset toolkit, relapse, rebuilding
- Deeply personal recovery guide — NOT clinical self-help

ANGLE: {angle}

RULES:
- Maximum 2-3 SHORT sentences. Be punchy and direct.
- NO emojis. Raw, honest tone — not salesy
- Use first person for personal_story/raw_honesty, second person for others
- Do NOT mention the price, hashtags, or links

Return ONLY the caption text, nothing else."""
    return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}]).content[0].text.strip()

def generate_voiceover_script(client):
    angle = random.choice(PROMO_ANGLES)
    hook = random.choice(VOICEOVER_HOOKS)
    closer = random.choice(VOICEOVER_CLOSERS)
    print(f"   Voiceover angle: {angle}")
    print(f"   Hook: {hook[:50]}...")
    print(f"   Closer: {closer}")
    prompt = f"""Write a SHORT voiceover script for a TikTok video promoting an ebook called
"{EBOOK_TITLE} — {EBOOK_SUBTITLE}" by Keith, Founder of MindCore AI.

The ebook is a deeply personal recovery guide written by someone who spent 20 years in addiction and has been 2 years clean.
7 chapters: rock bottom, willpower, shame, the first 7 days, mental reset toolkit, relapse, rebuilding identity.

ANGLE: {angle}
OPENING HOOK (use this as the first line or adapt it): "{hook}"
CLOSING LINE (end with this exactly): "{closer}"

RULES:
- Total 3-5 sentences including hook and closer. 10-18 seconds spoken.
- Speak as Keith (first person) — raw, honest, direct, no filter
- The middle 1-3 sentences should connect the hook to the closer naturally
- NO emojis, NO hashtags, NO links, NO "Hey", NO "What's up"
- Sound like a man talking to himself at 3am, not a marketer

Return ONLY the voiceover text, nothing else."""
    return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=300, messages=[{"role": "user", "content": prompt}]).content[0].text.strip()

def download_cover(url, path):
    resp = requests.get(url, timeout=30); resp.raise_for_status()
    with open(path, "wb") as f: f.write(resp.content)
    print(f"   Cover downloaded ({len(resp.content) / 1024:.0f} KB)")

def generate_voiceover(script_text, output_path):
    if not ELEVENLABS_API_KEY: print("   ELEVENLABS_API_KEY not set"); return False
    url = f"{ELEVENLABS_API_URL}/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {"text": script_text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.50, "similarity_boost": 0.75}}
    try:
        print(f"   ElevenLabs TTS: {len(script_text)} chars")
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
        if not resp.ok: print(f"   ElevenLabs error {resp.status_code}"); return False
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65_536):
                if chunk: f.write(chunk)
        print(f"   Voiceover generated ({os.path.getsize(output_path) / 1024:.0f} KB)"); return True
    except Exception as e: print(f"   ElevenLabs failed: {e}"); return False

def create_static_video_with_voice(image_path, audio_path, output_path):
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path, "-vf",
           "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
           "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "128k",
           "-pix_fmt", "yuv420p", "-shortest", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0: raise RuntimeError(f"FFmpeg failed")
    print(f"   Video created ({os.path.getsize(output_path) / (1024*1024):.1f} MB)")

def create_static_video_silent(image_path, output_path, duration=10):
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-vf",
           "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
           "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-t", str(duration), output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0: raise RuntimeError(f"FFmpeg failed")

def get_scheduled_time(hour_utc):
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target: target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")

def upload_all_platforms(video_path, tiktok_caption, fb_title, fb_description, yt_title, yt_description, yt_tags, scheduled_date=None):
    """Upload video to TikTok + Facebook + YouTube in a single Upload-Post call."""
    if not UPLOAD_POST_API_KEY: return {"skipped": True, "reason": "no API key"}
    data = [
        ("user", UPLOAD_POST_USER),
        ("platform[]", "tiktok"),
        ("platform[]", "facebook"),
        ("platform[]", "youtube"),
        ("title", tiktok_caption[:2200]),
        ("facebook_title", fb_title[:255]),
        ("facebook_description", fb_description),
        ("youtube_title", yt_title[:100]),
        ("youtube_description", yt_description[:5000]),
        ("youtube_tags", yt_tags),
    ]
    if scheduled_date: data.append(("scheduled_date", scheduled_date))
    try:
        with open(video_path, "rb") as f:
            resp = requests.post(UPLOAD_POST_API_URL, headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
                                 files=[("video", ("ebook_promo.mp4", f, "video/mp4"))], data=data, timeout=180)
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        result["status_code"] = resp.status_code
        if scheduled_date: result["scheduled_date"] = scheduled_date
        print(f"   Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"   {resp.text[:300]}")
        return result
    except Exception as e: print(f"   Upload failed: {e}"); return {"error": str(e)}

def main():
    print(f"== MindCore AI — Ebook Promotion Pipeline v2.5 ==\n")
    print(f"   Cover: {COVER_IMAGE_URL.split('/')[-1]}")
    if not ANTHROPIC_API_KEY: sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    scheduled_date = get_scheduled_time(10)

    with tempfile.TemporaryDirectory() as tmp:
        cover = os.path.join(tmp, "cover.png")
        audio = os.path.join(tmp, "voiceover.mp3")
        video = os.path.join(tmp, "ebook_promo.mp4")

        print("1. Downloading cover..."); download_cover(COVER_IMAGE_URL, cover)
        print("2. Generating caption..."); caption = generate_caption(client); print(f"   {caption}\n")
        print("3. Generating voiceover..."); vo_script = generate_voiceover_script(client); print(f"   {vo_script}\n")
        has_voice = generate_voiceover(vo_script, audio)
        print("4. Creating video...")
        if has_voice: create_static_video_with_voice(cover, audio, video)
        else: create_static_video_silent(cover, video)

        tiktok_caption = f"{caption}\n\nGet your copy: {PAYHIP_LINK}\n\n{TK_HASHTAGS}"
        fb_title = EBOOK_TITLE
        fb_description = f"{caption}\n\nGet your copy: {PAYHIP_LINK}\n\n{FB_HASHTAGS}"
        yt_title = f"{EBOOK_TITLE} — {EBOOK_SUBTITLE} #Shorts"[:100]
        yt_description = f"{caption}\n\nGet your copy: {PAYHIP_LINK}\n\nA deeply personal recovery guide by Keith, Founder of MindCore AI.\n\n#mindcoreai #mentalhealth #recovery #addiction #sobriety #ebook #selfhelp #Shorts"
        yt_tags = "mental health,recovery,addiction,sobriety,ebook,self help,the silent struggle,mindcore ai,healing,wellness"

        print("5. Uploading to TikTok + Facebook + YouTube...")
        result = upload_all_platforms(video, tiktok_caption, fb_title, fb_description, yt_title, yt_description, yt_tags, scheduled_date=scheduled_date)

        if result.get("status_code") in (200, 202):
            print(f"   All platforms: Scheduled OK — {scheduled_date}")
        elif result.get("skipped"):
            print(f"   Skipped — {result.get('reason')}")
        else:
            print(f"   Check result — {result.get('status_code', 'unknown')}")

    print("\n== Done ==")

if __name__ == "__main__":
    main()
