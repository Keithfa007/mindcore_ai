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

# ── Categories ─────────────────────────────────────────────────────────────────
CATEGORIES = [
    "Anxiety & Stress",
    "Recovery & Sobriety",
    "Men's Mental Health",
    "AI & Wellness",
    "Sleep & Burnout",
    "Relationships & Family",
]


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_wp_auth():
    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}"}


# ── Step 1 · SEO Research & Topic Selection ────────────────────────────────────
def research_topic():
    print("🔍  Researching best SEO topic for this week...")

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
  • Fits one of the three niches above

Available blog categories (pick the most relevant one for your chosen topic):
{chr(10).join(f'  - {c}' for c in CATEGORIES)}

Respond ONLY in this exact JSON format — no markdown, no preamble:
{{
  "topic": "Full blog post title (compelling, keyword-rich)",
  "primary_keyword": "exact low-competition keyword to target",
  "secondary_keywords": ["kw2", "kw3", "kw4", "kw5"],
  "search_intent": "what the reader is actually looking for",
  "meta_description": "150-160 character meta description — include primary keyword",
  "image_prompt": "Detailed DALL-E prompt: warm, soft, hopeful illustration for a mental wellness blog — human, approachable, NOT dark or neon. Describe scene, colours, mood.",
  "rationale": "Why this topic has high demand and low competition right now",
  "category": "exact category name from the list above"
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
    print("✍️   Writing blog post...")

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

WRITING REQUIREMENTS:
  • 1,200–1,500 words
  • Tone: warm, honest, human — like advice from a friend who has been there
  • Audience: men 35+, people in recovery, adults open to AI wellness tools
  • Primary keyword must appear in: H1, first paragraph, at least 2 H2s, conclusion
  • Secondary keywords woven in naturally — never forced
  • Keyword density for primary keyword: 0.5 %–2 %
  • Structure: H1 → intro (2 para) → 4–6 H2 sections → conclusion + CTA
  • Real, actionable advice — zero fluff, zero generic platitudes
  • Final paragraph: natural CTA to download MindCore AI (AI mental health companion)

FORMAT:
  • Return clean WordPress-ready HTML only
  • Use <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong> tags
  • Do NOT include <html>, <head>, <body>, <style>, or <script> tags
  • After ALL the content, on its own line, write exactly:
    EXCERPT: [2-3 sentence hook for the post preview]"""
        }]
    )

    content = response.content[0].text
    word_count = len(content.split())
    print(f"   ✅  Written (~{word_count} words)")
    return content


# ── Step 3 · Generate Illustration ────────────────────────────────────────────
def generate_illustration(image_prompt):
    print("🎨  Generating DALL-E illustration...")

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
    print("📤  Uploading illustration to WordPress...")

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
    """Fetch existing WP categories and create any missing ones. Returns name→id map."""
    print("📂  Setting up categories...")
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
    print("📰  Publishing draft to WordPress...")

    # Split excerpt from content
    excerpt = ""
    if "EXCERPT:" in content:
        parts   = content.split("EXCERPT:")
        content = parts[0].strip()
        excerpt = parts[1].strip()

    # Resolve category ID
    category_ids = []
    if category_map:
        chosen = topic_data.get("category", "")
        if chosen in category_map:
            category_ids = [category_map[chosen]]
            print(f"   📂  Category assigned: {chosen}")
        else:
            print(f"   ⚠️   Category '{chosen}' not found, posting uncategorised")

    headers = get_wp_auth()
    headers["Content-Type"] = "application/json"

    post_payload = {
        "title":      topic_data["topic"],
        "content":    content,
        "excerpt":    excerpt,
        "status":     "draft",       # ← drafts for first 6 weeks
        "categories": category_ids,
        "meta": {
            "_yoast_wpseo_metadesc": topic_data["meta_description"],
            "_yoast_wpseo_focuskw":  topic_data["primary_keyword"],
        },
    }

    # Create post WITHOUT featured image first (Hostinger AI theme bug workaround)
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

    # Attach featured image separately (avoids Hostinger theme 500 error)
    if image_id:
        update_response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            json={"featured_media": image_id},
            timeout=30,
        )
        if update_response.status_code == 200:
            print(f"   ✅  Featured image attached")
        else:
            print(f"   ⚠️   Image attach failed (post still saved): {update_response.text}")

    return post


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n🚀  MindCore AI — Weekly Blog Automation Pipeline")
    print("=" * 52)

    # 1. Research topic (includes category selection)
    topic_data = research_topic()

    # 2. Write blog post
    content = write_blog_post(topic_data)

    # 3. Generate & upload illustration
    try:
        image_data = generate_illustration(topic_data["image_prompt"])
        image_id   = upload_image_to_wordpress(image_data, topic_data["topic"])
    except Exception as exc:
        print(f"   ⚠️   Illustration step failed: {exc}\n   Continuing without image.")
        image_id = None

    # 4. Set up categories in WordPress
    try:
        category_map = get_or_create_categories()
    except Exception as exc:
        print(f"   ⚠️   Category setup failed: {exc}\n   Continuing without categories.")
        category_map = None

    # 5. Publish as draft with category
    publish_to_wordpress(topic_data, content, image_id, category_map)

    print("\n🎉  Pipeline complete! Check WordPress › Posts › Drafts.")
    print("=" * 52)


if __name__ == "__main__":
    main()
