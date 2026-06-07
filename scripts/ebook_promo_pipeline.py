#!/usr/bin/env python3
"""
MindCore AI — Ebook Promotion Pipeline
========================================
Posts "The Silent Struggle" ebook promo content to Facebook (static image)
and TikTok (slow-zoom video from cover) with AI-generated captions.

Schedule: Every Sunday at 08:00 UTC (10:00 Malta)
"""

import os, sys, json, random, requests, subprocess, tempfile, datetime

from anthropic import Anthropic

# ── Config ────────────────────────────────────────────────────────────────────

COVER_IMAGE_URL = "https://mindcoreai.eu/wp-content/uploads/2026/06/MindCore-AI.png"
PAYHIP_LINK     = "https://payhip.com/b/3HyoE"
WEBSITE_LINK    = "https://mindcoreai.eu/#ebook"
EBOOK_TITLE     = "The Silent Struggle"
EBOOK_SUBTITLE  = "How to Rebuild Your Mental Health from Rock Bottom"
EBOOK_PRICE     = "€9.99"

UPLOAD_POST_API = "https://app.upload-post.com/api/v1"
ANTHROPIC_MODEL = "claude-sonnet-4-6"

VIDEO_DURATION  = 10   # seconds
VIDEO_FPS       = 30


# ── Promotional Angles ────────────────────────────────────────────────────────

PROMO_ANGLES = [
    "chapter_teaser",
    "personal_story",
    "pain_point",
    "transformation",
    "quote_style",
    "urgency",
    "social_proof_style",
    "raw_honesty",
]


def generate_caption(client):
    """Generate a fresh promotional caption with a random angle."""
    angle = random.choice(PROMO_ANGLES)
    print(f"   Angle: {angle}")

    prompt = f"""You are writing a social media promotional post for an ebook called
"{EBOOK_TITLE} — {EBOOK_SUBTITLE}" by Keith, Founder of MindCore AI.

EBOOK DETAILS:
- 7 chapters about addiction recovery, written by someone with 20 years of
  addiction who has been 2 years clean
- Topics: rock bottom, why willpower alone fails, shame and isolation, the
  first 7 days of recovery, building a mental reset toolkit, handling relapse
  without shame, rebuilding your life
- This is a deeply personal, honest, raw recovery guide — NOT a clinical
  self-help book

ANGLE FOR THIS POST: {angle}

Angle descriptions:
- chapter_teaser: Tease one specific chapter with a hook that makes people
  need to read more
- personal_story: Lead with Keith's personal story — 20 years addiction,
  casino manager, 2 years clean, built MindCore AI
- pain_point: Speak directly to someone who is suffering right now — 3am
  thoughts, carrying everything alone, nobody to talk to
- transformation: Focus on before/after — what life looked like during
  addiction vs 2 years into recovery
- quote_style: Write as if quoting a powerful passage from the book (make it
  original, not an actual quote)
- urgency: Honest urgency around taking action today — not aggressive
- social_proof_style: Frame it as "this is the book I wish someone had given
  me" — peer recommendation feel
- raw_honesty: Brutally honest, no filter, the uncomfortable truths about
  addiction and recovery

RULES:
- Write 3-5 short paragraphs
- Use line breaks between paragraphs
- NO hashtags
- NO emojis
- Tone: raw, honest, human — not salesy or corporate
- Maximum 200 words
- Do NOT mention the price
- Use first person ("I") for personal_story and raw_honesty angles
- Use second person ("you") for pain_point and transformation angles

Return ONLY the caption text, nothing else."""

    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


# ── Image & Video ─────────────────────────────────────────────────────────────

def download_cover(url, path):
    """Download cover image from WordPress."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    size_kb = len(resp.content) / 1024
    print(f"   Cover downloaded ({size_kb:.0f} KB)")


def create_tiktok_video(image_path, output_path):
    """Convert static cover image to a 10-second video with slow zoom."""
    total_frames = VIDEO_DURATION * VIDEO_FPS
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"zoompan=z='min(zoom+0.001\\,1.2)'"
            f":d={total_frames}:s=1080x1920:fps={VIDEO_FPS}"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-t", str(VIDEO_DURATION),
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   FFmpeg stderr: {result.stderr[-1500:]}")
        raise RuntimeError("Failed to create TikTok video")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   TikTok video created ({size_mb:.1f} MB, {VIDEO_DURATION}s)")


# ── Upload-Post helpers ───────────────────────────────────────────────────────

def upload_media(file_path, api_key):
    """Upload a media file to Upload-Post and return the media URL."""
    headers = {"Authorization": f"Bearer {api_key}"}
    mime = "image/png" if file_path.endswith(".png") else "video/mp4"
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, mime)}
        resp = requests.post(
            f"{UPLOAD_POST_API}/media/upload",
            headers=headers,
            files=files,
            timeout=120,
        )
    resp.raise_for_status()
    data = resp.json()
    media_url = data.get("url") or data.get("data", {}).get("url")
    print(f"   Media uploaded: {media_url}")
    return media_url


def create_post(api_key, profile_id, caption, media_url,
                scheduled_date=None, media_type="image"):
    """Create a post via Upload-Post API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "profile_id": profile_id,
        "caption": caption,
        "media_urls": [media_url],
        "media_type": media_type,
    }
    if scheduled_date:
        payload["scheduled_date"] = scheduled_date

    resp = requests.post(
        f"{UPLOAD_POST_API}/posts/create",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    status = "scheduled" if scheduled_date else "immediate"
    print(f"   Posted ({status}: {scheduled_date or 'now'})")
    return resp.json()


# ── Scheduling helpers ────────────────────────────────────────────────────────

def next_slot(hour_utc):
    """Return the next future datetime string for a given UTC hour today/tomorrow."""
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("== MindCore AI — Ebook Promotion Pipeline ==\n")

    # ── Environment variables ─────────────────────────────────────────────
    api_key           = os.environ.get("ANTHROPIC_API_KEY")
    upload_key        = os.environ.get("UPLOAD_POST_API_KEY")
    fb_profile        = os.environ.get("UPLOAD_POST_FB_PROFILE_ID")
    tiktok_profile    = os.environ.get("UPLOAD_POST_TIKTOK_PROFILE_ID")

    if not api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    if not upload_key:
        sys.exit("ERROR: UPLOAD_POST_API_KEY not set")

    client = Anthropic(api_key=api_key)

    # Scheduled times
    fb_time     = next_slot(10)   # 10:00 UTC = 12:00 Malta
    tiktok_time = next_slot(16)   # 16:00 UTC = 18:00 Malta

    with tempfile.TemporaryDirectory() as tmp:
        cover  = os.path.join(tmp, "cover.png")
        video  = os.path.join(tmp, "ebook_promo.mp4")

        # 1 — Download cover image
        print("1. Downloading cover image...")
        download_cover(COVER_IMAGE_URL, cover)

        # 2 — Generate caption
        print("2. Generating promotional caption...")
        caption = generate_caption(client)
        print(f"   Caption preview: {caption[:120]}...\n")

        # 3 — Facebook (static image)
        if fb_profile:
            print("3. Posting to Facebook (image)...")
            fb_url = upload_media(cover, upload_key)
            fb_caption = caption + f"\n\nGet your copy here: {PAYHIP_LINK}"
            create_post(upload_key, fb_profile, fb_caption, fb_url,
                        scheduled_date=fb_time, media_type="image")
        else:
            print("3. SKIP Facebook — UPLOAD_POST_FB_PROFILE_ID not set")

        # 4 — TikTok (video from cover)
        if tiktok_profile:
            print("4. Creating TikTok video from cover...")
            create_tiktok_video(cover, video)

            print("5. Posting to TikTok (video)...")
            tt_url = upload_media(video, upload_key)
            tt_caption = caption + f"\n\nGet your copy: {PAYHIP_LINK}"
            create_post(upload_key, tiktok_profile, tt_caption, tt_url,
                        scheduled_date=tiktok_time, media_type="video")
        else:
            print("4. SKIP TikTok — UPLOAD_POST_TIKTOK_PROFILE_ID not set")

    print("\n== Ebook promotion pipeline complete ==")


if __name__ == "__main__":
    main()
