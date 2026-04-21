import os
import json
import base64
import requests
from anthropic import Anthropic
from openai import OpenAI
from datetime import datetime

# ── Clients ────────────────────────────────────────────────────────────────────
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
openai_client    = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]
SERP_API_KEY    = os.environ.get("SERP_API_KEY", "")
SERP_API_URL    = "https://serpapi.com/search"

HISTORY_FILE = "scripts/blog_history.json"

# ── Categories ─────────────────────────────────────────────────────────────────
CATEGORIES = [
    "Anxiety & Stress",
    "Recovery & Sobriety",
    "Men's Mental Health",
    "AI & Wellness",
    "Sleep & Burnout",
    "Relationships & Family",
]

# Seed queries per category -- used for SERP research
CATEGORY_SEEDS = {
    "Anxiety & Stress":      "anxiety relief for men",
    "Recovery & Sobriety":   "sobriety mental health men",
    "Men's Mental Health":   "men mental health struggles",
    "AI & Wellness":         "AI mental health coach",
    "Sleep & Burnout":       "sleep problems burnout men over 35",
    "Relationships & Family": "men relationships mental health",
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_wp_auth():
    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}"}


# ── SERP Research ──────────────────────────────────────────────────────────────
def fetch_serp_data(category_name):
    """
    Fetch real Google search data for a category using SerpAPI.
    Returns a structured dict with People Also Ask questions and related searches.
    Falls back to empty dict if SERP_API_KEY not set or request fails.
    """
    if not SERP_API_KEY:
        print("   ⚠️   SERP_API_KEY not set -- skipping SERP research")
        return {}

    seed = CATEGORY_SEEDS.get(category_name, category_name)
    print(f"   🔍  Fetching SERP data for: '{seed}'")

    try:
        params = {
            "engine":  "google",
            "q":       seed,
            "api_key": SERP_API_KEY,
            "num":     10,
            "hl":      "en",
            "gl":      "us",
        }
        resp = requests.get(SERP_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Extract People Also Ask questions
        paa = [
            q.get("question", "")
            for q in data.get("related_questions", [])[:8]
            if q.get("question")
        ]

        # Extract related searches
        related = [
            r.get("query", "")
            for r in data.get("related_searches", [])[:8]
            if r.get("query")
        ]

        # Extract top organic titles for competitive analysis
        organic_titles = [
            r.get("title", "")
            for r in data.get("organic_results", [])[:5]
            if r.get("title")
        ]

        print(f"   ✅  SERP: {len(paa)} PAA questions, {len(related)} related searches")
        return {
            "seed_query":       seed,
            "people_also_ask":  paa,
            "related_searches": related,
            "organic_titles":   organic_titles,
        }

    except Exception as exc:
        print(f"   ⚠️   SERP fetch failed ({exc}) -- continuing without SERP data")
        return {}


def format_serp_for_prompt(serp_data):
    """Format SERP data into a readable block for Claude prompts."""
    if not serp_data:
        return "No SERP data available -- use your own keyword research knowledge."

    lines = [f"Seed query: \"{serp_data.get('seed_query', '')}\"", ""]

    paa = serp_data.get("people_also_ask", [])
    if paa:
        lines.append("PEOPLE ALSO ASK (real Google questions):")
        for q in paa:
            lines.append(f"  - {q}")
        lines.append("")

    related = serp_data.get("related_searches", [])
    if related:
        lines.append("RELATED SEARCHES (real Google queries):")
        for r in related:
            lines.append(f"  - {r}")
        lines.append("")

    organic = serp_data.get("organic_titles", [])
    if organic:
        lines.append("TOP RANKING ARTICLES (competition to beat):")
        for t in organic:
            lines.append(f"  - {t}")

    return "\n".join(lines)


# ── History Management ─────────────────────────────────────────────────────────
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def format_history_for_prompt(history):
    if not history:
        return "None yet -- this is the first post."
    lines = []
    for i, entry in enumerate(history, 1):
        lines.append(
            f"  {i}. [{entry['date']}] \"{entry['title']}\" "
            f"-- keyword: \"{entry['primary_keyword']}\""
        )
    return "\n".join(lines)


# ── Step 1 · SEO Research & Topic Selection ────────────────────────────────────
def research_topic(history):
    print("\n[1/7] Researching best SEO topic...")

    history_text = format_history_for_prompt(history)

    # Pick the category with the best rotation (simple round-robin from history)
    used_cats = [e.get("category", "") for e in history]
    chosen_category = None
    for cat in CATEGORIES:
        if cat not in used_cats[-len(CATEGORIES):]:
            chosen_category = cat
            break
    if not chosen_category:
        chosen_category = CATEGORIES[len(history) % len(CATEGORIES)]

    print(f"   📂  Category this week: {chosen_category}")

    # Fetch real SERP data for this category
    serp_data = fetch_serp_data(chosen_category)
    serp_block = format_serp_for_prompt(serp_data)

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are an expert SEO strategist specialising in mental wellness content.

Your task: identify the single best blog topic for this week for mindcoreai.eu.
Target audience:
  - Men 35+ (primary -- massively underserved)
  - People in addiction recovery seeking mental wellness support
  - Adults exploring AI-powered mental health tools

CATEGORY THIS WEEK: {chosen_category}

REAL GOOGLE SEARCH DATA (use this to pick a topic people are ACTUALLY searching for):
{serp_block}

Selection criteria:
  - Choose a topic directly inspired by the real Google questions and searches above
  - Target a specific long-tail keyword with high demand but LOW competition
  - Evergreen -- ranks over months, not just days
  - Answer a real question from the People Also Ask section if possible

CRITICAL -- ALREADY PUBLISHED POSTS (DO NOT REPEAT ANY):
{history_text}

You MUST NOT choose any topic similar to the above. Every post must be a completely fresh angle.

Respond ONLY in this exact JSON format -- no markdown, no preamble:
{{
  "topic": "Full blog post title (compelling, keyword-rich, answers a real search question)",
  "primary_keyword": "exact long-tail keyword to target (from SERP data ideally)",
  "secondary_keywords": ["kw2", "kw3", "kw4", "kw5"],
  "people_also_ask": ["real question 1 to answer in the post", "real question 2", "real question 3"],
  "search_intent": "what the reader is actually looking for",
  "meta_description": "150-160 character meta description -- include primary keyword",
  "image_prompt": "Detailed DALL-E prompt: warm, soft, hopeful illustration for a mental wellness blog -- human, approachable, NOT dark or neon.",
  "rationale": "Why this topic has high demand and low competition based on SERP data",
  "category": "{chosen_category}"
}}"""
        }]
    )

    raw = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    print(f"   ✅  Topic    : {data['topic']}")
    print(f"   🔑  KW       : {data['primary_keyword']}")
    print(f"   📂  Category : {data.get('category', 'N/A')}")
    print(f"   💡  Why      : {data['rationale']}")
    return data


# ── Step 2 · Write the Blog Post ───────────────────────────────────────────────
def write_blog_post(topic_data):
    print("\n[2/7] Writing blog post...")

    # Format PAA questions for the writing prompt
    paa_questions = topic_data.get("people_also_ask", [])
    paa_block = ""
    if paa_questions:
        paa_block = (
            "\nPEOPLE ALSO ASK (answer each of these naturally within the post "
            "-- this dramatically improves Google ranking):\n"
            + "\n".join(f"  - {q}" for q in paa_questions)
        )

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4500,
        messages=[{
            "role": "user",
            "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full, publish-ready blog post using these details:

  Title            : {topic_data['topic']}
  Primary Keyword  : {topic_data['primary_keyword']}
  Secondary KWs    : {', '.join(topic_data['secondary_keywords'])}
  Search Intent    : {topic_data['search_intent']}
  Category         : {topic_data.get('category', '')}
{paa_block}

WRITING REQUIREMENTS:
  - 1,200-1,500 words
  - Tone: warm, honest, human -- like advice from a friend who has been there
  - Audience: men 35+, people in recovery, adults open to AI wellness tools
  - Primary keyword must appear in: H1, first paragraph, at least 2 H2s, conclusion
  - Secondary keywords woven in naturally -- never forced
  - Keyword density for primary keyword: 0.5%-2%
  - Structure: H1 -> intro (2 para) -> 4-6 H2 sections -> FAQ section -> conclusion + CTA
  - FAQ SECTION: include an <h2>Frequently Asked Questions</h2> section that directly answers
    each "People Also Ask" question above. Use <h3> for each question, <p> for the answer.
    This is critical for Google featured snippets and PAA boxes.
  - Real, actionable advice -- zero fluff, zero generic platitudes
  - Final paragraph: natural CTA to download MindCore AI

FORMAT:
  - Return clean WordPress-ready HTML only
  - Use <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong> tags
  - Do NOT include <html>, <head>, <body>, <style>, or <script> tags
  - After ALL the content, on its own line, write exactly:
    EXCERPT: [2-3 sentence hook for the post preview]"""
        }]
    )

    content = response.content[0].text
    word_count = len(content.split())
    print(f"   ✅  Written (~{word_count} words)")
    return content


# ── Step 3 · Generate Illustration ────────────────────────────────────────────
def generate_illustration(image_prompt):
    print("\n[3/7] Generating DALL-E illustration...")

    full_prompt = (
        f"{image_prompt} "
        "Style: soft watercolour illustration, warm gentle colours, "
        "hopeful and human, suitable for a mental wellness blog. "
        "No text, no words, no letters in the image."
    )

    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    img_bytes  = requests.get(image_url, timeout=30).content
    print("   ✅  Illustration generated")
    return img_bytes


# ── Step 4 · Upload Image to WordPress ────────────────────────────────────────
def upload_image_to_wordpress(image_data, title):
    print("\n[4/7] Uploading illustration to WordPress...")

    filename = f"mindcore-blog-{datetime.now().strftime('%Y%m%d')}.png"
    headers  = get_wp_auth()
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    headers["Content-Type"]        = "image/png"

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        headers=headers,
        data=image_data,
        timeout=60,
    )

    if response.status_code == 201:
        media_id = response.json()["id"]
        print(f"   ✅  Image uploaded (ID: {media_id})")
        return media_id
    else:
        print(f"   ⚠️   Image upload failed ({response.status_code}): {response.text}")
        return None


# ── Step 5 · Category Management ──────────────────────────────────────────────
def get_or_create_categories():
    print("\n[5/7] Setting up categories...")
    headers = get_wp_auth()

    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?per_page=100",
        headers=headers,
        timeout=15,
    )
    existing = {c["name"]: c["id"] for c in response.json()} if response.status_code == 200 else {}

    category_map = {}
    for name in CATEGORIES:
        if name in existing:
            category_map[name] = existing[name]
        else:
            create = requests.post(
                f"{WP_URL}/wp-json/wp/v2/categories",
                headers={**headers, "Content-Type": "application/json"},
                json={"name": name},
                timeout=15,
            )
            if create.status_code == 201:
                category_map[name] = create.json()["id"]
                print(f"   ✅  Created category: {name}")
            else:
                print(f"   ⚠️   Could not create '{name}': {create.text}")

    print(f"   ✅  {len(category_map)} categories ready")
    return category_map


# ── Step 6 · Publish to WordPress as Draft ────────────────────────────────────
def publish_to_wordpress(topic_data, content, image_id=None, category_map=None):
    print("\n[6/7] Publishing draft to WordPress...")

    excerpt = ""
    if "EXCERPT:" in content:
        parts   = content.split("EXCERPT:")
        content = parts[0].strip()
        excerpt = parts[1].strip()

    category_ids = []
    if category_map:
        chosen = topic_data.get("category", "")
        if chosen in category_map:
            category_ids = [category_map[chosen]]
            print(f"   📂  Category assigned: {chosen}")

    headers = get_wp_auth()
    headers["Content-Type"] = "application/json"

    post_payload = {
        "title":      topic_data["topic"],
        "content":    content,
        "excerpt":    excerpt,
        "status":     "draft",
        "categories": category_ids,
        "meta": {
            "_yoast_wpseo_metadesc": topic_data["meta_description"],
            "_yoast_wpseo_focuskw":  topic_data["primary_keyword"],
        },
    }

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        headers=headers,
        json=post_payload,
        timeout=30,
    )

    if response.status_code != 201:
        raise RuntimeError(
            f"WordPress publish failed ({response.status_code}): {response.text}"
        )

    post    = response.json()
    post_id = post["id"]
    print(f"   ✅  Draft saved  →  {post.get('link', 'N/A')}")

    if image_id:
        update_response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            json={"featured_media": image_id},
            timeout=30,
        )
        if update_response.status_code == 200:
            print(f"   ✅  Featured image attached")

    return post


# ── Step 7 · Update History File via GitHub API ───────────────────────────────
def update_history_on_github(history, new_entry):
    print("\n[7/7] Saving post to history...")

    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        print("   ⚠️   GITHUB_TOKEN or GITHUB_REPOSITORY not set -- skipping history save")
        return

    api_url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    get_response = requests.get(api_url, headers=headers, timeout=15)
    sha = get_response.json().get("sha") if get_response.status_code == 200 else None

    history.append(new_entry)
    content = base64.b64encode(json.dumps(history, indent=2).encode()).decode()

    payload = {"message": f"blog: log post -- {new_entry['title'][:60]}", "content": content}
    if sha:
        payload["sha"] = sha

    put_response = requests.put(api_url, headers=headers, json=payload, timeout=15)
    if put_response.status_code in (200, 201):
        print(f"   ✅  History committed to repo ({len(history)} posts total)")
    else:
        print(f"   ⚠️   History commit failed: {put_response.text}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n🚀  MindCore AI -- Weekly Blog Automation Pipeline")
    print("=" * 52)
    print(f"   SERP API: {'✅ active' if SERP_API_KEY else '⚠️  not configured (Claude fallback)'}")

    history = load_history()
    print(f"   📋  History loaded -- {len(history)} posts published so far")

    topic_data   = research_topic(history)
    content      = write_blog_post(topic_data)

    try:
        image_data = generate_illustration(topic_data["image_prompt"])
        image_id   = upload_image_to_wordpress(image_data, topic_data["topic"])
    except Exception as exc:
        print(f"   ⚠️   Illustration step failed: {exc} -- continuing without image.")
        image_id = None

    try:
        category_map = get_or_create_categories()
    except Exception as exc:
        print(f"   ⚠️   Category setup failed: {exc} -- continuing without categories.")
        category_map = None

    post = publish_to_wordpress(topic_data, content, image_id, category_map)

    new_entry = {
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "title":           topic_data["topic"],
        "primary_keyword": topic_data["primary_keyword"],
        "category":        topic_data.get("category", ""),
        "wp_post_id":      post.get("id"),
    }
    update_history_on_github(history, new_entry)

    print("\n🎉  Pipeline complete! Check WordPress › Posts › Drafts.")
    print("=" * 52)


if __name__ == "__main__":
    main()
