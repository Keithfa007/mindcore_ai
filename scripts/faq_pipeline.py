import anthropic
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import random

# ── All existing local theme titles (from frequently_asked.dart) ───────────────
LOCAL_THEMES = [
    "Recognition & Self\u2011Awareness",
    "Stigma, Identity & Masculinity",
    "Stress, Anxiety & Depression",
    "Relationships & Communication",
    "Work, Purpose & Midlife Challenges",
    "Healing, Therapy & Lifestyle Tools",
    "Growth, Motivation & Loneliness",
]


# ── Firebase init ──────────────────────────────────────────────────────────────
def init_firebase():
    service_account_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(service_account_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Pipeline state ─────────────────────────────────────────────────────────────
def get_pipeline_state(db):
    doc = db.collection("pipeline_state").document("faq").get()
    if doc.exists:
        return doc.to_dict()
    return {"used_themes": [], "expanded_themes": []}


def save_pipeline_state(db, state):
    db.collection("pipeline_state").document("faq").set(state)


# ── PART 1: Generate new FAQ theme ────────────────────────────────────────────
def generate_new_faq_theme(client, used_themes):
    print("  Calling Anthropic API for new theme...")

    prompt = f"""You are a mental wellness content expert for MindCore AI.

Generate one new FAQ theme with questions and answers for the MindCore AI app.

MindCore AI targets:
- Adults 35+ (men AND women equally)
- People in recovery from alcohol or substances
- Women experiencing perimenopause and hormonal mental health challenges
- People dealing with anxiety, stress, depression, loneliness
- Anyone who feels alone and needs support

ALREADY COVERED THEMES - do NOT repeat:
{chr(10).join(f'  - {t}' for t in used_themes) if used_themes else '  (none yet)'}

Pick ONE new high-value theme based on real Google search demand. Consider:
Perimenopause & Mental Health, Women in Recovery, Postpartum Anxiety, Grief & Loss,
Hormonal Mood Changes, Body Image & Self-Esteem, Caregiver Burnout, Loneliness in Midlife,
Chronic Pain & Mental Health, Emotional Eating, Workplace Trauma, Social Media & Anxiety,
Anger Management, Imposter Syndrome, Compassion Fatigue, Financial Anxiety, Parenting Stress.

Generate exactly 8 questions and answers.
Tone: warm, honest, evidence-informed, non-clinical. Like a trusted friend who has been through it.
Gender-inclusive - speak to both men and women.

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Respond ONLY in this exact JSON format - no markdown, no preamble:
{{
  "title": "Theme Title",
  "items": [
    {{
      "question": "A real question someone would search on Google",
      "answer": "A warm, honest, 150-250 word answer that genuinely helps."
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    print(f"   OK  New theme  : {data['title']}")
    print(f"   OK  Questions  : {len(data['items'])}")
    return data


def save_new_faq_theme(db, theme_data):
    docs  = db.collection("faq_themes").where("is_new", "==", True).stream()
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"is_new": False})
        count += 1
    if count > 0:
        batch.commit()
        print(f"   OK  Cleared is_new on {count} previous theme(s)")

    doc_ref = db.collection("faq_themes").document()
    doc_ref.set({
        "title":      theme_data["title"],
        "items":      theme_data["items"],
        "active":     True,
        "is_new":     True,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    print(f"   OK  Saved (ID: {doc_ref.id})")
    return doc_ref.id


# ── PART 2: Add new questions to an existing theme ────────────────────────────
def pick_theme_to_expand(db, expanded_themes, new_theme_title):
    firestore_themes = [
        doc.to_dict().get("title", "")
        for doc in db.collection("faq_themes").where("active", "==", True).stream()
    ]

    all_themes = LOCAL_THEMES + firestore_themes
    candidates = [
        t for t in all_themes
        if t not in expanded_themes and t != new_theme_title
    ]

    if not candidates:
        candidates = [t for t in all_themes if t != new_theme_title]

    chosen = random.choice(candidates)
    print(f"   OK  Expanding  : {chosen}")
    return chosen


def generate_extra_questions(client, theme_title):
    print(f"  Generating extra questions for: {theme_title}...")

    prompt = f"""You are a mental wellness content expert for MindCore AI.

The app already has a FAQ theme called "{theme_title}" with existing questions and answers.

Generate 4 NEW questions and answers to add to this theme.

Requirements:
- Questions must be NEW and different from what already exists in this theme
- Based on real Google "People Also Ask" search patterns
- Gender-inclusive - relevant to both men and women 35+
- Warm, honest, evidence-informed tone. 150-250 words per answer.
- Particularly welcome: questions relevant to women, perimenopause, recovery, or midlife

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Respond ONLY in this exact JSON format - no markdown, no preamble:
{{
  "extra_items": [
    {{
      "question": "A real question someone searches on Google",
      "answer": "A warm, honest, helpful 150-250 word answer."
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw  = response.content[0].text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    print(f"   OK  Extra Q&As : {len(data['extra_items'])}")
    return data["extra_items"]


def save_extra_questions(db, theme_title, extra_items):
    existing_docs = list(
        db.collection("faq_extra_questions")
        .where("theme_title", "==", theme_title)
        .limit(1)
        .stream()
    )

    if existing_docs:
        doc_ref       = existing_docs[0].reference
        current_items = existing_docs[0].to_dict().get("extra_items", [])
        doc_ref.update({
            "extra_items": current_items + extra_items,
            "updated_at":  firestore.SERVER_TIMESTAMP,
        })
        print(f"   OK  Appended {len(extra_items)} questions to existing doc")
    else:
        doc_ref = db.collection("faq_extra_questions").document()
        doc_ref.set({
            "theme_title": theme_title,
            "extra_items": extra_items,
            "created_at":  firestore.SERVER_TIMESTAMP,
            "updated_at":  firestore.SERVER_TIMESTAMP,
        })
        print(f"   OK  Created new extra questions doc ({doc_ref.id})")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n  MindCore AI - FAQ Pipeline")
    print("=" * 50)

    print("\n[1/6] Connecting to Firebase...")
    db = init_firebase()
    print("      OK Connected")

    print("\n[2/6] Reading pipeline state...")
    state           = get_pipeline_state(db)
    used_themes     = state.get("used_themes", [])
    expanded_themes = state.get("expanded_themes", [])
    print(f"      OK {len(used_themes)} new theme(s) generated so far")
    print(f"      OK {len(expanded_themes)} theme(s) expanded so far")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("\n[3/6] Generating new FAQ theme...")
    new_theme = generate_new_faq_theme(client, used_themes)

    print("\n[4/6] Saving new theme to Firestore...")
    theme_id = save_new_faq_theme(db, new_theme)

    print("\n[5/6] Expanding existing theme with new questions...")
    theme_to_expand = pick_theme_to_expand(db, expanded_themes, new_theme["title"])
    extra_items     = generate_extra_questions(client, theme_to_expand)
    save_extra_questions(db, theme_to_expand, extra_items)

    print("\n[6/6] Updating pipeline state...")
    save_pipeline_state(db, {
        "used_themes":     used_themes + [new_theme["title"]],
        "expanded_themes": expanded_themes + [theme_to_expand],
        "last_run":        firestore.SERVER_TIMESTAMP,
        "last_new_theme":  new_theme["title"],
        "last_expanded":   theme_to_expand,
    })
    print("      OK State saved")

    print("\n" + "=" * 50)
    print("Done - FAQ Pipeline complete!")
    print(f"    New theme : {new_theme['title']} ({theme_id})")
    print(f"    Expanded  : {theme_to_expand} (+{len(extra_items)} questions)")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
