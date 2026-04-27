import os
import json
import base64
import re
import time
import requests
from anthropic import Anthropic
from openai import OpenAI
from datetime import datetime

# ── Clients ───────────────────────────────────────────────────────────────────
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
openai_client    = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

HISTORY_FILE   = "scripts/blog_history.json"
MIN_WORD_COUNT = 1200

# ── Categories ─────────────────────────────────────────────────────────────────
CATEGORIES = [
    "Anxiety & Stress",
    "Recovery & Sobriety",
    "Men's Mental Health",
    "AI & Wellness",
    "Sleep & Burnout",
    "Relationships & Family",
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_wp_auth():
    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}"}


def keyword_to_slug(keyword):
    slug = keyword.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def count_words_in_html(html):
    clean = re.sub(r"<[^>]+>", " ", html)
    return len(clean.split())


def validate_seo(content, title, meta, primary_keyword, slug):
    print("\n📊  SEO Validation Report:")
    kw    = primary_keyword.lower()
    text  = re.sub(r"<[^>]+>", " ", content).lower()
    words = text.split()
    word_count  = len(words)
    first_10pct = " ".join(words[:max(1, word_count // 10)])
    kw_count    = text.count(kw)
    density     = (kw_count / word_count * 100) if word_count > 0 else 0

    checks = {
        "Focus keyword in SEO title":         kw in title.lower(),
        "Focus keyword in meta description":  kw in meta.lower(),
        "Focus keyword in URL slug":          kw.replace(" ", "-") in slug,
        "Focus keyword in first 10% of text": kw in first_10pct,
        "Focus keyword found in content":     kw in text,
        f"Word count >= {MIN_WORD_COUNT}":     word_count >= MIN_WORD_COUNT,
    }

    all_pass = True
    for label, passed in checks.items():
        icon = "✅" if passed else "❌"
        print(f"   {icon}  {label}")
        if not passed:
            all_pass = False

    print(f"   📝  Word count : {word_count}")
    print(f"   🔑  KW density : {density:.2f}% ({kw_count} occurrences)")
    print(f"   🔗  Slug       : {slug}")
    if all_pass:
        print("   🎉  All SEO checks passed!")
    else:
        print("   ⚠️   Some checks failed — post saved as draft for review.")
    return word_count


# ── History Management ─────────────────────────────────────────────────────────
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def format_history_for_prompt(history):
    if not history:
        return "None yet — this is the first post."
    return "\n".join(
        f"  {i}. [{e['date']}] \"{e['title']}\" — keyword: \"{e['primary_keyword']}\""
        for i, e in enumerate(history, 1)
    )


# ── Step 1 · SEO Research & Topic Selection ────────────────────────────────────
def research_topic(history):
    print("🔍  Researching best SEO topic for this week...")
    history_text = format_history_for_prompt(history)

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are an expert SEO strategist specialising in mental wellness content.

Your task: identify the single best blog topic for this week for mindcoreai.eu.
This is an AI mental health companion app targeting:
  • Men 35+ (primary — massively underserved)
  • People in addiction recovery seeking mental wellness support
  • Adults exploring AI-powered mental health tools

Selection criteria:
  • High Google search demand, VERY low keyword competition
  • Mirrors real "People Also Ask" or "Related Searches" questions on Google
  • Evergreen — ranks over months, not just days
  • Primary keyword must be 2-5 words, specific enough to rank

CRITICAL — ALREADY PUBLISHED (DO NOT REPEAT):
{history_text}

Available categories (pick the most relevant):
{chr(10).join(f'  - {c}' for c in CATEGORIES)}

Respond ONLY in this exact JSON format — no markdown, no preamble:
{{
  "topic": "Full blog post title containing the primary keyword",
  "primary_keyword": "exact low-competition keyword (2-5 words)",
  "secondary_keywords": ["kw2", "kw3", "kw4", "kw5"],
  "search_intent": "what the reader is looking for",
  "meta_description": "150-160 char meta description containing the primary keyword",
  "image_prompt": "DALL-E prompt: warm, soft, hopeful mental wellness illustration, human, approachable, no text",
  "rationale": "Why high demand and low competition",
  "category": "exact category name from list above"
}}"""
        }]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    print(f"   ✅  Topic    : {data['topic']}")
    print(f"   🔑  KW       : {data['primary_keyword']}")
    print(f"   📂  Category : {data.get('category', 'N/A')}")
    print(f"   💡  Why      : {data['rationale']}")
    return data


# ── Step 2 · Write the Blog Post ───────────────────────────────────────────────
def write_blog_post(topic_data):
    print("✍️   Writing blog post...")

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=6000,
        messages=[{
            "role": "user",
            "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full, publish-ready blog post:

  Title           : {topic_data['topic']}
  Primary Keyword : {topic_data['primary_keyword']}
  Secondary KWs   : {', '.join(topic_data['secondary_keywords'])}
  Search Intent   : {topic_data['search_intent']}
  Category        : {topic_data.get('category', '')}

YOAST SEO REQUIREMENTS (all must be met):
  1. Primary keyword in the H1 title
  2. Primary keyword in the very first sentence
  3. Primary keyword in at least 3 H2 subheadings
  4. Keyword density between 0.8% and 2%
  5. Minimum 1,200 words of readable content (not counting HTML tags)

WRITING REQUIREMENTS:
  • Tone: warm, honest, human — like advice from a friend who has been there
  • Audience: men 35+, people in recovery, adults open to AI wellness tools
  • Structure: H1 → intro (2-3 para) → 5-7 H2 sections (150-200 words each) → conclusion + CTA
  • Include at least one <ul> list
  • Real, actionable advice — zero fluff
  • Final section: natural CTA to download MindCore AI

FORMAT:
  • Clean WordPress-ready HTML only
  • Tags: <h1> <h2> <h3> <p> <ul> <li> <strong> <em>
  • No <html> <head> <body> <style> <script> tags
  • After all HTML, on its own line:
    EXCERPT: [2-3 sentence hook containing the primary keyword]"""
        }]
    )

    content    = response.content[0].text
    word_count = count_words_in_html(content)
    print(f"   ✅  Written ({word_count} words)")

    if word_count < MIN_WORD_COUNT:
        print(f"   ⚠️   Only {word_count} words — requesting expansion...")
        content = expand_blog_post(content, topic_data, word_count)

    return content


def expand_blog_post(content, topic_data, current_words):
    needed   = MIN_WORD_COUNT - current_words
    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"""This blog post is {current_words} words but needs at least {MIN_WORD_COUNT}.
Add ~{needed} words by expanding sections or adding 2 new H2 sections.
Keep same tone, HTML format, include keyword: "{topic_data['primary_keyword']}".
Return the COMPLETE updated post including EXCERPT at the end.

{content}"""
        }]
    )
    expanded   = response.content[0].text
    word_count = count_words_in_html(expanded)
    print(f"   ✅  Expanded to {word_count} words")
    return expanded


# ── Step 3 · Generate Illustration ────────────────────────────────────────────
def generate_illustration(image_prompt):
    print("🎨  Generating DALL-E illustration...")
    full_prompt = (
        f"{image_prompt} "
        "Style: soft watercolour illustration, warm gentle colours, "
        "hopeful and human, suitable for a mental wellness blog. "
        "No text, no words, no letters in the image."
    )
    response  = openai_client.images.generate(
        model="dall-e-3", prompt=full_prompt,
        size="1792x1024", quality="standard", n=1,
    )
    img_bytes = requests.get(response.data[0].url, timeout=30).content
    print("   ✅  Illustration generated")
    return img_bytes


# ── Step 4 · Upload Image to WordPress ────────────────────────────────────────
def upload_image_to_wordpress(image_data, title):
    print("📤  Uploading illustration to WordPress...")
    filename = f"mindcore-blog-{datetime.now().strftime('%Y%m%d')}.png"
    headers  = get_wp_auth()
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    headers["Content-Type"]        = "image/png"
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        headers=headers, data=image_data, timeout=60,
    )
    if response.status_code == 201:
        media_id = response.json()["id"]
        print(f"   ✅  Image uploaded (ID: {media_id})")
        return media_id
    print(f"   ⚠️   Image upload failed ({response.status_code}): {response.text}")
    return None


# ── Step 5 · Category Management ──────────────────────────────────────────────
def get_or_create_categories():
    """Fetch existing WP categories and create any missing ones.
    If a category already exists (term_exists error), extract its ID from the error response."""
    print("📂  Setting up categories...")
    headers = get_wp_auth()

    # Fetch all existing categories first
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?per_page=100",
        headers=headers, timeout=15,
    )
    existing = {}
    if response.status_code == 200:
        for c in response.json():
            existing[c["name"]] = c["id"]

    category_map = {}
    for name in CATEGORIES:
        if name in existing:
            # Already exists — use the existing ID
            category_map[name] = existing[name]
            print(f"   ✅  Found category: {name} (ID: {existing[name]})")
        else:
            # Try to create it
            create = requests.post(
                f"{WP_URL}/wp-json/wp/v2/categories",
                headers={**headers, "Content-Type": "application/json"},
                json={"name": name}, timeout=15,
            )
            if create.status_code == 201:
                cat_id = create.json()["id"]
                category_map[name] = cat_id
                print(f"   ✅  Created category: {name} (ID: {cat_id})")
            elif create.status_code == 400:
                # term_exists — extract the ID from the error data
                err = create.json()
                term_id = None
                if "data" in err and "term_id" in err["data"]:
                    term_id = err["data"]["term_id"]
                elif "additional_data" in err and len(err["additional_data"]) > 0:
                    term_id = err["additional_data"][0]
                if term_id:
                    category_map[name] = term_id
                    print(f"   ✅  Category exists: {name} (ID: {term_id})")
                else:
                    print(f"   ⚠️   Could not resolve category '{name}': {create.text}")
            else:
                print(f"   ⚠️   Could not create '{name}' ({create.status_code}): {create.text}")

    print(f"   ✅  {len(category_map)} categories ready")
    return category_map


# ── Step 6 · Publish to WordPress as Draft ────────────────────────────────────
def publish_to_wordpress(topic_data, content, image_id=None, category_map=None):
    print("📰  Publishing draft to WordPress...")

    excerpt = ""
    if "EXCERPT:" in content:
        parts   = content.split("EXCERPT:")
        content = parts[0].strip()
        excerpt = parts[1].strip()

    slug = keyword_to_slug(topic_data["primary_keyword"])

    category_ids = []
    if category_map:
        chosen = topic_data.get("category", "")
        if chosen in category_map:
            category_ids = [category_map[chosen]]
            print(f"   📂  Category  : {chosen}")
        else:
            print(f"   ⚠️   Category '{chosen}' not in map — posting uncategorised")

    validate_seo(
        content,
        topic_data["topic"],
        topic_data["meta_description"],
        topic_data["primary_keyword"],
        slug,
    )

    headers = get_wp_auth()
    headers["Content-Type"] = "application/json"

    post_payload = {
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

    # Small delay before publishing to avoid 429 rate limit
    print("   ⏳  Waiting 3s before publish to avoid rate limit...")
    time.sleep(3)

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        headers=headers, json=post_payload, timeout=30,
    )

    if response.status_code == 429:
        # Rate limited — wait and retry once
        retry_after = int(response.headers.get("Retry-After", 10))
        print(f"   ⏳  Rate limited — retrying after {retry_after}s...")
        time.sleep(retry_after)
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=headers, json=post_payload, timeout=30,
        )

    if response.status_code != 201:
        raise RuntimeError(
            f"WordPress publish failed ({response.status_code}): {response.text}"
        )

    post    = response.json()
    post_id = post["id"]
    print(f"   ✅  Draft saved  →  {post.get('link', 'N/A')}")

    # Attach featured image separately (Hostinger theme bug workaround)
    if image_id:
        time.sleep(2)
        upd = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            json={"featured_media": image_id},
            timeout=30,
        )
        if upd.status_code == 200:
            print("   ✅  Featured image attached")
        else:
            print(f"   ⚠️   Image attach failed (post still saved): {upd.text}")

    return post


# ── Step 7 · Update History File via GitHub API ───────────────────────────────
def update_history_on_github(history, new_entry):
    print("📝  Saving post to history...")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("   ⚠️   GITHUB_TOKEN or GITHUB_REPOSITORY not set — skipping")
        return

    api_url  = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    gh_hdrs  = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_resp = requests.get(api_url, headers=gh_hdrs, timeout=15)
    sha      = get_resp.json().get("sha") if get_resp.status_code == 200 else None

    history.append(new_entry)
    content = base64.b64encode(json.dumps(history, indent=2).encode()).decode()
    payload = {"message": f"blog: log post — {new_entry['title'][:60]}", "content": content}
    if sha:
        payload["sha"] = sha

    put = requests.put(api_url, headers=gh_hdrs, json=payload, timeout=15)
    if put.status_code in (200, 201):
        print(f"   ✅  History committed ({len(history)} posts total)")
    else:
        print(f"   ⚠️   History commit failed: {put.text}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n🚀  MindCore AI — Weekly Blog Automation Pipeline")
    print("=" * 52)

    history = load_history()
    print(f"📋  History loaded — {len(history)} posts published so far")

    topic_data = research_topic(history)
    content    = write_blog_post(topic_data)

    try:
        image_data = generate_illustration(topic_data["image_prompt"])
        image_id   = upload_image_to_wordpress(image_data, topic_data["topic"])
    except Exception as exc:
        print(f"   ⚠️   Illustration failed: {exc}\n   Continuing without image.")
        image_id = None

    try:
        category_map = get_or_create_categories()
    except Exception as exc:
        print(f"   ⚠️   Category setup failed: {exc}\n   Continuing without categories.")
        category_map = None

    post = publish_to_wordpress(topic_data, content, image_id, category_map)

    new_entry = {
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "title":           topic_data["topic"],
        "primary_keyword": topic_data["primary_keyword"],
        "category":        topic_data.get("category", ""),
        "slug":            keyword_to_slug(topic_data["primary_keyword"]),
        "wp_post_id":      post.get("id"),
    }
    update_history_on_github(history, new_entry)

    print("\n🎉  Pipeline complete! Check WordPress › Posts › Drafts.")
    print("=" * 52)


if __name__ == "__main__":
    main()
