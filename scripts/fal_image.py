"""
fal.ai Flux Schnell image generation helper.
Replaces OpenAI gpt-image-1 in the carousel pipeline.
Cost: ~$0.003/image vs ~$0.02-0.19/image on OpenAI.
"""
import os, requests, time

FAL_API_KEY = os.environ.get("FAL_KEY", "")
FAL_BASE_URL = "https://queue.fal.run"
FAL_MODEL = "fal-ai/flux/schnell"


def generate_fal_image(prompt, image_size="portrait_4_3", num_inference_steps=4):
    """Generate an image with fal.ai Flux Schnell. Returns image bytes."""
    if not FAL_API_KEY:
        raise RuntimeError("FAL_KEY not set")

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

    resp = requests.post(
        f"{FAL_BASE_URL}/{FAL_MODEL}",
        headers=headers, json=payload, timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if "images" in result:
        image_url = result["images"][0]["url"]
    elif "request_id" in result:
        req_id = result["request_id"]
        poll_url = f"{FAL_BASE_URL}/{FAL_MODEL}/requests/{req_id}"
        for _ in range(60):
            time.sleep(2)
            poll_resp = requests.get(poll_url, headers=headers, timeout=30)
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()
            status = poll_data.get("status", "")
            if status == "COMPLETED":
                image_url = poll_data["output"]["images"][0]["url"]
                break
            elif status in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"fal.ai job {status}: {poll_data}")
        else:
            raise TimeoutError(f"fal.ai job {req_id} timed out")
    else:
        raise RuntimeError(f"Unexpected fal.ai response: {result}")

    img_resp = requests.get(image_url, timeout=60)
    img_resp.raise_for_status()
    return img_resp.content
