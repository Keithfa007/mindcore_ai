#!/usr/bin/env python3
"""
MindCore AI — Ebook Promotion Pipeline
========================================
Posts "The Silent Struggle" ebook promo content to Facebook and TikTok
with AI-generated captions. Uses the same Upload-Post API pattern as
the male/female video pipelines.

Schedule: Every Sunday at 08:00 UTC (10:00 Malta)
"""

import os, sys, json, random, requests, subprocess, tempfile, datetime

from anthropic import Anthropic

# ── Config ────────────────────────────────────────────────────────────────────

COVER_IMAGE_URL     = "https://mindcoreai.eu/wp-content/uploads/2026/06/MindCore-AI.png"
PAYHIP_LINK         = "https://payhip.com/b/3HyoE"
EBOOK_TITLE         = "The Silent Struggle"
EBOOK_SUBTITLE      = "How to Rebuild Your Mental Health from Rock Bottom"

UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"
UPLOAD_POST_USER    = "MindCoreAI"
ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL     = "claude-sonnet-4-6"

VIDEO_DURATION      = 10   # seconds
VIDEO_FPS           = 30


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


# ── Upload-Post (matches male/female pipeline pattern) ───────────────────────

def get_scheduled_time(hour_utc):
    """Return the next future datetime string for a given UTC hour."""
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_to_platforms(video_path, caption, scheduled_date=None):
    """Upload video to TikTok + Facebook via Upload-Post API.

    Uses the same API pattern as male_pipeline.py / male_pipeline_patch.py:
    - Endpoint: https://api.upload-post.com/api/upload
    - Auth: Apikey header
    - User: MindCoreAI
    - Multipart form POST with video file + form fields
    """
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}

    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}

    # Build form data — same structure as male pipeline
    data = [
        ("user",                  UPLOAD_POST_USER),
        ("platform[]",            "tiktok"),
        ("platform[]",            "facebook"),
        ("title",                 caption[:2200]),          # TikTok caption
        ("facebook_title",        f"{EBOOK_TITLE} — {EBOOK_SUBTITLE}"[:255]),
        ("facebook_description",  caption + f"\n\nGet your copy: {PAYHIP_LINK}"),
    ]

    if scheduled_date:
        data.append(("scheduled_date", scheduled_date))

    try:
        with open(video_path, "rb") as f:
            files = [("video", ("ebook_promo.mp4", f, "video/mp4"))]
            resp = requests.post(
                UPLOAD_POST_API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=180,
            )

        result = (
            resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else {"raw": resp.text}
        )
        result["status_code"] = resp.status_code
        print(f"   Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok:
            print(f"   {resp.text[:300]}")
        return result

    except Exception as e:
        print(f"   Upload failed: {e}")
        return {"error": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("== MindCore AI — Ebook Promotion Pipeline ==\n")

    if not ANTHROPIC_API_KEY:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    if not UPLOAD_POST_API_KEY:
        sys.exit("ERROR: UPLOAD_POST_API_KEY not set")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Schedule for 12:00 Malta (10:00 UTC)
    scheduled_date = get_scheduled_time(10)

    with tempfile.TemporaryDirectory() as tmp:
        cover = os.path.join(tmp, "cover.png")
        video = os.path.join(tmp, "ebook_promo.mp4")

        # 1 — Download cover image
        print("1. Downloading cover image...")
        download_cover(COVER_IMAGE_URL, cover)

        # 2 — Generate caption
        print("2. Generating promotional caption...")
        caption = generate_caption(client)
        print(f"   Caption preview: {caption[:120]}...\n")

        # Append Payhip link to caption for TikTok
        full_caption = caption + f"\n\nGet your copy: {PAYHIP_LINK}"

        # 3 — Create video from cover
        print("3. Creating video from cover image...")
        create_tiktok_video(cover, video)

        # 4 — Upload to TikTok + Facebook via Upload-Post
        print("4. Uploading to TikTok + Facebook...")
        result = upload_to_platforms(
            video, full_caption, scheduled_date=scheduled_date
        )

        if result.get("status_code") == 200:
            print(f"   Scheduled OK — fires at {scheduled_date}")
        elif result.get("skipped"):
            print(f"   Skipped: {result.get('reason')}")

    print("\n== Ebook promotion pipeline complete ==")


if __name__ == "__main__":
    main()
