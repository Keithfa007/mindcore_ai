"""
MindCore AI -- fal.ai Scene Clip Generator v2.0
================================================
Generates all 5 scene clips via fal.ai Wan 2.5.
Scene-specific prompts ensure emotional arc: cold (hook/problem) to warm (story/cta).

v2.0:
  - Explicit Caucasian Western European subjects (prevents Asian default)
  - 6 rotating problem scene settings (no more same dark bedroom every video)
  - More varied shot types per scene for visual interest
  - Stronger hook close-ups and more engaging camera moves

Cost: ~$0.25 per 5-second clip at $0.05/sec.
"""

import random
from pathlib import Path
import requests

FAL_MODEL = "fal-ai/wan-25-preview/text-to-video"

NEGATIVE_PROMPT = (
    "Asian, East Asian, South Asian, Middle Eastern, African, "
    "wounds, injuries, scars, blood, medical, needles, syringes, "
    "war, violence, self-harm, bright sunlight, cheerful, sunny, smiling, "
    "outdoor daylight, beach, text, watermark, logo, anime, cartoon, CGI, "
    "busy crowd, distorted faces, blurry faces"
)

# ---------------------------------------------------------------------------
# Problem scene settings -- rotates to prevent every video looking identical
# ---------------------------------------------------------------------------
PROBLEM_SETTINGS_MALE = [
    (
        "A Caucasian Western European man sitting on the edge of a bed in a dark bedroom at night, "
        "head slightly bowed, hands resting on knees, dim bedside lamp the only light source."
    ),
    (
        "A Caucasian Western European man sitting alone at a dark kitchen table at 2am, "
        "hands wrapped around a mug, staring at nothing, city light barely visible through the window."
    ),
    (
        "A Caucasian Western European man sitting in the driver's seat of a parked car at night, "
        "engine off, hands on the wheel, staring forward into the dark, streetlight casting long shadows."
    ),
    (
        "A Caucasian Western European man standing at a bathroom sink, looking down, "
        "dim overhead light, hands gripping the edge of the counter, face just out of focus."
    ),
    (
        "A Caucasian Western European man leaning against a shadowed hallway wall, "
        "arms crossed, head tilted back slightly, single strip of light from a doorway."
    ),
    (
        "A Caucasian Western European man sitting on a sofa in a dark living room, "
        "curtains partly open, city lights and rain on the glass behind him, "
        "elbows on knees, face in his hands."
    ),
]

PROBLEM_SETTINGS_FEMALE = [
    (
        "A Caucasian Western European woman sitting on the edge of a bed in a dark bedroom at night, "
        "knees pulled to her chest, dim lamp the only light, staring at the wall."
    ),
    (
        "A Caucasian Western European woman sitting alone at a kitchen table at night, "
        "hands around a mug, shoulders slightly rounded, rain on the window behind her."
    ),
    (
        "A Caucasian Western European woman sitting in a parked car at night, "
        "hands in her lap, staring forward, streetlights reflecting on the windscreen, still."
    ),
    (
        "A Caucasian Western European woman standing at a bathroom mirror, looking down at the sink, "
        "dim warm light, hair loose, hands gripping the basin edge."
    ),
    (
        "A Caucasian Western European woman sitting on a staircase in low light, "
        "knees drawn up, chin resting on her arms, shadows across the lower half of her face."
    ),
    (
        "A Caucasian Western European woman curled on a sofa in a darkened living room, "
        "phone face-down beside her, city light and rain on the window, utterly still."
    ),
]

# ---------------------------------------------------------------------------
# Scene prompt templates
# ---------------------------------------------------------------------------
SCENE_PROMPTS = {
    "hook": (
        "Cinematic extreme close-up portrait for mental wellness short-form video. "
        "A Caucasian Western European {gender}'s face -- tired, emotionally heavy, raw. "
        "Dark moody interior, single soft ambient side light catching cheekbone, "
        "shallow depth of field, eyes downcast or barely open. "
        "Very slow subtle camera push into face. Natural film grain, photorealistic. "
        "Highly desaturated cold blue-grey colour grade. "
        "NO injuries, NO wounds, NO scars. 9:16 vertical portrait. "
        "Emotional atmosphere: {voiceover}"
    ),
    "problem": (
        "Cinematic portrait of emotional weight and isolation, mental wellness content. "
        "{setting} "
        "Heavy still atmosphere, slow subtle camera drift, cold desaturated grey-blue grade, "
        "film grain, photorealistic. "
        "NO injuries, NO wounds, NO medical imagery. NO bright outdoor scenes. "
        "9:16 vertical portrait. Emotional atmosphere: {voiceover}"
    ),
    "story": (
        "Cinematic interior shot of quiet emotional transition, mental wellness short-form video. "
        "A Caucasian Western European {gender} or intimate interior space beginning to shift. "
        "Soft diffused natural light through a window -- not bright, just less oppressive. "
        "Contemplative stillness, slow gentle camera drift. "
        "Neutral grade with very slight warmth beginning, film grain, photorealistic. "
        "NO injuries, NO wounds. 9:16 vertical portrait. "
        "Emotional atmosphere: {voiceover}"
    ),
    "solution_cta": (
        "Cinematic warm intimate interior, mental wellness short-form video. "
        "A Caucasian Western European {gender} in a quiet still moment of resolution -- "
        "seated by a window with soft golden morning light, or standing in a warm kitchen, "
        "or lying still with dawn light crossing the ceiling. "
        "Warm amber-gold grade, gentle slow camera movement, hopeful resolved atmosphere. "
        "Soft bokeh, film grain, photorealistic. "
        "NO injuries, NO wounds. 9:16 vertical portrait. "
        "Emotional atmosphere: {voiceover}"
    ),
}

# Track problem setting index across calls within a run
_problem_index = random.randint(0, 5)


def generate_scene_clip_fal(
    scene_name: str,
    voiceover: str,
    output_path: str,
    fal_key: str,
    gender: str = "person",
):
    """Generate a scene-specific clip via fal.ai Wan 2.5.
    Returns output_path on success, None on failure.

    v2.0: Caucasian European subjects + rotating problem settings.
    """
    global _problem_index

    if not fal_key:
        return None
    try:
        import fal_client

        template = SCENE_PROMPTS.get(scene_name, SCENE_PROMPTS["problem"])
        vo_snippet = voiceover[:80] if voiceover else "emotional raw authentic"

        if scene_name == "problem":
            # Rotate through the 6 problem settings for visual variety
            settings = PROBLEM_SETTINGS_MALE if gender == "man" else PROBLEM_SETTINGS_FEMALE
            setting = settings[_problem_index % len(settings)]
            _problem_index += 1
            prompt = template.format(
                setting=setting,
                voiceover=vo_snippet,
            )
        else:
            prompt = template.format(
                gender=gender,
                voiceover=vo_snippet,
            )

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
