#!/usr/bin/env python3
"""
MindCore AI -- RunPod Serverless Handler v1.1
=============================================
Receives a prompt, generates a 5-second Wan 2.1 video clip,
returns the clip as base64-encoded MP4.

v1.1: Robust imports, HF_TOKEN support, better error handling.
"""
import os, sys, base64

os.environ["HF_HOME"] = "/workspace/.cache/huggingface"
os.environ["TMPDIR"] = "/workspace/tmp"
os.makedirs("/workspace/tmp", exist_ok=True)

import runpod

pipe = None


def load_model():
    """Load Wan 2.1 T2V 1.3B model. Downloads on first call."""
    global pipe
    import torch
    from diffusers import AutoModel, WanPipeline

    print("Loading Wan 2.1 T2V 1.3B...")
    sys.stdout.flush()

    vae = AutoModel.from_pretrained(
        "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        subfolder="vae",
        torch_dtype=torch.float32,
        cache_dir="/workspace/.cache/huggingface",
    )
    pipe = WanPipeline.from_pretrained(
        "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        vae=vae,
        torch_dtype=torch.bfloat16,
        cache_dir="/workspace/.cache/huggingface",
    )
    pipe.enable_model_cpu_offload()
    print("Model loaded successfully.")
    sys.stdout.flush()


def handler(event):
    """Handle a video generation request."""
    global pipe

    try:
        if pipe is None:
            load_model()

        from diffusers.utils import export_to_video

        inp = event.get("input", {})
        prompt = inp.get("prompt", "Cinematic aerial drone shot of ocean waves at sunset")
        num_frames = inp.get("num_frames", 81)
        height = inp.get("height", 832)
        width = inp.get("width", 480)
        guidance = inp.get("guidance_scale", 7.5)
        fps = inp.get("fps", 16)

        print(f"Generating: {prompt[:80]}...")
        sys.stdout.flush()

        import torch
        output = pipe(
            prompt=prompt,
            num_frames=num_frames,
            guidance_scale=guidance,
            height=height,
            width=width,
        ).frames[0]

        path = "/workspace/tmp/output.mp4"
        export_to_video(output, path, fps=fps)

        with open(path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode()

        size_kb = os.path.getsize(path) / 1024
        print(f"Done: {size_kb:.0f} KB")
        sys.stdout.flush()

        return {"video_base64": video_b64, "size_kb": round(size_kb)}

    except Exception as e:
        print(f"Handler error: {e}")
        sys.stdout.flush()
        return {"error": str(e)}


print("MindCore AI RunPod Handler v1.1 starting...")
sys.stdout.flush()
runpod.serverless.start({"handler": handler})
