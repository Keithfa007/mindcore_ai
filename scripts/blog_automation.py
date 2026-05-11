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
MIN_WORD_COUNT = 1200

# Audience rotation order
AUDIENCE_ROTATION = ["men", "women", "neutral"]

# Known category IDs from WordPress
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

# Audience-specific guidance — expanded topic pools for maximum keyword coverage
AUDIENCE_PROFILES = {
    "men": {
        "label": "Men's Mental Health",
        "description": (
            "Men 35+ who are massively underserved in mental health. They suffer in silence, "
            "rarely seek help, and respond to honest, shame-free, practical content. "
            "TOPIC POOL — find untapped angles within these areas:\n"
            "  - Emotional suppression and how to open up\n"
            "  - Male depression (men die by suicide at 3-4x the rate of women — almost zero targeted content)\n"
            "  - The male loneliness epidemic (friendship loss after 35)\n"
            "  - Addiction and recovery: alcohol, cocaine, gambling, porn\n"
            "  - Men and anxiety (often presents physically — chest, stomach — men don't recognise it)\n"
            "  - Men and panic attacks (frequently mistaken for heart attacks)\n"
            "  - ADHD in adult men (undiagnosed, misunderstood, affecting relationships and work)\n"
            "  - Male burnout and work identity crisis\n"
            "  - Anger and emotional dysregulation in men\n"
            "  - Men and grief (loss of parent, relationship, identity)\n"
            "  - Men and trauma (childhood, workplace, relationship)\n"
            "  - Men and PTSD\n"
            "  - Men and OCD\n"
            "  - Men and eating disorders (massively underreported)\n"
            "  - Men and insomnia\n"
            "  - Men and social anxiety\n"
            "  - Men and perfectionism\n"
            "  - Men and imposter syndrome at work\n"
            "  - Men and self-worth\n"
            "  - Men after divorce or separation\n"
            "  - Fatherhood and mental health\n"
            "  - Midlife identity crisis in men\n"
            "  - Masculinity, stoicism and mental health\n"
            "  - Men and therapy resistance (why they avoid it and how to start)\n"
            "  - Men in recovery navigating social life\n"
            "  - High-functioning depression in men\n"
            "  - Men and high-pressure careers\n"
            "  - Veterans and mental health"
        ),
        "tone": (
            "Direct, honest, no-nonsense — like advice from a mate who has been there. "
            "Never preachy. Never clinical. Speak to men who would never normally "
            "read a mental health article. Use real language, not therapy-speak."
        ),
        "preferred_categories": ["Men's Mental Health", "Recovery & Sobriety", "Anxiety & Stress", "Sleep & Burnout"],
    },
    "women": {
        "label": "Women's Mental Health",
        "description": (
            "Women 25-50 who are willing to seek help but overwhelmed by generic advice. "
            "They carry invisible loads and need content that truly validates their experience. "
            "TOPIC POOL — find untapped angles within these areas:\n"
            "  - ADHD in women (massively underdiagnosed — exploding search volume, almost no targeted content)\n"
            "  - Perimenopause and mental health (anxiety, depression, rage — barely covered)\n"
            "  - Menopause and identity loss\n"
            "  - Postpartum depression vs postpartum anxiety (very different, confused constantly)\n"
            "  - Maternal mental health beyond postpartum\n"
            "  - Caregiver burnout (women disproportionately carry this)\n"
            "  - The mental load and emotional labour\n"
            "  - Burnout in working mothers\n"
            "  - People-pleasing and codependency\n"
            "  - Setting boundaries without guilt\n"
            "  - Imposter syndrome in women at work\n"
            "  - Women in addiction recovery (underserved niche)\n"
            "  - Loneliness in adult women (friendships fading after 35)\n"
            "  - Perfectionism and anxiety in women\n"
            "  - Body image, self-worth and mental health\n"
            "  - Financial anxiety in women\n"
            "  - Empty nest syndrome\n"
            "  - Grief and loss in women\n"
            "  - Trauma recovery for women\n"
            "  - Toxic relationship recovery\n"
            "  - Women and OCD\n"
            "  - Women and social anxiety\n"
            "  - Women navigating divorce\n"
            "  - Chronic illness and mental health in women\n"
            "  - Endometriosis, PCOS and mental health\n"
            "  - Hormones and mood (PMS, PMDD)\n"
            "  - Women and sleep disorders\n"
            "  - Anxiety in high-achieving women\n"
            "  - Self-compassion for women who always put others first\n"
            "  - Women and panic attacks\n"
            "  - Emotional exhaustion and recovery\n"
            "  - Gaslighting and recovery\n"
            "  - Women and eating disorders (beyond stereotypes)"
        ),
        "tone": (
            "Warm, empathetic, validating — like advice from a trusted friend who truly gets it. "
            "Acknowledge the invisible load women carry without dramatising it. "
            "Practical and empowering, never patronising or preachy. "
            "Make the reader feel seen, understood, and capable."
        ),
        "preferred_categories": ["Women's Mental Health", "Anxiety & Stress", "Relationships & Family", "Sleep & Burnout", "Recovery & Sobriety"],
    },
    "neutral": {
        "label": "Gender-Neutral Mental Wellness",
        "description": (
            "Adults of any gender exploring mental wellness, recovery, and emotional health. "
            "Broad audience — people who wouldn't necessarily identify as 'mental health seekers' "
            "but are Googling their symptoms, struggles, or questions. "
            "TOPIC POOL — find untapped angles within these areas:\n"
            "  - High-functioning anxiety (looks fine on the outside, chaos inside)\n"
            "  - High-functioning depression\n"
            "  - Complex PTSD (C-PTSD) — what it is and how to recover\n"
            "  - Nervous system dysregulation and how to regulate\n"
            "  - Emotional dysregulation in adults\n"
            "  - AI and mental health (how AI companions are changing support)\n"
            "  - Therapy alternatives when you can't afford it\n"
            "  - Sobriety and social life (navigating sober in a drinking world)\n"
            "  - Early sobriety challenges\n"
            "  - Sleep and mental health (bidirectional relationship)\n"
            "  - Insomnia and anxiety loop\n"
            "  - Seasonal affective disorder (SAD)\n"
            "  - Financial anxiety and mental health\n"
            "  - Workplace mental health and burnout\n"
            "  - Burnout recovery — what actually works\n"
            "  - Loneliness epidemic — why everyone feels alone\n"
            "  - Loneliness in remote workers\n"
            "  - Social media and mental health\n"
            "  - Digital detox and mental health\n"
            "  - Grief and loss — practical support\n"
            "  - Chronic illness and mental health\n"
            "  - Panic attacks — what they are and how to stop them\n"
            "  - Anxiety management without medication\n"
            "  - Meditation alternatives for people who hate meditation\n"
            "  - Journaling and mental health\n"
            "  - Exercise and mental health\n"
            "  - Gut health and mental health\n"
            "  - Nutrition and mental health\n"
            "  - Mental health during major life transitions\n"
            "  - Imposter syndrome — practical solutions\n"
            "  - Codependency recovery\n"
            "  - Emotional intelligence — how to build it\n"
            "  - Self-compassion practices that actually work\n"
            "  - Mental health stigma — why people still don't seek help\n"
            "  - Setting boundaries — real-world guide\n"
            "  - Trauma-informed self-care\n"
            "  - Mental health apps — what works and what doesn't\n"
            "  - Gaslighting — how to recognise and recover\n"
            "  - Rumination and how to stop overthinking"
        ),
        "tone": (
            "Accessible, intelligent, and warm — speaks to anyone who is struggling but "
            "might not call it a mental health issue. Not gendered. Not clinical. "
            "Curious, practical, and grounded. Like a smart friend who has done the research "
            "so you don't have to."
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
        "Focus keyword in SEO title":         kw in title.lower(),
        "Focus keyword in meta description":  kw in meta.lower(),
        "Focus keyword in URL slug":          kw.replace(" ", "-") in slug,
        "Focus keyword in first 10% of text": kw in first,
        "Focus keyword found in content":     kw in text,
        f"Word count >= {MIN_WORD_COUNT}":    wc >= MIN_WORD_COUNT,
    }
    all_ok = True
    for label, ok in checks.items():
        icon = "OK" if ok else "FAIL"
        print(f"   [{icon}]  {label}")
        if not ok:
            all_ok = False
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
    if not history:
        return "men"
    last_audience = history[-1].get("audience", "neutral")
    current_index = AUDIENCE_ROTATION.index(last_audience) if last_audience in AUDIENCE_ROTATION else 2
    next_index    = (current_index + 1) % len(AUDIENCE_ROTATION)
    return AUDIENCE_ROTATION[next_index]


def format_history_for_prompt(history):
    if not history:
        return "None yet - this is the first post."
    return "\n".join(
        f"  {i}. [{e['date']}] \"{e['title']}\" - keyword: \"{e['primary_keyword']}\" (audience: {e.get('audience', 'unknown')})"
        for i, e in enumerate(history, 1)
    )


# -- Step 1: Research topic ---------------------------------------------------
def research_topic(history):
    audience    = get_next_audience(history)
    profile     = AUDIENCE_PROFILES[audience]
    history_txt = format_history_for_prompt(history)

    print(f"Researching best SEO topic... (Audience: {profile['label']})")

    all_cats = "\n".join(f"  - {c}" for c in CATEGORIES)
    pref_cats = "\n".join(f"  - {c}" for c in profile["preferred_categories"])

    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO strategist specialising in mental wellness content.

Your task: find the single most UNTAPPED blog topic for this week for mindcoreai.eu.
Think like a SERP analyst. Find the sweet spot: HIGH monthly search volume + VERY LOW competition + NO strong existing content from big sites.

THIS WEEK'S TARGET AUDIENCE: {profile['label']}
{profile['description']}

SELECTION CRITERIA:
  - High Google search demand (ideally 1,000+ monthly searches)
  - VERY low keyword difficulty — avoid terms dominated by WebMD, Healthline, Mayo Clinic, Psychology Today, Verywell Mind
  - Prefer long-tail, question-based, conversational keywords that authority sites ignore
  - Look for "People Also Ask" questions and "Related Searches" that have no dedicated quality content
  - Evergreen — ranks for months, not days
  - Primary keyword: 2-5 words, specific enough to rank

ALREADY PUBLISHED — DO NOT REPEAT ANY TOPIC, KEYWORD, OR CLOSE VARIATION:
{history_txt}

PREFERRED CATEGORIES FOR THIS AUDIENCE:
{pref_cats}

ALL AVAILABLE CATEGORIES:
{all_cats}

Be bold — pick the most genuinely untapped angle. Niche and specific beats broad and competitive every time.

Respond ONLY in this exact JSON — no markdown, no preamble:
{{"topic":"compelling title containing primary keyword","primary_keyword":"2-5 word keyword","secondary_keywords":["kw2","kw3","kw4","kw5"],"search_intent":"what the reader is actually looking for","meta_description":"150-160 char meta description containing primary keyword","image_prompt":"DALL-E prompt: warm soft hopeful mental wellness illustration, human and approachable, no text or letters","rationale":"specific SERP insight — why high demand and low competition","category":"exact category name from list above","audience":"{audience}"}}"""}]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    data["audience"] = audience
    print(f"   Audience : {profile['label']}")
    print(f"   Topic    : {data['topic']}")
    print(f"   Keyword  : {data['primary_keyword']}")
    print(f"   Category : {data.get('category', 'N/A')}")
    print(f"   Why      : {data['rationale']}")
    return data


# -- Step 2: Write post -------------------------------------------------------
def write_blog_post(topic_data):
    print("Writing blog post...")
    audience = topic_data.get("audience", "neutral")
    profile  = AUDIENCE_PROFILES[audience]

    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=6000,
        messages=[{"role": "user", "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full, publish-ready blog post:
  Title           : {topic_data['topic']}
  Primary Keyword : {topic_data['primary_keyword']}
  Secondary KWs   : {', '.join(topic_data['secondary_keywords'])}
  Search Intent   : {topic_data['search_intent']}
  Target Audience : {profile['label']}

TONE & VOICE:
  {profile['tone']}

YOAST SEO REQUIREMENTS:
  1. Primary keyword in the H1 title
  2. Primary keyword in the very first sentence
  3. Primary keyword in at least 3 H2 subheadings
  4. Keyword density between 0.8% and 2%
  5. Minimum 1,200 words of readable content

WRITING REQUIREMENTS:
  - Structure: H1 -> intro (2-3 para) -> 5-7 H2 sections (150-200 words each) -> conclusion + CTA
  - Include at least one list
  - Real, actionable, specific advice — zero generic platitudes
  - Final section: natural CTA to download MindCore AI as their 24/7 AI mental wellness companion

FORMAT:
  - Clean WordPress HTML only: h1 h2 h3 p ul li strong em tags
  - No html head body style script tags
  - After all HTML on its own line: EXCERPT: [2-3 sentence hook containing primary keyword]"""}]
    )

    content = response.content[0].text
    wc      = count_words_in_html(content)
    print(f"   Written ({wc} words)")
    if wc < MIN_WORD_COUNT:
        print(f"   Only {wc} words - expanding...")
        content = expand_blog_post(content, topic_data, wc)
    return content


def expand_blog_post(content, topic_data, current_words):
    needed   = MIN_WORD_COUNT - current_words
    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=3000,
        messages=[{"role": "user", "content": f"""This blog post is {current_words} words but needs {MIN_WORD_COUNT}.
Add ~{needed} words by expanding sections or adding 2 new H2 sections.
Same tone, HTML format, include keyword: "{topic_data['primary_keyword']}".
Return the COMPLETE updated post including EXCERPT at the end.

{content}"""}]
    )
    expanded = response.content[0].text
    print(f"   Expanded to {count_words_in_html(expanded)} words")
    return expanded


# -- Step 3: Illustration -----------------------------------------------------
def generate_illustration(image_prompt):
    print("Generating DALL-E illustration...")
    resp = openai_client.images.generate(
        model="dall-e-3",
        prompt=f"{image_prompt} Style: soft watercolour, warm gentle colours, hopeful and human, mental wellness blog. No text or letters in the image.",
        size="1792x1024", quality="standard", n=1,
    )
    img = requests.get(resp.data[0].url, timeout=30).content
    print("   Illustration generated")
    return img


def upload_image_to_wordpress(image_data):
    print("Uploading illustration...")
    filename = f"mindcore-blog-{datetime.now().strftime('%Y%m%d')}.png"
    headers  = get_wp_auth()
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    headers["Content-Type"]        = "image/png"
    resp = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=image_data, timeout=60)
    if resp.status_code == 201:
        mid = resp.json()["id"]
        print(f"   Image uploaded (ID: {mid})")
        return mid
    print(f"   Upload failed ({resp.status_code})")
    return None


# -- Step 4: Resolve category ID ----------------------------------------------
def resolve_category_id(category_name):
    if CATEGORY_IDS.get(category_name) is not None:
        cat_id = CATEGORY_IDS[category_name]
        print(f"   Category  : {category_name} (ID: {cat_id})")
        return cat_id

    print(f"   Fetching category ID for: {category_name}")
    auth = get_wp_auth()
    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?per_page=100&search={requests.utils.quote(category_name)}",
        headers=auth, timeout=15,
    )
    if resp.status_code == 200:
        for c in resp.json():
            name_clean = c["name"].replace("&amp;", "&").replace("&#039;", "'")
            if name_clean.lower() == category_name.lower():
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

    print(f"   Could not resolve category: {category_name} - posting uncategorised")
    return None


# -- Step 5: Publish ----------------------------------------------------------
def publish_to_wordpress(topic_data, content, image_id=None):
    print("Publishing to WordPress...")

    excerpt = ""
    if "EXCERPT:" in content:
        bits    = content.split("EXCERPT:")
        content = bits[0].strip()
        excerpt = bits[1].strip() if len(bits) > 1 else ""

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

    print("   Waiting 60s before publishing to avoid rate limit...")
    time.sleep(60)

    for attempt in range(4):
        resp = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=auth, json=payload, timeout=30)
        if resp.status_code == 201:
            break
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 30 * (attempt + 1)))
            print(f"   Rate limited - waiting {wait}s (attempt {attempt + 1}/4)...")
            time.sleep(wait)
            continue
        raise RuntimeError(f"WordPress publish failed ({resp.status_code}): {resp.text}")
    else:
        raise RuntimeError("WordPress publish failed after 4 attempts with 429")

    post    = resp.json()
    post_id = post["id"]
    print(f"   Published -> {post.get('link', 'N/A')}")

    if image_id:
        time.sleep(5)
        upd = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            headers=auth, json={"featured_media": image_id}, timeout=30,
        )
        if upd.status_code == 200:
            print("   Featured image attached")
        else:
            print(f"   Image attach failed: {upd.text}")

    return post


# -- Step 6: Save history -----------------------------------------------------
def update_history_on_github(history, new_entry):
    print("Saving post to history...")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("   Skipping - GITHUB_TOKEN not set")
        return
    api_url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    hdrs    = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_r   = requests.get(api_url, headers=hdrs, timeout=15)
    sha     = get_r.json().get("sha") if get_r.status_code == 200 else None
    history.append(new_entry)
    encoded = base64.b64encode(json.dumps(history, indent=2).encode()).decode()
    payload = {"message": f"blog: log post - {new_entry['title'][:60]}", "content": encoded}
    if sha:
        payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    if put.status_code in (200, 201):
        print(f"   History committed ({len(history)} posts total)")
    else:
        print(f"   History commit failed: {put.text}")


# -- Main ---------------------------------------------------------------------
def main():
    print("\n== MindCore AI - Weekly Blog Automation Pipeline ==")

    history    = load_history()
    print(f"History loaded - {len(history)} posts published so far")

    topic_data = research_topic(history)
    content    = write_blog_post(topic_data)

    try:
        image_data = generate_illustration(topic_data["image_prompt"])
        image_id   = upload_image_to_wordpress(image_data)
    except Exception as exc:
        print(f"   Illustration failed: {exc}")
        image_id = None

    post = publish_to_wordpress(topic_data, content, image_id)

    update_history_on_github(history, {
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "title":           topic_data["topic"],
        "primary_keyword": topic_data["primary_keyword"],
        "category":        topic_data.get("category", ""),
        "audience":        topic_data.get("audience", "neutral"),
        "slug":            keyword_to_slug(topic_data["primary_keyword"]),
        "wp_post_id":      post.get("id"),
    })

    print("\nPipeline complete! Post is live on mindcoreai.eu")
    print("=" * 50)


if __name__ == "__main__":
    main()
