#!/usr/bin/env python3
"""
MindCore AI -- Affiliate Product Carousel Pipeline v1.5
========================================================
Promotes Online-Therapy.com as personal recommendation carousels.
Rotates through different therapy angles (individual, couples, CBT, affordability, etc.). Visually distinct from
the main emotional carousel (warm amber tones, centered layout,
lifestyle backgrounds, 5 slides).

v1.5: Split into 3 separate Upload-Post requests for correct descriptions.
      EU TikTok, EU Facebook (with clickable affiliate link), US TikTok.

Schedule: Wednesday + Friday
Cost: ~$0.025/post (5 x fal.ai Flux Schnell @ ~$0.005)
"""

import base64, io, json, os, random, time, math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import anthropic, requests
from PIL import Image, ImageDraw, ImageFont
from scripts.fal_image import generate_fal_image

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
GITHUB_RUN_NUMBER = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload_photos"
OUTPUT_DIR = Path("scripts/output_affiliate_carousel")
HISTORY_PATH = Path("scripts/affiliate_carousel_history.json")

IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
TIKTOK_TITLE_LIMIT = 90
TIKTOK_DESC_LIMIT = 4000
CLAUDE_MAX_RETRIES = 8
CLAUDE_RETRY_BASE = 30
POST_HOUR_UTC = 12
US_POST_HOUR_UTC = 14
REQUIRED_BRAND_HASHTAG = "#mindcoreai"
TIKTOK_HASHTAGS = "#mindcoreai #mentalhealth #onlinetherapy #therapy #CBT #selfcare #fyp #ad"
FB_HASHTAGS = "#mindcoreai #mentalhealth #onlinetherapy #therapy #selfcare #ad"
US_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #onlinetherapy #therapytok #CBT #healing #selfcare #fyp #ad"
SLIDE_COUNT = 5

BADGE_BG = (212, 165, 116)
BADGE_TEXT = (20, 15, 10)
HOOK_COLOR = (255, 255, 255)
BODY_COLOR = (240, 235, 225)
BOLD_COLOR = (255, 255, 255)
CTA_COLOR = (255, 255, 255)
ACCENT_COLOR = (212, 165, 116)
URL_COLOR = (200, 190, 175)
GRADIENT_TOP_ALPHA = 60
GRADIENT_BOTTOM_ALPHA = 200

BADGE_SIZE = 32
HOOK_SIZE = 78
BODY_SIZE = 44
BOLD_SIZE = 50
CTA_TRIG = 56
CTA_APP = 72
CTA_URL = 36

TEXT_CENTER_Y = 0.48
MAX_TEXT_W = int(IMAGE_WIDTH * 0.82)
LINE_GAP = 16
SECTION_GAP = 40


def get_scheduled_post_time():
    now = datetime.now(timezone.utc)
    target = now.replace(hour=POST_HOUR_UTC, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    s = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"  EU Scheduled: {s} ({POST_HOUR_UTC:02d}:00 UTC / 14:00 Malta)")
    return s


THERAPY_ANGLES = [
    {
        "angle": "individual_therapy",
        "name": "Online-Therapy.com",
        "hook": "Individual therapy from home",
        "focus": "Licensed therapists, CBT-based sessions, worksheets, and messaging. Real therapy without the waiting room.",
        "audience": "anyone struggling with anxiety, depression, stress, or just needing someone to talk to"
    },
    {
        "angle": "couples_therapy",
        "name": "Online-Therapy.com",
        "hook": "Couples therapy you can do together from home",
        "focus": "Work on your relationship with a licensed therapist. Video sessions, messaging, and tools designed for couples.",
        "audience": "couples dealing with communication issues, trust, distance, or wanting to strengthen their relationship"
    },
    {
        "angle": "affordability",
        "name": "Online-Therapy.com",
        "hook": "Therapy that does not break the bank",
        "focus": "Quality CBT-based therapy at a fraction of in-person costs. No insurance needed. Cancel anytime.",
        "audience": "people who want therapy but think they cannot afford it"
    },
    {
        "angle": "mens_mental_health",
        "name": "Online-Therapy.com",
        "hook": "Built for men who find it hard to ask for help",
        "focus": "Private, no waiting room, no judgment. Text your therapist when talking feels too hard. CBT tools that actually work.",
        "audience": "men dealing with anger, isolation, stress, or emotional shutdown"
    },
    {
        "angle": "anxiety_focus",
        "name": "Online-Therapy.com",
        "hook": "Too anxious to sit in a waiting room?",
        "focus": "Start therapy from your couch. CBT-based tools, live video sessions, and a therapist who gets it. Built for people with anxiety.",
        "audience": "people with social anxiety, general anxiety, or who feel overwhelmed by traditional therapy settings"
    },
    {
        "angle": "recovery_support",
        "name": "Online-Therapy.com",
        "hook": "Extra support alongside your recovery",
        "focus": "Sobriety is the start, not the finish. Get ongoing CBT-based therapy to work through what drove you there in the first place.",
        "audience": "people in recovery from addiction who need ongoing emotional support"
    },
    {
        "angle": "first_step",
        "name": "Online-Therapy.com",
        "hook": "Not ready for in-person? Start here.",
        "focus": "Your first therapy session from home. No commute, no small talk in a waiting room. Just you and a licensed therapist.",
        "audience": "people who have never tried therapy and feel nervous about starting"
    },
    {
        "angle": "cbt_tools",
        "name": "Online-Therapy.com",
        "hook": "CBT therapy that gives you real tools",
        "focus": "Not just talking. Worksheets, journal exercises, yoga, and live sessions. A complete toolkit for your mental health.",
        "audience": "people who want practical, evidence-based mental health tools, not just conversation"
    }
]

AFFILIATE_LINK = "https://go.online-therapy.com/SHY0"


def load_history():
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text())
        except:
            return []
    return []


def save_history(h, entry):
    h.append(entry)
    HISTORY_PATH.write_text(json.dumps(h[-60:], indent=2))


def pick_angle():
    history = load_history()
    recent_angles = [h.get("angle", "") for h in history[-4:]]
    available = [a for a in THERAPY_ANGLES if a["angle"] not in recent_angles]
    if not available:
        available = list(THERAPY_ANGLES)
    angle = random.choice(available)
    print(f"  Angle: {angle['angle']} -- {angle['hook']}")
    return angle


LIFESTYLE_PROMPTS = {"slide_1": ["Cinematic overhead shot of a cosy reading nook at night, warm amber lamp light, soft blankets, steaming mug. 9:16 vertical. No text, no people, no faces.","Warm golden hour light streaming through sheer curtains into a peaceful bedroom. Soft textures, muted tones. 9:16 vertical. No text, no people.","Close-up of warm candlelight on a wooden table, soft bokeh background, amber and honey tones. 9:16 vertical. No text, no watermarks.","Moody cosy evening scene: soft blanket, warm lamp, rain on window. Amber tones, intimate warmth. 9:16 vertical. No text, no people."],"slide_2": ["Warm morning light on rumpled white bed sheets, peaceful, minimal. Golden hour tones. 9:16 vertical. No text, no people.","Soft focus on a steaming cup of tea on a wooden surface, warm amber background light. 9:16 vertical. No text, no watermarks.","Rain drops on a window at night, warm interior light blurred behind. Intimate, reflective mood. 9:16 vertical. No text.","Close-up of hands wrapped around a warm mug, soft golden light, wooden table. 9:16 vertical. No faces, no text."],"slide_3": ["Warm flat lay of self-care items on a wooden surface: candle, journal, warm drink. Soft golden light from above. 9:16 vertical. No text.","Peaceful morning scene: open book on a sunlit table beside a window, warm tones. 9:16 vertical. No text, no people.","Soft golden light on a wooden shelf with plants, books, and a candle. Warm cosy aesthetic. 9:16 vertical. No text.","Morning sunlight casting warm shadows through blinds onto a peaceful desk. Minimal, warm. 9:16 vertical. No text."],"slide_4": ["Beautiful lifestyle flat lay on warm wood: journal, pen, coffee, soft morning light. Clean and aspirational. 9:16 vertical. No text.","Warm sunset light through a window onto a wooden table with a book and warm drink. Peaceful evening. 9:16 vertical. No text.","Close-up of soft fabrics and warm textures in golden amber light. Cosy, tactile, inviting. 9:16 vertical. No text.","Soft golden light on an open notebook beside a window, morning, peaceful. 9:16 vertical. No text, no people."],"slide_5": ["Warm inviting phone on a wooden table, soft amber candlelight, cosy evening setting. 9:16 vertical. No text, no watermarks.","Smartphone face-up on a warm wooden surface, soft golden morning light. Clean, minimal, inviting. 9:16 vertical. No text.","Phone on a cosy bedside table with warm lamp light, soft evening tones. 9:16 vertical. No text.","Clean minimal shot of a phone on a marble surface beside a warm drink, golden light. 9:16 vertical. No text."]}


def generate_slide_image(slide_key):
    prompts = LIFESTYLE_PROMPTS.get(slide_key, LIFESTYLE_PROMPTS["slide_3"])
    idx = (GITHUB_RUN_NUMBER + int(slide_key.split("_")[1]) - 1) % len(prompts)
    for attempt in range(3):
        pick = (idx + attempt) % len(prompts)
        prompt = prompts[pick]
        print(f"  [fal.ai] {slide_key} generating... (attempt {attempt + 1}/3)")
        try:
            ib = generate_fal_image(prompt)
            print(f"  [fal.ai] {slide_key} ready ({len(ib) // 1024:.0f} KB)")
            return ib
        except Exception as e:
            if "safety" in str(e).lower() or "moderation" in str(e).lower():
                print(f"  [fal.ai] {slide_key} BLOCKED, trying next...")
                continue
            raise
    raise RuntimeError(f"All image prompts for {slide_key} were blocked")


def get_font(size, bold=False):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w and current:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def draw_warm_gradient(draw, w, h):
    for y in range(h // 3):
        alpha = int(GRADIENT_TOP_ALPHA * (1 - y / (h / 3)))
        draw.rectangle([(0, y), (w, y + 1)], fill=(15, 10, 5, alpha))
    grad_start = int(h * 0.35)
    for y in range(grad_start, h):
        progress = (y - grad_start) / (h - grad_start)
        alpha = int(GRADIENT_BOTTOM_ALPHA * progress)
        draw.rectangle([(0, y), (w, y + 1)], fill=(15, 10, 5, alpha))


def draw_badge(draw, text, cx, y, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 24, 10
    rx = cx - tw // 2 - pad_x
    ry = y
    draw.rounded_rectangle([rx, ry, rx + tw + pad_x * 2, ry + th + pad_y * 2], radius=20, fill=BADGE_BG)
    draw.text((cx - tw // 2, ry + pad_y), text, fill=BADGE_TEXT, font=font)
    return th + pad_y * 2 + 20


def render_slide(bg_bytes, lines_data, slide_type="body", badge_text=None):
    bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA").resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
    overlay = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    draw_warm_gradient(od, IMAGE_WIDTH, IMAGE_HEIGHT)
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)
    cx = IMAGE_WIDTH // 2
    total_h = 0
    rendered_lines = []
    for text, size, color, bold in lines_data:
        font = get_font(size, bold)
        wrapped = wrap_text(text, font, MAX_TEXT_W, draw)
        line_h = draw.textbbox((0, 0), "Ay", font=font)[3]
        block_h = len(wrapped) * (line_h + LINE_GAP)
        rendered_lines.append((wrapped, font, color, line_h))
        total_h += block_h + SECTION_GAP
    y = int(IMAGE_HEIGHT * TEXT_CENTER_Y) - total_h // 2
    if badge_text:
        badge_font = get_font(BADGE_SIZE, bold=True)
        badge_h = draw_badge(draw, badge_text, cx, y, badge_font)
        y += badge_h
    for wrapped, font, color, line_h in rendered_lines:
        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            draw.text((cx - tw // 2 + 2, y + 2), line, fill=(0, 0, 0, 120), font=font)
            draw.text((cx - tw // 2, y), line, fill=color, font=font)
            y += line_h + LINE_GAP
        y += SECTION_GAP
    return bg.convert("RGB")


def _call_claude(prompt, client, max_tokens=2000):
    for a in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            r = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return r.content[0].text.strip()
        except Exception as e:
            if "overloaded" in str(e).lower() or "529" in str(e):
                wait = CLAUDE_RETRY_BASE * a + random.randint(0, 30)
                print(f"  Claude overloaded, waiting {wait}s (attempt {a}/{CLAUDE_MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Claude unavailable after all retries")


def generate_content(client, angle):
    prompt = f"""Write a 5-slide TikTok carousel promoting Online-Therapy.com as a personal recommendation.

Angle: {angle['hook']}
Focus: {angle['focus']}
Target audience: {angle['audience']}

RULES:
- Slide 1: Emotional hook that stops the scroll. Short, raw, personal. No product name yet.
- Slide 2: Name the pain point. Make the reader feel seen.
- Slide 3: Introduce Online-Therapy.com naturally. What it offers: licensed therapists, CBT-based, worksheets, live sessions, messaging.
- Slide 4: Why it works. Practical benefits: from home, affordable, no waiting room, cancel anytime.
- Slide 5: Warm CTA. Not salesy. "If you have been thinking about it, this is your sign."
- Each slide: 1 bold heading (5 words max), 2-3 lines of body text (15 words max each)
- Voice: First person, warm, like telling a friend. No clinical language.
- NEVER use em dashes. Use commas or periods instead.
- Do NOT start any slide with "I" or "You know"

Also write:
- tiktok_title: 1 emotional line under 80 chars (no hashtags)
- fb_title: 1-2 sentences, warm and personal (under 200 chars)

Return valid JSON:
{{"slides": [{{"heading": "...", "body": "..."}}, ...], "tiktok_title": "...", "fb_title": "..."}}
"""

    raw = _call_claude(prompt, client)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def post_to_platform(headers, platform_data, final_slides):
    """Post carousel to a single platform via Upload-Post."""
    photos = []
    for i, p in enumerate(final_slides):
        photos.append(("photos[]", (f"slide_{i+1}.jpg", open(p, "rb"), "image/jpeg")))
    try:
        r = requests.post(UPLOAD_POST_PHOTOS_URL, headers=headers, data=platform_data, files=photos, timeout=180)
        result = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
        return r.status_code, str(result)[:200]
    except Exception as e:
        return 0, str(e)


def main():
    print("=" * 60)
    print("MindCore AI  - Affiliate Product Carousel v1.5")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("\n1. Selecting angle...")
    angle = pick_angle()
    affiliate_link = AFFILIATE_LINK

    print("\n2. Generating content...")
    content = generate_content(client, angle)
    print(f"  TikTok title: {content['tiktok_title']}")

    print("\n3. Generating slide images...")
    slide_images = {}
    for i in range(1, SLIDE_COUNT + 1):
        key = f"slide_{i}"
        slide_images[key] = generate_slide_image(key)
        time.sleep(1)

    print("\n4. Rendering slides...")
    final_slides = []
    slides_data = content["slides"]

    for i, sd in enumerate(slides_data):
        key = f"slide_{i + 1}"
        bg = slide_images[key]

        if i == 0:
            lines = [(sd.get("hook", ""), HOOK_SIZE, HOOK_COLOR, True)]
            img = render_slide(bg, lines, badge_text="PERSONAL PICK")
        elif i == 1:
            lines = [(sd.get("story", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)
        elif i == 2:
            lines = [(sd.get("shift", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)
        elif i == 3:
            lines = [(sd.get("heading", ""), BOLD_SIZE, BOLD_COLOR, True)]
            img = render_slide(bg, lines)
        elif i == 4:
            cta_text = sd.get("cta", "Check the link below")
            lines = [
                (cta_text, CTA_TRIG, CTA_COLOR, True),
                ("MindCore AI", CTA_APP, ACCENT_COLOR, True),
            ]
            img = render_slide(bg, lines)

        path = OUTPUT_DIR / f"{key}.jpg"
        img.save(path, "JPEG", quality=92)
        final_slides.append(path)
        print(f"  {key} saved ({path})")

    print("\n5. Posting...")
    if not UPLOAD_POST_API_KEY:
        print("  SKIP: UPLOAD_POST_API_KEY not set")
    else:
        title = content["tiktok_title"][:TIKTOK_TITLE_LIMIT]
        headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}
        scheduled = get_scheduled_post_time()

        # Build descriptions
        tiktok_desc = content["description"].strip()
        if affiliate_link:
            tiktok_desc += f"\n\nGet it here: {affiliate_link}"
        if REQUIRED_BRAND_HASHTAG not in tiktok_desc:
            tiktok_desc += f" {REQUIRED_BRAND_HASHTAG}"
        if "#ad" not in tiktok_desc.lower():
            tiktok_desc += " #ad"
        tiktok_desc += f"\n\n{TIKTOK_HASHTAGS}"

        fb_desc = content["description"].strip()
        if affiliate_link:
            fb_desc += f"\n\nGet it here: {affiliate_link}"
        fb_desc += f"\n\n{FB_HASHTAGS}"
        if "#ad" not in fb_desc.lower():
            fb_desc += " #ad"

        us_desc = content["description"].strip()
        if affiliate_link:
            us_desc += f"\n\nGet it here: {affiliate_link}"
        if "#ad" not in us_desc.lower():
            us_desc += " #ad"
        us_desc += f"\n\n{US_HASHTAGS}"

        # ── 1. EU TikTok (14:00 Malta / 12:00 UTC) ──
        print("  [1/3] EU TikTok...")
        eu_tt_data = [
            ("user", "MindCoreAI"),
            ("platform[]", "tiktok"),
            ("tiktok_title", title),
            ("description", tiktok_desc[:TIKTOK_DESC_LIMIT]),
            ("post_mode", "DIRECT_POST"),
            ("auto_add_music", "true"),
            ("photo_cover_index", "0"),
            ("scheduled_date", scheduled),
        ]
        code, msg = post_to_platform(headers, eu_tt_data, final_slides)
        print(f"  EU TikTok: {code}  - {msg}")

        # ── 2. EU Facebook (14:00 Malta / 12:00 UTC) ──
        print("  [2/3] EU Facebook...")
        eu_fb_data = [
            ("user", "MindCoreAI"),
            ("platform[]", "facebook"),
            ("description", fb_desc[:TIKTOK_DESC_LIMIT]),
            ("post_mode", "DIRECT_POST"),
            ("photo_cover_index", "0"),
            ("scheduled_date", scheduled),
        ]
        code, msg = post_to_platform(headers, eu_fb_data, final_slides)
        print(f"  EU Facebook: {code}  - {msg}")

        # ── 3. US TikTok (16:00 Malta / 14:00 UTC) ──
        print("  [3/3] US TikTok...")
        now_utc = datetime.now(timezone.utc)
        us_target = now_utc.replace(hour=US_POST_HOUR_UTC, minute=0, second=0, microsecond=0)
        if now_utc >= us_target:
            us_target += timedelta(days=1)
        us_scheduled = us_target.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"  US Scheduled: {us_scheduled} ({US_POST_HOUR_UTC:02d}:00 UTC / 16:00 Malta)")

        us_tt_data = [
            ("user", "MindCoreAI_US"),
            ("platform[]", "tiktok"),
            ("tiktok_title", title),
            ("description", us_desc[:TIKTOK_DESC_LIMIT]),
            ("post_mode", "DIRECT_POST"),
            ("auto_add_music", "true"),
            ("photo_cover_index", "0"),
            ("scheduled_date", us_scheduled),
        ]
        code, msg = post_to_platform(headers, us_tt_data, final_slides)
        print(f"  US TikTok: {code}  - {msg}")

        print(f"  Affiliate link: {AFFILIATE_LINK}")

    print("\n6. Saving history...")
    history = load_history()
    save_history(history, {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "product_name": angle["name"], "angle": angle["angle"], "title": content["tiktok_title"], "affiliate_link": affiliate_link})

    print("\n" + "=" * 60)
    print("DONE  - Affiliate carousel posted!")
    print("=" * 60)


if __name__ == "__main__":
    main()
