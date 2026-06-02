import os
import json
import base64
import re
import time
import requests
from anthropic import Anthropic
from openai import OpenAI
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# -- Clients ------------------------------------------------------------------
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
openai_client    = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]
SERP_API_KEY    = os.environ.get("SERP_API_KEY", "")
SERP_API_URL    = "https://serpapi.com/search"

WP_BLOG_CATEGORY = "Relaxation & Meditation"
MIN_WORD_COUNT   = 1200

# Internal site pages to link to naturally
INTERNAL_LINKS = [
    ("MindCore AI features", "https://mindcoreai.eu/features/"),
    ("our story",            "https://mindcoreai.eu/about-us/"),
    ("MindCore AI blog",     "https://mindcoreai.eu/blog/"),
]

# External authoritative sources
EXTERNAL_LINKS = [
    ("Mind",                      "https://www.mind.org.uk"),
    ("Mental Health Foundation",  "https://www.mentalhealth.org.uk"),
    ("NHS mental health support", "https://www.nhs.uk/mental-health/"),
]

# Inline app link — used naturally within content
APP_INLINE_LINK = (
    '<a href="https://play.google.com/store/apps/details?id=com.mindcoreai.app" '
    'target="_blank" rel="noopener noreferrer"><strong>MindCore AI</strong></a>'
)

# Official Google Play badge — used in the final CTA section
GP_CTA_LINK = (
    '<a href="https://play.google.com/store/apps/details?id=com.mindcoreai.app" '
    'target="_blank" rel="noopener noreferrer">'
    '<img src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png" '
    'alt="Get it on Google Play" style="height:60px;width:auto;display:block;margin-top:0.75rem;">'
    '</a>'
)


# -- Firebase init ------------------------------------------------------------
def init_firebase():
    service_account_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(service_account_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


# -- Read last audio track ----------------------------------------------------
def get_latest_track(db):
    doc = db.collection("pipeline_state").document("relax_audio").get()
    if not doc.exists:
        raise RuntimeError("No pipeline state found — run the audio pipeline first.")
    data          = doc.to_dict()
    title         = data.get("last_title")
    category_key  = data.get("last_category")
    category_name = data.get("last_category_name")
    seo_keywords  = data.get("last_seo_keywords")
    audio_url     = data.get("last_audio_url")
    if not title:
        raise RuntimeError("last_title missing from pipeline state.")
    print(f"   Track    : {title}")
    print(f"   Category : {category_name}")
    return title, category_key, category_name, seo_keywords, audio_url


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


# -- SERP Research ------------------------------------------------------------
def fetch_serp_data(title, seo_keywords):
    if not SERP_API_KEY:
        print("   SERP_API_KEY not set — skipping SERP research")
        return {}
    seed = seo_keywords.split(",")[0].strip() if seo_keywords else title
    print(f"   Fetching SERP data for: '{seed}'")
    try:
        params = {"engine": "google", "q": seed, "api_key": SERP_API_KEY, "num": 10, "hl": "en", "gl": "us"}
        resp   = requests.get(SERP_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data   = resp.json()
        paa     = [q.get("question", "") for q in data.get("related_questions", [])[:6] if q.get("question")]
        related = [r.get("query", "") for r in data.get("related_searches", [])[:6] if r.get("query")]
        print(f"   SERP: {len(paa)} PAA questions, {len(related)} related searches")
        return {"seed_query": seed, "people_also_ask": paa, "related_searches": related}
    except Exception as exc:
        print(f"   SERP fetch failed ({exc}) — continuing without SERP data")
        return {}

def format_serp_for_prompt(serp_data):
    if not serp_data:
        return "No SERP data — use your own SEO knowledge."
    lines = []
    paa = serp_data.get("people_also_ask", [])
    if paa:
        lines.append("PEOPLE ALSO ASK (real Google questions to answer in the post):")
        for q in paa: lines.append(f"  - {q}")
        lines.append("")
    related = serp_data.get("related_searches", [])
    if related:
        lines.append("RELATED SEARCHES (weave as secondary keywords):")
        for r in related: lines.append(f"  - {r}")
    return "\n".join(lines)


# -- Write companion blog post ------------------------------------------------
def write_companion_post(title, category_name, seo_keywords, audio_url, serp_data):
    print("Writing companion blog post...")

    audio_embed = ""
    if audio_url:
        audio_embed = (
            f'<p><audio controls style="width:100%">'
            f'<source src="{audio_url}" type="audio/mpeg">'
            f'Your browser does not support audio.</audio></p>'
        )

    serp_block    = format_serp_for_prompt(serp_data)
    primary_kw    = seo_keywords.split(",")[0].strip() if seo_keywords else title
    int_links     = "\n".join(f'  - Link text: "{t[0]}" → {t[1]}' for t in INTERNAL_LINKS)
    ext_links     = "\n".join(f'  - Link text: "{t[0]}" → {t[1]}' for t in EXTERNAL_LINKS)

    # Build SERP-based FAQ questions or use topic-relevant defaults
    paa_questions = serp_data.get("people_also_ask", [])
    if not paa_questions:
        paa_questions = [
            f"What is {primary_kw} and how does it help?",
            f"How often should I practise {primary_kw}?",
            f"How long does {primary_kw} take to work?",
            f"Can {primary_kw} help with anxiety?",
            f"Is {primary_kw} suitable for beginners?",
        ]

    faq_questions_str = "\n".join(f"  - {q}" for q in paa_questions[:5])

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=7000,
        messages=[{"role": "user", "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a companion blog post for a new guided relaxation audio session published in the MindCore AI app.

AUDIO SESSION DETAILS:
  Title        : {title}
  Category     : {category_name}
  SEO Keywords : {seo_keywords}
  Primary KW   : {primary_kw}

REAL GOOGLE SEARCH DATA:
{serp_block}

CRITICAL KEYWORD RULES (Yoast SEO compliance):
  1. EXACT phrase "{primary_kw}" must appear in the H1 title (with a number e.g. "5 Ways..." or "7 Benefits...")
  2. EXACT phrase "{primary_kw}" must be in the very FIRST sentence
  3. EXACT phrase "{primary_kw}" must appear in at least 3 H2 subheadings
  4. EXACT phrase "{primary_kw}" must appear at least 8-10 times total
  5. Use EXACTLY "{primary_kw}" — no synonyms, no variations
  6. Keyword density: 1.0%-1.5%
  7. Minimum 1,200 words of readable content

MANDATORY LINKS — all must appear as proper HTML anchor tags:
  Internal site pages (include ALL 3):
{int_links}

  External authoritative sources (include at least 2):
{ext_links}

  MindCore AI app inline link (include naturally at least ONCE in the body):
  Use: {APP_INLINE_LINK}
  Example: "Apps like {APP_INLINE_LINK} are designed specifically for this."

MANDATORY FAQ SECTION (must always be included):
  After the main content sections, add:
  <h2>Frequently Asked Questions About {primary_kw.title()}</h2>
  Answer each of these 5 questions using <h3> for the question, <p> for the answer (2-4 sentences each):
{faq_questions_str}
  - At least 2 answers must include the exact phrase "{primary_kw}"
  - One answer should naturally mention MindCore AI as a helpful tool

FINAL CTA SECTION (MANDATORY — use exactly this structure):
  After the FAQ, write a short concluding section with:
  1. A bold paragraph encouraging the reader to open MindCore AI and listen to the session:
     <p><strong>Open MindCore AI now and listen to &#8220;{title}&#8221; — [complete with a motivating sentence about starting their journey].</strong></p>
  2. Immediately followed by this EXACT Google Play badge HTML:
     {GP_CTA_LINK}

STRUCTURE:
  H1 (with number + keyword) → intro (2 para) → audio player → 4-5 H2 sections → FAQ section → Final CTA

  Other requirements:
  - At least one <ul> list in the main content
  - Real, actionable content — zero fluff

INSERT this audio player HTML after the intro paragraph:
  {audio_embed}

FORMAT:
  - Clean WordPress HTML: h1 h2 h3 p ul li strong em a audio img
  - External links: target="_blank" rel="noopener noreferrer"
  - No html head body style script tags
  - After ALL HTML on its own line:
    EXCERPT: [2-3 sentence hook containing the exact phrase "{primary_kw}"]"""}]
    )

    content   = response.content[0].text
    wc        = count_words_in_html(content)
    kw_count  = content.lower().count(primary_kw.lower())
    print(f"   Written ({wc} words, keyword appears {kw_count} times)")

    if wc < MIN_WORD_COUNT:
        print(f"   Only {wc} words — expanding...")
        content = expand_post(content, primary_kw, wc)

    return content, primary_kw


def expand_post(content, primary_kw, current_words):
    needed = MIN_WORD_COUNT - current_words
    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=3000,
        messages=[{"role": "user", "content": f"""Post is {current_words} words — needs {MIN_WORD_COUNT}.
Add ~{needed} words by expanding sections or adding 2 H2s. Same tone, HTML format.
Use EXACT phrase "{primary_kw}" at least 3 more times. Return COMPLETE post with EXCERPT.

{content}"""}]
    )
    expanded = response.content[0].text
    print(f"   Expanded to {count_words_in_html(expanded)} words")
    return expanded


# -- Generate cinematic image -------------------------------------------------
def generate_illustration(title, category_name):
    print("Generating cinematic image...")
    prompt = (
        f"A peaceful scene evoking '{category_name}' relaxation and mental wellness. "
        "Cinematic photography style, warm golden-hour lighting, soft focus background, "
        "shallow depth of field, no faces shown — shoot from behind or hands/objects only. "
        "Warm amber and soft teal colour grading, photorealistic, hopeful atmosphere. "
        "No text, no words, no letters in the image."
    )

    try:
        resp = openai_client.images.generate(
            model="gpt-image-1", prompt=prompt, size="1536x1024", quality="high", n=1,
        )
        data = resp.data[0]
        img  = requests.get(data.url, timeout=30).content if getattr(data, "url", None) else base64.b64decode(data.b64_json)
        print("   Cinematic image generated (gpt-image-1)")
        return img
    except Exception as e1:
        print(f"   gpt-image-1 failed: {e1} — trying dall-e-2...")

    try:
        resp = openai_client.images.generate(model="dall-e-2", prompt=prompt[:1000], size="1024x1024", n=1)
        img  = requests.get(resp.data[0].url, timeout=30).content
        print("   Cinematic image generated (dall-e-2 fallback)")
        return img
    except Exception as e2:
        raise RuntimeError(f"All image models failed. gpt-image-1: {e1} | dall-e-2: {e2}")


# -- Upload image to WordPress ------------------------------------------------
def upload_image(image_data, alt_text=""):
    print("Uploading image...")
    filename = f"mindcore-relax-{datetime.now().strftime('%Y%m%d')}.png"
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
        print(f"   Alt text set: '{alt_text}'" if patch.status_code == 200 else "   Alt text failed")

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


# -- Get or create WordPress category ----------------------------------------
def get_or_create_wp_category(name):
    auth = get_wp_auth()
    resp = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?search={name}&per_page=10", headers=auth, timeout=15)
    if resp.status_code == 200:
        for cat in resp.json():
            if cat["name"].lower() == name.lower():
                return cat["id"]
    create = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers={**auth, "Content-Type": "application/json"},
        json={"name": name}, timeout=15,
    )
    if create.status_code == 201:
        cat_id = create.json()["id"]
        print(f"   Created WP category: {name} (ID: {cat_id})")
        return cat_id
    elif create.status_code == 400:
        err     = create.json()
        term_id = err.get("data", {}).get("term_id") or (err.get("additional_data") or [None])[0]
        if term_id:
            print(f"   Category exists: {name} (ID: {term_id})")
            return int(term_id)
    return None


# -- Publish to WordPress -----------------------------------------------------
def publish_to_wordpress(title, content, primary_keyword, media_id, media_url, category_id):
    print("Publishing to WordPress...")

    excerpt = ""
    if "EXCERPT:" in content:
        bits    = content.split("EXCERPT:")
        content = bits[0].strip()
        excerpt = bits[1].strip() if len(bits) > 1 else ""

    if media_url:
        content = inject_image_into_content(content, media_url, primary_keyword)

    slug      = keyword_to_slug(primary_keyword)
    meta_desc = excerpt[:155] if excerpt else f"{title} — MindCore AI guided relaxation."

    validate_seo(content, title, meta_desc, primary_keyword, slug)

    auth = get_wp_auth()
    auth["Content-Type"] = "application/json"

    post_payload = {
        "title":      title,
        "content":    content,
        "excerpt":    excerpt,
        "slug":       slug,
        "status":     "publish",
        "categories": [category_id] if category_id else [],
        "meta": {
            "_yoast_wpseo_metadesc": meta_desc,
            "_yoast_wpseo_focuskw":  primary_keyword,
            "_yoast_wpseo_title":    title,
        },
    }

    print("   Waiting 60s before publishing (Hostinger rate limit)...")
    time.sleep(60)

    for attempt in range(4):
        resp = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=auth, json=post_payload, timeout=30)
        if resp.status_code == 201:
            break
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 30 * (attempt + 1)))
            print(f"   Rate limited — waiting {wait}s (attempt {attempt + 1}/4)...")
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
                print(f"   Image attach failed: {upd.status_code}")
                break

    return post


# -- Main ---------------------------------------------------------------------
def main():
    print("\n== MindCore AI — Relax Audio Companion Blog Pipeline ==")
    print(f"   SERP API: {'active' if SERP_API_KEY else 'not configured (Claude fallback)'}")

    print("\n[1/6] Reading latest audio track from Firestore...")
    db = init_firebase()
    title, category_key, category_name, seo_keywords, audio_url = get_latest_track(db)

    print("\n[2/6] Fetching real Google SEO data (SERP)...")
    serp_data = fetch_serp_data(title, seo_keywords)

    print("\n[3/6] Writing companion blog post...")
    content, primary_keyword = write_companion_post(title, category_name, seo_keywords, audio_url, serp_data)

    print("\n[4/6] Generating cinematic image...")
    media_id  = None
    media_url = None
    try:
        image_data          = generate_illustration(title, category_name)
        media_id, media_url = upload_image(image_data, alt_text=primary_keyword)
    except Exception as exc:
        print(f"   Image failed: {exc} — continuing without image.")

    print("\n[5/6] Setting up WordPress category...")
    category_id = get_or_create_wp_category(WP_BLOG_CATEGORY)

    print("\n[6/6] Publishing to WordPress...")
    post = publish_to_wordpress(title, content, primary_keyword, media_id, media_url, category_id)

    print("\n" + "=" * 52)
    print("Pipeline complete!")
    print(f"   Audio    : {title}")
    print(f"   Category : {category_name}")
    print(f"   Post URL : {post.get('link', 'N/A')}")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    main()
