"""One-time fix: removes duplicate image from the weighted blankets post."""
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


def get_post():
    print(f"Fetching post: {POST_SLUG}...")
    resp = scraper.get(
        f"{WP_URL}/wp-json/wp/v2/posts?slug={POST_SLUG}&status=publish&context=edit",
        headers=auth(), timeout=15,
    )
    posts = resp.json()
    if not posts:
        raise RuntimeError(f"Post not found")
    post = posts[0]
    print(f"   Found: '{post['title']['rendered']}' (ID: {post['id']})")
    # Use raw content (context=edit gives us the unrendered content)
    content = post["content"].get("raw") or post["content"].get("rendered", "")
    print(f"   Content length: {len(content)} chars")
    return post["id"], content


def remove_duplicate_image(content):
    """Remove all wp-block-image figures from content body.
    The featured image shows at the top automatically — no need for it in body."""

    # Pattern 1: self-closing img tag
    pattern1 = re.compile(
        r'\s*<figure[^>]*class=["\'][^"\']*(wp-block-image|wp-image)[^"\'][^>]*>'
        r'.*?<img[^>]*/?>.*?</figure>\s*',
        re.DOTALL | re.IGNORECASE
    )

    # Pattern 2: figure with any img inside (broader)
    pattern2 = re.compile(
        r'\s*<figure\b[^>]*>\s*<img\b[^>]*/?>\s*</figure>\s*',
        re.DOTALL | re.IGNORECASE
    )

    # Show what we find before removing
    matches1 = list(pattern1.finditer(content))
    matches2 = list(pattern2.finditer(content))
    print(f"   Pattern 1 matches: {len(matches1)}")
    print(f"   Pattern 2 matches: {len(matches2)}")

    # Show first 200 chars of each match
    for i, m in enumerate(matches2):
        print(f"   Match {i+1}: {m.group()[:150].strip()}...")

    # Remove using whichever pattern found something
    if matches1:
        fixed = pattern1.sub('', content)
        print(f"   Removed {len(matches1)} figure(s) using pattern 1")
        return fixed
    elif matches2:
        fixed = pattern2.sub('', content)
        print(f"   Removed {len(matches2)} figure(s) using pattern 2")
        return fixed
    else:
        # Last resort: search for any <img src= tag that's inside a figure
        print("   Trying raw string search...")
        # Find all img tags in content and show them
        imgs = re.findall(r'<img[^>]+>', content, re.IGNORECASE)
        print(f"   Found {len(imgs)} img tags in content:")
        for img in imgs:
            print(f"     {img[:120]}")
        print("   No figure pattern matched — check output above to diagnose")
        return content


def update_post(post_id, content):
    print(f"\nUpdating post ID {post_id}...")
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
    print("\n== Removing duplicate image from weighted blankets post ==")
    post_id, content = get_post()
    fixed            = remove_duplicate_image(content)
    if fixed != content:
        update_post(post_id, fixed)
        print("\nDone! Duplicate image removed. \u2705")
    else:
        print("\nNo changes made — check the img tag output above to diagnose.")


if __name__ == "__main__":
    main()
