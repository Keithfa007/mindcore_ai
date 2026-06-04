"""
MindCore AI -- fal.ai Scene Clip Generator
==========================================
Generates all 5 video clips via fal.ai Wan 2.5.
Each scene gets a different emotionally calibrated prompt:
  hook         -- cold, raw, close-up, tired/numb
  problem      -- cold, isolation, weight, empty interior
  story        -- transitional, neutral-to-warm, quiet shift
  solution_cta -- warm, amber, resolved, peaceful

Cost: ~$0.25 per 5-second clip (Wan 2.5 at $0.05/sec).
Full video (5 clips): ~$1.25 per video.
"""

import requests
from pathlib import Path

FAL_MODEL = "fal-ai/wan-25-preview/text-to-video"

NEGATIVE_PROMPT = (
    "wounds, injuries, scars, blood, medical equipment, needles, syringes, "
    "war, violence, self-harm, abuse, text, watermark, logo, "
    "anime, cartoon, CGI, artificial, overly bright, cheerful, sunny beach"
)

SCENE_BASE_PROMPTS = {
    "hook": (
        "Cinematic close-up portrait for mental wellness content. "
        "A {gender} showing raw authentic emotion -- tired, numb, heavy, disconnected. "
        "Dark moody interior, single soft ambient light source, very shallow depth of field. "
        "Slow subtle camera movement, natural film grain, photorealistic. "
        "Desaturated cold blue-grey colour grade, atmospheric. "
        "NO injuries, NO wounds, NO scars. NO bright cheerful scenes. "
        "9:16 vertical portrait format. "
    ),
    "problem": (
        "Cinematic interior scene showing isolation and emotional weight for mental wellness content. "
        "A {gender} alone in a dim space -- dark bedroom, shadowed room, window at night. "
        "Heavy still atmosphere, single ambient light, slow camera movement. "
        "Cold desaturated colour grade, film grain, photorealistic. "
        "NO injuries, NO wounds, NO medical imagery. NO bright outdoor scenes. "
        "9:16 vertical portrait format. "
    ),
    "story": (
        "Cinematic interior shot showing quiet emotional transition for mental wellness content. "
        "A {gender} or space beginning to shift -- slightly warmer ambient light, "
        "soft illumination, a window with gentle light, contemplative stillness. "
        "Neutral to slightly warm colour grade, slow gentle camera movement. "
        "Photorealistic, intimate. NO injuries, NO wounds. "
        "9:16 vertical portrait format. "
    ),
    "solution_cta": (
        "Cinematic warm interior or soft golden light scene for mental wellness content. "
        "A {gender} in a peaceful still moment, or warm amber light through curtains or a window. "
        "Soft warm amber colour grade, gentle slow camera movement, hopeful resolved atmosphere. "
        "Intimate, photorealistic. NO injuries, NO wounds. "
        "9:16 vertical portrait format. "
    ),
}


def generate_scene_clip_fal(
    scene_name: str,
    voiceover: str,
    output_path: str,
    fal_key: str,
    gender: str = "person",
) -> str | None:
    """
    Generate a scene-specific video clip via fal.ai Wan 2.5.
    Returns output_path on success, None on failure.

    Args:
        scene_name: one of hook, problem, story, solution_cta
        voiceover: the voiceover text for this scene (for prompt context)
        output_path: where to save the downloaded MP4
        fal_key: fal.ai API key
        gender: 'man', 'woman', or 'person'
    """
    if not fal_key:
        return None
    try:
        import fal_client

        base = SCENE_BASE_PROMPTS.get(scene_name, SCENE_BASE_PROMPTS["problem"])
        prompt = base.format(gender=gender)
        prompt += f"Emotional context: {voiceover[:100]}"

        print(f"  fal.ai [{scene_name.upper()}]: generating clip (~$0.25)...")

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
        print(f"  fal.ai [{scene_name.upper()}]: ready ({size_kb:.0f} KB)")
        return output_path

    except Exception as e:
        print(f"  fal.ai [{scene_name.upper()}] failed: {e}")
        return None
