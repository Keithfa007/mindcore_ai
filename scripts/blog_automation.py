import os
import json
import base64
import re
import time
import html
import requests
from anthropic import Anthropic
from openai import OpenAI
from datetime import datetime

# ── Clients ──────────────────────────────────────────────────
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
openai_client    = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

HISTORY_FILE   = "scripts/blog_history.json"
MIN_WORD_COUNT = 1200

CATEGORIES = [
    "Anxiety & Stress",
    "Recovery & Sobriety",
    "Men's Mental Health",
    "AI & Wellness",
    "Sleep & Burnout",
    "Relationships & Family",
]


# ── Helpers ──────────────────────────────────────────────────
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
    print("\n\U0001f4ca  SEO Validation Report:")
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
        f"Word count >= {MIN_WORD_COUNT}":     wc >= MIN_WORD_COUNT,
    }
    all_ok = True
    for label, ok in checks.items():
        print(f"   {'\u2705' if ok else '\u274c'}  {label}")
        if not ok:
            all_ok = False
    print(f"   \U0001f4dd  Word count : {wc}")
    print(f"   \U0001f511  KW density : {dens:.2f}% ({kw_n} occurrences)")
    print(f"   \U0001f517  Slug       : {slug}")
    print("   \U0001f389  All SEO checks passed!" if all_ok else
          "   \u26a0\ufe0f   Some checks failed \u2014 saved as draft for review.")


def wp_post(endpoint, headers, payload, retries=3, base_delay=15):
    """POST to WordPress with automatic retry on 429 rate limit."""
    url = f"{WP_URL}/wp-json/wp/v2/{endpoint}"
    for attempt in range(retries):
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", base_delay * (attempt + 1)))
            print(f"   \u23f3  Rate limited \u2014 waiting {wait}s (attempt {attempt + 1}/{retries})...")
            time.sleep(wait)
            continue
        return resp
    raise RuntimeError(f"WordPress {endpoint} failed after {retries} retries with 429")


# ── History ──────────────────────────────────────────────────
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def format_history_for_prompt(history):
    if not history:
        return "None yet \u2014 this is the first post."
    return "\n".join(
        f"  {i}. [{e['date']}] \"{e['title']}\" \u2014 keyword: \"{e['primary_keyword']}\""
        for i, e in enumerate(history, 1)
    )


# ── Step 1: Research topic ──────────────────────────────────────────────
def research_topic(history):
    print("\U0001f50d  Researching best SEO topic for this week...")
    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO strategist specialising in mental wellness content.

Your task: identify the single best blog topic for this week for mindcoreai.eu.
This is an AI mental health companion app targeting:
  \u2022 Men 35+ (primary \u2014 massively underserved)
  \u2022 People in addiction recovery seeking mental wellness support
  \u2022 Adults exploring AI-powered mental health tools

Selection criteria:
  \u2022 High Google search demand, VERY low keyword competition
  \u2022 Mirrors real \"People Also Ask\" or \"Related Searches\" questions on Google
  \u2022 Evergreen \u2014 ranks over months, not just days
  \u2022 Primary keyword must be 2-5 words

CRITICAL \u2014 ALREADY PUBLISHED (DO NOT REPEAT):
{format_history_for_prompt(history)}

Available categories:
{chr(10).join(f'  - {c}' for c in CATEGORIES)}

Respond ONLY in this exact JSON \u2014 no markdown, no preamble:
{{"topic":"title containing keyword","primary_keyword":"2-5 word keyword","secondary_keywords":["kw2","kw3","kw4","kw5"],"search_intent":"intent","meta_description":"150-160 char description with keyword","image_prompt":"DALL-E prompt: warm soft hopeful mental wellness illustration, human, approachable, no text","rationale":"why high demand low competition","category":"exact category name"}}"""}]
    )
    raw  = response.content[0].text.replace("```json","").replace("```","").strip()
    data = json.loads(raw)
    print(f"   \u2705  Topic    : {data['topic']}")
    print(f"   \U0001f511  KW       : {data['primary_keyword']}")
    print(f"   \U0001f4c2  Category : {data.get('category','N/A')}")
    return data


# ── Step 2: Write post ────────────────────────────────────────────────
def write_blog_post(topic_data):
    print("\u270d\ufe0f   Writing blog post...")
    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=6000,
        messages=[{"role": "user", "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full blog post:
  Title           : {topic_data['topic']}
  Primary Keyword : {topic_data['primary_keyword']}
  Secondary KWs   : {', '.join(topic_data['secondary_keywords'])}
  Search Intent   : {topic_data['search_intent']}

YOAST SEO REQUIREMENTS:
  1. Primary keyword in the H1 title
  2. Primary keyword in the very first sentence
  3. Primary keyword in at least 3 H2 subheadings
  4. Keyword density between 0.8% and 2%
  5. Minimum 1,200 words of readable content

WRITING REQUIREMENTS:
  \u2022 Warm, honest, human tone \u2014 like advice from a friend who has been there
  \u2022 Audience: men 35+, people in recovery, adults open to AI wellness
  \u2022 Structure: H1 \u2192 intro (2-3 para) \u2192 5-7 H2 sections (150-200 words each) \u2192 conclusion + CTA
  \u2022 Include at least one <ul> list
  \u2022 Final section: natural CTA to download MindCore AI

FORMAT:
  \u2022 Clean WordPress HTML only: <h1><h2><h3><p><ul><li><strong><em>
  \u2022 No <html><head><body><style><script>
  \u2022 After all HTML on its own line: EXCERPT: [2-3 sentence hook with keyword]"""}]
    )
    content = response.content[0].text
    wc      = count_words_in_html(content)
    print(f"   \u2705  Written ({wc} words)")
    if wc < MIN_WORD_COUNT:
        print(f"   \u26a0\ufe0f   Only {wc} words \u2014 expanding...")
        content = expand_blog_post(content, topic_data, wc)
    return content


def expand_blog_post(content, topic_data, current_words):
    needed   = MIN_WORD_COUNT - current_words
    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=3000,
        messages=[{"role": "user", "content": f"""This blog post is {current_words} words but needs {MIN_WORD_COUNT}.
Add ~{needed} words by expanding sections or adding 2 new H2 sections.
Same tone, HTML format, include keyword: \"{topic_data['primary_keyword']}\".
Return the COMPLETE updated post including EXCERPT at the end.\n\n{content}"""}]
    )
    expanded = response.content[0].text
    print(f"   \u2705  Expanded to {count_words_in_html(expanded)} words")
    return expanded


# ── Step 3: Illustration ──────────────────────────────────────────────
def generate_illustration(image_prompt):
    print("\U0001f3a8  Generating DALL-E illustration...")
    resp = openai_client.images.generate(
        model="dall-e-3",
        prompt=f"{image_prompt} Style: soft watercolour, warm gentle colours, hopeful and human, mental wellness blog. No text or letters.",
        size="1792x1024", quality="standard", n=1,
    )
    img = requests.get(resp.data[0].url, timeout=30).content
    print("   \u2705  Illustration generated")
    return img


def upload_image_to_wordpress(image_data):
    print("\U0001f4e4  Uploading illustration...")
    filename = f"mindcore-blog-{datetime.now().strftime('%Y%m%d')}.png"
    headers  = get_wp_auth()
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    headers["Content-Type"]        = "image/png"
    resp = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=image_data, timeout=60)
    if resp.status_code == 201:
        mid = resp.json()["id"]
        print(f"   \u2705  Image uploaded (ID: {mid})")
        return mid
    print(f"   \u26a0\ufe0f   Upload failed ({resp.status_code})")
    return None


# ── Step 4: Categories ──────────────────────────────────────────────
def get_or_create_categories():
    """Build a name->id map for all categories.
    Decode HTML entities from WP response (& comes back as &amp;).
    If a category already exists, grab its ID from the error response."""
    print("\U0001f4c2  Setting up categories...")
    auth = get_wp_auth()

    # Fetch existing categories and decode HTML entities in names
    resp     = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?per_page=100", headers=auth, timeout=15)
    existing = {}
    if resp.status_code == 200:
        for c in resp.json():
            decoded_name          = html.unescape(c["name"])  # &amp; -> &
            existing[decoded_name] = c["id"]

    print(f"   Found {len(existing)} existing categories: {list(existing.keys())}")

    category_map = {}
    for name in CATEGORIES:
        if name in existing:
            category_map[name] = existing[name]
            print(f"   \u2705  Using existing: {name} (ID: {existing[name]})")
            continue

        # Try to create
        create = requests.post(
            f"{WP_URL}/wp-json/wp/v2/categories",
            headers={**auth, "Content-Type": "application/json"},
            json={"name": name}, timeout=15,
        )
        if create.status_code == 201:
            cat_id = create.json()["id"]
            category_map[name] = cat_id
            print(f"   \u2705  Created: {name} (ID: {cat_id})")
        elif create.status_code == 400:
            err = create.json()
            # Extract existing term ID from error response
            term_id = (err.get("data", {}).get("term_id")
                       or (err.get("additional_data", [None])[0]))
            if term_id:
                category_map[name] = int(term_id)
                print(f"   \u2705  Already exists: {name} (ID: {term_id})")
            else:
                print(f"   \u26a0\ufe0f   Could not resolve: {name} | {err}")
        else:
            print(f"   \u26a0\ufe0f   Failed ({create.status_code}): {name}")

    print(f"   \u2705  {len(category_map)}/{len(CATEGORIES)} categories ready")
    return category_map


# ── Step 5: Publish ─────────────────────────────────────────────────
def publish_to_wordpress(topic_data, content, image_id=None, category_map=None):
    print("\U0001f4f0  Publishing draft to WordPress...")

    excerpt = ""
    if "EXCERPT:" in content:
        parts, content = content.split("EXCERPT:", 1)[0], content.split("EXCERPT:", 1)
        content, excerpt = parts.strip(), content[1].strip() if len(content) > 1 else content[0].strip()
        # Simpler split
    if "EXCERPT:" in topic_data.get("_raw_content", "") or "EXCERPT:" in content:
        bits    = content.split("EXCERPT:")
        content = bits[0].strip()
        excerpt = bits[1].strip() if len(bits) > 1 else ""

    slug         = keyword_to_slug(topic_data["primary_keyword"])
    category_ids = []
    if category_map:
        chosen = topic_data.get("category", "")
        if chosen in category_map:
            category_ids = [category_map[chosen]]
            print(f"   \U0001f4c2  Category  : {chosen} (ID: {category_ids[0]})")
        else:
            print(f"   \u26a0\ufe0f   Category '{chosen}' not resolved \u2014 posting uncategorised")

    validate_seo(content, topic_data["topic"], topic_data["meta_description"],
                 topic_data["primary_keyword"], slug)

    auth = get_wp_auth()
    auth["Content-Type"] = "application/json"

    payload = {
        "title":      topic_data["topic"],
        "content":    content,
        "excerpt":    excerpt,
        "slug":       slug,
        "status":     "draft",
        "categories": category_ids,
        "meta": {
            "_yoast_wpseo_metadesc": topic_data["meta_description"],
            "_yoast_wpseo_focuskw":  topic_data["primary_keyword"],
            "_yoast_wpseo_title":    topic_data["topic"],
        },
    }

    print("   \u23f3  Waiting 10s before publish to avoid rate limiting...")
    time.sleep(10)

    resp = wp_post("posts", auth, payload)
    if resp.status_code != 201:
        raise RuntimeError(f"WordPress publish failed ({resp.status_code}): {resp.text}")

    post    = resp.json()
    post_id = post["id"]
    print(f"   \u2705  Draft saved  \u2192  {post.get('link', 'N/A')}")

    if image_id:
        time.sleep(3)
        upd = wp_post(f"posts/{post_id}", auth, {"featured_media": image_id})
        if upd.status_code == 200:
            print("   \u2705  Featured image attached")
        else:
            print(f"   \u26a0\ufe0f   Image attach failed: {upd.text}")

    return post


# ── Step 6: Save history ─────────────────────────────────────────────
def update_history_on_github(history, new_entry):
    print("\U0001f4dd  Saving post to history...")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("   \u26a0\ufe0f   Skipping \u2014 GITHUB_TOKEN not set")
        return
    api_url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    hdrs    = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_r   = requests.get(api_url, headers=hdrs, timeout=15)
    sha     = get_r.json().get("sha") if get_r.status_code == 200 else None
    history.append(new_entry)
    encoded = base64.b64encode(json.dumps(history, indent=2).encode()).decode()
    payload = {"message": f"blog: log post \u2014 {new_entry['title'][:60]}", "content": encoded}
    if sha:
        payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    if put.status_code in (200, 201):
        print(f"   \u2705  History committed ({len(history)} posts total)")
    else:
        print(f"   \u26a0\ufe0f   History commit failed: {put.text}")


# ── Main ──────────────────────────────────────────────────
def main():
    print("\n\U0001f680  MindCore AI \u2014 Weekly Blog Automation Pipeline")
    print("=" * 52)

    history    = load_history()
    print(f"\U0001f4cb  History loaded \u2014 {len(history)} posts published so far")

    topic_data = research_topic(history)
    content    = write_blog_post(topic_data)

    try:
        image_data = generate_illustration(topic_data["image_prompt"])
        image_id   = upload_image_to_wordpress(image_data)
    except Exception as exc:
        print(f"   \u26a0\ufe0f   Illustration failed: {exc}")
        image_id = None

    try:
        category_map = get_or_create_categories()
    except Exception as exc:
        print(f"   \u26a0\ufe0f   Category setup failed: {exc}")
        category_map = None

    post = publish_to_wordpress(topic_data, content, image_id, category_map)

    update_history_on_github(history, {
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "title":           topic_data["topic"],
        "primary_keyword": topic_data["primary_keyword"],
        "category":        topic_data.get("category", ""),
        "slug":            keyword_to_slug(topic_data["primary_keyword"]),
        "wp_post_id":      post.get("id"),
    })

    print("\n\U0001f389  Pipeline complete! Check WordPress \u203a Posts \u203a Drafts.")
    print("=" * 52)


if __name__ == "__main__":
    main()
