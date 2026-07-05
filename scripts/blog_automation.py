import os
import json
import base64
import re
import time
import requests
from anthropic import Anthropic
from scripts.fal_image import generate_fal_image
from datetime import datetime

# SERP research (graceful fallback if module unavailable)
try:
    from scripts.serp_research import research_topics, pick_best_topic
    SERP_AVAILABLE = True
except ImportError:
    try:
        from serp_research import research_topics, pick_best_topic
        SERP_AVAILABLE = True
    except ImportError:
        SERP_AVAILABLE = False

# -- Clients ------------------------------------------------------------------
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

import time as _time
import random as _random

def _call_anthropic_with_retry(client, max_retries=5, **kwargs):
    """Wrapper for Anthropic API calls with retry on 529 overloaded errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return client.messages.create(**kwargs)
        except Exception as e:
            if "529" in str(e) or "overloaded" in str(e).lower():
                wait = 30 * attempt + _random.randint(0, 30)
                print(f"   Anthropic overloaded (attempt {attempt}/{max_retries}), waiting {wait}s...")
                _time.sleep(wait)
                if attempt == max_retries:
                    raise
            else:
                raise

# Image generation: fal.ai Flux Pro (baked in, no OpenAI needed)
SERP_API_KEY     = os.environ.get("SERP_API_KEY", "")

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

HISTORY_FILE   = "scripts/blog_history.json"
LIBRARY_FILE   = "scripts/keyword_library.json"
MIN_WORD_COUNT = 1200

AUDIENCE_ROTATION = ["men", "women", "neutral"]

CATEGORY_IDS = {
    "Anxiety & Stress":       6,
    "Recovery & Sobriety":    7,
    "AI & Wellness":          4,
    "Men's Mental Health":    None,
    "Women's Mental Health":  None,
    "Sleep & Burnout":        None,
    "Relationships & Family": None,
}
CATEGORIES = list(CATEGORY_IDS.keys())

LIBRARY_CATEGORY_MAP = {
    "mental health app":                "AI & Wellness",
    "mental wellness apps":             "AI & Wellness",
    "women's mental health":            "Women's Mental Health",
    "women and mental health":          "Women's Mental Health",
    "sobriety app":                     "Recovery & Sobriety",
    "sober app":                        "Recovery & Sobriety",
    "mood tracking app":                "AI & Wellness",
    "sober time app":                   "Recovery & Sobriety",
    "ai companion app":                 "AI & Wellness",
    "ai chat companion":                "AI & Wellness",
    "postpartum depression support":    "Women's Mental Health",
    "sobriety tracker":                 "Recovery & Sobriety",
    "sober tracker":                    "Recovery & Sobriety",
    "days sober app":                   "Recovery & Sobriety",
    "sober counter":                    "Recovery & Sobriety",
    "sobriety counter":                 "Recovery & Sobriety",
    "best mood tracker app":            "AI & Wellness",
    "self improvement app":             "AI & Wellness",
    "personal growth apps":             "AI & Wellness",
    "wellbeing apps":                   "AI & Wellness",
    "mood diary app":                   "AI & Wellness",
    "sober buddy app":                  "Recovery & Sobriety",
    "stay sober app":                   "Recovery & Sobriety",
    "loneliness app":                   "AI & Wellness",
    "anxiety relief app":               "Anxiety & Stress",
    "emotional support app":            "AI & Wellness",
    "self improving apps":              "AI & Wellness",
    "mood journal app":                 "AI & Wellness",
    "sobriety tracking app":            "Recovery & Sobriety",
    "stress anxiety companion app":     "Anxiety & Stress",
    "body scan meditation for sleep":   "Sleep & Burnout",
    "bedtime meditation for sleep":     "Sleep & Burnout",
    "guided relaxation meditation":     "Sleep & Burnout",
    "meditation to fall asleep":        "Sleep & Burnout",
    "short meditation for anxiety":     "Anxiety & Stress",
    "meditation to calm the mind":      "Anxiety & Stress",
    "guided meditation for beginners":  "AI & Wellness",
}

INTERNAL_LINKS = [
    ("MindCore AI features", "https://mindcoreai.eu/features/"),
    ("our story",            "https://mindcoreai.eu/about-us/"),
    ("MindCore AI blog",     "https://mindcoreai.eu/blog/"),
]

EXTERNAL_LINKS = [
    ("Mind",                      "https://www.mind.org.uk"),
    ("Mental Health Foundation",  "https://www.mentalhealth.org.uk"),
    ("NHS mental health support", "https://www.nhs.uk/mental-health/"),
    ("NAMI",                      "https://www.nami.org"),
    ("SAMHSA",                    "https://www.samhsa.gov"),
]

# Inline app link
APP_INLINE_LINK = (
    '<a href="https://play.google.com/store/apps/details?id=com.mindcoreai.app" '
    'target="_blank" rel="noopener noreferrer"><strong>MindCore AI</strong></a>'
)

# CTA button
GP_CTA_LINK = (
    '<a href="https://play.google.com/store/apps/details?id=com.mindcoreai.app" '
    'target="_blank" rel="noopener noreferrer" '
    'style="font-weight:700;color:#07071a;background-color:#3ecfb2;'
    'padding:0.5rem 1.2rem;border-radius:8px;text-decoration:none;'
    'display:inline-block;margin-top:0.5rem;">'
    '<strong>Download MindCore AI on Google Play</strong>'
    '</a>'
)

AUDIENCE_PROFILES = {
    "men": {
        "label": "Men's Mental Health",
        "description": (
            "Men 35+ who are massively underserved in mental health. They suffer in silence, "
            "rarely seek help, and respond to honest, shame-free, practical content. "
            "TOPIC POOL:\n"
            "  - Emotional suppression and how to open up\n"
            "  - Male depression and suicide risk\n"
            "  - The male loneliness epidemic\n"
            "  - Addiction and recovery: alcohol, cocaine, gambling, porn\n"
            "  - Men and anxiety (physical symptoms men don't recognise)\n"
            "  - Men and panic attacks\n"
            "  - ADHD in adult men (undiagnosed)\n"
            "  - Male burnout and work identity crisis\n"
            "  - Anger and emotional dysregulation\n"
            "  - Men and grief, trauma, PTSD, OCD\n"
            "  - Men and eating disorders (massively underreported)\n"
            "  - Men and insomnia, social anxiety, perfectionism\n"
            "  - Men and self-worth, imposter syndrome, divorce\n"
            "  - Fatherhood and mental health\n"
            "  - Midlife identity crisis in men\n"
            "  - Masculinity, stoicism and mental health\n"
            "  - Men and therapy resistance\n"
            "  - High-functioning depression in men\n"
            "  - Veterans and mental health"
        ),
        "tone": (
            "Direct, honest, no-nonsense  - like advice from a mate who has been there. "
            "Never preachy. Never clinical. Speak to men who would never normally "
            "read a mental health article."
        ),
        "preferred_categories": ["Men's Mental Health", "Recovery & Sobriety", "Anxiety & Stress", "Sleep & Burnout"],
    },
    "women": {
        "label": "Women's Mental Health",
        "description": (
            "Women 25-50 who carry invisible loads and need content that truly validates them. "
            "TOPIC POOL:\n"
            "  - ADHD in women (massively underdiagnosed  - exploding search volume)\n"
            "  - Perimenopause and mental health\n"
            "  - Menopause and identity loss\n"
            "  - Postpartum depression vs postpartum anxiety\n"
            "  - Caregiver burnout\n"
            "  - The mental load and emotional labour\n"
            "  - Burnout in working mothers\n"
            "  - People-pleasing and codependency\n"
            "  - Setting boundaries without guilt\n"
            "  - Imposter syndrome in women at work\n"
            "  - Women in addiction recovery\n"
            "  - Loneliness in adult women\n"
            "  - Perfectionism and anxiety in women\n"
            "  - Body image, self-worth and mental health\n"
            "  - Financial anxiety in women\n"
            "  - Empty nest syndrome\n"
            "  - Grief and loss in women\n"
            "  - Trauma recovery, toxic relationship recovery\n"
            "  - Women and OCD, social anxiety, eating disorders\n"
            "  - Hormones and mood (PMS, PMDD)\n"
            "  - Endometriosis, PCOS and mental health\n"
            "  - Anxiety in high-achieving women\n"
            "  - Gaslighting and recovery"
        ),
        "tone": (
            "Warm, empathetic, validating  - like advice from a trusted friend. "
            "Acknowledge the invisible load women carry. Practical and empowering, never patronising."
        ),
        "preferred_categories": ["Women's Mental Health", "Anxiety & Stress", "Relationships & Family", "Sleep & Burnout", "Recovery & Sobriety"],
    },
    "neutral": {
        "label": "Gender-Neutral Mental Wellness",
        "description": (
            "Adults of any gender exploring mental wellness, apps, recovery, and emotional health. "
            "TOPIC POOL:\n"
            "  - High-functioning anxiety and depression\n"
            "  - Complex PTSD (C-PTSD)\n"
            "  - Nervous system and emotional dysregulation\n"
            "  - AI and mental health tools\n"
            "  - Mental wellness and sobriety apps\n"
            "  - Therapy alternatives when you can't afford it\n"
            "  - Sobriety and social life\n"
            "  - Sleep and mental health\n"
            "  - Insomnia and anxiety loop\n"
            "  - Seasonal affective disorder\n"
            "  - Financial anxiety and mental health\n"
            "  - Workplace burnout and recovery\n"
            "  - Loneliness epidemic\n"
            "  - Social media and mental health\n"
            "  - Grief, chronic illness, panic attacks\n"
            "  - Anxiety management without medication\n"
            "  - Meditation alternatives\n"
            "  - Journaling, exercise, gut health and mental health\n"
            "  - Imposter syndrome, codependency, emotional intelligence\n"
            "  - Mental health apps  - what works and what doesn't\n"
            "  - Rumination and overthinking"
        ),
        "tone": (
            "Accessible, intelligent, and warm. Not gendered. Not clinical. "
            "Like a smart friend who has done the research so you don't have to."
        ),
        "preferred_categories": ["AI & Wellness", "Recovery & Sobriety", "Sleep & Burnout", "Anxiety & Stress", "Relationships & Family"],
    },
}


# -- SERP seed queries per audience -------------------------------------------
SERP_SEEDS = {
    "men": [
        "men's mental health struggles",
        "male depression signs",
        "men emotional suppression",
        "male loneliness epidemic",
        "men anxiety symptoms",
        "men burnout recovery",
        "men addiction recovery support",
        "high functioning depression men",
        "men midlife crisis mental health",
        "men anger management",
        "men therapy resistance",
        "fatherhood mental health",
        "men grief and loss",
        "men self worth issues",
        "men panic attacks",
    ],
    "women": [
        "ADHD in women undiagnosed",
        "perimenopause mental health",
        "postpartum depression support",
        "caregiver burnout women",
        "mental load emotional labour",
        "women imposter syndrome",
        "people pleasing codependency",
        "setting boundaries without guilt",
        "women addiction recovery",
        "loneliness adult women",
        "women perfectionism anxiety",
        "body image self worth",
        "empty nest syndrome",
        "PMDD mood hormones",
        "gaslighting recovery",
    ],
    "neutral": [
        "high functioning anxiety",
        "complex PTSD symptoms",
        "nervous system dysregulation",
        "AI mental health tools",
        "therapy alternatives affordable",
        "sobriety social life",
        "insomnia anxiety loop",
        "workplace burnout recovery",
        "loneliness epidemic adults",
        "social media mental health",
        "anxiety management without medication",
        "rumination overthinking",
        "journaling mental health benefits",
        "emotional intelligence skills",
        "mental health apps that work",
    ],
}


# -- Helpers ------------------------------------------------------------------
def get_wp_auth():
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

def keyword_to_slug(keyword):
    slug = keyword.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")

def count_words_in_html(h):
    return len(re.sub(r"<[^>]+>", " ", h).split())

def validate_seo(content, title, meta, primary_keyword, slug):
    print("\n-- SEO Validation Report --")
    kw    = primary_keyword.lower()
    text  = re.sub(r"<[^>]+>", " ", content).lower()
    words = text.split()
    wc    = len(words)
    first = " ".join(words[:max(1, wc // 10)])
    kw_n  = text.count(kw)
    dens  = (kw_n / wc * 100) if wc > 0 else 0
    checks = {
        "Keyword in title":             kw in title.lower(),
        "Keyword in meta description":  kw in meta.lower(),
        "Keyword in URL slug":          kw.replace(" ", "-") in slug,
        "Keyword in first 10%":         kw in first,
        "Keyword found in content":     kw in text,
        f"Word count >= {MIN_WORD_COUNT}": wc >= MIN_WORD_COUNT,
        "External link present":        'href="http' in content,
        "Internal link present":        "mindcoreai.eu" in content,
        "Google Play link present":     "play.google.com" in content,
        "FAQ section present":          "Frequently Asked Questions" in content,
    }
    all_ok = True
    for label, ok in checks.items():
        icon = "OK" if ok else "FAIL"
        print(f"   [{icon}]  {label}")
        if not ok: all_ok = False
    print(f"   Word count : {wc}")
    print(f"   KW density : {dens:.2f}% ({kw_n} occurrences)")
    print(f"   Slug       : {slug}")
    print("   All SEO checks passed!" if all_ok else "   Some checks failed - post still published.")


# -- History ------------------------------------------------------------------

# ── Deduplication guard: prevent semantically similar posts ──────────────
KEYWORD_SIMILARITY_GROUPS = [
    ["sober", "sobriety", "recovery app", "clean app", "addiction app"],
    ["mood track", "mood diary", "mood journal", "mood log"],
    ["self improvement", "personal growth", "self improving", "wellbeing app"],
    ["anxiety relief", "anxiety app", "emotional support", "stress companion"],
    ["meditation sleep", "bedtime meditation", "sleep meditation", "fall asleep meditation"],
    ["ai companion", "ai chat", "ai mental health", "ai wellness"],
    ["weighted blanket", "anxiety blanket"],
    ["mental health app", "mental wellness app", "wellness app"],
    ["women mental", "perimenopause", "postpartum"],
]

def is_duplicate_keyword(new_keyword, history):
    """Check if new keyword is too similar to any already-published keyword."""
    used_keywords = [e.get("primary_keyword", "").lower() for e in history]
    new_lower = new_keyword.lower()
    
    for group in KEYWORD_SIMILARITY_GROUPS:
        new_matches = any(term in new_lower for term in group)
        if new_matches:
            for used_kw in used_keywords:
                used_matches = any(term in used_kw for term in group)
                if used_matches:
                    print(f"   DEDUP: '{new_keyword}' blocked (similar to '{used_kw}')")
                    return True
    return False

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def get_next_audience(history):
    if not history: return "men"
    last = history[-1].get("audience", "neutral")
    idx  = AUDIENCE_ROTATION.index(last) if last in AUDIENCE_ROTATION else 2
    return AUDIENCE_ROTATION[(idx + 1) % len(AUDIENCE_ROTATION)]

def format_history_for_prompt(history):
    if not history: return "None yet."
    return "\n".join(
        f"  {i}. [{e['date']}] \"{e['title']}\"  - keyword: \"{e['primary_keyword']}\" (audience: {e.get('audience','unknown')})"
        for i, e in enumerate(history, 1)
    )

def build_post_links(history):
    posts = []
    for post in history:
        slug = post.get("slug", "")
        if not slug:
            slug = keyword_to_slug(post.get("primary_keyword", ""))
        if slug:
            posts.append({
                "title": post["title"],
                "url":   f"https://mindcoreai.eu/{slug}/",
            })
    return posts


# -- Keyword Library ----------------------------------------------------------
def load_library():
    if not os.path.exists(LIBRARY_FILE):
        return []
    with open(LIBRARY_FILE, "r") as f:
        return json.load(f)

def pick_from_library(library, audience, history):
    used_keywords = {e["primary_keyword"].lower() for e in history}
    candidates = [
        kw for kw in library
        if not kw["used"]
        and kw["keyword"].lower() not in used_keywords
            and not is_duplicate_keyword(kw["keyword"], history)
        and kw["audience"] == audience
    ]
    if not candidates and audience != "neutral":
        candidates = [
            kw for kw in library
            if not kw["used"]
            and kw["keyword"].lower() not in used_keywords
            and kw["audience"] == "neutral"
        ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x["priority_rank"], 0 if "+900%" in x.get("trend", "") else 1))
    return candidates[0]

def update_library_on_github(library, used_keyword):
    for entry in library:
        if entry["keyword"].lower() == used_keyword.lower():
            entry["used"] = True
            break
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("   Skipping library update - GITHUB_TOKEN not set")
        return
    api_url = f"https://api.github.com/repos/{repo}/contents/{LIBRARY_FILE}"
    hdrs    = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_r   = requests.get(api_url, headers=hdrs, timeout=15)
    sha     = get_r.json().get("sha") if get_r.status_code == 200 else None
    encoded = base64.b64encode(json.dumps(library, indent=2, ensure_ascii=False).encode()).decode()
    payload = {"message": f"blog: mark keyword used  - {used_keyword}", "content": encoded}
    if sha: payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    if put.status_code in (200, 201):
        remaining = sum(1 for k in library if not k["used"])
        print(f"   Library updated  - {remaining} keywords remaining")
    else:
        print(f"   Library update failed: {put.text}")



# -- Online-Therapy.com Affiliate CTA (appended to every blog post) -----------
ONLINE_THERAPY_CTA = """
<div style="background:#1a1a2e;border-radius:12px;padding:28px;margin-top:40px;border:1px solid rgba(212,165,116,0.2);">
  <h3 style="color:#ffffff;font-size:20px;margin:0 0 12px;font-weight:600;">Need Professional Support?</h3>
  <p style="color:rgba(255,255,255,0.75);font-size:15px;line-height:1.7;margin:0 0 20px;">
    If you're ready to take the next step, I personally recommend Online-Therapy.com. It offers CBT-based therapy with licensed therapists, completely online. Worksheets, live sessions, messaging, and a personal therapist you can reach anytime. Affordable, private, and built for people who want real support without the waiting room.
  </p>
  <a href="https://go.online-therapy.com/SHY0" target="_blank" rel="noopener noreferrer" style="display:inline-block;background:#d4a574;color:#1a1a2e;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;text-decoration:none;">Try Online-Therapy.com &rarr;</a>
</div>
<img src="https://go.online-therapy.com/aff_i?offer_id=2&aff_id=3963" width="0" height="0" style="position:absolute;visibility:hidden;" border="0" />
"""

# -- Step 1: Research topic ---------------------------------------------------
def research_topic(history):
    audience = get_next_audience(history)
    profile  = AUDIENCE_PROFILES[audience]
    print(f"Researching topic... (Audience: {profile['label']})")

    library = load_library()
    picked  = pick_from_library(library, audience, history)

    if picked:
        print(f"   [LIBRARY] Using verified keyword: '{picked['keyword']}' ({picked['monthly_searches']} searches/mo, {picked['competition']} competition, {picked['trend']})")
        return research_from_library(picked, audience, profile, history, library)

    # Try SERP research before falling back to Claude
    if SERP_AVAILABLE and SERP_API_KEY:
        try:
            result = research_from_serp(audience, profile, history)
            if result:
                return result
        except Exception as e:
            print(f"   [SERP] Failed: {e}  - falling back to Claude")
    elif not SERP_API_KEY:
        print("   [SERP] Skipped  - no SERP_API_KEY set")

    remaining = sum(1 for k in library if not k["used"])
    print(f"   [RESEARCH] No library/SERP keyword for this audience ({remaining} remaining for others)  - using Claude research")
    return research_from_claude(audience, profile, history)


def research_from_library(picked, audience, profile, history, library):
    history_txt = format_history_for_prompt(history)
    category    = LIBRARY_CATEGORY_MAP.get(picked["keyword"].lower(), profile["preferred_categories"][0])

    # SERP enrichment: fetch real PAA questions for this keyword
    paa_block = ""
    if SERP_AVAILABLE and SERP_API_KEY:
        try:
            print(f"   [SERP] Enriching library keyword with real search data...")
            serp_candidates = research_topics([picked["keyword"]], SERP_API_KEY, country="gb", num_seeds=1, num_autocomplete=2)
            paa_questions = [c["text"] for c in serp_candidates if c.get("source") == "people_also_ask"][:8]
            related_terms = [c["text"] for c in serp_candidates if c.get("source") in ("autocomplete", "related_searches")][:6]
            if paa_questions:
                paa_block = "\nREAL GOOGLE 'PEOPLE ALSO ASK' QUESTIONS (use 3-5 of these in the blog FAQ section):\n"
                paa_block += "\n".join(f"  - {q}" for q in paa_questions) + "\n"
                print(f"   [SERP] Found {len(paa_questions)} PAA questions + {len(related_terms)} related terms")
            if related_terms:
                paa_block += "\nRELATED SEARCH TERMS (weave 2-3 of these naturally into the post):\n"
                paa_block += "\n".join(f"  - {t}" for t in related_terms) + "\n"
        except Exception as e:
            print(f"   [SERP] Enrichment failed (non-fatal): {e}")
    else:
        print("   [SERP] Skipped enrichment (no API key)")

    response = _call_anthropic_with_retry(anthropic_client, 
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO content strategist for mindcoreai.eu.

VERIFIED KEYWORD: {picked['keyword']}
MONTHLY SEARCHES: {picked['monthly_searches']}
COMPETITION: {picked['competition']}
TREND: {picked['trend']}
SUGGESTED TITLE: {picked['suggested_title']}
ASSIGNED CATEGORY: {category}
TARGET AUDIENCE: {profile['label']}

AUDIENCE CONTEXT:
{profile['description']}

{paa_block}
ALREADY PUBLISHED (avoid repeating):
{history_txt}

Tasks:
1. Use the verified keyword as primary keyword  - do NOT change it
2. Write a compelling title that CONTAINS A NUMBER (e.g. "7 Signs...", "5 Ways...", "3 Things...") and contains the keyword
3. Choose the best 5 secondary keywords
4. Write a meta description (150-160 chars) that contains the primary keyword verbatim
5. Write a DALL-E image prompt for a cinematic-warm scene


WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Respond ONLY in this exact JSON  - no markdown:
{{"topic":"title with number and keyword","primary_keyword":"{picked['keyword']}","secondary_keywords":["kw2","kw3","kw4","kw5"],"search_intent":"what reader is looking for","meta_description":"150-160 char meta containing primary keyword verbatim","image_prompt":"specific cinematic-warm scene: what is happening, where, time of day, lighting","rationale":"why this keyword will rank","category":"{category}","audience":"{audience}"}}"""}]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    data["primary_keyword"] = picked["keyword"]
    data["audience"]        = audience
    data["_library_entry"]  = picked
    data["_library"]        = library
    print(f"   Topic    : {data['topic']}")
    print(f"   Keyword  : {data['primary_keyword']}")
    print(f"   Category : {data.get('category', 'N/A')}")
    return data


def research_from_claude(audience, profile, history):
    history_txt = format_history_for_prompt(history)
    all_cats    = "\n".join(f"  - {c}" for c in CATEGORIES)
    pref_cats   = "\n".join(f"  - {c}" for c in profile["preferred_categories"])

    response = _call_anthropic_with_retry(anthropic_client, 
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO strategist for mindcoreai.eu.

Find the most UNTAPPED blog topic for: {profile['label']}
{profile['description']}

CRITERIA:
  - High demand, VERY low competition
  - Avoid terms dominated by WebMD, Healthline, Mayo Clinic, Psychology Today
  - Long-tail, question-based keywords big sites ignore
  - Evergreen  - ranks for months
  - 2-5 word primary keyword

ALREADY PUBLISHED:
{history_txt}

PREFERRED CATEGORIES:
{pref_cats}

ALL CATEGORIES:
{all_cats}


WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Respond ONLY in this exact JSON:
{{"topic":"title containing a number (e.g. 7 Signs / 5 Ways) and the keyword","primary_keyword":"keyword","secondary_keywords":["kw2","kw3","kw4","kw5"],"search_intent":"intent","meta_description":"150-160 char meta containing primary keyword verbatim","image_prompt":"specific cinematic-warm scene: what is happening, where, time of day, lighting","rationale":"SERP insight","category":"exact category","audience":"{audience}"}}"""}]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    data["audience"]       = audience
    data["_library_entry"] = None
    data["_library"]       = None
    print(f"   Topic    : {data['topic']}")
    print(f"   Keyword  : {data['primary_keyword']}")
    print(f"   Category : {data.get('category', 'N/A')}")
    print(f"   Why      : {data.get('rationale', '')}")
    return data


def research_from_serp(audience, profile, history):
    """Use SERP API to find real trending topics, then Claude to shape the blog."""
    print(f"   [SERP] Researching real search data for {profile['label']}...")
    seeds = SERP_SEEDS.get(audience, SERP_SEEDS["neutral"])
    candidates = research_topics(seeds, SERP_API_KEY, country="gb", num_seeds=3, num_autocomplete=2)
    if not candidates:
        print("   [SERP] No candidates found")
        return None

    used_topics = [e.get("primary_keyword", "").lower() for e in history]
    winner = pick_best_topic(
        candidates, anthropic_client, history=used_topics,
        context=f"{profile['label']} blog for mindcoreai.eu", model="claude-sonnet-4-6"
    )
    if not winner:
        return None

    history_txt = format_history_for_prompt(history)
    all_cats    = "\n".join(f"  - {c}" for c in CATEGORIES)
    pref_cats   = "\n".join(f"  - {c}" for c in profile["preferred_categories"])

    # Collect PAA questions for FAQ section
    paa_questions = [c["text"] for c in candidates if c["source"] == "people_also_ask"][:8]
    paa_block = ""
    if paa_questions:
        paa_block = "\nREAL PEOPLE ALSO ASK QUESTIONS (use 3-5 of these in the FAQ section):\n"
        paa_block += "\n".join(f"  - {q}" for q in paa_questions) + "\n"

    response = _call_anthropic_with_retry(anthropic_client, 
        model="claude-sonnet-4-6", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO content strategist for mindcoreai.eu.

SERP-RESEARCHED KEYWORD: {winner.get('keyword', winner.get('topic', ''))}
SERP SOURCE: {winner.get('source', 'unknown')}
COMPETITION SIGNAL: {winner.get('competition_signal', 'unknown')}
TARGET AUDIENCE: {profile['label']}
{paa_block}
AUDIENCE CONTEXT:
{profile['description']}

ALREADY PUBLISHED (avoid repeating):
{history_txt}

PREFERRED CATEGORIES:
{pref_cats}

ALL CATEGORIES:
{all_cats}

Tasks:
1. Use the SERP keyword as primary keyword or refine to 2-5 words
2. Write a compelling title that CONTAINS A NUMBER (e.g. "7 Signs...", "5 Ways...") and contains the keyword
3. Choose the best 5 secondary keywords
4. Write a meta description (150-160 chars) containing the primary keyword verbatim
5. Write a DALL-E image prompt for a cinematic-warm scene


WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Respond ONLY in this exact JSON  - no markdown:
{{"topic":"title with number and keyword","primary_keyword":"2-5 word keyword","secondary_keywords":["kw2","kw3","kw4","kw5"],"search_intent":"what reader is looking for","meta_description":"150-160 char meta containing primary keyword verbatim","image_prompt":"specific cinematic-warm scene: what is happening, where, time of day, lighting","rationale":"SERP insight","category":"exact category","audience":"{audience}","serp_paa_questions":{json.dumps(paa_questions[:5])}}}"""}]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    data["audience"]       = audience
    data["_library_entry"] = None
    data["_library"]       = None
    data["_serp_winner"]   = winner
    data["_serp_paa"]      = paa_questions
    print(f"   Topic    : {data['topic']}")
    print(f"   Keyword  : {data['primary_keyword']} [SERP-driven]")
    print(f"   Category : {data.get('category', 'N/A')}")
    print(f"   PAA Qs   : {len(paa_questions)} available for FAQ")
    return data


# -- Step 2: Write post -------------------------------------------------------
def write_blog_post(topic_data, history):
    print("Writing blog post...")
    audience = topic_data.get("audience", "neutral")
    profile  = AUDIENCE_PROFILES[audience]
    kw       = topic_data["primary_keyword"]

    int_links = "\n".join(f'  - Link text: "{t[0]}" → {t[1]}' for t in INTERNAL_LINKS)
    ext_links = "\n".join(f'  - Link text: "{t[0]}" → {t[1]}' for t in EXTERNAL_LINKS[:3])

    # Use real SERP PAA questions for FAQ if available
    serp_paa = topic_data.get("_serp_paa", []) or topic_data.get("serp_paa_questions", [])
    if serp_paa:
        faq_instruction = (
            f'\n\nMANDATORY FAQ SECTION (SERP-DRIVEN):\n'
            f'  After the main content and before the final CTA, include a FAQ section with this structure:\n'
            f'  <h2>Frequently Asked Questions About {kw.title()}</h2>\n'
            f'  Then 5 questions and answers using <h3> for each question and <p> for each answer.\n'
            f'  USE THESE REAL "People Also Ask" QUESTIONS FROM GOOGLE (pick the best 3-5, rephrase slightly if needed):\n'
            + "\n".join(f'    - {q}' for q in serp_paa[:8]) +
            f'\n  - Add 1-2 more questions if needed to reach 5 total\n'
            f'  - At least 2 questions must include the exact phrase "{kw}"\n'
            f'  - Answers must be 2-4 sentences  - specific and helpful, not generic\n'
            f'  - One answer should naturally mention MindCore AI as a useful tool'
        )
    else:
        faq_instruction = (
            f'\n\nMANDATORY FAQ SECTION:\n'
            f'  After the main content and before the final CTA, include a FAQ section with this structure:\n'
            f'  <h2>Frequently Asked Questions About {kw.title()}</h2>\n'
            f'  Then 5 questions and answers using <h3> for each question and <p> for each answer.\n'
            f'  - Questions must be natural, conversational, things people actually Google\n'
            f'  - At least 2 questions must include the exact phrase "{kw}"\n'
            f'  - Answers must be 2-4 sentences  - specific and helpful, not generic\n'
            f'  - One answer should naturally mention MindCore AI as a useful tool'
        )

    existing_posts   = build_post_links(history)
    cross_link_block = ""
    if len(existing_posts) >= 2:
        cross_link_block = (
            "\nCROSS-POST LINKS (MANDATORY  - link to exactly 2 of these existing posts "
            "naturally within the content using relevant anchor text):\n"
        )
        for p in existing_posts:
            cross_link_block += f'  - "{p["title"]}" → {p["url"]}\n'
        cross_link_block += "Pick the 2 most topically relevant. Link mid-content, not just at the end.\n"
    elif len(existing_posts) == 1:
        cross_link_block = (
            f'\nCROSS-POST LINK (link naturally in the content):\n'
            f'  - "{existing_posts[0]["title"]}" → {existing_posts[0]["url"]}\n'
        )

    response = _call_anthropic_with_retry(anthropic_client, 
        model="claude-opus-4-5", max_tokens=7000,
        messages=[{"role": "user", "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full, publish-ready blog post:
  Title           : {topic_data['topic']}
  Primary Keyword : {kw}
  Secondary KWs   : {', '.join(topic_data['secondary_keywords'])}
  Search Intent   : {topic_data['search_intent']}
  Target Audience : {profile['label']}

TONE:
  {profile['tone']}

CRITICAL KEYWORD RULES:
  1. EXACT phrase "{kw}" in the H1 title
  2. EXACT phrase "{kw}" in the very first sentence
  3. EXACT phrase "{kw}" in at least 3 H2 subheadings
  4. EXACT phrase "{kw}" at least 8-10 times total
  5. No synonyms or variations  - EXACT phrase only
  6. Keyword density: 1.0%-1.5%
  7. Minimum 1,200 words (not counting FAQ)

MANDATORY LINKS  - all must appear as proper HTML anchor tags:

  Internal site pages (include ALL 3):
{int_links}

  External authoritative sources (include at least 2):
{ext_links}

  MindCore AI app link (include naturally at least ONCE in the body content, separate from the CTA button):
  - Use this HTML inline in a sentence: {APP_INLINE_LINK}
  - Example: "That is why tools like {APP_INLINE_LINK} were built  - to be there at 3am when no one else is."
{cross_link_block}
GOOGLE PLAY CTA BUTTON (use this EXACT HTML in the final CTA section):
  {GP_CTA_LINK}
{faq_instruction}

STRUCTURE:
  H1 → intro (2-3 para) → 5-7 H2 sections (150-200 words each) → FAQ section → conclusion + CTA button

  Other requirements:
  - At least one <ul> list in the main content
  - Real, actionable advice  - zero platitudes

FORMAT:
  - Clean WordPress HTML: h1 h2 h3 p ul li strong em a
  - External links: target="_blank" rel="noopener noreferrer"
  - No html head body style script tags
  - After ALL HTML: EXCERPT: [2-3 sentence hook with exact phrase "{kw}"]"""}]
    )

    content  = response.content[0].text
    wc       = count_words_in_html(content)
    kw_count = content.lower().count(kw.lower())
    print(f"   Written ({wc} words, keyword appears {kw_count} times)")

    if wc < MIN_WORD_COUNT:
        print("   Expanding...")
        content = expand_blog_post(content, topic_data, wc)

    return content


def expand_blog_post(content, topic_data, current_words):
    needed = MIN_WORD_COUNT - current_words
    kw     = topic_data["primary_keyword"]
    response = _call_anthropic_with_retry(anthropic_client, 
        model="claude-opus-4-5", max_tokens=3000,
        messages=[{"role": "user", "content": f"""Post is {current_words} words  - needs {MIN_WORD_COUNT}.
Add ~{needed} words, expand sections or add 2 H2s. Same tone, HTML format.
Use EXACT phrase "{kw}" at least 3 more times. Return COMPLETE post with EXCERPT.

{content}"""}]
    )
    expanded = response.content[0].text
    print(f"   Expanded to {count_words_in_html(expanded)} words")
    return expanded


# -- Step 3: Image generation -------------------------------------------------
def generate_illustration(image_prompt):
    """Generate cinematic-warm image using fal.ai Flux Pro."""
    print("Generating cinematic image (fal.ai Flux Pro)...")
    cinematic_prompt = (
        f"{image_prompt}. "
        "Style: cinematic photography, warm golden-hour lighting, "
        "soft focus background with shallow depth of field, "
        "peaceful and hopeful atmosphere, no faces shown, "
        "warm amber and soft teal colour grading, photorealistic. "
        "No text, no words, no letters in the image."
    )
    return generate_fal_image(cinematic_prompt, image_size="landscape_4_3", model="pro")


def upload_image_to_wordpress(image_data, alt_text=""):
    print("Uploading image...")
    filename = f"mindcore-blog-{datetime.now().strftime('%Y%m%d')}.png"
    auth     = get_wp_auth()

    upload_headers = {**auth}
    upload_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    upload_headers["Content-Type"]        = "image/png"
    resp = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=upload_headers, data=image_data, timeout=60)

    if resp.status_code != 201:
        print(f"   Upload failed ({resp.status_code}): {resp.text}")
        return None, None

    media     = resp.json()
    media_id  = media["id"]
    media_url = media.get("source_url", "")
    print(f"   Image uploaded (ID: {media_id})")

    if alt_text:
        time.sleep(2)
        patch = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            headers={**auth, "Content-Type": "application/json"},
            json={"alt_text": alt_text, "caption": alt_text},
            timeout=15,
        )
        print(f"   Alt text set: '{alt_text}'" if patch.status_code == 200 else f"   Alt text failed: {patch.text}")

    return media_id, media_url


def inject_image_into_content(content, media_url, alt_text):
    if not media_url:
        return content
    img_html = (
        f'\n<figure class="wp-block-image size-full">'
        f'<img src="{media_url}" alt="{alt_text}" class="wp-image"/>'
        f'</figure>\n'
    )
    insert_pos = content.find("</p>")
    if insert_pos != -1:
        content = content[:insert_pos + 4] + img_html + content[insert_pos + 4:]
    else:
        content = img_html + content
    return content


# -- Step 4: Category ---------------------------------------------------------
def resolve_category_id(category_name):
    if CATEGORY_IDS.get(category_name) is not None:
        print(f"   Category  : {category_name} (ID: {CATEGORY_IDS[category_name]})")
        return CATEGORY_IDS[category_name]
    auth = get_wp_auth()
    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?per_page=100&search={requests.utils.quote(category_name)}",
        headers=auth, timeout=15,
    )
    if resp.status_code == 200:
        for c in resp.json():
            if c["name"].replace("&amp;", "&").replace("&#039;", "'").lower() == category_name.lower():
                CATEGORY_IDS[category_name] = c["id"]
                print(f"   Category  : {category_name} (ID: {c['id']})")
                return c["id"]
    create = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers={**auth, "Content-Type": "application/json"},
        json={"name": category_name}, timeout=15,
    )
    if create.status_code == 201:
        cat_id = create.json()["id"]
        CATEGORY_IDS[category_name] = cat_id
        print(f"   Category  : {category_name} (ID: {cat_id}) [created]")
        return cat_id
    elif create.status_code == 400:
        err     = create.json()
        term_id = err.get("data", {}).get("term_id") or (err.get("additional_data") or [None])[0]
        if term_id:
            CATEGORY_IDS[category_name] = int(term_id)
            print(f"   Category  : {category_name} (ID: {term_id})")
            return int(term_id)
    print(f"   Could not resolve: {category_name}")
    return None


# -- Step 5: Publish ----------------------------------------------------------
def publish_to_wordpress(topic_data, content, media_id=None, media_url=None):
    print("Publishing to WordPress...")

    excerpt = ""
    if "EXCERPT:" in content:
        bits    = content.split("EXCERPT:")
        content = bits[0].strip()
        excerpt = bits[1].strip() if len(bits) > 1 else ""

    if media_url:
        content = inject_image_into_content(content, media_url, topic_data["primary_keyword"])

    # Append Online-Therapy.com affiliate CTA to every blog post
    content += ONLINE_THERAPY_CTA

    slug     = keyword_to_slug(topic_data["primary_keyword"])
    cat_name = topic_data.get("category", "")
    cat_id   = resolve_category_id(cat_name) if cat_name else None

    validate_seo(content, topic_data["topic"], topic_data["meta_description"],
                 topic_data["primary_keyword"], slug)

    auth = get_wp_auth()
    auth["Content-Type"] = "application/json"

    payload = {
        "title":      topic_data["topic"],
        "content":    content,
        "excerpt":    excerpt,
        "slug":       slug,
        "status":     "publish",
        "categories": [cat_id] if cat_id else [],
        "meta": {
            "_yoast_wpseo_metadesc": topic_data["meta_description"],
            "_yoast_wpseo_focuskw":  topic_data["primary_keyword"],
            "_yoast_wpseo_title":    topic_data["topic"],
        },
    }

    print("   Waiting 60s before publishing...")
    time.sleep(60)

    for attempt in range(4):
        resp = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=auth, json=payload, timeout=30)
        if resp.status_code == 201:
            break
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 30 * (attempt + 1)))
            print(f"   Rate limited - waiting {wait}s...")
            time.sleep(wait)
            continue
        raise RuntimeError(f"WordPress publish failed ({resp.status_code}): {resp.text}")
    else:
        raise RuntimeError("WordPress publish failed after 4 attempts")

    post    = resp.json()
    post_id = post["id"]
    print(f"   Published -> {post.get('link', 'N/A')}")

    if media_id:
        for img_attempt in range(3):
            wait_time = 10 * (img_attempt + 1)
            print(f"   Waiting {wait_time}s before attaching featured image...")
            time.sleep(wait_time)
            upd = requests.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                headers=auth,
                json={"featured_media": media_id},
                timeout=30,
            )
            if upd.status_code == 200:
                print("   Featured image attached")
                break
            elif upd.status_code == 429:
                print(f"   Image attach rate limited (attempt {img_attempt + 1}/3)")
            else:
                print(f"   Image attach failed: {upd.status_code}  - {upd.text}")
                break

    return post


# -- Step 6: Save history & update library ------------------------------------
def update_history_on_github(history, new_entry):
    print("Saving to history...")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("   Skipping  - GITHUB_TOKEN not set")
        return
    api_url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    hdrs    = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_r   = requests.get(api_url, headers=hdrs, timeout=15)
    sha     = get_r.json().get("sha") if get_r.status_code == 200 else None
    history.append(new_entry)
    encoded = base64.b64encode(json.dumps(history, indent=2).encode()).decode()
    payload = {"message": f"blog: log  - {new_entry['title'][:60]}", "content": encoded}
    if sha: payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    print(f"   History committed ({len(history)} posts)" if put.status_code in (200, 201) else f"   History failed: {put.text}")


# -- Main ---------------------------------------------------------------------


def pin_to_pinterest(image_data, post_title, post_url, primary_keyword):
    """Pin the blog featured image to Pinterest via Upload-Post."""
    if not UPLOAD_POST_API_KEY:
        print("   Pinterest: skipped (no UPLOAD_POST_API_KEY)")
        return
    import tempfile
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(image_data)
        tmp.close()
        pinterest_desc = (
            f"{post_title}\n\n"
            f"Read the full article: {post_url}\n\n"
            f"#mentalhealth #mentalhealthmatters #mindcoreai #healing #selfcare "
            f"#recovery #anxiety #mentalwellness #{primary_keyword.replace(' ', '').lower()}"
        )[:500]
        data = [
            ("user", "MindCoreAI"),
            ("platform[]", "pinterest"),
            ("title", post_title[:280]),
            ("pinterest_description", pinterest_desc),
            ("pinterest_board_id", "1123366769493611180"),
            ("post_mode", "DIRECT_POST"),
            ("photo_cover_index", "0"),
        ]
        f = open(tmp.name, "rb")
        files = [("photos[]", ("blog_pin.jpg", f, "image/jpeg"))]
        resp = requests.post(
            UPLOAD_POST_PHOTOS_URL,
            headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
            files=files, data=data, timeout=180,
        )
        f.close()
        os.unlink(tmp.name)
        if resp.ok:
            print(f"   Pinterest: pinned OK ({resp.status_code})")
        else:
            print(f"   Pinterest: WARNING {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"   Pinterest: failed - {e}")


def main():
    print("\n== MindCore AI - Blog Automation Pipeline ==")
    history = load_history()
    print(f"History: {len(history)} posts published")

    topic_data = research_topic(history)
    content    = write_blog_post(topic_data, history)

    media_id  = None
    media_url = None
    image_data = None
    try:
        image_data          = generate_illustration(topic_data["image_prompt"])
        media_id, media_url = upload_image_to_wordpress(image_data, alt_text=topic_data["primary_keyword"])
    except Exception as exc:
        print(f"   Image failed: {exc}")

    post = publish_to_wordpress(topic_data, content, media_id, media_url)

    # Pin to Pinterest
    if image_data and post.get("link"):
        print("\n6. Pinning to Pinterest...")
        pin_to_pinterest(image_data, topic_data["topic"], post["link"], topic_data["primary_keyword"])
    elif image_data:
        post_slug = keyword_to_slug(topic_data["primary_keyword"])
        print("\n6. Pinning to Pinterest...")
        pin_to_pinterest(image_data, topic_data["topic"], f"https://mindcoreai.eu/{post_slug}/", topic_data["primary_keyword"])

    if topic_data.get("_library_entry") and topic_data.get("_library") is not None:
        update_library_on_github(topic_data["_library"], topic_data["primary_keyword"])

    update_history_on_github(history, {
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "title":           topic_data["topic"],
        "primary_keyword": topic_data["primary_keyword"],
        "category":        topic_data.get("category", ""),
        "audience":        topic_data.get("audience", "neutral"),
        "slug":            keyword_to_slug(topic_data["primary_keyword"]),
        "wp_post_id":      post.get("id"),
        "source":          "library" if topic_data.get("_library_entry") else ("serp" if topic_data.get("_serp_winner") else "claude_research"),
    })

    print("\nPipeline complete! Post is live on mindcoreai.eu")
    print("=" * 50)


if __name__ == "__main__":
    main()
