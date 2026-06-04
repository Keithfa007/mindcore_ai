"""
MindCore AI -- fal.ai Scene Clip Generator
==========================================
Generates all 5 scene clips via fal.ai Wan 2.5.
Scene-specific prompts ensure emotional arc: cold (hook/problem) to warm (story/cta).
Safe prompts: no wounds, no trauma imagery, no TikTok policy risk.
Cost: ~$0.25 per 5-second clip at $0.05/sec.
"""

from pathlib import Path
import requests

FAL_MODEL = "fal-ai/wan-25-preview/text-to-video"

NEGATIVE_PROMPT = (
    "wounds, injuries, scars, blood, medical, needles, syringes, "
    "war, violence, self-harm, bright sunlight, cheerful, sunny, smiling, "
    "outdoor daylight, beach, text, watermark, logo, anime, cartoon, CGI, "
    "busy crowd, distorted faces"
)

SCENE_PROMPTS = {
    "hook": (
        "Cinematic extreme close-up portrait for mental wellness content. "
        "A {gender}'s face or hands showing raw authentic emotion -- tired, numb, heavy, disconnected. "
        "Dark moody interior, single soft ambient side light, shallow depth of field. "
        "Very subtle slow camera push, natural film grain, photorealistic. "
        "Highly desaturated cold blue-grey colour grade. "
        "NO injuries, NO wounds, NO scars. NO bright scenes. 9:16 vertical portrait. "
        "Emotional atmosphere: {voiceover}"
    ),
    "problem": (
        "Cinematic portrait of emotional isolation and weight. "
        "A {gender} alone in a dark interior -- dim bedroom, empty room, dark hallway, shadowed corner. "
        "Heavy still atmosphere, single dim ambient light source, slow subtle camera drift. "
        "Cold desaturated grey-blue grade, film grain, photorealistic. "
        "NO injuries, NO wounds, NO medical imagery. NO bright outdoor scenes. "
        "9:16 vertical portrait. Emotional atmosphere: {voiceover}"
    ),
    "story": (
        "Cinematic interior shot of quiet emotional transition. "
        "A {gender} or intimate space beginning to shift -- a window with soft diffused natural light, "
        "less oppressive than before, contemplative stillness. Slow gentle camera movement. "
        "Neutral grade with very slight warmth beginning to emerge, film grain, photorealistic. "
        "NO injuries, NO wounds. 9:16 vertical portrait. "
        "Emotional atmosphere: {voiceover}"
    ),
    "solution_cta": (
        "Cinematic warm intimate interior scene. "
        "Soft golden amber light through a window, or dawn light filling a quiet room. "
        "A {gender} in a quiet peaceful still moment, or empty intimate space bathed in warm light. "
        "Warm amber-gold grade, gentle slow camera movement, hopeful resolved atmosphere. "
        "Soft bokeh, film grain, photorealistic. "
        "NO injuries, NO wounds. 9:16 vertical portrait. "
        "Emotional atmosphere: {voiceover}"
    ),
}


def generate_scene_clip_fal(
    scene_name: str,
    voiceover: str,
    output_path: str,
    fal_key: str,
    gender: str = "person",
):
    """Generate a scene-specific clip via fal.ai Wan 2.5.
    Returns output_path on success, None on failure."""
    if not fal_key:
        return None
    try:
        import fal_client
        template = SCENE_PROMPTS.get(scene_name, SCENE_PROMPTS["problem"])
        prompt = template.format(
            gender=gender,
            voiceover=voiceover[:80] if voiceover else "emotional raw authentic"
        )
        result = fal_client.subscribe(
            FAL_MODEL,
            arguments={
                "prompt": prompt,
                "negative_prompt": NEGATIVE_PROMPT,
                "resolution": "480p",
                "aspect_ratio": "9:16",
                "duration": 5,
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
