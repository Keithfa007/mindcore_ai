import anthropic
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os


# ── Firebase init ──────────────────────────────────────────────────────────────
def init_firebase():
    service_account_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(service_account_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Pipeline state ──────────────────────────────────────────────────────────
def get_pipeline_state(db):
    doc = db.collection("pipeline_state").document("learning").get()
    if doc.exists:
        return doc.to_dict()
    return {"used_topics": []}


def save_pipeline_state(db, state):
    db.collection("pipeline_state").document("learning").set(state)


# ── Generate learning seeds via Anthropic ─────────────────────────────────────
def generate_learning_seeds(client, used_topics):
    print("  Calling Anthropic API...")

    prompt = f"""You are a mental wellness content expert for MindCore AI.

Generate 3 new learning cards for the MindCore AI app.

MindCore AI targets adults 35+ (men AND women equally), people in recovery from alcohol/substances, and women experiencing perimenopause.

ALREADY COVERED TOPICS  - do NOT repeat:
{chr(10).join(f'  - {t}' for t in used_topics) if used_topics else '  (none yet)'}

Generate 3 NEW high-value mental wellness learning topics that:
- Are frequently searched on Google
- Fill genuine content gaps
- Are inclusive of both men and women
- Could cover: perimenopause mental health, hormonal anxiety, postpartum recovery, chronic pain & mood, loneliness, anger management, imposter syndrome, procrastination, body image, social comparison, compassion fatigue, caregiver burnout, emotional regulation, shame resilience, workplace anxiety, etc.

Each learning card should be practical, evidence-informed, and written in plain language.

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Respond ONLY in this exact JSON format  - no markdown, no preamble:
{{
  "seeds": [
    {{
      "seed_id": "url-slug-format",
      "title": "Short clear title (4-6 words)",
      "overview": "2-3 paragraph evidence-informed overview. Plain language. 150-200 words total.",
      "examples": [
        "Concrete relatable real-life example",
        "Second example",
        "Third example"
      ],
      "strategies": [
        "Specific actionable strategy doable today",
        "Second strategy",
        "Third strategy",
        "Fourth strategy"
      ],
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

Generate exactly 3 seeds."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    seeds = data["seeds"]
    print(f"   ✅  Generated {len(seeds)} seeds")
    for s in seeds:
        print(f"      - {s['title']}")
    return seeds


# ── Save seeds to Firestore ───────────────────────────────────────────────────────
def save_learning_seeds(db, seeds):
    # Clear is_new on previous items
    docs = db.collection("learning_items").where("is_new", "==", True).stream()
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"is_new": False})
        count += 1
    if count > 0:
        batch.commit()
        print(f"   ✅  Cleared is_new on {count} previous item(s)")

    saved_ids = []
    for seed in seeds:
        doc_ref = db.collection("learning_items").document()
        doc_ref.set({
            "seed_id":    seed["seed_id"],
            "title":      seed["title"],
            "overview":   seed["overview"],
            "examples":   seed["examples"],
            "strategies": seed["strategies"],
            "tags":       seed["tags"],
            "active":     True,
            "is_new":     True,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        saved_ids.append(doc_ref.id)
        print(f"   ✅  Saved: {seed['title']} ({doc_ref.id})")

    return saved_ids


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n📚  MindCore AI  - Learning Pipeline")
    print("=" * 45)

    print("\n[1/4] Connecting to Firebase...")
    db = init_firebase()
    print("      ✅ Connected")

    print("\n[2/4] Reading pipeline state...")
    state       = get_pipeline_state(db)
    used_topics = state.get("used_topics", [])
    print(f"      ✅ {len(used_topics)} topic(s) already generated")

    print("\n[3/4] Generating learning seeds (Anthropic API)...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    seeds  = generate_learning_seeds(client, used_topics)

    print("\n[4/4] Saving to Firestore...")
    saved_ids  = save_learning_seeds(db, seeds)
    new_topics = [s["title"] for s in seeds]

    save_pipeline_state(db, {
        "used_topics":  used_topics + new_topics,
        "last_run":     firestore.SERVER_TIMESTAMP,
        "last_titles":  new_topics,
    })

    print("\n" + "=" * 45)
    print("🎉  Learning Pipeline complete!")
    for title in new_topics:
        print(f"    - {title}")
    print("=" * 45 + "\n")


if __name__ == "__main__":
    main()
