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
    doc = db.collection("pipeline_state").document("faq").get()
    if doc.exists:
        return doc.to_dict()
    return {"used_themes": []}


def save_pipeline_state(db, state):
    db.collection("pipeline_state").document("faq").set(state)


# ── Generate FAQ theme via Anthropic ───────────────────────────────────────────
def generate_faq_theme(client, used_themes):
    print("  Calling Anthropic API...")

    prompt = f"""You are a mental wellness content expert for MindCore AI.

Generate one new FAQ theme with questions and answers for the MindCore AI app.

MindCore AI is a mental wellness companion app targeting:
- Adults 35+ (men AND women equally)
- People in recovery from alcohol or substances
- Women experiencing perimenopause and hormonal mental health challenges
- People dealing with anxiety, stress, depression, loneliness
- Anyone who feels alone and needs support

ALREADY COVERED THEMES — do NOT repeat these:
{chr(10).join(f'  - {t}' for t in used_themes) if used_themes else '  (none yet)'}

Your task: pick ONE new high-value theme that:
- Is based on real Google search patterns ("People Also Ask" style questions)
- Is gender-inclusive and relevant to our audience
- Fills a genuine content gap
- Could cover topics like: perimenopause mental health, women in recovery, hormonal mood, postpartum anxiety, grief, loneliness, chronic pain, workplace trauma, emotional eating, body image, compassion fatigue, caregiver burnout, midlife identity, social anxiety, etc.

Generate exactly 8 questions and answers.
Tone: warm, honest, evidence-informed, non-clinical. Like a trusted friend who has been through it.

Respond ONLY in this exact JSON format — no markdown, no preamble:
{{
  "title": "Theme Title",
  "items": [
    {{
      "question": "A real question someone would search on Google",
      "answer": "A warm, honest, 150-250 word answer that genuinely helps. Evidence-based but human."
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    print(f"   ✅  Theme     : {data['title']}")
    print(f"   ✅  Questions : {len(data['items'])}")
    return data


# ── Clear previous is_new and save to Firestore ───────────────────────────────────
def save_faq_theme(db, theme_data):
    # Clear is_new on previous themes
    docs = db.collection("faq_themes").where("is_new", "==", True).stream()
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"is_new": False})
        count += 1
    if count > 0:
        batch.commit()
        print(f"   ✅  Cleared is_new on {count} previous theme(s)")

    doc_ref = db.collection("faq_themes").document()
    doc_ref.set({
        "title":      theme_data["title"],
        "items":      theme_data["items"],
        "active":     True,
        "is_new":     True,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    print(f"   ✅  Saved (ID: {doc_ref.id})")
    return doc_ref.id


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n❓  MindCore AI — FAQ Pipeline")
    print("=" * 45)

    print("\n[1/4] Connecting to Firebase...")
    db = init_firebase()
    print("      ✅ Connected")

    print("\n[2/4] Reading pipeline state...")
    state       = get_pipeline_state(db)
    used_themes = state.get("used_themes", [])
    print(f"      ✅ {len(used_themes)} theme(s) already generated")

    print("\n[3/4] Generating FAQ theme (Anthropic API)...")
    client     = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    theme_data = generate_faq_theme(client, used_themes)

    print("\n[4/4] Saving to Firestore...")
    theme_id = save_faq_theme(db, theme_data)

    save_pipeline_state(db, {
        "used_themes": used_themes + [theme_data["title"]],
        "last_run":    firestore.SERVER_TIMESTAMP,
        "last_theme":  theme_data["title"],
    })

    print("\n" + "=" * 45)
    print("🎉  FAQ Pipeline complete!")
    print(f"    Theme : {theme_data['title']}")
    print(f"    ID    : {theme_id}")
    print("=" * 45 + "\n")


if __name__ == "__main__":
    main()
