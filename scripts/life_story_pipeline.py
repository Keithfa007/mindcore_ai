"""
Life Story Pipeline - MindCore AI
=================================

Turns ONE true personal-story "kernel" (written by K.F.) into a first-person
blog post, generates an atmospheric image, and creates it as a WordPress DRAFT.
It then notifies Telegram so K.F. can read and publish it himself.

DESIGN GUARDRAILS (do not remove):
  1. NO FABRICATION. The AI only ever expands a kernel that K.F. wrote. The
     system prompt forbids inventing any biographical fact (names, dates,
     places, events, numbers, dialogue) not present in the kernel. The story
     bank is the single source of truth for what actually happened.
  2. DRAFT ONLY. Posts are created with status="draft". Nothing about K.F.'s
     life is ever auto-published. A human (K.F.) reviews every post and hits
     publish. This is deliberate and must not be changed to "publish".
  3. INITIALS ONLY. The author is never named in full. Posts are signed "K.F."

The story bank lives in the STORY_BANK_JSON secret (NOT in this public repo),
because it is raw personal material. Format: a JSON array of objects:
  [
    {
      "id": "k01",
      "title": "optional working title",
      "theme": "e.g. the turning point",
      "kernel": "A few sentences of what ACTUALLY happened. The truth. The AI
                 may only use facts contained here.",
      "keyword": "optional SEO focus phrase"
    },
    ...
  ]

story_history.json (in this repo) records which kernel ids have been used, so
each runs a fresh one. It only stores ids, never story content.
"""

import os
import re
import json
import time
import base64
import requests

from anthropic import Anthropic
from datetime import datetime

from scripts.fal_image import generate_fal_image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WP_URL          = "https://mindcoreai.eu"
WP_USERNAME     = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

STORY_CATEGORY = os.environ.get("STORY_CATEGORY", "Recovery & Sobriety")
HISTORY_FILE   = "scripts/story_history.json"
WRITE_MODEL    = os.environ.get("STORY_MODEL", "claude-opus-4-5")

anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _call_anthropic_with_retry(client, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 5 * (attempt + 1)
            print(f"   Anthropic retry {attempt + 1}/{max_retries} in {wait}s: {e}")
            time.sleep(wait)


def get_wp_auth():
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("   Telegram not configured - skipping notify")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message,
               "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"   Telegram notify failed: {e}")


def slugify(text):
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower()).strip()
    return re.sub(r"[\s-]+", "-", text)[:70]


# ---------------------------------------------------------------------------
# Story bank + history
# ---------------------------------------------------------------------------
def load_story_bank():
    raw = os.environ.get("STORY_BANK_JSON", "").strip()
    if not raw:
        raise RuntimeError("STORY_BANK_JSON secret is empty. Add your story bank.")
    bank = json.loads(raw)
    if not isinstance(bank, list) or not bank:
        raise RuntimeError("STORY_BANK_JSON must be a non-empty JSON array.")
    return bank


def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("used", [])
    except Exception:
        return []


def pick_kernel(bank, used_ids):
    for k in bank:
        if k.get("id") and k["id"] not in used_ids:
            return k
    return None


def mark_used_on_github(used_ids, kernel_id):
    used_ids = list(used_ids) + [kernel_id]
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    body  = {"used": used_ids}
    if not token or not repo:
        # Fall back to local write (useful for local testing)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2)
        print("   GITHUB_TOKEN not set - wrote history locally only")
        return
    api_url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
    hdrs    = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    get_r   = requests.get(api_url, headers=hdrs, timeout=15)
    sha     = get_r.json().get("sha") if get_r.status_code == 200 else None
    encoded = base64.b64encode(json.dumps(body, indent=2).encode()).decode()
    payload = {"message": f"life-story: mark kernel used - {kernel_id}", "content": encoded}
    if sha:
        payload["sha"] = sha
    put = requests.put(api_url, headers=hdrs, json=payload, timeout=15)
    if put.status_code in (200, 201):
        print(f"   History updated - {kernel_id} marked used")
    else:
        print(f"   History update failed: {put.text}")


# ---------------------------------------------------------------------------
# Write the post from a kernel (anti-fabrication)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You help K.F., the founder of MindCore AI, turn ONE true memory from his own life into a first-person blog post for people who feel alone.

ABSOLUTE RULES (a violation makes the post unusable):
1. TRUTH ONLY. Use ONLY the facts contained in the KERNEL provided. You must NOT invent or add any concrete biographical detail that is not in the kernel: no specific names of people, no dates, no place names, no job titles, no events, no dialogue, and no numbers that the kernel did not give you. If the kernel is thin, stay emotionally honest and general rather than inventing specifics. You are shaping a true memory into good prose, not writing fiction.
2. NEVER state the founder's full name. He is referred to only as "I" in the body, and the piece is signed with his initials "K.F." on its own line at the very end.
3. Write in raw, honest, plain first-person. This is a man who suffered in silence for years and is now reaching back for others. Not clinical, not corporate, not salesy. Short sentences are welcome.
4. Do NOT use em dashes anywhere. Use commas, full stops, or "and".
5. End the body with one short, gentle line that MindCore AI exists for people who feel this way. Soft, never a hard sell.
6. Length: roughly 700 to 950 words.

Return your answer in EXACTLY this structure and nothing else:

TITLE: <a human, non-clickbait title>
META: <SEO meta description, max 155 characters>
EXCERPT: <one or two sentence summary>
IMAGE_PROMPT: <a cinematic, atmospheric, NON-literal image concept with NO people's faces and NO text: mood, light, place, symbolism>
BODY:
<the post as clean HTML using <p> and <h2> tags, signed with a final line: <p>K.F.</p>>"""


def write_story(kernel):
    user = f"""KERNEL (the only source of truth - do not add facts beyond this):

Theme: {kernel.get('theme', '')}
Working title: {kernel.get('title', '')}
SEO focus (optional): {kernel.get('keyword', '')}

What actually happened:
{kernel['kernel']}
"""
    resp = _call_anthropic_with_retry(
        anthropic_client,
        model=WRITE_MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def parse_sections(text):
    def grab(label, nxt):
        m = re.search(rf"{label}:\s*(.*?)(?=\n{nxt}:|\nBODY:|$)", text, re.S)
        return m.group(1).strip() if m else ""
    title = grab("TITLE", "META")
    meta  = grab("META", "EXCERPT")
    excerpt = grab("EXCERPT", "IMAGE_PROMPT")
    image_prompt = grab("IMAGE_PROMPT", "BODY")
    bm = re.search(r"BODY:\s*(.*)$", text, re.S)
    body = bm.group(1).strip() if bm else text
    return {
        "title": title or "A Note From K.F.",
        "meta": meta[:155],
        "excerpt": excerpt,
        "image_prompt": image_prompt,
        "body": body,
    }


# ---------------------------------------------------------------------------
# WordPress: image + DRAFT post
# ---------------------------------------------------------------------------
def upload_image(image_bytes, alt_text=""):
    if not image_bytes:
        return None, None
    filename = f"mindcore-story-{datetime.now().strftime('%Y%m%d%H%M')}.png"
    auth = get_wp_auth()
    headers = {**auth,
               "Content-Disposition": f'attachment; filename="{filename}"',
               "Content-Type": "image/png"}
    resp = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers,
                         data=image_bytes, timeout=60)
    if resp.status_code != 201:
        print(f"   Image upload failed ({resp.status_code}): {resp.text[:200]}")
        return None, None
    media = resp.json()
    if alt_text:
        time.sleep(2)
        requests.post(f"{WP_URL}/wp-json/wp/v2/media/{media['id']}",
                      headers={**auth, "Content-Type": "application/json"},
                      json={"alt_text": alt_text}, timeout=15)
    return media["id"], media.get("source_url", "")


def resolve_category_id(name):
    auth = get_wp_auth()
    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?per_page=100&search={requests.utils.quote(name)}",
        headers=auth, timeout=15)
    if resp.status_code == 200:
        for c in resp.json():
            if c["name"].replace("&amp;", "&").lower() == name.lower():
                return c["id"]
    create = requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
                           headers={**auth, "Content-Type": "application/json"},
                           json={"name": name}, timeout=15)
    if create.status_code == 201:
        return create.json()["id"]
    return None


def inject_image(content, media_url, alt):
    if not media_url:
        return content
    fig = (f'\n<figure class="wp-block-image size-large">'
           f'<img src="{media_url}" alt="{alt}" class="wp-image"/></figure>\n')
    pos = content.find("</p>")
    return (content[:pos + 4] + fig + content[pos + 4:]) if pos != -1 else fig + content


def create_draft(sections, media_id, media_url):
    content = sections["body"]
    if media_url:
        content = inject_image(content, media_url, sections["title"])
    cat_id = resolve_category_id(STORY_CATEGORY)
    auth = {**get_wp_auth(), "Content-Type": "application/json"}
    payload = {
        "title":   sections["title"],
        "content": content,
        "excerpt": sections["excerpt"],
        "slug":    slugify(sections["title"]),
        "status":  "draft",          # GUARDRAIL: never auto-publish personal stories
        "categories": [cat_id] if cat_id else [],
        "featured_media": media_id or 0,
        "meta": {
            "_yoast_wpseo_metadesc": sections["meta"],
            "_yoast_wpseo_title":    sections["title"],
        },
    }
    resp = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=auth,
                         json=payload, timeout=30)
    if resp.status_code != 201:
        raise RuntimeError(f"Draft create failed ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Life Story Pipeline - starting")
    bank = load_story_bank()
    used = load_history()
    kernel = pick_kernel(bank, used)

    if not kernel:
        msg = ("\U0001f4d6 *Life Story Pipeline*\nStory bank is empty - every kernel "
               "has been used. Add more true kernels to the STORY_BANK_JSON secret "
               "when you're ready for the next post.")
        print("   No unused kernels left.")
        send_telegram(msg)
        return

    print(f"   Kernel: {kernel['id']} - {kernel.get('theme', '')}")
    raw = write_story(kernel)
    sections = parse_sections(raw)
    print(f"   Title: {sections['title']}")

    image_bytes = None
    try:
        image_bytes = generate_fal_image(
            sections["image_prompt"] or "soft dawn light through a window, quiet hope, cinematic, no people",
            image_size="landscape_4_3", model="pro")
    except Exception as e:
        print(f"   Image generation failed (continuing without): {e}")

    media_id, media_url = upload_image(image_bytes, sections["title"]) if image_bytes else (None, None)
    post = create_draft(sections, media_id, media_url)

    post_id  = post["id"]
    edit_url = f"{WP_URL}/wp-admin/post.php?post={post_id}&action=edit"
    preview  = post.get("link", "")

    mark_used_on_github(used, kernel["id"])

    remaining = sum(1 for k in bank if k.get("id") and k["id"] not in used) - 1
    msg = (f"\U0001f4d6 *New life story DRAFT ready to review*\n\n"
           f"*{sections['title']}*\n\n"
           f"Kernel: `{kernel['id']}`  |  Theme: {kernel.get('theme', '')}\n"
           f"Kernels left in bank: {remaining}\n\n"
           f"Read, edit, and publish it here:\n{edit_url}\n\n"
           f"_Draft only. Nothing is live until you hit Publish._")
    send_telegram(msg)
    print(f"   DRAFT created (id {post_id}). Review: {edit_url}")


if __name__ == "__main__":
    main()
