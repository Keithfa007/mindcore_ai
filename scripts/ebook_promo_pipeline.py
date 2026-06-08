#!/usr/bin/env python3
"""
MindCore AI — Ebook Promotion Pipeline
========================================
Posts "The Silent Struggle" ebook promo content to Facebook and TikTok.
- TikTok: static image video (no movement, no music)
- Facebook: static image upload (no video needed)

Schedule: Every Sunday at 08:00 UTC (10:00 Malta)
"""

import os, sys, json, random, requests, subprocess, tempfile, datetime

from anthropic import Anthropic

# ── Config ────────────────────────────────────────────────────────────────────

COVER_IMAGE_URL     = "https://mindcoreai.eu/wp-content/uploads/2026/06/Poster-The-Silent-Struggle-Rise-from-Rock-Bottom.png"
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

HASHTAGS            = "#mindcoreai #mentalhealth #recovery #addiction #sobriety #ebook #menswellness #selfhelp #healing #fyp"


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
    """Generate a short, punchy promotional caption."""
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
- Do NOT include hashtags (they will be added separately)
- Do NOT include any links (they will be added separately)

Return ONLY the caption text, nothing else."""

    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=200,
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


def create_static_video(image_path, output_path):
    """Create a STATIC video from cover image — no zoom, no movement, no music.
    TikTok requires video format but the image stays perfectly still."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920"
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
        raise RuntimeError("Failed to create video")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   Static video created ({size_mb:.1f} MB, {VIDEO_DURATION}s, no movement)")


# ── Upload-Post ───────────────────────────────────────────────────────────────

def get_scheduled_time(hour_utc):
    """Return the next future datetime string for a given UTC hour."""
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_tiktok_video(video_path, caption, scheduled_date=None):
    """Upload static video to TikTok via Upload-Post API."""
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}

    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}

    data = [
        ("user",       UPLOAD_POST_USER),
        ("platform[]", "tiktok"),
        ("title",      caption[:2200]),
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
        print(f"   TikTok upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok:
            print(f"   {resp.text[:300]}")
        return result

    except Exception as e:
        print(f"   TikTok upload failed: {e}")
        return {"error": str(e)}


def upload_facebook_image(image_path, caption, scheduled_date=None):
    """Upload static image to Facebook via Upload-Post API."""
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}

    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}

    data = [
        ("user",                  UPLOAD_POST_USER),
        ("platform[]",            "facebook"),
        ("facebook_title",        EBOOK_TITLE[:255]),
        ("facebook_description",  caption),
    ]

    if scheduled_date:
        data.append(("scheduled_date", scheduled_date))

    try:
        with open(image_path, "rb") as f:
            files = [("image", ("ebook_cover.png", f, "image/png"))]
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
        print(f"   Facebook upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok:
            print(f"   {resp.text[:300]}")
        return result

    except Exception as e:
        print(f"   Facebook upload failed: {e}")
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
        print(f"   Caption: {caption}\n")

        # 3 — Build captions with link and hashtags
        tiktok_caption = f"{caption}\n\nGet your copy: {PAYHIP_LINK}\n\n{HASHTAGS}"
        fb_caption = f"{caption}\n\nGet your copy: {PAYHIP_LINK}\n\n{HASHTAGS}"

        # 4 — Create STATIC video for TikTok (no zoom, no music)
        print("3. Creating static video for TikTok...")
        create_static_video(cover, video)

        # 5 — Upload to TikTok (video) and Facebook (image) separately
        print("4. Uploading to TikTok (static video)...")
        tk_result = upload_tiktok_video(video, tiktok_caption, scheduled_date=scheduled_date)

        print("5. Uploading to Facebook (static image)...")
        fb_result = upload_facebook_image(cover, fb_caption, scheduled_date=scheduled_date)

        # Summary
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
