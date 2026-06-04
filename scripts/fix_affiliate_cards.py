"""One-time fix: removes duplicate image and updates product card colours in the weighted blankets post."""
import os
import base64
import re
import cloudscraper

WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]
POST_SLUG       = "best-weighted-blankets-for-anxiety"

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

def auth():
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

# Fixed product cards with full inline colour styles
FIXED_CARDS = [
    (
        "Bearaby Hand-Knit Weighted Blanket",
        '<div style="background:#0c0c24;border:2px solid #3ecfb2;border-radius:12px;padding:20px;margin:20px 0;color:#e0e8e8;">'
        '<h3 style="color:#ffffff;margin-top:0;">Bearaby Hand-Knit Weighted Blanket</h3>'
        '<p style="color:#b0c8c8;">Hand-knit from organic cotton, naturally cooling, machine washable</p>'
        '<ul style="color:#b0c8c8;padding-left:20px;">'
        '<li><strong style="color:#3ecfb2;">Best for:</strong> Premium quality, breathable, eco-friendly</li>'
        '<li><strong style="color:#3ecfb2;">Price:</strong> $149-249</li>'
        '<li><strong style="color:#3ecfb2;">Weight:</strong> 5-25 lbs</li>'
        '</ul>'
        '<p style="margin-top:15px;"><a href="https://amzn.to/4nYm3a0" target="_blank" rel="noopener sponsored" '
        'style="background:#3ecfb2;color:#07071a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;">'
        '\U0001f449 View on Amazon</a></p></div>'
    ),
    (
        "YnM Weighted Blanket",
        '<div style="background:#0c0c24;border:2px solid #3ecfb2;border-radius:12px;padding:20px;margin:20px 0;color:#e0e8e8;">'
        '<h3 style="color:#ffffff;margin-top:0;">YnM Weighted Blanket</h3>'
        '<p style="color:#b0c8c8;">7-layer system with cooling glass beads, multiple sizes and colours</p>'
        '<ul style="color:#b0c8c8;padding-left:20px;">'
        '<li><strong style="color:#3ecfb2;">Best for:</strong> Best value, cooling glass beads, all-season</li>'
        '<li><strong style="color:#3ecfb2;">Price:</strong> $35-65</li>'
        '<li><strong style="color:#3ecfb2;">Weight:</strong> 5-25 lbs</li>'
        '</ul>'
        '<p style="margin-top:15px;"><a href="https://amzn.to/4dY0YrF" target="_blank" rel="noopener sponsored" '
        'style="background:#3ecfb2;color:#07071a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;">'
        '\U0001f449 View on Amazon</a></p></div>'
    ),
    (
        "Yescool Weighted Blanket",
        '<div style="background:#0c0c24;border:2px solid #3ecfb2;border-radius:12px;padding:20px;margin:20px 0;color:#e0e8e8;">'
        '<h3 style="color:#ffffff;margin-top:0;">Yescool Weighted Blanket</h3>'
        '<p style="color:#b0c8c8;">Premium glass beads, breathable fabric, great for hot sleepers</p>'
        '<ul style="color:#b0c8c8;padding-left:20px;">'
        '<li><strong style="color:#3ecfb2;">Best for:</strong> Budget-friendly, breathable, machine washable</li>'
        '<li><strong style="color:#3ecfb2;">Price:</strong> $30-50</li>'
        '<li><strong style="color:#3ecfb2;">Weight:</strong> 15-25 lbs</li>'
        '</ul>'
        '<p style="margin-top:15px;"><a href="https://amzn.to/4dTzZNM" target="_blank" rel="noopener sponsored" '
        'style="background:#3ecfb2;color:#07071a;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;">'
        '\U0001f449 View on Amazon</a></p></div>'
    ),
]

FIXED_QUICK_LINKS = (
    '<div style="background:#0c0c24;border:2px solid #a594f9;border-radius:12px;padding:20px;margin:30px 0;color:#e0e8e8;">'
    '<h2 style="color:#ffffff;margin-top:0;">Quick Links \u2014 All Products</h2>'
    '<p style="margin:6px 0;">\U0001f449 <a href="https://amzn.to/4nYm3a0" target="_blank" rel="noopener sponsored" style="color:#3ecfb2;text-decoration:none;">Bearaby Hand-Knit Weighted Blanket</a></p>'
    '<p style="margin:6px 0;">\U0001f449 <a href="https://amzn.to/4dY0YrF" target="_blank" rel="noopener sponsored" style="color:#3ecfb2;text-decoration:none;">YnM Weighted Blanket</a></p>'
    '<p style="margin:6px 0;">\U0001f449 <a href="https://amzn.to/4dTzZNM" target="_blank" rel="noopener sponsored" style="color:#3ecfb2;text-decoration:none;">Yescool Weighted Blanket</a></p>'
    '</div>'
)


def get_post():
    print(f"Fetching post: {POST_SLUG}...")
    resp = scraper.get(
        f"{WP_URL}/wp-json/wp/v2/posts?slug={POST_SLUG}&status=publish",
        headers=auth(), timeout=15,
    )
    posts = resp.json()
    if not posts:
        raise RuntimeError(f"Post '{POST_SLUG}' not found")
    post = posts[0]
    print(f"   Found: '{post['title']['rendered']}' (ID: {post['id']})")
    return post["id"], post["content"]["rendered"]


def fix_content(content):
    fixed = content

    # 1. Remove duplicate injected image (wp-block-image figure)
    img_pattern = r'\n?<figure class="wp-block-image size-full"><img[^/]*/></figure>\n?'
    img_matches = list(re.finditer(img_pattern, fixed, re.DOTALL))
    if len(img_matches) > 0:
        # Remove the first occurrence (injected into body — featured image handles display)
        fixed = fixed[:img_matches[0].start()] + fixed[img_matches[0].end():]
        print(f"   Removed duplicate injected image")
    else:
        print("   No duplicate image found")

    # 2. Fix product cards
    for product_name, new_card in FIXED_CARDS:
        pattern = r'<div[^>]*background:#0c0c24[^>]*>(?:(?!</div>).)*?' + re.escape(product_name) + r'.*?</div>'
        match = re.search(pattern, fixed, re.DOTALL | re.IGNORECASE)
        if match:
            fixed = fixed[:match.start()] + new_card + fixed[match.end():]
            print(f"   Fixed card: {product_name}")
        else:
            print(f"   Card not found: {product_name}")

    # 3. Fix quick links box
    ql_pattern = r'<div[^>]*background:#0c0c24[^>]*border:2px solid #a594f9[^>]*>.*?Quick Links.*?</div>'
    ql_match = re.search(ql_pattern, fixed, re.DOTALL | re.IGNORECASE)
    if ql_match:
        fixed = fixed[:ql_match.start()] + FIXED_QUICK_LINKS + fixed[ql_match.end():]
        print("   Fixed quick links box")
    else:
        print("   Quick links box not found")

    return fixed


def update_post(post_id, content):
    print(f"Updating post ID {post_id}...")
    resp = scraper.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        headers=auth(),
        json={"content": content},
        timeout=30,
    )
    if resp.status_code == 200:
        print(f"   Updated! -> {resp.json().get('link', 'N/A')}")
    else:
        raise RuntimeError(f"Update failed ({resp.status_code}): {resp.text[:300]}")


def main():
    print("\n== Fixing weighted blankets post ==")
    post_id, content = get_post()
    fixed            = fix_content(content)
    update_post(post_id, fixed)
    print("\nDone! Duplicate image removed, cards fully visible. \u2705")


if __name__ == "__main__":
    main()
