"""
MindCore AI -- fal.ai Hook Clip Generator
=========================================
Generates AI hook clips via fal.ai Wan 2.5.
Safe prompt: no wounds, no trauma imagery, no policy risk.
Falls back silently if FAL_KEY not set or generation fails.
Cost: ~$0.25 per 5-second hook clip.
"""

from pathlib import Path
import requests

FAL_MODEL = "fal-ai/wan-25-preview/text-to-video"


def generate_hook_clip_fal(hook_voiceover: str, niche_name: str, output_path: str, fal_key: str) -> str | None:
    """Generate an AI hook clip. Returns output_path on success, None on failure."""
    if not fal_key:
        return None
    try:
        import fal_client

        prompt = (
            "Cinematic close-up portrait for mental wellness content. "
            "A person showing authentic raw emotion -- tired, numb, heavy, disconnected. "
            "Dark moody interior, single soft ambient light source, shallow depth of field. "
            "Subtle slow camera movement, natural film grain, photorealistic. "
            "Desaturated cold colour grade, atmospheric and intimate. "
            "NO injuries, NO wounds, NO scars, NO blood, NO medical equipment. "
            "NO bright scenes, NO cheerful settings, NO outdoor sunny footage. "
            "9:16 vertical portrait format. "
            f"Emotional atmosphere: {hook_voiceover[:100]}"
        )
        negative_prompt = (
            "wounds, injuries, scars, blood, medical, needles, syringes, "
            "war, violence, self-harm, bright, cheerful, sunny, smiling, "
            "outdoor, beach, text, watermark, logo, anime, cartoon, CGI"
        )

        print(f"  fal.ai: Generating hook clip (Wan 2.5, ~$0.25)...")

        result = fal_client.subscribe(
            FAL_MODEL,
            arguments={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
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
        print(f"  fal.ai: Hook clip ready ({size_kb:.0f} KB) | AI generated")
        return output_path

    except Exception as e:
        print(f"  fal.ai hook failed ({e}) -- falling back to Pexels")
        return None
