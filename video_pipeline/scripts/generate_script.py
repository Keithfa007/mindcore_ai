"""
generate_script.py
MindCore AI Video Pipeline — Step 1
Picks a video topic from keywords.json and generates SEO-optimised
script, video prompt, and caption via Anthropic API.
Saves output to outputs/script_output.json
"""

import os
import json
import random
import anthropic
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
KEYWORDS   = BASE_DIR / "keywords.json"
PROMPT_TXT = BASE_DIR / "prompts" / "script_prompt.txt"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "script_output.json"

OUTPUT_DIR.mkdir(exist_ok=True)

# ── Load assets ────────────────────────────────────────────────────────────
with open(KEYWORDS, "r") as f:
    keyword_data = json.load(f)

with open(PROMPT_TXT, "r") as f:
    system_prompt = f.read()

# ── Pick a topic (rotate through list, avoid repeats) ─────────────────────
topics = keyword_data["video_topics"]
used_file = OUTPUT_DIR / "used_topics.json"

if used_file.exists():
    with open(used_file) as f:
        used = json.load(f)
else:
    used = []

# Reset if all topics have been used
available = [t for t in topics if t["topic"] not in used]
if not available:
    available = topics
    used = []

topic = random.choice(available)
used.append(topic["topic"])

with open(used_file, "w") as f:
    json.dump(used, f, indent=2)

print(f"[generate_script] Selected topic: {topic['topic']}")

# ── Build user message ────────────────────────────────────────────────────
user_message = f"""
VIDEO TOPIC: {topic['topic']}
PRIMARY KEYWORD: {topic['primary_keyword']}
CONTENT ANGLE: {topic['angle']}

Generate the full JSON output now.
"""

# ── Call Anthropic API ────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1500,
    system=system_prompt,
    messages=[{"role": "user", "content": user_message}]
)

raw = response.content[0].text.strip()

# Strip markdown fences if present
if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
        raw = raw[4:]
raw = raw.strip()

# ── Parse and save ─────────────────────────────────────────────────────────
try:
    output = json.loads(raw)
except json.JSONDecodeError as e:
    print(f"[generate_script] JSON parse error: {e}")
    print(f"[generate_script] Raw response:\n{raw}")
    raise

output["generated_at"] = datetime.utcnow().isoformat()
output["topic_angle"] = topic["angle"]

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"[generate_script] ✅ Script saved to {OUTPUT_FILE}")
print(f"[generate_script] Title: {output.get('title')}")
print(f"[generate_script] Hook:  {output.get('hook')}")
