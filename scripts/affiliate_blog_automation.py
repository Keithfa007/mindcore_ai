import os
import json
import base64
import re
import time
import requests
import cloudscraper
from anthropic import Anthropic
from scripts.fal_image import generate_fal_image
from datetime import datetime

# -- Clients ------------------------------------------------------------------
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
# Image generation: fal.ai Flux Pro (baked in, no OpenAI needed)

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

HISTORY_FILE   = "scripts/affiliate_blog_history.json"
PRODUCTS_FILE  = "scripts/affiliate_products.json"
MIN_WORD_COUNT = 1200

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

APP_INLINE_LINK = (
    '<a href="https://play.google.com/store/apps/details?id=com.mindcoreai.app" '
    'target="_blank" rel="noopener noreferrer"><strong>MindCore AI</strong></a>'
)

GP_CTA_LINK = (
    '<a href="https://play.google.com/store/apps/details?id=com.mindcoreai.app" '
    'target="_blank" rel="noopener noreferrer">'
    '<img src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png" '
    'alt="Get it on Google Play" style="height:60px;width:auto;display:block;margin-top:0.75rem;">'
    '</a>'
)

AFFILIATE_DISCLOSURE = (
    '<div style="background:#0c0c24;border-left:4px solid #a594f9;padding:15px 20px;'
    'margin:0 0 25px 0;border-radius:0 8px 8px 0;font-size:0.9em;color:#9090b8;">'
    '<strong style="color:#c0b8f0;">Disclosure:</strong> This post contains affiliate links. If you purchase '
    'through these links, MindCore AI may earn a small commission at no extra cost to you. '
    'We only recommend products we genuinely believe support your mental wellness journey.'
    '</div>'
)


def product_card_html(product):
    weight_row = (
        f'<li style="color:#b0c8c8;"><strong style="color:#3ecfb2;">Weight:</strong> {product["weight"]}</li>'
        if product.get("weight") and product["weight"] != "N/A" else ""
    )
    return (
        f'<div style="background:#0c0c24;border:2px solid #3ecfb2;border-radius:12px;'
        f'padding:20px;margin:20px 0;color:#e0e8e8;">'
        f'<h3 style="color:#ffffff;margin-top:0;">{product["name"]}</h3>'
        f'<p style="color:#b0c8c8;">{product["highlight"]}</p>'
        f'<ul style="color:#b0c8c8;padding-left:20px;">'
        f'<li><strong style="color:#3ecfb2;">Best for:</strong> {product["best_for"]}</li>'
        f'<li><strong style="color:#3ecfb2;">Price:</strong> {product["price_range"]}</li>'
        f'{weight_row}'
        f'</ul>'
        f'<p style="margin-top:15px;">'
        f'<a href="{product["affiliate_link"]}" target="_blank" rel="noopener sponsored" '
        f'style="background:#3ecfb2;color:#07071a;padding:12px 24px;border-radius:8px;'
        f'text-decoration:none;font-weight:bold;display:inline-block;">'
        f'\U0001f449 View on Amazon</a></p></div>'
    )


def quick_links_html(products):
    links = "".join(
        f'<p style="margin:6px 0;">\U0001f449 <a href="{p["affiliate_link"]}" target="_blank" '
        f'rel="noopener sponsored" style="color:#3ecfb2;text-decoration:none;">{p["name"]}</a></p>'
        for p in products
    )
    return (
        f'<div style="background:#0c0c24;border:2px solid #a594f9;border-radius:12px;'
        f'padding:20px;margin:30px 0;color:#e0e8e8;">'
        f'<h2 style="color:#ffffff;margin-top:0;">Quick Links \u2014 All Products</h2>'
        f'{links}</div>'
    )


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
    kw    = primary_keyword.lower().replace("-", " ")
    text  = re.sub(r"<[^>]+>", " ", content).lower().replace("-", " ")
    words = text.split()
    wc    = len(words)
    first = " ".join(words[:max(1, wc // 10)])
    kw_n  = text.count(kw)
    dens  = (kw_n / wc * 100) if wc > 0 else 0
    checks = {
        "Keyword in title":             kw in title.lower().replace("-", " "),
        "Keyword in meta description":  kw in meta.lower().replace("-", " "),
        "Keyword in URL slug":          kw.replace(" ", "-") in slug,
        "Keyword in first 10%":         kw in first,
        "Keyword found in content":     kw in text,
        f"Word count >= {MIN_WORD_COUNT}": wc >= MIN_WORD_COUNT,
        "External link present":        'href="http' in content,
        "Internal link present":        "mindcoreai.eu" in content,
        "Google Play link present":     "play.google.com" in content,
        "FAQ section present":          "Frequently Asked Questions" in content,
        "Affiliate disclosure present": "affiliate links" in content.lower(),
        "Product cards present":        "View on Amazon" in content,
        "Quick links present":          "Quick Links" in content,
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

def format_history_for_prompt(history):
    if not history: return "None yet."
    return "\n".join(
        f"  {i}. [{e['date']}] \"{e['title']}\" \u2014 keyword: \"{e['primary_keyword']}\""
        for i, e in enumerate(history, 1)
    )

def build_post_links(history):
    posts = []
    for post in history:
        slug = post.get("slug", "")
        if not slug:
            slug = keyword_to_slug(post.get("primary_keyword", ""))
        if slug:
            posts.append({"title": post["title"], "url": f"https://mindcoreai.eu/{slug}/"})
    return posts

def load_main_blog_history():
    main_history_file = "scripts/blog_history.json"
    if not os.path.exists(main_history_file):
        return []
    with open(main_history_file, "r") as f:
        return json.load(f)


# -- Products -----------------------------------------------------------------
def load_products():
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

def pick_product_category(products_data, history):
    used_categories = {e["product_category"] for e in history}
    categories = products_data["product_categories"]
    available  = [c for c in categories if c["category"] not in used_categories]
    if not available:
        available = categories
    return available[0]


# -- Step 1: Research topic ---------------------------------------------------
def research_topic(product_cat, history):
    print(f"Researching affiliate topic for: {product_cat['category']}")
    history_txt = format_history_for_prompt(history)

    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO content strategist for mindcoreai.eu.

PRODUCT CATEGORY: {product_cat['category']}
SUGGESTED KEYWORD: {product_cat['blog_keyword']}
SUGGESTED TITLE: {product_cat['blog_title_template']}
WP CATEGORY: {product_cat['wp_category']}
NUMBER OF PRODUCTS: {len(product_cat['products'])}

PRODUCTS TO REVIEW:
{json.dumps([{"name": p["name"], "best_for": p["best_for"]} for p in product_cat['products']], indent=2)}

ALREADY PUBLISHED (avoid repeating):
{history_txt}

Tasks:
1. Use the suggested keyword or improve it
2. Write a compelling title with a NUMBER and the keyword
3. Choose 5 secondary keywords
4. Write a meta description (150-160 chars) with primary keyword
5. Write a DALL-E image prompt for a cinematic-warm lifestyle scene

Respond ONLY in this exact JSON \u2014 no markdown:
{{"topic":"title","primary_keyword":"{product_cat['blog_keyword']}","secondary_keywords":["kw2","kw3","kw4","kw5","kw6"],"search_intent":"intent","meta_description":"meta","image_prompt":"scene","category":"{product_cat['wp_category']}"}}\n"""}]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    data["primary_keyword"] = product_cat["blog_keyword"]
    print(f"   Topic    : {data['topic']}")
    print(f"   Keyword  : {data['primary_keyword']}")
    print(f"   Category : {data.get('category', 'N/A')}")
    return data


# -- Step 2: Write affiliate post ---------------------------------------------
def write_affiliate_post(topic_data, product_cat, history):
    print("Writing affiliate blog post...")
    kw       = topic_data["primary_keyword"]
    products = product_cat["products"]

    product_details = ""
    for i, p in enumerate(products, 1):
        product_details += f"\nPRODUCT {i}:\n  Name: {p['name']}\n  Affiliate link: {p['affiliate_link']}\n  Price: {p['price_range']}\n  Best for: {p['best_for']}\n  Highlight: {p['highlight']}\n"

    int_links = "\n".join(f'  - Link text: "{t[0]}" \u2192 {t[1]}' for t in INTERNAL_LINKS)
    ext_links = "\n".join(f'  - Link text: "{t[0]}" \u2192 {t[1]}' for t in EXTERNAL_LINKS[:2])

    main_history = load_main_blog_history()
    all_posts    = build_post_links(main_history) + build_post_links(history)
    cross_link_block = ""
    if len(all_posts) >= 2:
        cross_link_block = "\nCROSS-POST LINKS (link to exactly 2 naturally):\n"
        for p in all_posts[-10:]:
            cross_link_block += f'  - "{p["title"]}" \u2192 {p["url"]}\n'

    product_card_instructions = ""
    for i, p in enumerate(products, 1):
        product_card_instructions += f"\nFor product {i} ({p['name']}), insert this EXACT product card HTML:\n{product_card_html(p)}\n"

    quick_links_block = quick_links_html(products)

    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=7000,
        messages=[{"role": "user", "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full publish-ready AFFILIATE REVIEW blog post:
  Title           : {topic_data['topic']}
  Primary Keyword : {kw}
  Secondary KWs   : {', '.join(topic_data['secondary_keywords'])}

PRODUCTS:
{product_details}

CRITICAL KEYWORD RULES:
  1. EXACT phrase "{kw}" in H1
  2. EXACT phrase "{kw}" in first sentence
  3. EXACT phrase "{kw}" in at least 3 H2s
  4. EXACT phrase "{kw}" 8-10 times total
  5. Keyword density 1.0%-1.5%
  6. Min 1,200 words

STRUCTURE:
1. Affiliate Disclosure (insert EXACT HTML):
{AFFILIATE_DISCLOSURE}
2. H1 with keyword + number
3. Intro 2-3 paragraphs (keyword in first sentence)
4. H2 - Why these products matter for mental wellness
5. H2 - How we chose them
6. H2 per product - 100-150 word review then EXACT product card HTML:
{product_card_instructions}
7. H2 - How to choose the right one (with <ul> list)
8. FAQ SECTION (MANDATORY):
   <h2>Frequently Asked Questions About {kw.title()}</h2>
   5 x <h3> questions, <p> answers (2-4 sentences)
   At least 2 questions include exact phrase "{kw}"
   One answer mentions MindCore AI
9. Quick links (insert EXACT HTML):
{quick_links_block}
10. FINAL CTA:
   <p><strong>These products support your body. {APP_INLINE_LINK} supports your mind \u2014 24/7, no waiting room required.</strong></p>
   {GP_CTA_LINK}

MANDATORY LINKS:
  Internal (ALL 3):
{int_links}
  External (at least 2):
{ext_links}
{cross_link_block}
FORMAT:
  - Clean WordPress HTML only
  - Affiliate links: rel="noopener sponsored"
  - External links: rel="noopener noreferrer"
  - After ALL HTML: EXCERPT: [2-3 sentence hook with "{kw}"]\n"""}]
    )

    content  = response.content[0].text
    wc       = count_words_in_html(content)
    kw_count = content.lower().count(kw.lower())
    print(f"   Written ({wc} words, keyword appears {kw_count} times)")
    if wc < MIN_WORD_COUNT:
        print("   Expanding...")
        content = expand_post(content, topic_data, wc)
    return content


def expand_post(content, topic_data, current_words):
    needed = MIN_WORD_COUNT - current_words
    kw     = topic_data["primary_keyword"]
    response = anthropic_client.messages.create(
        model="claude-opus-4-5", max_tokens=3000,
        messages=[{"role": "user", "content": f"""Post is {current_words} words \u2014 needs {MIN_WORD_COUNT}. Add ~{needed} words. Use EXACT phrase "{kw}" 3+ more times. Return COMPLETE post with EXCERPT.\n\n{content}"""}]
    )
    expanded = response.content[0].text
    print(f"   Expanded to {count_words_in_html(expanded)} words")
    return expanded


# -- Step 3: Image generation -------------------------------------------------
def generate_illustration(image_prompt):
    print("Generating cinematic image (fal.ai Flux Pro)...")
    prompt = (
        f"{image_prompt}. Style: cinematic photography, warm golden-hour lighting, "
        "soft focus background, shallow depth of field, no faces shown, "
        "warm amber and soft teal colour grading, photorealistic. No text in the image."
    )
    return generate_fal_image(prompt, image_size="landscape_4_3", model="pro")


def upload_image_to_wordpress(image_data, alt_text=""):
    print("Uploading image via cloudscraper...")
    filename = f"mindcore-affiliate-{datetime.now().strftime('%Y%m%d')}.png"
    auth     = get_wp_auth()
    upload_headers = {**auth, "Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": "image/png"}
    resp = scraper.post(f"{WP_URL}/wp-json/wp/v2/media", headers=upload_headers, data=image_data, timeout=60)
    if resp.status_code != 201:
        print(f"   Upload failed ({resp.status_code}): {resp.text[:200]}")
        return None, None
    media     = resp.json()
    media_id  = media["id"]
    media_url = media.get("source_url", "")
    print(f"   Image uploaded (ID: {media_id})")
    if alt_text:
        time.sleep(2)
        scraper.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            headers={**auth, "Content-Type": "application/json"},
            json={"alt_text": alt_text, "caption": alt_text}, timeout=15,
        )
        print(f"   Alt text set: '{alt_text}'")
    return media_id, media_url


# -- Step 4: Category ---------------------------------------------------------
def resolve_category_id(category_name):
    resp = scraper.get(
        f"{WP_URL}/wp-json/wp/v2/categories?per_page=100&search={requests.utils.quote(category_name)}",
        headers=get_wp_auth(), timeout=15,
    )
    if resp.status_code == 200:
        for c in resp.json():
            if c["name"].replace("&amp;", "&").replace("&#039;", "'").lower() == category_name.lower():
                return c["id"]
    create = scraper.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers={**get_wp_auth(), "Content-Type": "application/json"},
        json={"name": category_name}, timeout=15,
    )
    if create.status_code == 201:
        return create.json()["id"]
    elif create.status_code == 400:
        err = create.json()
        term_id = err.get("data", {}).get("term_id")
        if term_id: return int(term_id)
    return None


# -- Step 5: Publish ----------------------------------------------------------
def publish_to_wordpress(topic_data, content, media_id=None):
    """Publish post. Image is set as featured only — NOT injected into content to avoid duplication."""
    print("Publishing to WordPress via cloudscraper...")
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
    headers = {**get_wp_auth(), "Content-Type": "application/json"}
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
        resp = scraper.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=headers, json=payload, timeout=30)
        if resp.status_code == 201: break
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 30 * (attempt + 1)))
            print(f"   Rate limited - waiting {wait}s...")
            time.sleep(wait)
            continue
        raise RuntimeError(f"WordPress publish failed ({resp.status_code}): {resp.text[:300]}")
    else:
        raise RuntimeError("WordPress publish failed after 4 attempts")
    post    = resp.json()
    post_id = post["id"]
    print(f"   Published -> {post.get('link', 'N/A')}")
    # Attach featured image only — no content injection to avoid duplicate
    if media_id:
        for img_attempt in range(3):
            wait_time = 10 * (img_attempt + 1)
            print(f"   Waiting {wait_time}s before attaching featured image...")
            time.sleep(wait_time)
            upd = scraper.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                headers=headers, json={"featured_media": media_id}, timeout=30,
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


# -- Step 6: Save history -----------------------------------------------------
def update_history_on_github(history, new_entry):
    print("Saving to history...")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("   Skipping \u2014 GITHUB_TOKEN not set")
        return
    api_url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    hdrs    = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_r   = requests.get(api_url, headers=hdrs, timeout=15)
    sha     = get_r.json().get("sha") if get_r.status_code == 200 else None
    history.append(new_entry)
    encoded = base64.b64encode(json.dumps(history, indent=2).encode()).decode()
    payload = {"message": f"affiliate: log \u2014 {new_entry['title'][:60]}", "content": encoded}
    if sha: payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    print(f"   History committed ({len(history)} posts)" if put.status_code in (200, 201) else f"   History failed: {put.text}")


# -- Main ---------------------------------------------------------------------
def main():
    print("\n== MindCore AI - Affiliate Blog Pipeline ==")
    history       = load_history()
    products_data = load_products()
    print(f"History: {len(history)} affiliate posts published")
    print(f"Product categories available: {len(products_data['product_categories'])}")

    product_cat = pick_product_category(products_data, history)
    print(f"Selected category: {product_cat['category']}")

    topic_data = research_topic(product_cat, history)
    content    = write_affiliate_post(topic_data, product_cat, history)

    media_id = None
    try:
        image_data = generate_illustration(topic_data["image_prompt"])
        media_id, _ = upload_image_to_wordpress(image_data, alt_text=topic_data["primary_keyword"])
    except Exception as exc:
        print(f"   Image failed: {exc}")

    # Pass only media_id — no media_url to prevent content injection
    post = publish_to_wordpress(topic_data, content, media_id)

    update_history_on_github(history, {
        "date":             datetime.now().strftime("%Y-%m-%d"),
        "title":            topic_data["topic"],
        "primary_keyword":  topic_data["primary_keyword"],
        "category":         topic_data.get("category", ""),
        "product_category": product_cat["category"],
        "slug":             keyword_to_slug(topic_data["primary_keyword"]),
        "wp_post_id":       post.get("id"),
    })

    print("\nAffiliate pipeline complete! Post is live on mindcoreai.eu")
    print("=" * 50)


if __name__ == "__main__":
    main()
