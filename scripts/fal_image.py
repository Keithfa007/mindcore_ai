"""
fal.ai image generation helper for MindCore AI pipelines.
Supports multiple Flux models for different quality/cost needs.

Models:
  - schnell: fastest, $0.003/image -- for TikTok carousels
  - dev: balanced, ~$0.025/image -- general use
  - pro: best quality, ~$0.05/image -- blog featured images, website
"""
import os, requests, time

FAL_API_KEY = os.environ.get("FAL_KEY", "")

MODELS = {
    "schnell": "fal-ai/flux/schnell",
    "dev": "fal-ai/flux/dev",
    "pro": "fal-ai/flux-pro/v1.1",
}


def generate_fal_image(prompt, image_size="portrait_4_3", model="schnell", num_inference_steps=None):
    """Generate an image with fal.ai Flux. Returns image bytes.

    Args:
        prompt: Text description of the image to generate.
        image_size: Preset size or dict with width/height.
            Presets: square_hd, square, portrait_4_3, portrait_16_9,
                     landscape_4_3, landscape_16_9
        model: "schnell" (fast/cheap), "dev" (balanced), "pro" (best quality).
        num_inference_steps: Override inference steps (default: 4 for schnell, 28 for dev/pro).
    """
    if not FAL_API_KEY:
        raise RuntimeError("FAL_KEY not set")

    model_id = MODELS.get(model, MODELS["schnell"])
    if num_inference_steps is None:
        num_inference_steps = 4 if model == "schnell" else 28

    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "image_size": image_size,
        "num_inference_steps": num_inference_steps,
        "num_images": 1,
        "enable_safety_checker": False,
        "output_format": "jpeg",
    }

    # Use synchronous endpoint (fal.run) -- returns result directly.
    # Schnell completes in <5s, pro in <30s, well within timeout.
    sync_url = f"https://fal.run/{model_id}"
    print(f"  [fal.ai] Model: {model} ({model_id}) | Size: {image_size}")
    resp = requests.post(sync_url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()

    if "images" in result and result["images"]:
        image_url = result["images"][0]["url"]
    else:
        raise RuntimeError(f"Unexpected fal.ai response (no images): {result}")

    img_resp = requests.get(image_url, timeout=60)
    img_resp.raise_for_status()
    print(f"  [fal.ai] Image ready ({len(img_resp.content) // 1024:.0f} KB)")
    return img_resp.content
