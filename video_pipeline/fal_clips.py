"""
MindCore AI -- fal.ai Scene Clip Generator v2.1
================================================
Generates all 5 scene clips via fal.ai Wan 2.5.
Emotional arc: cold (hook/problem) -> warm (story/cta).

v2.1: Full rotation across ALL 4 scene types (hook, problem, story, cta).
      12 hook | 15 problem | 10 story | 10 CTA settings -- male + female separate.
      Caucasian Western European subjects enforced throughout.
      No two consecutive videos should look the same.

Cost: ~$0.25 per 5-second clip at $0.05/sec.
"""

import random
from pathlib import Path
import requests

FAL_MODEL = "fal-ai/wan-25-preview/text-to-video"

NEGATIVE_PROMPT = (
    "Asian, East Asian, South Asian, Middle Eastern, African, Latino, "
    "wounds, injuries, scars, blood, medical, needles, syringes, "
    "war, violence, self-harm, bright sunlight, cheerful, sunny, smiling, "
    "outdoor daylight, beach, text, watermark, logo, anime, cartoon, CGI, "
    "busy crowd, distorted faces, blurry faces, multiple people"
)

BASE = "Cinematic mental wellness short-form video. Photorealistic, film grain. 9:16 vertical. NO injuries, NO wounds, NO scars. "
COLD = "Highly desaturated cold blue-grey colour grade. "
WARM_HINT = "Neutral grade with very slight warmth emerging. "
WARM_FULL = "Warm amber-gold colour grade, soft bokeh. "

# ---------------------------------------------------------------------------
# HOOK scenes -- 12 variations each
# ---------------------------------------------------------------------------
HOOK_MALE = [
    BASE + COLD + "Extreme close-up of a Caucasian Western European man's face, tired and emotionally heavy. Dark moody bedroom interior, single soft side light catching his cheekbone, eyes downcast. Very slow subtle camera push into face. Shallow depth of field.",
    BASE + COLD + "Close-up of a Caucasian Western European man's hands clasped together, resting on his knees. Dark interior, dim light from one side, very still. Slow downward camera drift. The hands carry the weight of the scene.",
    BASE + COLD + "Profile close-up of a Caucasian Western European man staring at nothing, seated in darkness. A single strip of light from a doorway crosses his face. Slow lateral camera drift. Hollow expression.",
    BASE + COLD + "Extreme close-up of a Caucasian Western European man's eyes, barely open, red-rimmed, unfocused. Dark background, soft ambient side light. Camera holds completely still. Raw exhaustion.",
    BASE + COLD + "A Caucasian Western European man from behind, sitting on the edge of a bed in a dark room, shoulders rounded, head slightly bowed. Slow push toward him from behind. Single lamp, long shadow.",
    BASE + COLD + "Close-up of a Caucasian Western European man's face reflected in a dark bathroom mirror, looking down at the sink. Dim overhead light, still. Slow subtle zoom. Disconnected from his own reflection.",
    BASE + COLD + "A Caucasian Western European man's hands around a mug on a dark kitchen table, not drinking, just holding it. 2am light, very dim. Camera drifts slowly sideways. Stillness.",
    BASE + COLD + "Close-up of a Caucasian Western European man sitting in a parked car at night, hands on the wheel, staring straight ahead into the dark. Streetlight from outside. Camera slow push from passenger side.",
    BASE + COLD + "Extreme close-up of a Caucasian Western European man's jaw and neck, head slightly tilted back, leaning against a wall in darkness. Slow upward camera drift. Ceiling out of focus above.",
    BASE + COLD + "A Caucasian Western European man sitting on the floor, back against a wall in a dark hallway, knees up, arms resting on knees. Single light from far away. Camera slow push toward him.",
    BASE + COLD + "Close-up of a Caucasian Western European man's face from slightly above, lying in bed staring at the ceiling. Dark room, very faint ambient light. Camera very slowly pulling back. Motionless.",
    BASE + COLD + "Silhouette of a Caucasian Western European man standing at a window at night, city lights and rain behind him, interior in darkness. Slow zoom out. Only his outline visible.",
]

HOOK_FEMALE = [
    BASE + COLD + "Extreme close-up of a Caucasian Western European woman's face, tired and emotionally hollow. Dark moody interior, single soft side light, eyes downcast or barely open. Very slow camera push. Shallow depth of field.",
    BASE + COLD + "Close-up of a Caucasian Western European woman's hands in her lap, fingers loosely intertwined. Dark interior, dim ambient light. Slow downward camera drift. Stillness and weight.",
    BASE + COLD + "Profile close-up of a Caucasian Western European woman looking at nothing, seated in darkness. Single strip of light from a doorway crossing her face. Slow lateral drift. Empty expression.",
    BASE + COLD + "Extreme close-up of a Caucasian Western European woman's eyes, slightly red-rimmed, unfocused, not crying. Soft dark background, ambient side light. Camera holds still. Raw emotional weight.",
    BASE + COLD + "A Caucasian Western European woman from behind, seated on the edge of a bed in a dark bedroom, shoulders slightly rounded. Slow push from behind. Single lamp, long shadow.",
    BASE + COLD + "A Caucasian Western European woman standing at a bathroom mirror looking down at the sink, dim light, hair loose around her face. Slow subtle zoom. Disconnected from her own reflection.",
    BASE + COLD + "A Caucasian Western European woman's hands wrapped around a mug on a dark kitchen table at night, not drinking. Slow sideways camera drift. Complete stillness.",
    BASE + COLD + "A Caucasian Western European woman sitting in a parked car at night, hands in her lap, staring through the windscreen into the dark. Streetlight from outside. Camera slow push from the back seat.",
    BASE + COLD + "Extreme close-up of a Caucasian Western European woman's collarbone and chin, head tilted slightly back, leaning against a wall in darkness. Slow upward drift. Ceiling softly out of focus.",
    BASE + COLD + "A Caucasian Western European woman sitting on the floor in a dark hallway, knees drawn up, arms around her knees. Single far light. Camera slow push toward her.",
    BASE + COLD + "Close-up of a Caucasian Western European woman's face from slightly above, lying in bed staring at the ceiling in a dark room. Very faint light. Camera very slowly pulling back.",
    BASE + COLD + "Silhouette of a Caucasian Western European woman standing at a rain-streaked window at night, city lights behind her, interior dark. Slow zoom out from behind.",
]

# ---------------------------------------------------------------------------
# PROBLEM scenes -- 15 variations each
# ---------------------------------------------------------------------------
PROBLEM_MALE = [
    BASE + COLD + "A Caucasian Western European man sitting on the edge of a bed in a dark bedroom at night, head slightly bowed, hands resting on knees. Dim bedside lamp the only light. Slow subtle camera drift.",
    BASE + COLD + "A Caucasian Western European man sitting alone at a dark kitchen table at 2am, hands wrapped around a mug, staring at nothing. City light barely visible through the window. Camera very slowly circles.",
    BASE + COLD + "A Caucasian Western European man sitting in the driver's seat of a parked car at night, engine off, hands on the wheel, staring forward into the dark. Streetlight casting long shadows. Slow push from passenger side.",
    BASE + COLD + "A Caucasian Western European man standing at a bathroom sink, looking down, hands gripping the basin edge. Dim overhead light. Slow downward camera tilt.",
    BASE + COLD + "A Caucasian Western European man leaning against a shadowed hallway wall, arms crossed, head tilted back slightly. Single strip of light from a doorway. Slow lateral camera drift.",
    BASE + COLD + "A Caucasian Western European man sitting on a sofa in a dark living room, elbows on knees, face in his hands. Rain and city lights on the window behind him. Camera very slowly pulling back.",
    BASE + COLD + "A Caucasian Western European man lying on his back on a bed fully clothed, staring at the ceiling in a dark room. Arms at his sides. Camera very slow pull back from above.",
    BASE + COLD + "A Caucasian Western European man sitting on a staircase in low light, elbows on knees, looking down at the step below him. Shadows across his face. Slow downward camera drift.",
    BASE + COLD + "A Caucasian Western European man standing in a dark kitchen at night, leaning against the counter, arms crossed, staring at the floor. Faint light from outside. Slow push toward him.",
    BASE + COLD + "A Caucasian Western European man sitting with his back against a bed on the bedroom floor, knees up, looking at nothing. Dim lamp above and behind him. Slow lateral drift.",
    BASE + COLD + "A Caucasian Western European man standing at a window at night, one hand on the glass, looking out at city lights and rain. Interior almost completely dark. Slow zoom toward his back.",
    BASE + COLD + "A Caucasian Western European man sitting at a desk late at night, chair pushed back slightly, staring at a dark screen. Single desk lamp. Camera slow drift sideways.",
    BASE + COLD + "A Caucasian Western European man lying on a sofa in the dark, one arm over his face. City light and rain on the window. Camera slow drift from above.",
    BASE + COLD + "A Caucasian Western European man sitting in a dark garage or workshop, on a step or crate, elbows on knees, looking at the floor. Single overhead light. Camera slow push.",
    BASE + COLD + "Close-up of a Caucasian Western European man's hands on a dark kitchen table, turning a phone face-down, then stillness. Camera holds. 2am light. Heavy quiet.",
]

PROBLEM_FEMALE = [
    BASE + COLD + "A Caucasian Western European woman sitting on the edge of a bed in a dark bedroom at night, knees pulled to her chest, staring at the wall. Dim lamp the only light. Slow camera drift.",
    BASE + COLD + "A Caucasian Western European woman sitting alone at a kitchen table at night, hands around a mug, shoulders slightly rounded. Rain on the window behind her. Camera very slowly circles.",
    BASE + COLD + "A Caucasian Western European woman sitting in a parked car at night, hands in her lap, staring forward. Streetlights on the windscreen. Camera slow push from back seat.",
    BASE + COLD + "A Caucasian Western European woman standing at a bathroom mirror looking down at the sink, dim warm light, hair loose. Camera slow downward tilt. Hands on the basin edge.",
    BASE + COLD + "A Caucasian Western European woman sitting on a staircase in low light, knees drawn up, chin on her arms, shadows across her face. Slow downward drift.",
    BASE + COLD + "A Caucasian Western European woman curled on a sofa in a dark living room, phone face-down beside her. Rain and city lights on the window. Camera slowly pulling back.",
    BASE + COLD + "A Caucasian Western European woman lying fully clothed on a bed, staring at the ceiling in a dark room. Arms at her sides. Camera very slow pull back from above.",
    BASE + COLD + "A Caucasian Western European woman sitting on the floor with her back against a sofa in a dark room, knees up, arms wrapped around them. Single lamp far away. Slow push.",
    BASE + COLD + "A Caucasian Western European woman standing in a dark kitchen at night, leaning against the counter, arms crossed, staring at the floor. Faint outside light. Slow push toward her.",
    BASE + COLD + "A Caucasian Western European woman sitting at a desk late at night, chair pulled back, staring at a dark screen. Single desk lamp. Slow sideways drift.",
    BASE + COLD + "A Caucasian Western European woman standing at a rain-streaked window at night, arms crossed, looking out at city lights. Interior almost dark. Slow zoom toward her back.",
    BASE + COLD + "A Caucasian Western European woman lying on a sofa in the dark, one arm resting over her eyes. Rain on the window. Slow camera drift from above.",
    BASE + COLD + "A Caucasian Western European woman sitting in a dark living room, legs tucked under her, hugging a cushion, staring forward. City light through curtains. Slow pull back.",
    BASE + COLD + "Close-up of a Caucasian Western European woman's hands turning a phone face-down on a kitchen table at night, then stillness. Camera holds. Heavy quiet. 2am light.",
    BASE + COLD + "A Caucasian Western European woman standing in a dark hallway, one hand on the wall, head slightly bowed. Single far light. Slow push toward her.",
]

# ---------------------------------------------------------------------------
# STORY scenes -- 10 variations each (emotional transition, slight warmth)
# ---------------------------------------------------------------------------
STORY_MALE = [
    BASE + WARM_HINT + "A Caucasian Western European man sitting at a window, soft diffused grey morning light beginning to show, less oppressive than before. Looking out, expression slightly open. Slow gentle camera drift.",
    BASE + WARM_HINT + "A Caucasian Western European man standing at a kitchen window, hands around a mug, looking out at early morning light. Not bright, just less dark. Contemplative. Slow push toward him from behind.",
    BASE + WARM_HINT + "A Caucasian Western European man sitting on the edge of a bed, head slightly raised now compared to before, looking toward a window with diffused light. Slow sideways drift.",
    BASE + WARM_HINT + "A Caucasian Western European man's hands slowly relaxing -- unclenching from a mug on a table, fingers opening. Extreme close-up. Dim but slightly warmer light. Camera holds still.",
    BASE + WARM_HINT + "A Caucasian Western European man leaning against a wall in a hallway, but now looking forward rather than down. A door ahead with soft light through the crack. Slow push toward the door.",
    BASE + WARM_HINT + "A Caucasian Western European man sitting in a parked car, now looking out the side window at predawn grey sky rather than staring forward. Slight warmth. Slow drift.",
    BASE + WARM_HINT + "A Caucasian Western European man in a dark room, a thin line of grey dawn light appearing under the curtains. He sits still, but something has shifted. Slow drift toward the light.",
    BASE + WARM_HINT + "Close-up of a Caucasian Western European man's face, eyes slightly more open now, looking sideways toward a soft light source off camera. Expression beginning to settle. Slow drift.",
    BASE + WARM_HINT + "A Caucasian Western European man sitting on a staircase now looking up rather than down, soft light from above. Contemplative. Slow upward camera drift.",
    BASE + WARM_HINT + "A Caucasian Western European man's silhouette at a window, grey early morning outside. He places one hand on the glass. Still, but present. Slow zoom out.",
]

STORY_FEMALE = [
    BASE + WARM_HINT + "A Caucasian Western European woman sitting at a window, soft diffused grey morning light, looking out. Less oppressive than before. Slow gentle camera drift.",
    BASE + WARM_HINT + "A Caucasian Western European woman standing at a kitchen window, hands around a mug, looking at early morning grey light outside. Contemplative stillness. Slow push from behind.",
    BASE + WARM_HINT + "A Caucasian Western European woman sitting on the edge of a bed, head slightly raised, looking toward a window with diffused light. Slow sideways drift.",
    BASE + WARM_HINT + "Close-up of a Caucasian Western European woman's hands slowly loosening their grip on a mug -- fingers relaxing open. Slightly warmer dim light. Camera holds still.",
    BASE + WARM_HINT + "A Caucasian Western European woman in a dark hallway, now looking forward toward a door with soft light through the crack. Slow push toward the door.",
    BASE + WARM_HINT + "A Caucasian Western European woman in a parked car, now looking out the side window at predawn grey sky. Slight warmth. Slow drift.",
    BASE + WARM_HINT + "A Caucasian Western European woman in a dark room, a thin line of grey dawn light under the curtains. Sitting still, but something has shifted. Slow drift toward the light.",
    BASE + WARM_HINT + "Close-up of a Caucasian Western European woman's face, eyes slightly more open, looking sideways toward a soft light off camera. Expression beginning to settle. Slow drift.",
    BASE + WARM_HINT + "A Caucasian Western European woman on a staircase now looking upward rather than down, soft light from above. Contemplative. Slow upward camera drift.",
    BASE + WARM_HINT + "Silhouette of a Caucasian Western European woman at a window, grey early morning outside. She places one hand on the glass. Still, but present. Slow zoom out.",
]

# ---------------------------------------------------------------------------
# SOLUTION / CTA scenes -- 10 variations each (warm, resolved, hopeful)
# ---------------------------------------------------------------------------
CTA_MALE = [
    BASE + WARM_FULL + "A Caucasian Western European man sitting by a window, soft golden morning light washing over him. Eyes closed, face relaxed. Gentle slow camera drift. Quiet resolution.",
    BASE + WARM_FULL + "A Caucasian Western European man standing in a warm kitchen in early morning light, hands around a mug, looking out the window calmly. Amber light fills the space. Slow push.",
    BASE + WARM_FULL + "A Caucasian Western European man lying on his back in bed, dawn light slowly crossing the ceiling above him. Arms relaxed. Camera very slow pull back. Still but present.",
    BASE + WARM_FULL + "A Caucasian Western European man sitting at a wooden table in warm morning light, both hands flat on the surface, breathing. Soft amber. Camera holds gently still.",
    BASE + WARM_FULL + "A Caucasian Western European man walking slowly to a window in morning light, placing one hand on the glass, looking out calmly. Warm golden grade. Slow push from behind.",
    BASE + WARM_FULL + "Close-up of a Caucasian Western European man's hands around a mug, warm amber light, steam rising gently. Camera very slow zoom out. A moment of stillness and warmth.",
    BASE + WARM_FULL + "A Caucasian Western European man sitting on a staircase, now fully in warm morning light from above. Looking upward, calm expression. Slow upward drift.",
    BASE + WARM_FULL + "A Caucasian Western European man opening a curtain slightly, soft golden light pouring in. He stands still and lets it land on his face. Slow push toward him.",
    BASE + WARM_FULL + "A Caucasian Western European man sitting in a warm lit room, phone on the table in front of him, his hands resting near it. Calm, decided. Warm amber. Slow drift.",
    BASE + WARM_FULL + "A Caucasian Western European man from behind, standing at a window in full warm morning light, city quiet outside. One hand on the frame. Slow zoom out. Resolved.",
]

CTA_FEMALE = [
    BASE + WARM_FULL + "A Caucasian Western European woman sitting by a window in soft golden morning light, face relaxed, eyes closed. Gentle slow camera drift. Quiet resolution.",
    BASE + WARM_FULL + "A Caucasian Western European woman standing in a warm kitchen in early morning light, hands around a mug, looking out the window calmly. Amber light. Slow push.",
    BASE + WARM_FULL + "A Caucasian Western European woman lying on her back in bed, dawn light crossing the ceiling. Arms relaxed at her sides. Camera very slow pull back. Present and still.",
    BASE + WARM_FULL + "A Caucasian Western European woman sitting at a wooden table in warm morning light, both hands flat on the surface, breathing. Soft amber grade. Camera gently still.",
    BASE + WARM_FULL + "A Caucasian Western European woman walking slowly to a window in morning light, placing one hand on the glass, looking out calmly. Warm golden grade. Slow push from behind.",
    BASE + WARM_FULL + "Close-up of a Caucasian Western European woman's hands around a warm mug, amber light, steam rising gently. Very slow zoom out. Stillness and warmth.",
    BASE + WARM_FULL + "A Caucasian Western European woman sitting in warm morning light, hair loose, face turned gently toward the window. Soft bokeh. Slow drift.",
    BASE + WARM_FULL + "A Caucasian Western European woman opening a curtain, soft golden light pouring in. She stands still and lets it land on her face. Slow push toward her.",
    BASE + WARM_FULL + "A Caucasian Western European woman sitting in a warm lit room, phone on the table in front of her, hands resting near it. Calm, decided. Warm amber. Slow drift.",
    BASE + WARM_FULL + "A Caucasian Western European woman from behind, standing at a window in full warm morning light. One hand on the frame. Slow zoom out. Quietly resolved.",
]

# ---------------------------------------------------------------------------
# Index trackers -- randomised per run, increment per clip
# ---------------------------------------------------------------------------
_hook_index    = random.randint(0, 11)
_problem_index = random.randint(0, 14)
_story_index   = random.randint(0, 9)
_cta_index     = random.randint(0, 9)


def generate_scene_clip_fal(
    scene_name: str,
    voiceover: str,
    output_path: str,
    fal_key: str,
    gender: str = "person",
):
    """Generate a scene clip via fal.ai Wan 2.5.
    Rotates through full scene libraries for visual variety.
    Caucasian Western European subjects enforced throughout.
    Returns output_path on success, None on failure.
    """
    global _hook_index, _problem_index, _story_index, _cta_index

    if not fal_key:
        return None

    try:
        import fal_client

        is_male = (gender == "man")
        vo      = voiceover[:80] if voiceover else "emotional raw authentic"

        if scene_name == "hook":
            pool  = HOOK_MALE if is_male else HOOK_FEMALE
            prompt = pool[_hook_index % len(pool)] + f" Emotional atmosphere: {vo}"
            _hook_index += 1

        elif scene_name == "problem":
            pool  = PROBLEM_MALE if is_male else PROBLEM_FEMALE
            prompt = pool[_problem_index % len(pool)] + f" Emotional atmosphere: {vo}"
            _problem_index += 1

        elif scene_name == "story":
            pool  = STORY_MALE if is_male else STORY_FEMALE
            prompt = pool[_story_index % len(pool)] + f" Emotional atmosphere: {vo}"
            _story_index += 1

        else:  # solution_cta
            pool  = CTA_MALE if is_male else CTA_FEMALE
            prompt = pool[_cta_index % len(pool)] + f" Emotional atmosphere: {vo}"
            _cta_index += 1

        result = fal_client.subscribe(
            FAL_MODEL,
            arguments={
                "prompt":          prompt,
                "negative_prompt": NEGATIVE_PROMPT,
                "resolution":      "480p",
                "aspect_ratio":    "9:16",
                "duration":        5,
            },
        )
        video_url = result["video"]["url"]
        resp = requests.get(video_url, timeout=120)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        size_kb = Path(output_path).stat().st_size / 1024
        print(f"  fal.ai: {scene_name.upper()} clip ready ({size_kb:.0f} KB)")
        return output_path

    except Exception as e:
        print(f"  fal.ai {scene_name} failed ({e})")
        return None
