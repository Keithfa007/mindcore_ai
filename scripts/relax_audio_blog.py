import os
import json
import base64
import requests
from anthropic import Anthropic
from openai import OpenAI
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# ── Clients ────────────────────────────────────────────────────────────────────
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
openai_client    = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

# WordPress category for audio companion posts
WP_BLOG_CATEGORY = "Relaxation & Meditation"


# ── Firebase init ──────────────────────────────────────────────────────────────
def init_firebase():
    service_account_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(service_account_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Read last audio track from pipeline state ──────────────────────────────────
def get_latest_track(db):
    doc = db.collection("pipeline_state").document("relax_audio").get()
    if not doc.exists:
        raise RuntimeError("No pipeline state found — run the audio pipeline first.")
    data = doc.to_dict()
    title        = data.get("last_title")
    category_key = data.get("last_category")
    category_name= data.get("last_category_name")
    seo_keywords = data.get("last_seo_keywords")
    audio_url    = data.get("last_audio_url")
    if not title:
        raise RuntimeError("last_title missing from pipeline state.")
    print(f"   ✅  Track    : {title}")
    print(f"   ✅  Category : {category_name}")
    return title, category_key, category_name, seo_keywords, audio_url


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_wp_auth():
    credentials_str = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials_str.encode()).decode()
    return {"Authorization": f"Basic {token}"}


# ── Write companion blog post ──────────────────────────────────────────────────
def write_companion_post(title, category_name, seo_keywords, audio_url):
    print("✍️   Writing companion blog post...")

    audio_embed = ""
    if audio_url:
        audio_embed = f'<p><audio controls style="width:100%"><source src="{audio_url}" type="audio/mpeg">Your browser does not support audio.</audio></p>'

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4500,
        messages=[{
            "role": "user",
            "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a companion blog post for a new guided relaxation audio session just published in the MindCore AI app.

AUDIO SESSION DETAILS:
  Title        : {title}
  Category     : {category_name}
  SEO Keywords : {seo_keywords}

WRITING REQUIREMENTS:
  - 1,200-1,500 words
  - Tone: warm, honest, human — like advice from a trusted friend who has been there
  - Audience: men 35+, people in recovery, adults open to AI wellness tools
  - The post supports and explains the audio session — why this technique helps, the science behind it, how to get the most from it
  - Primary keyword must appear in: H1, first paragraph, at least 2 H2 sections, conclusion
  - Secondary keywords woven in naturally
  - Structure: H1 → intro (2 paragraphs) → 4-5 H2 sections → conclusion with CTA to open the app
  - Real, actionable content — zero fluff
  - Final paragraph: natural CTA to open MindCore AI and listen to the session

FORMAT:
  - Return clean WordPress-ready HTML only
  - Use <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong> tags
  - Do NOT include <html>, <head>, <body>, <style>, or <script> tags
  - Insert this audio player HTML immediately after the H1 and intro paragraph:
    {audio_embed}
  - After ALL the content, on its own line, write exactly:
    EXCERPT: [2-3 sentence hook for the post preview]"""
        }]
    )

    content = response.content[0].text
    word_count = len(content.split())
    print(f"   ✅  Written (~{word_count} words)")
    return content


# ── Generate DALL-E illustration ───────────────────────────────────────────────
def generate_illustration(title, category_name):
    print("🎨  Generating illustration...")

    prompt = (
        f"Soft watercolour illustration for a mental wellness blog post about '{title}'. "
        f"Category: {category_name}. "
        "Scene: a man sitting calmly in a peaceful environment — could be indoors by a window, "
        "or in nature. Warm, hopeful colours. Soft light. Grounded and real. "
        "No text, no words, no letters in the image. "
        "Style: gentle watercolour, human and approachable, suitable for a mental wellness brand."
    )

    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    img_bytes  = requests.get(image_url, timeout=30).content
    print("   ✅  Illustration generated")
    return img_bytes


# ── Upload image to WordPress ──────────────────────────────────────────────────
def upload_image(image_data, title):
    print("📤  Uploading illustration...")

    filename = f"mindcore-relax-{datetime.now().strftime('%Y%m%d')}.png"
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
        print(f"   ⚠️   Image upload failed ({response.status_code})")
        return None


# ── Get or create WordPress category ──────────────────────────────────────────
def get_or_create_wp_category(name):
    headers = get_wp_auth()
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?search={name}&per_page=10",
        headers=headers,
        timeout=15,
    )
    if response.status_code == 200:
        for cat in response.json():
            if cat["name"].lower() == name.lower():
                return cat["id"]

    create = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers={**headers, "Content-Type": "application/json"},
        json={"name": name},
        timeout=15,
    )
    if create.status_code == 201:
        cat_id = create.json()["id"]
        print(f"   ✅  Created WP category: {name} (ID: {cat_id})")
        return cat_id
    return None


# ── Publish to WordPress (live) ────────────────────────────────────────────────
def publish_to_wordpress(title, content, image_id, category_id):
    print("📰  Publishing to WordPress...")

    excerpt = ""
    if "EXCERPT:" in content:
        parts   = content.split("EXCERPT:")
        content = parts[0].strip()
        excerpt = parts[1].strip()

    headers = get_wp_auth()
    headers["Content-Type"] = "application/json"

    post_payload = {
        "title":      title,
        "content":    content,
        "excerpt":    excerpt,
        "status":     "publish",
        "categories": [category_id] if category_id else [],
    }

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        headers=headers,
        json=post_payload,
        timeout=30,
    )

    if response.status_code != 201:
        raise RuntimeError(f"WordPress publish failed ({response.status_code}): {response.text}")

    post    = response.json()
    post_id = post["id"]
    print(f"   ✅  Published → {post.get('link', 'N/A')}")

    if image_id:
        requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            json={"featured_media": image_id},
            timeout=30,
        )
        print("   ✅  Featured image attached")

    return post


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n📝  MindCore AI — Relax Audio Companion Blog Pipeline")
    print("=" * 52)

    print("\n[1/6] Reading latest audio track from Firestore...")
    db = init_firebase()
    title, category_key, category_name, seo_keywords, audio_url = get_latest_track(db)

    print("\n[2/6] Writing companion blog post...")
    content = write_companion_post(title, category_name, seo_keywords, audio_url)

    print("\n[3/6] Generating illustration...")
    try:
        image_data = generate_illustration(title, category_name)
        image_id   = upload_image(image_data, title)
    except Exception as exc:
        print(f"   ⚠️   Illustration failed: {exc} — continuing without image.")
        image_id = None

    print("\n[4/6] Setting up WordPress category...")
    category_id = get_or_create_wp_category(WP_BLOG_CATEGORY)

    print("\n[5/6] Publishing to WordPress...")
    post = publish_to_wordpress(title, content, image_id, category_id)

    print("\n[6/6] Done!")
    print("\n" + "=" * 52)
    print("🎉  Companion blog post published!")
    print(f"    Audio    : {title}")
    print(f"    Category : {category_name}")
    print(f"    Post URL : {post.get('link', 'N/A')}")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    main()
