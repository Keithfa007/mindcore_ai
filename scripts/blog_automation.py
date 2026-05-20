import os
import json
import base64
import re
import time
import requests
from anthropic import Anthropic
from openai import OpenAI
from datetime import datetime

# -- Clients ------------------------------------------------------------------
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
openai_client    = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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
    "mental health app":            "AI & Wellness",
    "mental wellness apps":         "AI & Wellness",
    "women's mental health":        "Women's Mental Health",
    "women and mental health":      "Women's Mental Health",
    "sobriety app":                 "Recovery & Sobriety",
    "sober app":                    "Recovery & Sobriety",
    "mood tracking app":            "AI & Wellness",
    "sober time app":               "Recovery & Sobriety",
    "ai companion app":             "AI & Wellness",
    "ai chat companion":            "AI & Wellness",
    "postpartum depression support":"Women's Mental Health",
    "sobriety tracker":             "Recovery & Sobriety",
    "sober tracker":                "Recovery & Sobriety",
    "days sober app":               "Recovery & Sobriety",
    "sober counter":                "Recovery & Sobriety",
    "sobriety counter":             "Recovery & Sobriety",
    "best mood tracker app":        "AI & Wellness",
    "self improvement app":         "AI & Wellness",
    "personal growth apps":         "AI & Wellness",
    "wellbeing apps":               "AI & Wellness",
    "mood diary app":               "AI & Wellness",
    "sober buddy app":              "Recovery & Sobriety",
    "stay sober app":               "Recovery & Sobriety",
    "loneliness app":               "AI & Wellness",
    "anxiety relief app":           "Anxiety & Stress",
    "emotional support app":        "AI & Wellness",
    "self improving apps":          "AI & Wellness",
    "mood journal app":             "AI & Wellness",
    "sobriety tracking app":        "Recovery & Sobriety",
    "stress anxiety companion app": "Anxiety & Stress",
}

# Internal site pages to link to naturally
INTERNAL_LINKS = [
    ("MindCore AI features", "https://mindcoreai.eu/features/"),
    ("our story",            "https://mindcoreai.eu/about-us/"),
    ("MindCore AI blog",     "https://mindcoreai.eu/blog/"),
]

# External authoritative sources
EXTERNAL_LINKS = [
    ("Mind",                     "https://www.mind.org.uk"),
    ("Mental Health Foundation", "https://www.mentalhealth.org.uk"),
    ("NHS mental health support","https://www.nhs.uk/mental-health/"),
    ("NAMI",                     "https://www.nami.org"),
    ("SAMHSA",                   "https://www.samhsa.gov"),
]

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
            "Direct, honest, no-nonsense — like advice from a mate who has been there. "
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
            "  - ADHD in women (massively underdiagnosed — exploding search volume)\n"
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
            "Warm, empathetic, validating — like advice from a trusted friend. "
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
            "  - Mental health apps — what works and what doesn't\n"
            "  - Rumination and overthinking"
        ),
        "tone": (
            "Accessible, intelligent, and warm. Not gendered. Not clinical. "
            "Like a smart friend who has done the research so you don't have to."
        ),
        "preferred_categories": ["AI & Wellness", "Recovery & Sobriety", "Sleep & Burnout", "Anxiety & Stress", "Relationships & Family"],
    },
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
        f"  {i}. [{e['date']}] \"{e['title']}\" — keyword: \"{e['primary_keyword']}\" (audience: {e.get('audience','unknown')})"
        for i, e in enumerate(history, 1)
    )

def build_post_links(history):
    """Build a list of existing published post titles + URLs for cross-linking."""
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
    payload = {"message": f"blog: mark keyword used — {used_keyword}", "content": encoded}
    if sha: payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    if put.status_code in (200, 201):
        remaining = sum(1 for k in library if not k["used"])
        print(f"   Library updated — {remaining} keywords remaining")
    else:
        print(f"   Library update failed: {put.text}")


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
    else:
        remaining = sum(1 for k in library if not k["used"])
        print(f"   [RESEARCH] No library keyword for this audience ({remaining} remaining for others) — using Claude research")
        return research_from_claude(audience, profile, history)


def research_from_library(picked, audience, profile, history, library):
    history_txt = format_history_for_prompt(history)
    category    = LIBRARY_CATEGORY_MAP.get(picked["keyword"].lower(), profile["preferred_categories"][0])

    response = anthropic_client.messages.create(
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

ALREADY PUBLISHED (avoid repeating):
{history_txt}

Tasks:
1. Use the verified keyword as primary keyword — do NOT change it
2. Write a compelling title that CONTAINS A NUMBER (e.g. "7 Signs...", "5 Ways...", "3 Things...") and contains the keyword
3. Choose the best 5 secondary keywords
4. Write a meta description (150-160 chars) that contains the primary keyword verbatim
5. Write a DALL-E image prompt for a cinematic-warm scene

Respond ONLY in this exact JSON — no markdown:
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

    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO strategist for mindcoreai.eu.

Find the most UNTAPPED blog topic for: {profile['label']}
{profile['description']}

CRITERIA:
  - High demand, VERY low competition
  - Avoid terms dominated by WebMD, Healthline, Mayo Clinic, Psychology Today
  - Long-tail, question-based keywords big sites ignore
  - Evergreen — ranks for months
  - 2-5 word primary keyword

ALREADY PUBLISHED:
{history_txt}

PREFERRED CATEGORIES:
{pref_cats}

ALL CATEGORIES:
{all_cats}

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


# -- Step 2: Write post -------------------------------------------------------
def write_blog_post(topic_data, history):
    print("Writing blog post...")
    audience = topic_data.get("audience", "neutral")
    profile  = AUDIENCE_PROFILES[audience]
    kw       = topic_data["primary_keyword"]

    # Build internal site page links
    int_links = "\n".join(f'  - Link text: "{t[0]}" → {t[1]}' for t in INTERNAL_LINKS)

    # Build external authoritative links
    ext_links = "\n".join(f'  - Link text: "{t[0]}" → {t[1]}' for t in EXTERNAL_LINKS[:3])

    # Build cross-post links from existing published posts
    existing_posts   = build_post_links(history)
    cross_link_block = ""
    if len(existing_posts) >= 2:
        cross_link_block = (
            "\nCROSS-POST LINKS (MANDATORY — link to exactly 2 of these existing posts "
            "naturally within the content using relevant anchor text):\n"
        )
        for p in existing_posts:
            cross_link_block += f'  - "{p["title"]}" → {p["url"]}\n'
        cross_link_block += (
            "Pick the 2 most topically relevant posts to the current article. "
            "Link to them mid-content, not just at the end.\n"
        )
    elif len(existing_posts) == 1:
        cross_link_block = (
            f'\nCROSS-POST LINK (link to this existing post naturally in the content):\n'
            f'  - "{existing_posts[0]["title"]}" → {existing_posts[0]["url"]}\n'
        )

    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=6000,
        messages=[{"role": "user", "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full, publish-ready blog post:
  Title           : {topic_data['topic']}
  Primary Keyword : {kw}
  Secondary KWs   : {', '.join(topic_data['secondary_keywords'])}
  Search Intent   : {topic_data['search_intent']}
  Target Audience : {profile['label']}

TONE:
  {profile['tone']}

CRITICAL KEYWORD RULES (Yoast SEO compliance):
  1. The EXACT phrase "{kw}" must appear in the H1 title
  2. The EXACT phrase "{kw}" must be in the very FIRST sentence of the first paragraph
  3. The EXACT phrase "{kw}" must appear in at least 3 H2 subheadings
  4. The EXACT phrase "{kw}" must appear throughout the body — at least 8-10 times total
  5. Use EXACTLY "{kw}" — not synonyms, not variations, the EXACT phrase every time
  6. Keyword density target: 1.0%-1.5%
  7. Minimum 1,200 words of readable content

MANDATORY LINKS — all must appear as proper HTML anchor tags:

  Internal site pages (include ALL 3):
{int_links}

  External authoritative sources (include at least 2):
{ext_links}
{cross_link_block}
WRITING REQUIREMENTS:
  - Structure: H1 → intro (2-3 para) → 5-7 H2 sections (150-200 words each) → conclusion + CTA
  - Include at least one <ul> list
  - Real, actionable advice — zero generic platitudes
  - Final section: natural CTA to download MindCore AI as their 24/7 companion

FORMAT RULES:
  - Return clean WordPress HTML ONLY: h1 h2 h3 p ul li strong em a tags
  - Links: <a href="URL">text</a>
  - External links: add target="_blank" rel="noopener noreferrer"
  - Internal links: no target="_blank" needed
  - No html head body style script tags
  - After ALL HTML, on its own line:
    EXCERPT: [2-3 sentence hook containing the exact phrase "{kw}"]"""}]
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
    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=3000,
        messages=[{"role": "user", "content": f"""This post is {current_words} words — needs {MIN_WORD_COUNT}.
Add ~{needed} words by expanding sections or adding 2 new H2 sections.
Same tone, HTML format.
IMPORTANT: use the EXACT phrase "{kw}" at least 3 more times in the additions.
Return the COMPLETE updated post including EXCERPT at the end.

{content}"""}]
    )
    expanded = response.content[0].text
    print(f"   Expanded to {count_words_in_html(expanded)} words")
    return expanded


# -- Step 3: Image generation -------------------------------------------------
def generate_illustration(image_prompt):
    print("Generating cinematic image...")
    cinematic_prompt = (
        f"{image_prompt}. "
        "Style: cinematic photography, warm golden-hour lighting, "
        "soft focus background with shallow depth of field, "
        "peaceful and hopeful atmosphere, no faces shown — shoot from behind or hands/objects only, "
        "warm amber and soft teal colour grading, professional camera lens quality, "
        "subtle lens flare, photorealistic. "
        "No text, no words, no letters in the image."
    )
    resp = openai_client.images.generate(
        model="dall-e-3",
        prompt=cinematic_prompt,
        size="1792x1024",
        quality="hd",
        n=1,
    )
    img = requests.get(resp.data[0].url, timeout=30).content
    print("   Cinematic image generated")
    return img


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

    # Attach featured image with retry
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
                print(f"   Image attach failed: {upd.status_code} — {upd.text}")
                break

    return post


# -- Step 6: Save history & update library ------------------------------------
def update_history_on_github(history, new_entry):
    print("Saving to history...")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("   Skipping — GITHUB_TOKEN not set")
        return
    api_url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    hdrs    = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_r   = requests.get(api_url, headers=hdrs, timeout=15)
    sha     = get_r.json().get("sha") if get_r.status_code == 200 else None
    history.append(new_entry)
    encoded = base64.b64encode(json.dumps(history, indent=2).encode()).decode()
    payload = {"message": f"blog: log — {new_entry['title'][:60]}", "content": encoded}
    if sha: payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    print(f"   History committed ({len(history)} posts)" if put.status_code in (200, 201) else f"   History failed: {put.text}")


# -- Main ---------------------------------------------------------------------
def main():
    print("\n== MindCore AI - Blog Automation Pipeline ==")
    history = load_history()
    print(f"History: {len(history)} posts published")

    topic_data = research_topic(history)
    content    = write_blog_post(topic_data, history)   # history passed for cross-linking

    media_id  = None
    media_url = None
    try:
        image_data          = generate_illustration(topic_data["image_prompt"])
        media_id, media_url = upload_image_to_wordpress(image_data, alt_text=topic_data["primary_keyword"])
    except Exception as exc:
        print(f"   Image failed: {exc}")

    post = publish_to_wordpress(topic_data, content, media_id, media_url)

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
        "source":          "library" if topic_data.get("_library_entry") else "claude_research",
    })

    print("\nPipeline complete! Post is live on mindcoreai.eu")
    print("=" * 50)


if __name__ == "__main__":
    main()
