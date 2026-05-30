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
    'target="_blank" rel="noopener noreferrer" '
    'style="font-weight:700;color:#07071a;background-color:#3ecfb2;'
    'padding:0.5rem 1.2rem;border-radius:8px;text-decoration:none;'
    'display:inline-block;margin-top:0.5rem;">'
    '<strong>Download MindCore AI on Google Play</strong>'
    '</a>'
)

AFFILIATE_DISCLOSURE = (
    '<div style="background:#0c0c24;border-left:4px solid #a594f9;padding:15px 20px;'
    'margin:0 0 25px 0;border-radius:0 8px 8px 0;font-size:0.9em;color:#9090b8;">'
    '<strong>Disclosure:</strong> This post contains affiliate links. If you purchase '
    'through these links, MindCore AI may earn a small commission at no extra cost to you. '
    'We only recommend products we genuinely believe support your mental wellness journey.'
    '</div>'
)


def product_card_html(product):
    return (
        f'<div style="background:#0c0c24;border:2px solid #3ecfb2;border-radius:12px;'
        f'padding:20px;margin:20px 0;">'
        f'<h3>{product["name"]}</h3>'
        f'<p>{product["highlight"]}</p>'
        f'<ul>'
        f'<li><strong>Best for:</strong> {product["best_for"]}</li>'
        f'<li><strong>Price:</strong> {product["price_range"]}</li>'
        f'{"<li><strong>Weight:</strong> " + product["weight"] + "</li>" if product.get("weight") and product["weight"] != "N/A" else ""}'
        f'</ul>'
        f'<p style="margin-top:15px;">'
        f'<a href="{product["affiliate_link"]}" target="_blank" rel="noopener sponsored" '
        f'style="background:#3ecfb2;color:#07071a;padding:12px 24px;border-radius:8px;'
        f'text-decoration:none;font-weight:bold;display:inline-block;">'
        f'\U0001f449 View on Amazon</a></p></div>'
    )


def quick_links_html(products):
    links = "".join(
        f'<p>\U0001f449 <a href="{p["affiliate_link"]}" target="_blank" '
        f'rel="noopener sponsored" style="color:#3ecfb2;">{p["name"]}</a></p>'
        for p in products
    )
    return (
        f'<div style="background:#0c0c24;border:2px solid #a594f9;border-radius:12px;'
        f'padding:20px;margin:30px 0;">'
        f'<h2>Quick Links \u2014 All Products</h2>{links}</div>'
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


# -- Load main blog history for cross-linking ---------------------------------
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
        model="claude-sonnet-4-20250514", max_tokens=2000,
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
1. Use the suggested keyword or improve it for higher search volume
2. Write a compelling title that CONTAINS A NUMBER and the keyword
3. Choose 5 secondary keywords related to this product category + mental wellness
4. Write a meta description (150-160 chars) containing the primary keyword
5. Write a DALL-E image prompt for a cinematic-warm lifestyle scene showing someone using or benefiting from this type of product

Respond ONLY in this exact JSON \u2014 no markdown:
{{"topic":"title with number and keyword","primary_keyword":"{product_cat['blog_keyword']}","secondary_keywords":["kw2","kw3","kw4","kw5","kw6"],"search_intent":"what reader is looking for","meta_description":"150-160 char meta containing primary keyword","image_prompt":"specific cinematic-warm lifestyle scene","category":"{product_cat['wp_category']}"}}"""}]
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
        product_details += f"""\nPRODUCT {i}:
  Name: {p['name']}
  Affiliate link: {p['affiliate_link']}
  Price: {p['price_range']}
  Weight: {p.get('weight', 'N/A')}
  Best for: {p['best_for']}
  Highlight: {p['highlight']}
"""

    int_links = "\n".join(f'  - Link text: "{t[0]}" \u2192 {t[1]}' for t in INTERNAL_LINKS)
    ext_links = "\n".join(f'  - Link text: "{t[0]}" \u2192 {t[1]}' for t in EXTERNAL_LINKS[:2])

    main_history = load_main_blog_history()
    main_posts   = build_post_links(main_history)
    aff_posts    = build_post_links(history)
    all_posts    = main_posts + aff_posts

    cross_link_block = ""
    if len(all_posts) >= 2:
        cross_link_block = (
            "\nCROSS-POST LINKS (link to exactly 2 of these existing posts "
            "naturally within the content):\n"
        )
        for p in all_posts[-10:]:
            cross_link_block += f'  - "{p["title"]}" \u2192 {p["url"]}\n'
        cross_link_block += "Pick the 2 most topically relevant.\n"

    product_card_instructions = ""
    for i, p in enumerate(products, 1):
        product_card_instructions += f"""
For product {i} ({p['name']}), insert this EXACT HTML product card:
{product_card_html(p)}
"""

    quick_links_block = quick_links_html(products)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=7000,
        messages=[{"role": "user", "content": f"""You are a senior mental wellness content writer for mindcoreai.eu.

Write a full, publish-ready AFFILIATE REVIEW blog post:
  Title           : {topic_data['topic']}
  Primary Keyword : {kw}
  Secondary KWs   : {', '.join(topic_data['secondary_keywords'])}
  Search Intent   : {topic_data['search_intent']}

THIS IS AN AFFILIATE REVIEW POST. The structure is different from regular blog posts.

PRODUCTS TO REVIEW:
{product_details}

CRITICAL KEYWORD RULES (same as main blog):
  1. EXACT phrase "{kw}" in the H1 title
  2. EXACT phrase "{kw}" in the very first sentence
  3. EXACT phrase "{kw}" in at least 3 H2 subheadings
  4. EXACT phrase "{kw}" at least 8-10 times total
  5. No synonyms or variations \u2014 EXACT phrase only
  6. Keyword density: 1.0%-1.5%
  7. Minimum 1,200 words

STRUCTURE (follow this EXACTLY):

1. FIRST ELEMENT \u2014 Affiliate Disclosure (insert this EXACT HTML first):
{AFFILIATE_DISCLOSURE}

2. H1 TITLE with keyword and number

3. INTRO (2-3 paragraphs):
   - Start with personal experience or relatable hook
   - Mention why this product type matters for mental wellness
   - Use "{kw}" in the very first sentence

4. H2 \u2014 "Why [Product Type] Matter for Mental Wellness"
   - Explain the connection between this product and mental health
   - Include research or evidence where possible
   - Use "{kw}" naturally

5. H2 \u2014 "How We Chose the {len(products)} Best [Products]"
   - Brief methodology: what criteria were used
   - Mention comfort, value, effectiveness for mental wellness

6. H2 \u2014 Each product gets its own H2 section:
   For each product write 100-150 words of genuine review text THEN insert the product card HTML.
   The product card HTML MUST be inserted EXACTLY as provided below \u2014 do not modify it.
{product_card_instructions}

7. H2 \u2014 "How to Choose the Right [Product] for You"
   - Buying guide with practical advice
   - Include a <ul> list of factors to consider

8. H2 \u2014 FAQ section:
   <h2>Frequently Asked Questions About {kw.title()}</h2>
   5 questions using <h3> tags:
   - At least 2 questions must include the exact phrase "{kw}"
   - Answers 2-4 sentences each
   - One answer mentions MindCore AI naturally

9. QUICK LINKS SUMMARY (insert this EXACT HTML before the final CTA):
{quick_links_block}

10. FINAL CTA:
   - Brief paragraph connecting physical wellness products to mental wellness
   - "These products support your body. MindCore AI supports your mind."
   - Use this inline link once: {APP_INLINE_LINK}
   - End with this CTA button: {GP_CTA_LINK}

MANDATORY LINKS:
  Internal (include ALL 3):
{int_links}

  External (include at least 2):
{ext_links}
{cross_link_block}
TONE:
  Honest, practical, trustworthy. Like a knowledgeable friend recommending products
  they actually use. Never salesy or pushy. Acknowledge that products alone don't
  fix mental health \u2014 they support a broader wellness practice.

FORMAT:
  - Clean WordPress HTML: h1 h2 h3 p ul li strong em a div
  - Affiliate links: target="_blank" rel="noopener sponsored"
  - External links: target="_blank" rel="noopener noreferrer"
  - No html head body style script tags
  - After ALL HTML: EXCERPT: [2-3 sentence hook with "{kw}"]"""}]
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
        model="claude-sonnet-4-20250514", max_tokens=3000,
        messages=[{"role": "user", "content": f"""Post is {current_words} words \u2014 needs {MIN_WORD_COUNT}.
Add ~{needed} words by expanding product reviews or adding buying guide detail.
Use EXACT phrase "{kw}" at least 3 more times. Return COMPLETE post with EXCERPT.

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
        "peaceful and hopeful atmosphere, no faces shown, "
        "warm amber and soft teal colour grading, photorealistic. "
        "No text, no words, no letters in the image."
    )
    try:
        resp = openai_client.images.generate(
            model="gpt-image-1", prompt=cinematic_prompt,
            size="1536x1024", quality="high", n=1,
        )
        data = resp.data[0]
        if getattr(data, "url", None):
            img = requests.get(data.url, timeout=30).content
        else:
            img = base64.b64decode(data.b64_json)
        print("   Cinematic image generated (gpt-image-1)")
        return img
    except Exception as e1:
        print(f"   gpt-image-1 failed: {e1} \u2014 trying dall-e-2...")
    try:
        resp = openai_client.images.generate(
            model="dall-e-2", prompt=cinematic_prompt[:1000],
            size="1024x1024", n=1,
        )
        img = requests.get(resp.data[0].url, timeout=30).content
        print("   Cinematic image generated (dall-e-2 fallback)")
        return img
    except Exception as e2:
        raise RuntimeError(f"All image models failed. {e1} | {e2}")


def upload_image_to_wordpress(image_data, alt_text=""):
    print("Uploading image...")
    filename = f"mindcore-affiliate-{datetime.now().strftime('%Y%m%d')}.png"
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
        requests.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            headers={**auth, "Content-Type": "application/json"},
            json={"alt_text": alt_text, "caption": alt_text}, timeout=15,
        )
    return media_id, media_url


def inject_image_into_content(content, media_url, alt_text):
    if not media_url: return content
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
    auth = get_wp_auth()
    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?per_page=100&search={requests.utils.quote(category_name)}",
        headers=auth, timeout=15,
    )
    if resp.status_code == 200:
        for c in resp.json():
            if c["name"].replace("&amp;", "&").replace("&#039;", "'").lower() == category_name.lower():
                return c["id"]
    create = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers={**auth, "Content-Type": "application/json"},
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
        if resp.status_code == 201: break
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
                headers=auth, json={"featured_media": media_id}, timeout=30,
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

    media_id  = None
    media_url = None
    try:
        image_data          = generate_illustration(topic_data["image_prompt"])
        media_id, media_url = upload_image_to_wordpress(image_data, alt_text=topic_data["primary_keyword"])
    except Exception as exc:
        print(f"   Image failed: {exc}")

    post = publish_to_wordpress(topic_data, content, media_id, media_url)

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
