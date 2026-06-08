#!/usr/bin/env python3
"""
MindCore AI -- Carousel Image Post Pipeline v2.7
=================================================
Hybrid: cinematic gpt-image-1 photography + 3-size text hierarchy.
Alternates MALE / FEMALE content daily.

v2.7: Full image variety pools -- 10 prompts per slide per gender.
      Hook slides are cinematic and scroll-stopping.
      Rotates daily using GITHUB_RUN_NUMBER so no two carousels look identical.
v2.6: POST_HOUR_UTC = 11 (1pm Malta)
v2.5: scheduled_date DIRECT_POST

Cost: ~$0.48/post (6 x gpt-image-1 high @ ~$0.08)
Cron: 02:00 UTC = 4am Malta
Post: 11:00 UTC = 1pm Malta (Upload-Post scheduled_date, exact)
"""

import base64
import io
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
import requests
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY      = os.environ["OPENAI_API_KEY"]
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload_photos"

OUTPUT_DIR   = Path("scripts/output_carousel")
PIPELINE_DIR = Path("scripts")
HISTORY_PATH = PIPELINE_DIR / "carousel_history.json"

REQUIRED_BRAND_HASHTAG = "#mindcoreai"
HASHTAGS = (
    "#mindcoreai #mentalhealth #fyp #foryou "
    "#mentalhealthawareness #anxiety #healing #selfcare"
)

IMAGE_WIDTH  = 1080
IMAGE_HEIGHT = 1920
TIKTOK_TITLE_LIMIT = 90
TIKTOK_DESC_LIMIT  = 4000
CLAUDE_MAX_RETRIES = 8
CLAUDE_RETRY_BASE  = 30

# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------
POST_HOUR_UTC = 11   # 1pm Malta (CEST = UTC+2)

def get_scheduled_post_time():
    now    = datetime.now(timezone.utc)
    target = now.replace(hour=POST_HOUR_UTC, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    scheduled = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"  Scheduled: {scheduled} ({POST_HOUR_UTC:02d}:00 UTC = {POST_HOUR_UTC+2:02d}:00 Malta)")
    return scheduled

# ---------------------------------------------------------------------------
# Text design
# ---------------------------------------------------------------------------
CMD_SIZE  = 50
HERO_SIZE = 88
BODY_SIZE = 42
BOLD_SIZE = 48
CTA_TRIG  = 60
CTA_APP   = 84
CTA_DL    = 50
CTA_URL   = 38

CMD_COLOR  = (200, 200, 200)
HERO_COLOR = (10,  10,  10)
BODY_COLOR = (255, 255, 255)
BOLD_COLOR = (255, 255, 255)
CTA_COLOR  = (255, 255, 255)
URL_COLOR  = (190, 190, 190)

BRUSH_PALETTE = [
    (168, 224, 99),
    (78,  205, 196),
    (255, 209, 102),
    (168, 224, 99),
    (78,  205, 196),
    (255, 209, 102),
]

TEXT_START_HOOK    = 0.55
TEXT_START_CONTENT = 0.50
TEXT_START_CTA     = 0.38
MAX_TEXT_W         = int(IMAGE_WIDTH * 0.87)
LINE_GAP           = 14
SECTION_GAP        = 38
GRADIENT_MAX_ALPHA = 155

# ---------------------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------------------
FEMALE_SEEDS = [
    "loving someone with anxiety",
    "supporting someone with depression",
    "loving someone in recovery from addiction",
    "what someone with burnout needs from you",
    "loving someone who carries everything alone",
    "what your anxious partner needs you to know",
    "supporting a partner with mental health struggles",
    "what loving someone with high-functioning anxiety looks like",
    "how to love someone who doesn't know how to ask for help",
    "what men in recovery need their partners to understand",
    "loving someone who can't switch their mind off",
    "what it means to love someone with depression",
    "how to support someone who overthinks everything",
    "what someone with trauma needs from the people they love",
    "loving someone who has never felt like enough",
]

MALE_SEEDS = [
    "what men carry alone in silence",
    "when a man goes quiet and disappears inside himself",
    "what burnout looks like in a man who never stops",
    "men who never learned it was okay to struggle",
    "when the strongest person in the room is drowning",
    "what depression looks like in men who still show up",
    "the weight men carry that nobody asks about",
    "when you are exhausted from being the strong one",
    "men in recovery from addiction who still carry shame",
    "what it feels like to carry everyone else and lose yourself",
    "men who built walls and now cannot find the door",
    "what loneliness feels like for men who seem fine",
    "when a man loses himself in survival mode",
    "men who were never given permission to not be okay",
    "what it means when a man stops talking about how he feels",
]

# ---------------------------------------------------------------------------
# IMAGE POOLS -- 10 per slide per gender, rotates daily
# Pool index: (GITHUB_RUN_NUMBER + slide_num - 1) % len(pool)
# ---------------------------------------------------------------------------

# Shared base strings
_C = "Cinematic portrait photography, 9:16 vertical format. Photorealistic, no text, no watermark, no logos. "
_F = "Caucasian Western European woman. "
_M = "Caucasian Western European man. "

IMAGE_POOLS_FEMALE = {

    # SLIDE 1 -- hook. Must be scroll-stopping. Dramatic, eye-catching, unexpected.
    "slide_1": [
        _C + "A " + _F + "floating peacefully on her back in warm golden-hour water, face serene, eyes closed, hair fanned around her head. Pink and lavender sunset reflections shimmering across the surface. Dreamy aspirational warmth.",
        _C + "A " + _F + "standing alone at the edge of a dramatic cliff, back to camera, looking out at a vast stormy ocean. Dark churning waves below, incredible dramatic sky above. Raw power and isolation.",
        _C + "Extreme close-up of a " + _F + "face in falling rain, eyes closed, head tilted slightly upward. Rain droplets catching light on skin, blurred city lights behind her. Vulnerable and raw.",
        _C + "A " + _F + "walking alone on an empty beach at dusk, from behind, small against vast ocean and dramatic orange-pink sky. Waves rushing in. Cinematic wide shot. Solitude.",
        _C + "A " + _F + "pressing her forehead against a rain-streaked window at night. Inside is dark. Outside: blurred city lights. Her breath slightly fogging the glass. Incredibly intimate.",
        _C + "A " + _F + "silhouette standing in a doorway flooded with warm golden light. Dark foreground, brilliant backlight. She pauses, threshold between two worlds. Dramatic contrast.",
        _C + "A " + _F + "lying in tall golden grass, looking up at a dramatic stormy sky with rays of light breaking through clouds. Golden hour. Dreamy and emotional.",
        _C + "Extreme close-up of a " + _F + "eyes -- one half in deep shadow, one lit by a single candle. No smile. Intense emotional depth. Shallow depth of field, blurred background.",
        _C + "A " + _F + "alone on a misty wooden pier at dawn, fog surrounding her on all sides, soft diffused grey light. Small and still against the vast quiet.",
        _C + "Dramatic wide shot: a " + _F + "standing completely still on an empty road, dark storm clouds building behind her, light breaking through above. Cinematic and epic.",
    ],

    # SLIDE 2 -- emotional weight, intimate, contemplative
    "slide_2": [
        _C + "A " + _F + "sitting alone near a rain-streaked window at dusk, warm soft interior ambient light, peaceful contemplative expression. Intimate quiet mood.",
        _C + "Extreme close-up of a " + _F + "hands gently pressed to her own chest. Soft warm side light. The gesture of self-holding. Tender and raw.",
        _C + "A " + _F + "sitting in a darkened room, face partially lit by blue phone light from below. The rest in shadow. Late at night. Alone.",
        _C + "Two " + _F + "hands -- one reaching slowly toward the other but not quite touching. Warm table, golden light. The gap between them holds the whole emotion.",
        _C + "A " + _F + "looking at her own reflection in a steamed bathroom mirror, face slightly obscured by steam. Dim warm light. Who is looking back?",
        _C + "A " + _F + "sitting on the floor, back against her bed, knees up, arms resting on knees, staring at something just off camera. Dim lamp. Heavy stillness.",
        _C + "Extreme close-up profile of a " + _F + "face, single candle light from one side. Eyes downcast, deep in thought. Sharp detail on eyelashes and skin.",
        _C + "A " + _F + "alone at a kitchen table late at night, both hands cupped around a mug, staring at nothing. City light from the window. Complete stillness.",
        _C + "A " + _F + "lying on her side in bed, not sleeping, eyes open, staring at nothing. Room in darkness except for faint light under a door. Awake at 3am.",
        _C + "Close-up of a " + _F + "hands in her lap, fingers interlaced loosely. Soft warm light from one side. The weight of waiting. Still.",
    ],

    # SLIDE 3 -- connection, presence, relationship
    "slide_3": [
        _C + "Two hands gently holding each other on a warm wooden table. Soft golden afternoon light. Tender quiet connection. No faces visible.",
        _C + "A " + _F + "hand reaching out slowly toward someone just off camera. Soft warm light. The act of reaching. Close-up.",
        _C + "Two Caucasian Western European people from behind, sitting together at a window, shoulders almost touching. Soft grey morning light.",
        _C + "Close-up of a long warm embrace -- just shoulders and arms, no faces. Deep amber light. The kind of hug that lasts.",
        _C + "A " + _F + "hands cupped around a warm steaming mug. Golden afternoon light. Simple, intimate, grounding.",
        _C + "Two Caucasian Western European people's intertwined hands on a wooden surface, one thumb gently over the other. Warm side light.",
        _C + "A Caucasian Western European couple from behind, sitting together on steps outside, close but not touching. Evening light. Comfortable silence.",
        _C + "A " + _F + "hand gently placed on another person's arm -- just the hands and arms visible. Warm light. Small gesture, enormous meaning.",
        _C + "Two Caucasian Western European people's feet, side by side on a wooden floor. Soft warm light from a low angle. Simple togetherness.",
        _C + "An empty chair beside a " + _F + "hand resting on an armrest. Warm side light. The presence felt through absence.",
    ],

    # SLIDE 4 -- transition, beginning to shift, slight warmth
    "slide_4": [
        _C + "A " + _F + "looking upward toward soft warm natural light streaming through a window. Face peaceful and quietly hopeful. Warm light touching skin gently.",
        _C + "A " + _F + "walking slowly toward a door with golden light streaming through the gap. From behind. Moving toward something.",
        _C + "A " + _F + "standing at a window, one hand on the glass, looking out at the first pale light of dawn. Interior still dark behind her.",
        _C + "Extreme close-up of a " + _F + "face with the very beginning of a quiet genuine expression -- not a smile yet, but something opening. Warm light from the side.",
        _C + "A " + _F + "sitting on the edge of a bed, dawn light slowly crossing the floor toward her feet. She watches it come. Hopeful stillness.",
        _C + "A " + _F + "reaching up to open curtains -- golden morning light beginning to pour through. Her face caught in the first warmth.",
        _C + "A " + _F + "turning to look over her shoulder back toward the camera. Behind her: warm golden light. She is between the dark and the light.",
        _C + "A beam of golden morning light falling across the floor of an otherwise empty room. Dust motes drifting. No person -- just the light arriving.",
        _C + "A " + _F + "sitting at a wooden table, hands flat on the surface, breathing. First morning light on her face. Beginning of a new day.",
        _C + "A " + _F + "standing still in a doorway, soft warm light from the room ahead. She is about to step through. Threshold moment.",
    ],

    # SLIDE 5 -- warm resolution, peace, safety
    "slide_5": [
        _C + "Soft golden sunrise light filtering through sheer white curtains into a peaceful bedroom. Warm amber tones, sense of safety and gentle hope.",
        _C + "A " + _F + "standing in a warm kitchen in early morning light, hands around a coffee cup, looking out the window calmly. Amber light fills the room.",
        _C + "A " + _F + "sitting in a garden in early morning sun, eyes closed, face tilted to the warmth. Golden light on skin. Complete peace.",
        _C + "Extreme close-up of a " + _F + "hands gently opening -- fingers uncurling and releasing. Soft warm amber light. The physical act of letting go.",
        _C + "A single warm candle on a wooden table in an otherwise dim room. The flame steady. Intimate, resolved, calm.",
        _C + "A " + _F + "lying on her back, arms relaxed at her sides, golden dawn light slowly crossing the ceiling above her. Peaceful and present.",
        _C + "Empty bedroom in golden morning light -- rumpled sheets, open window, sheer curtains moving. The sense of someone who finally rested.",
        _C + "A " + _F + "sitting beside a window with a book open in her lap, warm golden afternoon light. Not reading -- just resting. Safe.",
        _C + "Warm amber firelight on a " + _F + "face and hands as she sits quietly. Fireplace glow, evening, resolved.",
        _C + "Close-up of a " + _F + "face in full warm golden morning light. Eyes closed, a quiet exhale. The weight finally lifting.",
    ],

    # SLIDE 6 -- CTA, app, warm and inviting
    "slide_6": [
        _C + "A smartphone face-up on a warm wooden table, soft golden ambient glow, minimal and inviting. Candlelight warmth.",
        _C + "A " + _F + "hands gently holding a phone, warm amber light. Soft expression. The moment of reaching for help.",
        _C + "A phone on a marble surface beside a coffee cup, morning light, steam rising gently. Calm and clean.",
        _C + "A phone face-up on soft bedsheets, pale dawn light, minimal. An invitation to open it.",
        _C + "A phone on a dark wooden desk with a single lamp creating a warm pool of light. Evening, intimate.",
        _C + "A phone lying face-up on a windowsill, golden afternoon light streaming across it. Simple and warm.",
        _C + "Close-up of a " + _F + "finger about to touch the phone screen. Warm light. The moment of decision.",
        _C + "A phone on a wooden tray with a candle and a warm mug. Cosy, safe, inviting evening setup.",
        _C + "A phone screen glowing softly on a bedside table in a dark room. The only warm light. A presence.",
        _C + "A phone face-up on a garden table in golden afternoon light, surrounded by soft nature. Peaceful.",
    ],
}

IMAGE_POOLS_MALE = {

    # SLIDE 1 -- hook. Dramatic, cinematic, masculine, scroll-stopping.
    "slide_1": [
        _C + "A " + _M + "floating on his back in dark water at night, eyes open, looking up at a sky full of stars. Stars reflected in the water around him. Profound isolation and wonder.",
        _C + "A " + _M + "standing at the edge of a dramatic cliff, back to camera, looking out at a vast dark ocean. Waves far below, enormous stormy sky. Raw masculine isolation.",
        _C + "A " + _M + "walking alone on an empty highway stretching to the horizon at sunset. From behind. Small figure against a vast burning sky. Solitude.",
        _C + "Extreme close-up of a " + _M + "weathered hands, clasped tightly together. Knuckles prominent. Strong hands that carry things. Shallow depth of field, warm side light.",
        _C + "A " + _M + "sitting in a parked car at night, rain on the windscreen, streetlights blurred behind the glass. Hands on the wheel. Staring forward. Not going anywhere.",
        _C + "A " + _M + "silhouette standing on a rooftop against a dramatic city skyline at dusk. Orange and purple sky. Man alone above it all.",
        _C + "A " + _M + "standing completely still in heavy rain on an empty street, head slightly bowed. Not running. Not sheltering. Just standing in it.",
        _C + "Extreme close-up of a " + _M + "face, one half deep in shadow, one half lit by a single hard side light. Strong jaw, tired eyes. Cinematic and raw.",
        _C + "A " + _M + "alone on an empty park bench in thick morning fog. The city barely visible behind him. He sits perfectly still. The fog holds everything.",
        _C + "Dramatic wide shot: a " + _M + "standing in the middle of an empty industrial space or warehouse, a single shaft of light from above falling on him. Everything else in darkness.",
    ],

    # SLIDE 2 -- emotional weight, alone, carrying it
    "slide_2": [
        _C + "A " + _M + "sitting alone at a rain-streaked window at night, warm interior ambient light, head slightly bowed, hands clasped. Dark moody weight.",
        _C + "Close-up of a " + _M + "hands gripping the steering wheel of a parked car at night. Knuckles white. Rain on the windscreen. Not driving. Just holding.",
        _C + "A " + _M + "sitting at a kitchen table at 2am, both hands around a mug, staring at nothing. City light from the window. Total stillness.",
        _C + "A " + _M + "leaning against a brick wall outside at night, arms crossed, head back slightly, looking up. Street light from one side. Alone in the city.",
        _C + "Extreme close-up of a " + _M + "eyes -- tired, slightly red-rimmed, unfocused, staring at something that isn't there. Hard side light. Emotionally exhausted.",
        _C + "A " + _M + "sitting on the floor in a dark room, back against the wall, knees up, arms resting on knees. Staring forward at nothing. The floor as the only option.",
        _C + "A " + _M + "at a work desk late at night, slumped slightly, screen off, head dropped forward. Single desk lamp. The end of something.",
        _C + "A " + _M + "standing at a bathroom sink, both hands gripping the basin edge, looking down at the drain. Dim light. Weight in his shoulders.",
        _C + "A " + _M + "lying fully clothed on his bed at night, staring at the ceiling. Arms at sides. Not sleeping. Just there. Room in darkness.",
        _C + "A " + _M + "sitting on a staircase in low light, elbows on knees, head bowed forward, looking at the step below. Shadows across his face.",
    ],

    # SLIDE 3 -- connection, support, brotherhood
    "slide_3": [
        _C + "Two hands gently resting together on a warm wooden table. Golden afternoon light. Quiet connection. No faces needed.",
        _C + "A " + _M + "hand reaching out toward someone just off camera. Warm light. The act of reaching. Close-up.",
        _C + "Two Caucasian Western European men from behind, one with his hand on the other's shoulder. Evening light. Standing together.",
        _C + "Close-up of a firm handshake becoming a longer hold -- fingers clasping. Warm amber light. The moment it becomes real support.",
        _C + "A " + _M + "hands cupped around a warm steaming mug. Golden light. Simple, grounding, present.",
        _C + "Two Caucasian Western European men sitting side by side on concrete steps outside, shoulders touching, looking forward. Evening light. No words needed.",
        _C + "Close-up of a strong warm embrace -- just shoulders and arms, no faces. Dark warm light. The kind of hug men rarely allow themselves.",
        _C + "A " + _M + "hand firmly placed on another man's shoulder from behind. Warm side light. A single gesture that says everything.",
        _C + "Two pairs of Caucasian Western European men's shoes on a wooden floor side by side. Warm light from a low angle. Simple presence.",
        _C + "An empty chair beside a " + _M + "hand resting on an armrest. The presence of someone who stayed. Warm light.",
    ],

    # SLIDE 4 -- beginning to shift, quiet resolve forming
    "slide_4": [
        _C + "A " + _M + "looking upward toward soft warm natural light through a window. Face calm and quietly resolving. Golden light on strong features.",
        _C + "A " + _M + "walking slowly toward a door with warm golden light streaming through. From behind. Moving toward something.",
        _C + "A " + _M + "standing at a window, one hand on the glass, watching the first pale dawn light arrive. Interior still dark. He waited for this.",
        _C + "Extreme close-up of a " + _M + "face, the very beginning of something settling -- not a smile, but a jaw unclenching. Warm side light.",
        _C + "A " + _M + "sitting on the edge of his bed, dawn light slowly crossing the floor toward him. He watches it come. A shift.",
        _C + "A " + _M + "reaching to open a window -- first morning air coming in, curtains beginning to move. His face in the first warmth.",
        _C + "A " + _M + "turning to look over his shoulder back toward the camera. Behind him: warm golden light. In front: where he came from.",
        _C + "A beam of golden morning light falling across the floor of an otherwise empty room. Dust motes drifting in the light. Something arriving.",
        _C + "A " + _M + "sitting at a wooden table, both hands flat on the surface. First morning light on his face. Breathing. Beginning.",
        _C + "An empty road stretching forward into dramatic golden light at the far end. Dark on the sides, light dead ahead. Direction found.",
    ],

    # SLIDE 5 -- warm resolution, earned peace
    "slide_5": [
        _C + "A " + _M + "standing in a warm kitchen in early morning light, hands around a coffee mug, looking out the window calmly. Amber light fills the room.",
        _C + "A " + _M + "sitting in a garden in early morning sun, eyes closed, face tilted to the warmth. Golden light. Complete peace. Earned.",
        _C + "Extreme close-up of a " + _M + "hands gently opening -- fingers uncurling, releasing. Warm amber light. The physical act of letting go.",
        _C + "A " + _M + "lying on his back in bed, arms relaxed, golden dawn light slowly crossing the ceiling above him. Awake but at rest.",
        _C + "A " + _M + "sitting in a leather armchair beside a fireplace, warm amber firelight. Evening. Quiet. He made it through the day.",
        _C + "Empty room with warm golden morning light crossing the floor. Work boots by the door. A man who went out and came back.",
        _C + "A " + _M + "sitting on a wooden porch step in early morning sun, coffee in both hands, looking out at something calm.",
        _C + "Close-up of a " + _M + "face in full warm golden morning light. Eyes closed. A single quiet exhale. The weight finally lighter.",
        _C + "A " + _M + "and another person from behind, side by side, watching a peaceful sunrise. Shoulders almost touching. They made it.",
        _C + "A " + _M + "standing at a window in full warm morning light, one hand on the frame. Looking out. Resolved. Present.",
    ],

    # SLIDE 6 -- CTA, warm and inviting
    "slide_6": [
        _C + "A smartphone face-up on a warm wooden table, soft golden ambient glow. Candlelight warmth. Minimal and inviting.",
        _C + "A " + _M + "hands holding a phone, warm amber light from the side. The moment of reaching for something that helps.",
        _C + "A phone on a dark leather surface beside a coffee cup, morning light. Masculine, clean, calm.",
        _C + "A phone face-up on a wooden desk, single lamp creating a warm pool of light around it. Evening. Intimate.",
        _C + "A phone on a wooden tray with a warm mug, firelight nearby. Evening. Grounded. Safe to open it.",
        _C + "A phone lying face-up on a windowsill, golden afternoon light across it. Simple. An invitation.",
        _C + "Close-up of a " + _M + "finger about to touch the phone screen. Warm light. The moment of choosing to reach out.",
        _C + "A phone screen glowing softly on a bedside table in a dark room. The only warm light. A presence when it's quiet.",
        _C + "A phone face-up on a garden table in golden late afternoon light. Peaceful. Ready.",
        _C + "A phone on a wooden surface with keys and a watch beside it. End of day. The choice to open it.",
    ],
}


def get_image_prompt(slide_key: str, gender: str, topic: str = "") -> str:
    """Select an image prompt from the rotating pool.
    Uses (GITHUB_RUN_NUMBER + slide_num - 1) % pool_size so each run
    gets a different set and slides within a run are all different.
    """
    pools = IMAGE_POOLS_MALE if gender == "male" else IMAGE_POOLS_FEMALE
    pool  = pools.get(slide_key, pools["slide_5"])
    slide_num = int(slide_key.split("_")[1])
    idx   = (GITHUB_RUN_NUMBER + slide_num - 1) % len(pool)
    prompt = pool[idx]
    if slide_key == "slide_1" and topic:
        prompt = f"{prompt} Emotional theme: {topic}."
    return prompt


# ---------------------------------------------------------------------------
# Gender
# ---------------------------------------------------------------------------
def get_gender_mode():
    return "male" if datetime.now(timezone.utc).day % 2 == 1 else "female"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_history():
    if HISTORY_PATH.exists():
        try: return json.loads(HISTORY_PATH.read_text())
        except: return []
    return []

def save_history(history, new_entry):
    history.append(new_entry)
    HISTORY_PATH.write_text(json.dumps(history[-30:], indent=2))
    print(f"  History: {len(history)} carousel posts")

def _call_claude(prompt, client, max_tokens=2000):
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = CLAUDE_RETRY_BASE * attempt
                print(f"  Overloaded -- waiting {wait}s..."); time.sleep(wait)
            else: raise
        except json.JSONDecodeError:
            if attempt == CLAUDE_MAX_RETRIES: raise
            time.sleep(10)
    raise RuntimeError("Claude failed after all retries")

def get_font(size, bold=True):
    bold_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    ]
    reg_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    paths = bold_paths if bold else reg_paths
    for path in paths:
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except: pass
    for path in (reg_paths if bold else bold_paths):
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except: pass
    return ImageFont.load_default()

def line_height(font):
    try: bb = font.getbbox("Ag"); return bb[3] - bb[1]
    except: return getattr(font, "size", 40)

def wrap_text(text, font, max_w):
    words = text.split(); lines = []; cur = []
    for word in words:
        test = " ".join(cur + [word])
        try: w = font.getbbox(test)[2] - font.getbbox(test)[0]
        except: w = len(test) * 30
        if w <= max_w: cur.append(word)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [word]
    if cur: lines.append(" ".join(cur))
    return lines or [""]

def draw_text_with_stroke(draw, cx, y, text, font, color, stroke_color=(0,0,0), stroke_w=3):
    for dx in range(-stroke_w, stroke_w+1):
        for dy in range(-stroke_w, stroke_w+1):
            if dx or dy:
                draw.text((cx+dx, y+dy), text, font=font, fill=stroke_color, anchor="mt")
    draw.text((cx, y), text, font=font, fill=color, anchor="mt")

def draw_text_block(draw, cx, y, lines, font, color, stroke_w=3):
    lh = line_height(font)
    for line in lines:
        draw_text_with_stroke(draw, cx, y, line, font, color, stroke_w=stroke_w)
        y += lh + LINE_GAP
    return y

def draw_brush_stroke(draw, cx, y_top, text, font, brush_color):
    try:
        bb = font.getbbox(text); tw = bb[2]-bb[0]; th = bb[3]-bb[1]
    except:
        tw = len(text) * getattr(font,"size",40) * 0.55; th = getattr(font,"size",40)
    pad_x, pad_y, skew = 26, 10, 8
    x1 = cx-tw//2-pad_x; x2 = cx+tw//2+pad_x; y1 = y_top-pad_y; y2 = y_top+th+pad_y
    draw.polygon([(x1+skew,y1-3),(x2+skew,y1+4),(x2-skew,y2+4),(x1-skew,y2-3)], fill=brush_color)

def add_gradient_overlay(img, text_start_y):
    overlay = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    zone_h = IMAGE_HEIGHT - text_start_y
    for y in range(text_start_y, IMAGE_HEIGHT):
        progress = (y - text_start_y) / zone_h
        alpha = int(GRADIENT_MAX_ALPHA * min(progress * 1.6, 1.0))
        draw.line([(0,y),(IMAGE_WIDTH,y)], fill=(0,0,0,alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

# ---------------------------------------------------------------------------
# Step 1: Script
# ---------------------------------------------------------------------------
def generate_carousel_script(client, history, gender):
    used  = [e.get("topic","") for e in history]
    seeds = MALE_SEEDS if gender == "male" else FEMALE_SEEDS
    seed  = random.choice(seeds)
    avoid = ", ".join(used[-10:]) if used else "none"

    if gender == "male":
        audience_instruction = (
            "Write a 5-content-slide carousel that speaks DIRECTLY TO a man who is struggling.\n"
            "Address him as 'you'. Validate his experience without preaching.\n"
            "Tone: direct, honest, no softening. Like a friend who has been there.\n"
            "Example voice: 'You're not falling apart. You've been holding everything together for too long.'"
        )
    else:
        audience_instruction = (
            "Write a 5-content-slide carousel in the PARTNER-DIRECTED style.\n"
            "Speak TO the person who loves someone with a mental health struggle.\n"
            "Tone: warm, empathetic, validating. Like advice from a wise friend.\n"
            "Example voice: 'Loving someone with anxiety means staying when you don't understand why.'"
        )

    prompt = f"""You are a TikTok carousel copywriter for a mental wellness brand.

{audience_instruction}

Each slide has THREE text layers over a cinematic image:
  1. COMMAND (small gray label, 2-5 words): sets context
  2. HERO (large bold, 2-4 words): KEY IDEA on neon highlight
  3. BODY (1-2 sentences, 18 words max): explains
  4. BOLD (1 sentence, 7 words max): quotable punchline

SEED TOPIC: "{seed}"
AVOID: {avoid}

WORD LIMITS:
  s1: command 4-7w, hero 2-4w ending "..." -- NO body/bold on slide 1
  s2-s5: command 2-4w, hero 2-4w, body 18w max, bold 7w max
  s4_bold = THE most screenshot-worthy line in the carousel
  cta_trigger = "Comment [WORD] if [emotional statement] 👇" (WORD: SAVED/SAME/THIS/YES/REAL)

Return ONLY valid JSON:
{{
  "topic": "...", "tiktok_title": "...(max 80 chars)...",
  "s1_command": "...", "s1_hero": "...(ends with ...)...",
  "s2_command": "...", "s2_hero": "...", "s2_body": "...", "s2_bold": "...",
  "s3_command": "...", "s3_hero": "...", "s3_body": "...", "s3_bold": "...",
  "s4_command": "...", "s4_hero": "...", "s4_body": "...", "s4_bold": "...",
  "s5_command": "...", "s5_hero": "...", "s5_body": "...", "s5_bold": "...",
  "cta_trigger": "...",
  "full_prose_caption": "200-280 word prose, no bullets, ends: Save this for the moments when you need a reminder.",
  "hashtag_topic": "..."
}}"""

    result = _call_claude(prompt, client, max_tokens=2000)
    for key in ["s1_hero","s2_hero","s3_hero","s4_hero","s5_hero"]:
        w = result.get(key,"").split()
        if len(w) > 5: result[key] = " ".join(w[:4])
    for key in ["s2_bold","s3_bold","s4_bold","s5_bold"]:
        w = result.get(key,"").split()
        if len(w) > 8:
            result[key] = " ".join(w[:7])
            if result[key][-1] not in ".!?": result[key] += "."
    for key in ["s2_body","s3_body","s4_body","s5_body"]:
        w = result.get(key,"").split()
        if len(w) > 20:
            result[key] = " ".join(w[:18])
            if result[key][-1] not in ".!?": result[key] += "."
    print(f"  Topic: {result.get('topic')}")
    for i in range(1,6):
        body = result.get(f"s{i}_body","")
        print(f"  Slide {i}: [{result.get(f's{i}_command','')}] | [{result.get(f's{i}_hero','')}] | {body[:40] if body else '—'}")
    return result

# ---------------------------------------------------------------------------
# Step 2: Image
# ---------------------------------------------------------------------------
def generate_slide_image(openai_client, slide_key, topic, gender):
    prompt = get_image_prompt(slide_key, gender, topic)
    pool_size = len(IMAGE_POOLS_MALE[slide_key] if gender == "male" else IMAGE_POOLS_FEMALE[slide_key])
    slide_num = int(slide_key.split("_")[1])
    idx = (GITHUB_RUN_NUMBER + slide_num - 1) % pool_size
    print(f"  [gpt-image-1 HIGH] {slide_key} generating... (pool idx {idx}/{pool_size-1})")
    response = openai_client.images.generate(
        model="gpt-image-1", prompt=prompt, size="1024x1536", quality="high", n=1,
    )
    data = response.data[0]
    img_bytes = requests.get(data.url, timeout=60).content if getattr(data,"url",None) else base64.b64decode(data.b64_json)
    print(f"  [gpt-image-1 HIGH] {slide_key} ready ({len(img_bytes)//1024:.0f} KB)")
    return img_bytes

# ---------------------------------------------------------------------------
# Step 3: Resize
# ---------------------------------------------------------------------------
def resize_to_tiktok(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    scale = max(IMAGE_WIDTH/img.width, IMAGE_HEIGHT/img.height)
    new_w, new_h = int(img.width*scale), int(img.height*scale)
    img = img.resize((new_w,new_h), Image.LANCZOS)
    left = (new_w-IMAGE_WIDTH)//2; top = (new_h-IMAGE_HEIGHT)//2
    return img.crop((left,top,left+IMAGE_WIDTH,top+IMAGE_HEIGHT))

# ---------------------------------------------------------------------------
# Step 4: Render
# ---------------------------------------------------------------------------
def render_hook_slide(img, script, brush_color):
    text_start = int(IMAGE_HEIGHT * TEXT_START_HOOK)
    img = add_gradient_overlay(img, text_start)
    draw = ImageDraw.Draw(img); cx = IMAGE_WIDTH//2; y = text_start+30
    cmd_font = get_font(CMD_SIZE, bold=False)
    y = draw_text_block(draw, cx, y, wrap_text(script["s1_command"], cmd_font, MAX_TEXT_W), cmd_font, CMD_COLOR, stroke_w=2)
    y += int(SECTION_GAP*0.7)
    hero_font = get_font(HERO_SIZE, bold=True); lh = line_height(hero_font)
    for line in wrap_text(script["s1_hero"], hero_font, MAX_TEXT_W):
        draw_brush_stroke(draw, cx, y, line, hero_font, brush_color)
        draw.text((cx,y), line, font=hero_font, fill=HERO_COLOR, anchor="mt")
        y += lh+LINE_GAP
    return img

def render_content_slide(img, script, slide_num, brush_color):
    n = str(slide_num)
    text_start = int(IMAGE_HEIGHT * TEXT_START_CONTENT)
    img = add_gradient_overlay(img, text_start)
    draw = ImageDraw.Draw(img); cx = IMAGE_WIDTH//2; y = text_start+25
    cmd_font = get_font(CMD_SIZE, bold=False)
    y = draw_text_block(draw, cx, y, wrap_text(script[f"s{n}_command"], cmd_font, MAX_TEXT_W), cmd_font, CMD_COLOR, stroke_w=2)
    y += int(SECTION_GAP*0.5)
    hero_font = get_font(HERO_SIZE, bold=True); lh = line_height(hero_font)
    for line in wrap_text(script[f"s{n}_hero"], hero_font, MAX_TEXT_W):
        draw_brush_stroke(draw, cx, y, line, hero_font, brush_color)
        draw.text((cx,y), line, font=hero_font, fill=HERO_COLOR, anchor="mt")
        y += lh+LINE_GAP
    y += SECTION_GAP
    body_text = script.get(f"s{n}_body","")
    if body_text:
        body_font = get_font(BODY_SIZE, bold=False)
        y = draw_text_block(draw, cx, y, wrap_text(body_text, body_font, MAX_TEXT_W), body_font, BODY_COLOR, stroke_w=3)
        y += int(LINE_GAP*0.5)
    bold_text = script.get(f"s{n}_bold","")
    if bold_text:
        bold_font = get_font(BOLD_SIZE, bold=True)
        draw_text_block(draw, cx, y, wrap_text(bold_text, bold_font, MAX_TEXT_W), bold_font, BOLD_COLOR, stroke_w=4)
    return img

def render_cta_slide(img, script, brush_color):
    text_start = int(IMAGE_HEIGHT * TEXT_START_CTA)
    img = add_gradient_overlay(img, max(text_start-120, 0))
    draw = ImageDraw.Draw(img); cx = IMAGE_WIDTH//2; y = text_start
    trig_font = get_font(CTA_TRIG, bold=True)
    y = draw_text_block(draw, cx, y, wrap_text(script.get("cta_trigger","Comment SAVED if you needed this 👇"), trig_font, MAX_TEXT_W), trig_font, CTA_COLOR, stroke_w=3)
    y += SECTION_GAP
    app_font = get_font(CTA_APP, bold=True); lh_app = line_height(app_font)
    draw_brush_stroke(draw, cx, y, "MindCore AI", app_font, brush_color)
    draw.text((cx,y), "MindCore AI", font=app_font, fill=HERO_COLOR, anchor="mt")
    y += lh_app+SECTION_GAP
    dl_font = get_font(CTA_DL, bold=False)
    y = draw_text_block(draw, cx, y, wrap_text("Download for free", dl_font, MAX_TEXT_W), dl_font, CTA_COLOR, stroke_w=2)
    gp_font = get_font(CTA_DL, bold=True)
    y = draw_text_block(draw, cx, y, wrap_text("on Google Play", gp_font, MAX_TEXT_W), gp_font, CTA_COLOR, stroke_w=3)
    y += int(LINE_GAP*1.5)
    url_font = get_font(CTA_URL, bold=False)
    draw_text_with_stroke(draw, cx, y, "mindcoreai.eu/app", url_font, URL_COLOR, stroke_w=2)
    return img

# ---------------------------------------------------------------------------
# Step 5: Caption
# ---------------------------------------------------------------------------
def build_tiktok_content(script):
    title = script.get("tiktok_title","")[:TIKTOK_TITLE_LIMIT]
    prose = script.get("full_prose_caption","")
    tag   = f"#{script.get('hashtag_topic','mentalwellness')}"
    desc  = f"{prose}\n\n{tag} {HASHTAGS}"
    if REQUIRED_BRAND_HASHTAG.lower() not in desc.lower(): desc += f" {REQUIRED_BRAND_HASHTAG}"
    return title, desc[:TIKTOK_DESC_LIMIT]

# ---------------------------------------------------------------------------
# Step 6: Upload with scheduled_date
# ---------------------------------------------------------------------------
def upload_carousel(image_paths, tiktok_title, description, cfg, scheduled_date):
    if not UPLOAD_POST_API_KEY: return {"skipped": True, "reason": "no API key"}
    user = cfg.get("upload_post_user","")
    if not user: return {"skipped": True, "reason": "no user configured"}
    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}
    data = [
        ("user",              user),
        ("platform[]",        "tiktok"),
        ("platform[]",        "facebook"),
        ("tiktok_title",      tiktok_title),
        ("description",       description),
        ("post_mode",         "DIRECT_POST"),
        ("auto_add_music",    "true"),
        ("photo_cover_index", "0"),
        ("scheduled_date",    scheduled_date),
    ]
    files = []
    try:
        for i, path in enumerate(image_paths):
            f = open(path,"rb")
            files.append(("photos[]",(f"slide_{i+1}.jpg",f,"image/jpeg")))
        resp = requests.post(UPLOAD_POST_PHOTOS_URL, headers=headers, files=files, data=data, timeout=180)
        result = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"raw":resp.text}
        result["status_code"] = resp.status_code
        result["scheduled_date"] = scheduled_date
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:400]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}"); return {"error":str(e)}
    finally:
        for _,(_, f,_) in files:
            try: f.close()
            except: pass

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client        = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    cfg = {}
    cfg_path = Path("video_pipeline/heygen_config.json")
    if cfg_path.exists():
        with open(cfg_path) as f: cfg = json.load(f)
    upload_enabled = cfg.get("upload_enabled", False) and bool(UPLOAD_POST_API_KEY)

    gender         = get_gender_mode()
    history        = load_history()
    scheduled_date = get_scheduled_post_time()

    print(f"\n  MindCore AI -- Carousel Image Post Pipeline v2.7")
    print(f"  Run #{GITHUB_RUN_NUMBER} | 6 slides | Gender: {gender.upper()} | ~$0.48")
    print(f"  Image pools: 10 prompts per slide -- no two carousels look the same")
    print(f"  Generates: 4am Malta | Posts: {POST_HOUR_UTC:02d}:00 UTC = {POST_HOUR_UTC+2:02d}:00 Malta")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    print("=" * 60)

    print(f"\n  Generating {gender} script...")
    script = generate_carousel_script(client, history, gender)
    (OUTPUT_DIR / "carousel_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    slide_keys = ["slide_1","slide_2","slide_3","slide_4","slide_5","slide_6"]
    image_paths = []
    for idx, slide_key in enumerate(slide_keys):
        print(f"\n  -- {slide_key.upper()} --")
        brush_color = BRUSH_PALETTE[idx]
        img_bytes = generate_slide_image(openai_client, slide_key, script.get("topic",""), gender)
        img = resize_to_tiktok(img_bytes)
        if slide_key == "slide_1":    img = render_hook_slide(img, script, brush_color)
        elif slide_key == "slide_6": img = render_cta_slide(img, script, brush_color)
        else: img = render_content_slide(img, script, int(slide_key[-1]), brush_color)
        out_path = str(OUTPUT_DIR / f"{slide_key}.jpg")
        img.save(out_path, format="JPEG", quality=94)
        image_paths.append(out_path)
        print(f"  Saved: {Path(out_path).stat().st_size//1024:.0f} KB")
        time.sleep(0.5)

    tiktok_title, description = build_tiktok_content(script)
    (OUTPUT_DIR / "carousel_caption.txt").write_text(
        f"GENDER: {gender.upper()}\nSCHEDULED: {scheduled_date}\n"
        f"TITLE ({len(tiktok_title)} chars):\n{tiktok_title}\n\n"
        f"DESCRIPTION ({len(description)} chars):\n{description}", encoding="utf-8"
    )
    print(f"\n  Title: {tiktok_title}")
    print(f"  Scheduled for: {scheduled_date}")

    if upload_enabled:
        print(f"\n  Uploading {gender} carousel -- scheduled for {scheduled_date}...")
        result = upload_carousel(image_paths, tiktok_title, description, cfg, scheduled_date)
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps(result, indent=2))
        if result.get("status_code") == 200:
            print(f"  Scheduled OK -- fires at {scheduled_date} (TikTok + Facebook)")
    else:
        print("\n  Upload DISABLED")
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps({"skipped":True}))

    save_history(history, {
        "date":           datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topic":          script.get("topic",""),
        "gender":         gender,
        "headline":       f"{script.get('s1_command')} / {script.get('s1_hero')}",
        "scheduled_date": scheduled_date,
        "run":            GITHUB_RUN_NUMBER,
    })
    print(f"\n  DONE | {gender.upper()} | {script.get('topic')} | fires at {scheduled_date}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import sys
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
